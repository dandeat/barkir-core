"""DPS Container Gate In Models

This module contains models for handling container gate-in operations
and COCO (Container Code) container management.
"""

import html
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom

import pytz
import requests
import xmltodict as xd

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning

from .utils import ctanggal_polos, ctanggalwaktu_polos, get_id

_logger = logging.getLogger(__name__)


class DpsCocoContainer(models.Model):
    """Header COCO Container Model
    
    This model handles the main container information for COCO operations
    including shipment details, document codes, and container status.
    """
    
    _name = 'dps.coco.container'
    _description = 'Header Coco Container'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _rec_name = 'name'

    def _get_default_tps(self) -> str:
        """Get default TPS code from current user's company."""
        return self.env.user.company_id.kode_tps or ''

    # Basic Information Fields
    name = fields.Char(
        string='REF Number',
        readonly=True,
        copy=False,
        help='Reference number generated automatically'
    )
    
    kd_dok_id = fields.Many2one(
        'dps.reference',
        string='Kode Dokumen',
        domain="[('kode_master', '=', 16)]",
        required=True,
        tracking=True,
        help='Document code reference'
    )
    
    kd_dok = fields.Integer(
        string='Document Code ID',
        compute='_compute_kd_dok',
        store=True,
        help='Computed document code ID'
    )

    # Shipment Related Fields
    shipment_id = fields.Many2one(
        'dps.shipment',
        string='Shipment',
        ondelete='cascade',
        required=True,
        help='Related shipment record'
    )
    
    no_container = fields.Char(
        string='Container Number',
        related="shipment_id.no_container",
        store=True,
        readonly=True,
        help='Container number from shipment'
    )

    # TPS and Transport Information
    kd_tps = fields.Char(
        string='Kode TPS',
        default=_get_default_tps,
        readonly=True,
        help='TPS (Terminal Petikemas) code'
    )
    
    nama_pengangkut = fields.Char(
        string='Nama Pengangkut',
        related="shipment_id.nama_pengangkut",
        readonly=True,
        help='Transporter name'
    )
    
    no_voy_flight = fields.Char(
        string='No Voy/Flight',
        related="shipment_id.no_voy_flight",
        readonly=True,
        help='Voyage or flight number'
    )
    
    call_sign = fields.Char(
        string='Call Sign',
        related="shipment_id.call_sign",
        readonly=True,
        help='Vessel call sign'
    )

    # Date and Warehouse Information
    tgl_tiba = fields.Date(
        string='Tanggal Tiba',
        related="shipment_id.arrival_date",
        readonly=True,
        help='Arrival date'
    )
    
    kd_gudang = fields.Char(
        string='Kode Gudang',
        default=_get_default_tps,
        readonly=True,
        help='Warehouse code'
    )

    # Detail Lines
    detail_ids = fields.One2many(
        comodel_name='dps.container.detail',
        inverse_name='coco_id',
        string='Container Details',
        copy=True,
        help='Container detail lines'
    )

    # Status and Response Information
    count_respon = fields.Integer(
        string='Response Count',
        default=0,
        help='Number of responses received'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('reject', 'Rejected'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True, help='Current status of the container')

    # SQL Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'REF Number must be unique!')
    ]

    @api.model_create_multi
    def create(self, vals_list: List[Dict[str, Any]]) -> 'DpsCocoContainer':
        """Create new COCO container records with auto-generated reference numbers."""
        records = super().create(vals_list)
        for record in records:
            if not record.name:
                sequence_code = 'coco.in'
                number = self.env['ir.sequence'].next_by_code(sequence_code) or ''
                record.name = number
        return records

    @api.depends('kd_dok_id')
    def _compute_kd_dok(self) -> None:
        """Compute document code ID from document reference."""
        for record in self:
            record.kd_dok = record.kd_dok_id.id if record.kd_dok_id else 0

    def action_set_draft(self) -> None:
        """Set container status to draft."""
        self.write({'state': 'draft'})

    def action_set_ready(self) -> None:
        """Set container status to ready."""
        self.write({'state': 'ready'})

    def create_coco_out(self) -> None:
        """Create COCO out records based on current container details."""
        for record in self:
            detail_lines = []
            
            for detail in record.detail_ids:
                gateout_time = record.shipment_id.gateout_time
                
                # Format dates safely
                tgl_dok_inout = None
                wk_inout = None
                tgl_segel_bc = None
                
                if gateout_time:
                    try:
                        dt = datetime.strptime(str(gateout_time), '%Y-%m-%d %H:%M:%S')
                        tgl_dok_inout = dt.strftime('%m/%d/%Y')
                        wk_inout = dt.strftime('%m/%d/%Y %H:%M:%S')
                        tgl_segel_bc = dt.strftime('%m/%d/%Y')
                    except (ValueError, TypeError) as e:
                        _logger.warning("Error formatting gateout_time: %s", e)

                detail_data = {
                    'ukuran_container': detail.ukuran_container.id,
                    'jenis_container': detail.jenis_container.id,
                    'kode_dokinout_id': 40,  # Fixed value for out operations
                    'no_dok_inout': '000000',
                    'tgl_dok_inout': tgl_dok_inout,
                    'no_pol': detail.no_pol,
                    'wk_inout': wk_inout,
                    'cont_kosong': True,
                    'no_segel_bc': detail.no_segel_bc,
                    'tgl_segel_bc': tgl_segel_bc,
                }
                detail_lines.append((0, 0, detail_data))

            # Get document code for out operation
            kd_dok_ref = self.env['dps.reference'].sudo().search([
                ('kode_master', '=', 16),
                ('name', '=', '6')
            ], limit=1)

            if not kd_dok_ref:
                raise UserError(_('Document code for out operation not found!'))

            coco_out_data = {
                'shipment_id': record.shipment_id.id,
                'kd_dok_id': kd_dok_ref.id,
                'detail_ids': detail_lines,
                'state': 'ready'
            }
            
            _logger.debug("Creating COCO out record: %s", coco_out_data)
            self.env['dps.coco.container'].create(coco_out_data)

    @api.model
    def cron_kirim_coco(self) -> None:
        """Cron job to send ready COCO containers."""
        ready_containers = self.search([('state', '=', 'ready')])
        
        for container in ready_containers:
            try:
                container.kirim_coco()
            except Exception as e:
                _logger.error("Error sending COCO for container %s: %s", container.name, e)
                container.write({'state': 'error'})
        
        _logger.info('COCO sending cron completed. Processed %s containers.', len(ready_containers))

    def kirim_coco(self) -> None:
        """Send COCO container data to external service."""
        self.ensure_one()
        
        company = self.env.user.company_id
        user_tps = company.user_tps
        password_tps = company.password_tps
        kode_tps = company.kode_tps

        if not all([user_tps, password_tps, kode_tps]):
            raise UserError(_('TPS credentials not configured in company settings!'))

        # Format arrival date
        tgl_tiba_formatted = ''
        if self.tgl_tiba:
            tgl_tiba_formatted = str(self.tgl_tiba).replace('-', '')

        # Build XML envelope
        xml_envelope_start = '<DOCUMENT xmlns="cococont.xsd"><COCOCONT>'
        xml_envelope_end = '</COCOCONT></DOCUMENT>'
        
        # Build header - using .format() for better Odoo compatibility
        xml_header = """
    <HEADER>
        <KD_DOK>{kd_dok}</KD_DOK>
        <KD_TPS>{kd_tps}</KD_TPS>
        <NM_ANGKUT>{nm_angkut}</NM_ANGKUT>
        <NO_VOY_FLIGHT>{no_voy_flight}</NO_VOY_FLIGHT>
        <CALL_SIGN>{call_sign}</CALL_SIGN>
        <TGL_TIBA>{tgl_tiba}</TGL_TIBA>
        <KD_GUDANG>{kd_gudang}</KD_GUDANG>
        <REF_NUMBER>{ref_number}</REF_NUMBER>
    </HEADER>
    """.format(
        kd_dok=self.kd_dok_id.name or "",
        kd_tps=self.kd_tps or "",
        nm_angkut=self.nama_pengangkut or "",
        no_voy_flight=self.no_voy_flight or "",
        call_sign=self.call_sign or "",
        tgl_tiba=tgl_tiba_formatted,
        kd_gudang=self.kd_tps or "",
        ref_number=self.name or ""
    )

        # Build details
        xml_details = self._build_xml_details()
        
        # Complete XML
        complete_xml = xml_envelope_start + xml_header + xml_details + xml_envelope_end
        
        _logger.debug("Sending COCO XML: %s", complete_xml)

        # Send to external service
        self._send_coco_request(complete_xml, user_tps, password_tps)

    def _build_xml_details(self) -> str:
        """Build XML details section for COCO container."""
        xml_details = ""
        
        for detail in self.detail_ids:
            fl_kosong = '1' if detail.cont_kosong else '2'
            
            # Using .format() for better Odoo compatibility
            xml_detail = """
            <DETIL>
                <CONT>
                    <NO_CONT>{no_container}</NO_CONT>
                    <UK_CONT>{ukuran_container}</UK_CONT>
                    <NO_SEGEL>{no_segel}</NO_SEGEL>
                    <JNS_CONT>{jenis_container}</JNS_CONT>
                    <NO_BL_AWB></NO_BL_AWB>
                    <TGL_BL_AWB></TGL_BL_AWB>
                    <NO_MASTER_BL_AWB>{no_master}</NO_MASTER_BL_AWB>
                    <TGL_MASTER_BL_AWB>{tgl_master}</TGL_MASTER_BL_AWB>
                    <ID_CONSIGNEE></ID_CONSIGNEE>
                    <CONSIGNEE></CONSIGNEE>
                    <BRUTO>{bruto}</BRUTO>
                    <NO_BC11>{no_bc11}</NO_BC11>
                    <TGL_BC11>{tgl_bc11}</TGL_BC11>
                    <NO_POS_BC11>{no_pos}</NO_POS_BC11>
                    <KD_TIMBUN></KD_TIMBUN>
                    <KD_DOK_INOUT>3</KD_DOK_INOUT>
                    <NO_DOK_INOUT>{no_dok_inout}</NO_DOK_INOUT>
                    <TGL_DOK_INOUT>{tgl_dok_inout}</TGL_DOK_INOUT>
                    <WK_INOUT>{wk_inout}</WK_INOUT>
                    <KD_SAR_ANGKUT_INOUT>{kode_pengangkut_id}</KD_SAR_ANGKUT_INOUT>
                    <NO_POL>{no_pol}</NO_POL>
                    <FL_CONT_KOSONG>{fl_kosong}</FL_CONT_KOSONG>
                    <ISO_CODE></ISO_CODE>
                    <PEL_MUAT></PEL_MUAT>
                    <PEL_TRANSIT></PEL_TRANSIT>
                    <PEL_BONGKAR></PEL_BONGKAR>
                    <GUDANG_TUJUAN>{gudang_tujuan_id}</GUDANG_TUJUAN>
                    <KODE_KANTOR>{kode_kantor_id}</KODE_KANTOR>
                    <NO_DAFTAR_PABEAN></NO_DAFTAR_PABEAN>
                    <TGL_DAFTAR_PABEAN ></TGL_DAFTAR_PABEAN>
                    <NO_SEGEL_BC>{no_segel_bc}</NO_SEGEL_BC>
                    <TGL_SEGEL_BC>{tgl_segel_bc}</TGL_SEGEL_BC>
                    <NO_IJIN_TPS>{no_ijin_tps}</NO_IJIN_TPS>
                    <TGL_IJIN_TPS>{tgl_ijin_tps}</TGL_IJIN_TPS>
                </CONT>
            </DETIL>
            """.format(
                no_container=detail.no_container or "",
                ukuran_container=detail.ukuran_container.name or "",
                no_segel=detail.no_segel or "",
                jenis_container=detail.jenis_container.name or "",
                no_master=detail.no_master or "",
                tgl_master=ctanggal_polos(detail.tgl_master) or "",
                bruto=detail.bruto or 0,
                no_bc11=detail.no_bc11 or "",
                tgl_bc11=ctanggal_polos(detail.tgl_bc11) or "",
                no_pos=detail.no_pos or "",
                no_dok_inout=detail.no_dok_inout or "",
                tgl_dok_inout=ctanggal_polos(detail.tgl_dok_inout) or "",
                wk_inout=ctanggalwaktu_polos(detail.wk_inout) or "",
                kode_pengangkut_id=detail.kode_pengangkut_id or "",
                no_pol=detail.no_pol or "",
                fl_kosong=fl_kosong,
                gudang_tujuan_id=detail.gudang_tujuan_id or "",
                kode_kantor_id=detail.kode_kantor_id.name or "",
                no_segel_bc=detail.no_segel_bc or "",
                tgl_segel_bc=ctanggal_polos(detail.tgl_segel_bc) or "",
                no_ijin_tps=detail.no_ijin_tps or "",
                tgl_ijin_tps=ctanggal_polos(detail.tgl_ijin_tps) or ""
            )
            xml_details += xml_detail
            
        return xml_details

    def _send_coco_request(self, xml_data: str, username: str, password: str) -> None:
        """Send COCO request to external service."""
        url = "https://tpsonline.beacukai.go.id/tps/service.asmx"
        
        # Using .format() for better Odoo compatibility
        soap_payload = """
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <CoarriCodeco_Container xmlns="http://services.beacukai.go.id/">
            <fStream>{}</fStream>
            <Username>{}</Username>
            <Password>{}</Password>
            </CoarriCodeco_Container>
        </soap:Body>
        </soap:Envelope>""".format(html.escape(xml_data), username, password)

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://services.beacukai.go.id/CoarriCodeco_Container',
            'Cookie': 'BIGipServerPOOL_DJBC_TPS_ONLINE_PUBLIK=958263562.47873.0000'
        }

        try:
            response = requests.post(url, headers=headers, data=soap_payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            _logger.error("COCO request failed: %s", e)
            raise UserError(_('Communication error: Unable to send COCO data'))

        self._process_coco_response(response.text)

    def _process_coco_response(self, response_text: str) -> None:
        """Process COCO service response."""
        _logger.debug("COCO Response: %s", response_text)
        
        try:
            parsed_xml = minidom.parseString(response_text)
            elements = parsed_xml.getElementsByTagName('CoarriCodeco_ContainerResult')
            
            if not elements:
                raise UserError(_('Invalid response format from COCO service'))
                
            result_text = elements[0].firstChild.nodeValue if elements[0].firstChild else ''
            
            success_keywords = ['BERHASIL', 'Berhasil', 'berhasil', 'sudah pernah diajukan']
            
            if any(keyword in result_text for keyword in success_keywords):
                self.write({'state': 'completed'})
                _logger.info("COCO container %s completed successfully", self.name)
            else:
                self.write({'state': 'error'})
                raise UserError(_('COCO submission failed: %s') % result_text)
                
        except Exception as e:
            _logger.error("Error processing COCO response: %s", e)
            self.write({'state': 'error'})
            raise UserError(_('Error processing service response'))


class DpsContainerDetail(models.Model):
    """Detail COCO Container Model
    
    This model contains detailed information for each container
    including dimensions, seals, documents, and customs information.
    """
    
    _name = 'dps.container.detail'
    _description = 'Detail Coco Container'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'coco_id, id'

    # Parent Reference
    coco_id = fields.Many2one(
        'dps.coco.container',
        string='COCO Container',
        ondelete='cascade',
        required=True,
        index=True,
        help='Parent COCO container record'
    )

    # Container Information
    no_container = fields.Char(
        string='Container Number',
        related="coco_id.shipment_id.no_container",
        readonly=True,
        help='Container number from shipment'
    )
    
    ukuran_container = fields.Many2one(
        'dps.reference',
        string='Container Size',
        domain="[('kode_master', '=', 14)]",
        related="coco_id.shipment_id.ukuran_container",
        readonly=True,
        help='Container size reference'
    )
    
    jenis_container = fields.Many2one(
        'dps.reference',
        string='Container Type',
        domain="[('kode_master', '=', 15)]",
        help='Container type reference'
    )
    
    no_segel = fields.Char(
        string='Seal Number',
        related="coco_id.shipment_id.no_segel",
        readonly=True,
        help='Container seal number'
    )

    # Bill of Lading Information
    no_bl_awb = fields.Char(
        string='BL/AWB Number',
        help='Bill of Lading or Air Waybill number'
    )
    
    tgl_bl_awb = fields.Date(
        string='BL/AWB Date',
        help='Bill of Lading or Air Waybill date'
    )
    
    no_master = fields.Char(
        string='Master BL/AWB Number',
        related="coco_id.shipment_id.name",
        readonly=True,
        help='Master Bill of Lading or Air Waybill number'
    )
    
    tgl_master = fields.Date(
        string='Master BL/AWB Date',
        related="coco_id.shipment_id.tgl_master",
        readonly=True,
        help='Master Bill of Lading or Air Waybill date'
    )

    # Consignee Information
    id_consignee = fields.Char(
        string='Consignee ID',
        help='Consignee identification number'
    )
    
    nama_consignee = fields.Char(
        string='Consignee Name',
        help='Name of the consignee'
    )

    # Weight and Customs Information
    bruto = fields.Float(
        string='Gross Weight',
        related="coco_id.shipment_id.brutto",
        readonly=True,
        help='Gross weight in kilograms'
    )
    
    no_bc11 = fields.Char(
        string='BC11 Number',
        related='coco_id.shipment_id.no_bc11',
        readonly=True,
        help='BC11 customs document number'
    )
    
    tgl_bc11 = fields.Date(
        string='BC11 Date',
        related='coco_id.shipment_id.tgl_bc11',
        readonly=True,
        help='BC11 customs document date'
    )
    
    no_pos = fields.Char(
        string='Position Number',
        related="coco_id.shipment_id.no_pos",
        readonly=True,
        help='Position number in BC11'
    )

    # Storage and Movement Information
    kode_timbun = fields.Char(
        string='Storage Code',
        help='Storage area code in the yard'
    )
    
    kode_dokinout_id = fields.Integer(
        string='In/Out Document Code',
        default=3,
        help='Document code for goods entry/exit (SPPB/PLP)'
    )
    
    no_dok_inout = fields.Char(
        string='In/Out Document Number',
        help='PLP document number'
    )
    
    tgl_dok_inout = fields.Date(
        string='In/Out Document Date',
        help='PLP document date'
    )
    
    wk_inout = fields.Datetime(
        string='Entry/Exit Time',
        help='Actual entry or exit time'
    )

    # Transport Information
    kode_pengangkut_id = fields.Char(
        string='Transport Mode',
        default='1',
        help='Transportation mode code'
    )
    
    no_pol = fields.Char(
        string='Vehicle Number',
        help='Vehicle license plate number'
    )
    
    cont_kosong = fields.Boolean(
        string='Empty Container',
        default=False,
        help='Indicates if container is empty'
    )
    
    iso_code = fields.Char(
        string='ISO Code',
        help='Container ISO code'
    )

    # Port Information
    pel_muat_id = fields.Many2one(
        'dps.reference',
        string='Loading Port',
        domain="[('kode_master', '=', 4)]",
        help='Port of loading'
    )
    
    pel_transit_id = fields.Many2one(
        'dps.reference',
        string='Transit Port',
        domain="[('kode_master', '=', 4)]",
        help='Transit port'
    )
    
    pel_bongkar_id = fields.Many2one(
        'dps.reference',
        string='Discharge Port',
        domain="[('kode_master', '=', 4)]",
        help='Port of discharge'
    )

    # Destination and Office Information
    gudang_tujuan_id = fields.Char(
        string='Destination Warehouse',
        default="BBLK",
        help='Destination warehouse code'
    )
    
    kode_kantor_id = fields.Many2one(
        'dps.reference',
        string='Service Office',
        domain="[('kode_master', '=', 13)]",
        related="coco_id.shipment_id.kode_kantor_id",
        readonly=True,
        help='Customs service office'
    )

    # Registration Information
    no_daftar = fields.Char(
        string='Registration Number',
        help='Customs registration number'
    )
    
    tgl_daftar = fields.Date(
        string='Registration Date',
        help='Customs registration date'
    )

    # Customs Seal Information
    no_segel_bc = fields.Char(
        string='Customs Seal Number',
        help='Customs seal number'
    )
    
    tgl_segel_bc = fields.Date(
        string='Customs Seal Date',
        help='Customs seal date'
    )

    # TPS License Information
    no_ijin_tps = fields.Char(
        string='TPS License Number',
        default="1784",
        help='TPS operation license number'
    )
    
    tgl_ijin_tps = fields.Date(
        string='TPS License Date',
        default=lambda self: date(2016, 10, 10),
        help='TPS operation license date'
    )

    @api.model
    def _get_default_tps_license_date(self) -> date:
        """Get default TPS license date."""
        return date(2016, 10, 10)
