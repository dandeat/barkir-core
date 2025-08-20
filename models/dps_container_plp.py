# -*- coding: utf-8 -*-
import html
import logging
from datetime import datetime
from xml.dom import minidom

import requests
from requests.exceptions import RequestException

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .utils import ctanggal_polos

_logger = logging.getLogger(__name__)

# Constants for better readability and maintenance
KODE_MASTER_KANTOR = 1
KODE_MASTER_GUDANG = 5
KODE_MASTER_ALASAN_PLP = 18
KODE_MASTER_UKURAN_CONTAINER = 14


class DpsPlpContainer(models.Model):
    """
    Manages the Pindah Lokasi Penimbunan (PLP) process for containers.
    This model handles the creation of PLP requests, communication with the
    Beacukai TPS Online service, and processing of responses.
    """
    _name = 'dps.container.plp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PLP Container'
    _order = 'create_date desc'

    # === Fields Definition ===
    name = fields.Char(
        string='Reference Number', required=True, copy=False,
        readonly=True, default=lambda self: _('New'), tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ready', 'Ready to Send'),
            ('kirim', 'Sent'),
            ('completed', 'Completed'),
            ('reject', 'Rejected'),
        ], string='Status', default='draft', tracking=True, copy=False)

    # Relational Fields
    shipment_id = fields.Many2one(
        'dps.shipment', string='Shipment', ondelete='cascade', copy=True, tracking=True)
    container_id = fields.Many2one(
        'dps.container', string='Container', ondelete='cascade', copy=True, tracking=True)
    kode_alasan_plp_id = fields.Many2one(
        'dps.reference', string='Alasan PLP',
        required=True,
        domain=lambda self: [('kode_master', '=', KODE_MASTER_ALASAN_PLP)],
        default=lambda self: self._get_default_reference('kode_alasan_plp', KODE_MASTER_ALASAN_PLP),
        tracking=True)
    ukuran_container_id = fields.Many2one(
        'dps.reference', string='Ukuran Container',
        domain=lambda self: [('kode_master', '=', KODE_MASTER_UKURAN_CONTAINER)],
        tracking=True)

    # Document & Reference Fields
    no_surat = fields.Char(string='Nomor Surat', tracking=True, copy=False)
    tanggal_surat = fields.Date(
        string='Tanggal Surat', default=fields.Date.context_today, tracking=True)
    no_bc11 = fields.Char(string='No BC 1.1', tracking=True)
    tgl_bc11 = fields.Date(string='Tanggal BC 1.1', tracking=True)
    no_plp = fields.Char(string='No PLP', readonly=True, tracking=True, copy=False)
    tanggal_plp = fields.Date(string='Tanggal PLP', readonly=True, tracking=True, copy=False)

    # TPS & Gudang Information
    kode_kantor = fields.Char(
        string='Kode Kantor', required=True,
        default=lambda self: self._get_default_company_value('kode_kantor'), tracking=True)
    tps_asal = fields.Char(
        string='TPS Asal', required=True,
        default=lambda self: self._get_default_company_value('kode_tps_asal'), tracking=True)
    gudang_asal = fields.Char(
        string='Gudang Asal', required=True,
        default=lambda self: self._get_default_company_value('gudang_asal'), tracking=True)
    tps_tujuan = fields.Char(
        string='TPS Tujuan', required=True,
        default=lambda self: self._get_default_company_value('kode_tps_tuju'), tracking=True)
    gudang_tujuan = fields.Char(
        string='Gudang Tujuan', required=True,
        default=lambda self: self._get_default_company_value('gudang_tuju'), tracking=True)

    # Shipment & Transport Details
    nama_pengangkut = fields.Char(string='Nama Pengangkut', tracking=True)
    no_voy_flight = fields.Char(string='No Voy/Flight', tracking=True)
    call_sign = fields.Char(string='Call Sign', tracking=True)
    arrival_date = fields.Date(string='Tgl Kedatangan', tracking=True)
    no_pos = fields.Char(string='No Pos', tracking=True)
    no_container = fields.Char(string='No Container', tracking=True)

    # Other Fields
    tipe_data = fields.Selection(
        [("1", "Baru"), ("2", "Manual")], string='Tipe Data', default="1", tracking=True)
    nama_pemohon = fields.Char(
        string='Nama Pemohon', required=True,
        default=lambda self: self._get_default_company_value('nama_pemohon'), tracking=True)
    ket_reject = fields.Text(string='Keterangan Reject', readonly=True, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Reference Number must be unique.')
    ]

    # === Default Methods ===
    @api.model
    def _get_default_company_value(self, field_name):
        """Generic method to get a default value from company settings."""
        value = self.env.company[field_name]
        if not value:
            raise UserError(_(
                "Default value for '%s' is not set in the company settings.",
                field_name
            ))
        return value

    @api.model
    def _get_default_reference(self, config_field, kode_master):
        """Generic method to get a default dps.reference record."""
        ref_code = self._get_default_company_value(config_field)
        reference = self.env['dps.reference'].search([
            ('name', '=', ref_code),
            ('kode_master', '=', kode_master)
        ], limit=1)
        if not reference:
            raise UserError(_(
                "Reference data for '%s' with code '%s' not found.",
                config_field, ref_code
            ))
        return reference.id

    # === CRUD Methods ===
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dps.container.plp') or _('New')
            if not vals.get('no_surat'):
                vals['no_surat'] = self._get_nomor_plp()
        return super().create(vals_list)

    def copy(self, default=None):
        raise UserError(_('Duplicating a PLP Container record is not allowed.'))

    # === Action Methods ===
    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_set_ready(self):
        self.write({'state': 'ready'})

    def action_send_plp(self):
        self.ensure_one()
        if self.state != 'ready':
            raise UserError(_("Only records in 'Ready to Send' state can be sent."))
        try:
            response = self._send_plp_request()
            if any(keyword in response for keyword in ['BERHASIL', 'Berhasil', 'berhasil', '018', '017']):
                self.state = 'kirim'
                self.message_post(body=_("PLP request sent successfully."))
            else:
                raise UserError(_('PLP submission failed: %s') % response)
        except (RequestException, UserError) as e:
            self.message_post(body=_("Failed to send PLP request: %s") % e)
            raise

    def action_get_response(self):
        self.ensure_one()
        if self.state != 'kirim':
            raise UserError(_("You can only get a response for 'Sent' records."))
        try:
            plp_response = self._get_plp_response_request()
            if not plp_response:
                raise UserError(_('Failed to get PLP response.'))
            self.message_post(body=_("Successfully fetched response: %s") % plp_response)
        except (RequestException, UserError) as e:
            self.message_post(body=_("Failed to get PLP response: %s") % e)
            raise

    def action_print_plp(self):
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_("You can only print a completed PLP document."))
        return self.env.ref('dps_cn_pibk.plp_report_qweb').report_action(self)

    # === Business Logic Methods ===
    @api.model
    def _get_nomor_plp(self):
        """Generate a sequential number for the PLP request."""
        total_plp = self.search_count([])
        bulan_romawi = ('', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII')
        now = datetime.now()
        seri = str(total_plp + 10).zfill(5)
        return f"{seri}/PLP/UTPK/{bulan_romawi[now.month]}/{now.year}"

    def _get_beacukai_config(self):
        """Centralized method to retrieve API credentials and URL."""
        get_param = self.env['ir.config_parameter'].sudo().get_param
        user_tps = get_param('beacukai.tpsonline.username')
        password_tps = get_param('beacukai.tpsonline.password')
        url = get_param('beacukai.tpsonline.url', "https://tpsonline.beacukai.go.id/tps/service.asmx")
        if not user_tps or not password_tps:
            raise UserError(_("TPS Online credentials are not configured in System Parameters."))
        return user_tps, password_tps, url

    def _build_plp_xml(self):
        """Builds the XML payload for the PLP submission."""
        self.ensure_one()
        return f"""<DOCUMENT xmlns="loadplp.xsd"><LOADPLP><HEADER>
            <KD_KANTOR>{self.kode_kantor or ''}</KD_KANTOR>
            <TIPE_DATA>{self.tipe_data or ''}</TIPE_DATA>
            <KD_TPS_ASAL>{self.tps_asal or ''}</KD_TPS_ASAL>
            <REF_NUMBER>{self.name or ''}</REF_NUMBER>
            <NO_SURAT>{self.no_surat or ''}</NO_SURAT>
            <TGL_SURAT>{ctanggal_polos(self.tanggal_surat) if self.tanggal_surat else ''}</TGL_SURAT>
            <GUDANG_ASAL>{self.gudang_asal or ''}</GUDANG_ASAL>
            <KD_TPS_TUJUAN>{self.tps_tujuan or ''}</KD_TPS_TUJUAN>
            <GUDANG_TUJUAN>{self.gudang_tujuan or ''}</GUDANG_TUJUAN>
            <KD_ALASAN_PLP>{self.kode_alasan_plp_id.name or ''}</KD_ALASAN_PLP>
            <YOR_ASAL>{self.yor_asal or ''}</YOR_ASAL>
            <YOR_TUJUAN>{self.yor_tujuan or ''}</YOR_TUJUAN>
            <CALL_SIGN>{self.call_sign or ''}</CALL_SIGN>
            <NM_ANGKUT>{self.nama_pengangkut or ''}</NM_ANGKUT>
            <NO_VOY_FLIGHT>{self.no_voy_flight or ''}</NO_VOY_FLIGHT>
            <TGL_TIBA>{ctanggal_polos(self.arrival_date) if self.arrival_date else ''}</TGL_TIBA>
            <NO_BC11>{self.no_bc11 or ''}</NO_BC11>
            <TGL_BC11>{ctanggal_polos(self.tgl_bc11) if self.tgl_bc11 else ''}</TGL_BC11>
            <NM_PEMOHON>{self.nama_pemohon or ''}</NM_PEMOHON>
            </HEADER><DETIL><CONT>
            <NO_CONT>{self.no_container or ''}</NO_CONT>
            <UK_CONT>{self.ukuran_container_id.name or ''}</UK_CONT>
            </CONT></DETIL></LOADPLP></DOCUMENT>"""

    def _send_plp_request(self):
        """Sends the PLP request to the Beacukai API."""
        self.ensure_one()
        user_tps, password_tps, url = self._get_beacukai_config()
        plp_xml = self._build_plp_xml()

        payload = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <PermohonanPLP xmlns="http://services.beacukai.go.id/">
                <fStream>{html.escape(plp_xml)}</fStream>
                <Username>{user_tps}</Username>
                <Password>{password_tps}</Password>
                </PermohonanPLP>
            </soap:Body></soap:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://services.beacukai.go.id/PermohonanPLP',
        }
        try:
            response = requests.post(url, headers=headers, data=payload.encode('utf-8'), timeout=15)
            response.raise_for_status()
            _logger.info("PLP Request for %s sent. Response: %s", self.name, response.text)
            parsed_xml = minidom.parseString(response.text)
            result_node = parsed_xml.getElementsByTagName('PermohonanPLPResult')
            return result_node[0].firstChild.nodeValue if result_node and result_node[0].firstChild else ''
        except RequestException as e:
            _logger.error("Error sending PLP request for %s: %s", self.name, e)
            raise UserError(_("Connection error during PLP request: %s") % e)

    def _parse_plp_response(self, response_xml):
        """Parses the XML response and updates the record state."""
        self.ensure_one()
        try:
            parsed_xml = minidom.parseString(html.unescape(response_xml))
            no_plp = parsed_xml.getElementsByTagName('NO_PLP')[0].firstChild.nodeValue
            tgl_plp = parsed_xml.getElementsByTagName('TGL_PLP')[0].firstChild.nodeValue
            fl_setuju = parsed_xml.getElementsByTagName('FL_SETUJU')[0].firstChild.nodeValue
            alasan_reject = parsed_xml.getElementsByTagName('ALASAN_REJECT')[0].firstChild.nodeValue

            vals = {'no_plp': no_plp, 'tanggal_plp': datetime.strptime(tgl_plp, '%Y%m%d').date()}
            is_rejected = fl_setuju == 'T' or not parsed_xml.getElementsByTagName('CONT')

            if is_rejected:
                vals.update({'state': 'reject', 'ket_reject': alasan_reject})
            else:
                vals['state'] = 'completed'
                if self.shipment_id:
                    self.shipment_id.write({'no_plp': no_plp, 'tgl_plp': vals['tanggal_plp']})
            self.write(vals)
            return "OK"
        except Exception as e:
            _logger.error("Failed to parse PLP response for %s: %s", self.name, e)
            self.message_post(body=_("Error parsing response: %s") % response_xml)
            return response_xml

    def _get_plp_response_request(self):
        """Fetches the PLP response from the Beacukai API."""
        self.ensure_one()
        user_tps, password_tps, url = self._get_beacukai_config()
        kode_tps = self.env.company.kode_tps

        payload = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <GetResponPlp_onDemands xmlns="http://services.beacukai.go.id/">
                <UserName>{user_tps}</UserName>
                <Password>{password_tps}</Password>
                <No_plp></No_plp><Tgl_plp></Tgl_plp>
                <KdGudang>{kode_tps or ''}</KdGudang>
                <RefNumber>{self.name}</RefNumber>
                </GetResponPlp_onDemands>
            </soap:Body></soap:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://services.beacukai.go.id/GetResponPlp_onDemands',
        }
        try:
            response = requests.post(url, headers=headers, data=payload.encode('utf-8'), timeout=15)
            response.raise_for_status()
            _logger.info("PLP Response for %s received. Response: %s", self.name, response.text)
            parsed_xml = minidom.parseString(response.text)
            result_node = parsed_xml.getElementsByTagName('GetResponPlp_onDemandsResult')
            if result_node and result_node[0].firstChild:
                return self._parse_plp_response(result_node[0].firstChild.nodeValue)
            return "Empty response from server."
        except RequestException as e:
            _logger.error("Error getting PLP response for %s: %s", self.name, e)
            raise UserError(_("Connection error while getting PLP response: %s") % e)

    # === Cron Job ===
    @api.model
    def _cron_get_plp_responses(self):
        """Cron job to automatically fetch responses for sent PLP requests."""
        plps_to_check = self.search([('state', '=', 'kirim')], limit=50)
        _logger.info("CRON: Checking PLP responses for %d records.", len(plps_to_check))
        for rec in plps_to_check:
            try:
                rec._get_plp_response_request()
                self.env.cr.commit()  # Commit after each successful record
            except Exception as e:
                self.env.cr.rollback() # Rollback on error for this record
                _logger.error("CRON: Failed to get PLP response for %s. Error: %s", rec.name, e)
