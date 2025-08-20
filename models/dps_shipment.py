import logging
import xmlrpc.client
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DpsShipment(models.Model):
    _name = 'dps.shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'DPS Shipment'
    _order = 'create_date desc'

    # State Fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in', 'GateIn'),
        ('on_clearance', 'On Clearance'),
        ('clearance_done', 'Clearance Done'),
    ], string='Status', default='draft', tracking=True)

    # === Core Fields ===
    name = fields.Char(
        string='Master BL/AWB Number',
        tracking=True,
        required=True
    )
    no_master = fields.Char(
        string='No Master BL/AWB',
        tracking=True,
        required=True
    )
    tgl_master = fields.Date(
        string='Tanggal Master BL/AWB',
        tracking=True,
        required=True
    )
    # shipment details
    nama_pengangkut = fields.Char(
        string='Nama Pengangkut',
        tracking=True
    )
    call_sign = fields.Char(
        string='Call Sign',
        tracking=True
    )
    no_voy_flight = fields.Char(
        string='No Voy/Flight',
        tracking=True
    )
    shipment_number = fields.Char(
        string='Shipment Number',
        tracking=True
    )
    depart_date = fields.Date(
        string='Tanggal Berangkat',
        tracking=True
    )
    arrival_date = fields.Date(
        string='Tanggal Tiba',
        tracking=True
    )

    # === Relational Fields ===
    container_ids = fields.One2many(
        comodel_name='dps.container',
        inverse_name='shipment_id',
        string='Container List'
    )
    kemasan_ids = fields.One2many(
        comodel_name='dps.kemasan',
        inverse_name='shipment_id',
        string='Kemasan Items'
    )
    # cn_ids = fields.One2many(
    #     comodel_name='dps.cn.pibk',
    #     inverse_name='shipment_id',
    #     string='CN/PIBK Documents'
    # )

    # === Computed Fields for Counting ===
    container_count = fields.Integer(
        string="Container Count",
        compute='_compute_counts',
        store=True
    )
    kemasan_count = fields.Integer(
        string="Kemasan Count",
        compute='_compute_counts',
        store=True
    )
    # cn_count = fields.Integer(
    #     string="CN/PIBK Count",
    #     compute='_compute_counts',
    #     store=True
    # )

    @api.depends('container_ids', 'kemasan_ids')
    def _compute_counts(self):
        for record in self:
            record.container_count = len(record.container_ids)
            record.kemasan_count = len(record.kemasan_ids)
            # record.cn_count = len(record.cn_ids)

    # === Action Methods to open related records ===
    def action_view_containers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Containers'),
            'res_model': 'dps.container',
            'view_mode': 'list,form',
            'domain': [('shipment_id', '=', self.id)],
            'context': {'default_shipment_id': self.id},
        }

    # def action_view_cn_pibk(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('CN/PIBK Documents'),
    #         'res_model': 'dps.cn.pibk',
    #         'view_mode': 'list,form',
    #         'domain': [('shipment_id', '=', self.id)],
    #         'context': {'default_shipment_id': self.id},
    #     }

    def action_view_kemasan(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kemasan Items'),
            'res_model': 'dps.kemasan',
            'view_mode': 'list,form',
            'domain': [('shipment_id', '=', self.id)],
            'context': {'default_shipment_id': self.id},
        }

    def action_confirm(self):
        # A simple placeholder, add your validation logic here
        self.write({'state': 'confirmed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    _sql_constraints = [
        ('no_master_unique', 'unique(no_master)', 'No Master BL/AWB harus unik!'),
    ]

    # # container details
    # # brutto = fields.Float(string='Brutto')
    # # netto = fields.Float(string='Netto')
    # # gatein_time = fields.Datetime(string='Tgl/Waktu Gate In', tracking=True)
    # # gateout_time = fields.Datetime(string='Tgl/Waktu Gate Out', tracking=True)
    # # ukuran_container = fields.Many2one(
    # #     'dps.reference', string='Ukuran Container',
    # #     domain="[('kode_master', '=', 14)]", tracking=True)
    # # no_container = fields.Char(string='No Container', tracking=True)
    # # no_segel_bc = fields.Char(string='No Segel BC', tracking=True)
    # # tgl_segel_bc = fields.Date(string='Tanggal Segel BC', tracking=True)
    # # no_pos = fields.Char(string='No Pos', tracking=True)
    # # no_sub_pos = fields.Char(string='No Sub Pos', tracking=True)
    # # no_sub_sub_pos = fields.Char(string='No Sub Sub Pos', tracking=True)
    
    # # Count Fields
    # # total_pungutan = fields.Float(
    # #     string='Total Pungutan', compute='get_pungutan_total', store=True)
    # # total_dibayar = fields.Float(
    # #     string='Total Dibayar', compute='get_total_dibayar')
    # # total_kemasan = fields.Integer(
    # #     string='Total Kemasan', compute='get_kemasan', store=True)
    # # total_cn = fields.Integer(
    # #     string='Total CN', compute='get_cn_total', store=True)
    # # total_cn_cleared = fields.Integer(
    # #     string='Total CN Cleared', compute='get_cn_cleared', store=True)
    # # total_container = fields.Integer(
    # #     string='Total Container', compute='get_container_total', store=True)
    
    # # Ids Fields
    # # cn_ids = fields.One2many('dps.cn.pibk', 'shipment_id', string='Detil CN')
    
    # # kode_shipment = fields.Char(string='Kode Shipment')
    
    # _sql_constraints = [
    #     ('no_master_unique', 'unique(no_master)', 'No Master BL/AWB harus unik!'),
    # ]
    
    # # Reset Fields Only on Confirm State
    # def set_draft(self):
    #     for rec in self :
    #         if rec.state != 'confirm':
    #             raise UserError(_("Hanya bisa di reset ke Draft dari status Confirm"))
            
    #         for cn in rec.cn_ids:
    #             if cn.state not in ('ready', 'draft'):
    #                 raise ValidationError(_("No Barang %s status %s. \n Proses Gagal" % (cn.name, dict(rec._fields['state'].selection).get(cn.state))))
    #         rec.state = 'draft'

    # # Confirm State and Validate Fields
    # # def set_confirm(self):
    # #     for rec in self:
    # #         if not rec.no_master:
    # #             raise ValidationError(_("No Master BL/AWB belum di isi"))
    # #         if not rec.tgl_master:
    # #             raise ValidationError(_("Tanggal Master BL/AWB belum di isi"))
    # #         if not rec.kode_kantor_id:
    # #             raise ValidationError(_("Kantor Pelayanan belum di isi"))
    # #         if not rec.kode_jenis_angkut_id:
    # #             raise ValidationError(_("Jenis Moda belum di isi"))
    # #         if not rec.gudang_id:
    # #             raise ValidationError(_("Kode Gudang belum di isi"))
    # #         if not rec.nama_pengangkut:
    # #             raise ValidationError(_("Nama Pengangkut belum di isi"))
    # #         if not rec.call_sign:
    # #             raise ValidationError(_("Call Sign belum di isi"))
    # #         if not rec.no_voy_flight:
    # #             raise ValidationError(_("No Voy/Flight belum di isi"))
    # #         if not rec.depart_date:
    # #             raise ValidationError(_("Tanggal Berangkat belum di isi"))
    # #         if not rec.arrival_date:
    # #             raise ValidationError(_("Tanggal Tiba belum di isi"))
            
    # #         #TODO: Validate CN fields and set to ready state
    # #         #TODO: Validate Container fields and set to ready state
    # #         #TODO: Validate Kemasan fields and set to ready state

    # #         # Set state to confirm
    # #         rec.state = 'confirm'

    # #TODO Proses PLP Container
    # def do_plp_container(self):
    #     for rec in self:
    #         if not rec.container_ids:
    #             raise ValidationError(_("Container belum di isi"))
            
    #         plp_vals = {
    #             'shipment_id': rec.id,
    #             'no_bc11': rec.no_bc11,
    #             'tgl_bc11': rec.tgl_bc11,
    #             'no_pos': rec.no_pos,
    #             'kode_alasan_plp': rec.alasan_plp_id.id,
    #             'nama_pengangkut': rec.nama_pengangkut,
    #             'no_voy_flight': rec.no_voy_flight,
    #             'call_sign': rec.call_sign,
    #             'arrival_date': rec.arrival_date,
    #             'ukuran_container': rec.ukuran_container.id,
    #             'no_container': rec.no_container,
    #         }
    #         _logger.debug(plp_vals)
    #         self.env['dps.plp.container'].create(plp_vals)

    # #TODO Proses Gate In Container
    # def create_coco_in(self, nopol):
    #     det = []
    #     _logger.debug("======================================================")
    #     for rec in self:
    #         det_container = (0, 0, {
    #             'jenis_container': get_id(self, 'L', 15),
    #             'ukuran_container': rec.ukuran_container.id,
    #             'no_pol': nopol,
    #             'no_segel_bc': rec.no_segel_bc,
    #             'tgl_segel_bc': rec.tgl_segel_bc,
    #             'no_dok_inout': rec.no_plp,
    #             'tgl_dok_inout': rec.tgl_plp,
    #             'wk_inout': rec.gatein_time.strftime('%m/%d/%Y %H:%M:%S') if rec.gatein_time else False,
    #         })
    #         det.append(det_container)
    #         kd_dok = self.env['dps.reference'].sudo().search([('kode_master', '=', 16), ('name', '=', '5')]).id
    #         coco_vals = {
    #             'shipment_id': rec.id,
    #             'kd_dok_id': kd_dok,
    #             'detail_ids': det,
    #             'state': 'ready'
    #         }
    #         _logger.debug(coco_vals)
    #         self.env['dps.coco.container'].create(coco_vals)

    # #TODO Proses Gate In Kemasan
    # def create_coke_in(self):
    #     for rec in self:
    #         coco_in = self.env['dps.coco.container'].sudo().search([
    #             ('shipment_id', '=', rec.id), ('kd_dok_id.name', '=', '5')
    #         ], limit=1, order="name desc")
    #         if not coco_in:
    #             raise MissingError(_("Gate In Container belum terdata"))
    #         if not rec.no_plp or not rec.tgl_plp:
    #             raise MissingError(_("Nomor dan Tanggal PLP Belum di isi"))
    #         if not rec.gatein_time:
    #             raise MissingError(_("Tanggal Waktu Gate In Belum di isi"))
    #         no_pol = False
    #         for con in coco_in.detail_ids:
    #             if con.no_pol:
    #                 no_pol = con.no_pol
    #                 break
    #         if not no_pol:
    #             raise MissingError(_("Nomor Polisi Gate In Belum di isi"))
    #         if not rec.call_sign:
    #             raise MissingError(_("Call Sign Belum di isi"))

    #         kode_kemasan_id = self.env['dps.reference'].sudo().search([
    #             ('kode_master', '=', 10), ('name', '=', 'PK')]).id
    #         det = []
    #         for i, cn in enumerate(rec.cn_ids, 1):
    #             det_kemasan = (0, 0, {
    #                 'cn_id': cn.id,
    #                 'seri_kemasan': i,
    #                 'no_dok_inout': rec.no_plp,
    #                 'tgl_dok_inout': rec.tgl_plp,
    #                 'wk_inout': rec.gatein_time.strftime('%m/%d/%Y %H:%M:%S'),
    #                 'kode_kemasan_id': kode_kemasan_id,
    #                 'tgl_segel_bc': rec.tgl_segel_bc,
    #                 'jumlah_kemasan': 1,
    #             })
    #             det.append(det_kemasan)
    #         kd_dok = self.env['dps.reference'].sudo().search([
    #             ('kode_master', '=', 16), ('name', '=', '5')]).id
    #         coke_vals = {
    #             'shipment_id': rec.id,
    #             'kd_dok_id': kd_dok,
    #             'detail_ids': det,
    #             'no_pol': no_pol,
    #             'no_segel_bc': rec.no_segel_bc,
    #         }
    #         _logger.debug(coke_vals)
    #         self.env['dps.coco.kemasan'].create(coke_vals)

    # #TODO Proses Gate Out Container
    # def create_coco_out(self):
    #     return

    # #TODO Proses Gate Out Kemasan
    # def create_coke_out(self):
    #     return

    # #TODO Cetak Dokumen SPPB
    # def cetak_sppb(self):

    #     if not self.cn_ids:
    #         raise UserError(_("Tidak ada dokumen CN yang tersedia untuk dicetak."))
    #     if not self.cn_ids.filtered(lambda cn: cn.state in ('ready', 'sent')):
    #         raise UserError(_("Tidak ada dokumen CN yang siap untuk dicetak."))

    #     self.ensure_one()
        
    #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #     tmp_folder = self.env['ir.config_parameter'].sudo().get_param('tmp.folder')
    #     merger = PdfFileMerger()

    #     for cn in self.cn_ids:
    #         b64 = False
    #         for res in cn.respon_ids:
    #             if res.kode_respon in ('401', '403', '404'):
    #                 b64 = res.pdf
    #         if not b64:
    #             continue

    #         pdf_bytes = base64.b64decode(b64, validate=True)
    #         if pdf_bytes[0:4] != b'%PDF':
    #             raise MissingError(_("Not a PDF file"))

    #         file_path = f"{tmp_folder}/file_{cn.id}.pdf"
    #         with open(file_path, 'wb') as f:
    #             f.write(pdf_bytes)

    #         with open(file_path, 'rb') as pdf_file:
    #             merger.append(PdfFileReader(pdf_file))

    #     merged_file_path = f"{tmp_folder}/hasil_{self.id}.pdf"
    #     merger.write(merged_file_path)
    #     merger.close()

    #     with open(merged_file_path, 'rb') as pdf_file:
    #         merged_pdf_b64 = base64.b64encode(pdf_file.read())

    #     fname = f"SPPB - {self.no_master}.pdf"
    #     attachment = self.env['ir.attachment'].create({
    #         'name': fname,
    #         'datas': merged_pdf_b64,
    #     })
    #     download_url = f'/web/content/{attachment.id}?download=true'
    #     return {
    #         "type": "ir.actions.act_url",
    #         "url": f"{base_url}{download_url}",
    #         "target": "new",
    #     }

    # @api.depends('no_container')
    # def get_tot_plp(self):
    #     for rec in self :
    #         tot_plp = self.env['dps.plp.container'].sudo().search_count([('no_container', '=', rec.no_container),('state', '!=', 'reject')])
    #         rec.tot_plp = tot_plp
    
    # @api.depends('no_container')
    # def get_tot_ci(self):
    #     for rec in self :
    #         tot_ci = self.env['dps.coco.container'].sudo().search_count([('shipment_id', '=', rec.id),('kd_dok_id.name', '=', 5)])
    #         rec.tot_ci = tot_ci

    # @api.depends('no_container')
    # def get_tot_co(self):
    #     for rec in self :
    #         tot_co = self.env['dps.coco.container'].sudo().search_count([('shipment_id', '=', rec.id),('kd_dok_id.name', '=', 6)])
    #         rec.tot_co = tot_co
            

    # @api.depends('no_container')
    # def get_tot_ki(self):
    #     for rec in self :
    #         tot_ki = self.env['dps.coco.kemasan'].sudo().search_count([('shipment_id', '=', rec.id),('kd_dok_id.name', '=', 5)])
    #         rec.tot_ki = tot_ki

    # @api.depends('no_container')
    # def get_tot_ko(self):
    #     for rec in self :
    #         tot_ko = self.env['dps.coco.kemasan'].sudo().search_count([('shipment_id', '=', rec.id),('kd_dok_id.name', '=', 6)])
    #         rec.tot_ko = tot_ko

    # @api.depends('name')
    # def get_tot_biaya(self):
    #     for rec in self :
    #         tot_biaya = self.env['dps.biaya'].sudo().search_count([('shipment_id', '=', rec.id)])
    #         rec.tot_biaya = tot_biaya

    # def update_kode_001(self):
    #     for rec in self :
    #         for cn in rec.cn_ids :
    #             if cn.state == 'ready' :
    #                 cn.kode_respon = '001'
    
    # def update_kode_003(self):
    #     for rec in self :
    #         for cn in rec.cn_ids :
    #             if cn.state == 'ready' and cn.kode_respon in ('000','001'):
    #                 cn.kode_respon = '003'

    # # tambahan update ke CN 01
    # def update_CN01(self):
    #     for rec in self:
    #         for cn in rec.cn_ids:
    #             if cn.state == 'reject' and cn.kat_reject == 'Invalid Nama Pengirim':
    #                 cn.state = 'ready'
    #                 cn.jenis_aju_id = 3
    #         rec.env.cr.execute("SELECT \"val_hscn1\"(%s)", (rec.no_master,))
 

    # #TODO Kirim CN
    # def kirim_all(self) :
    #     send_cn(self,'all')
    # def kirim_all_lama(self) :
    #     send_cn_old(self,'all')
    # def cron_send_cn(self):
    #     send_cn(self)
    
    # def get_kemasan(self):
    #     self.tot_kemasan = self.env['dps.kemasan'].search_count([('shipment_id','=',self.id)])

    # def get_status_shipment(self):
    #     for rec in self :
    #         asinc(self,rec.id)

    # def cron_get_respon_405(self):
    #     get_respon(self,'405')

    # def cron_get_respon_313(self):
    #     get_respon(self,'313')

    # def cron_get_respon(self):
    #     get_respon(self,'')

    # # Scheduler Cepat
    # def cron_get_respon_203(self):
    #     get_respon(self,'203')

    # # Scheduler Lambat
    # def cron_get_respon_408(self):
    #     get_respon(self,'408')

    # def get_respon_test(self):
    #     get_respon(self,'ST##'+str(self.id))
    
    # def get_respon_shipment(self):
    #     get_respon(self,'SH##'+str(self.id))


    # def update_status(self):
    #     for rec in self :
    #         for cn in rec.cn_ids :
    #             jm = self.env['dps.respon'].search_count([('cn_id','=',cn.id),('kode_respon','=','307')])
    #             if  jm > 0 :
    #                 cn.state = 'spjm'
    #             elif cn.state in ('ready','sent')  :
    #                 if cn.kode_respon in ('401','403','405','408') :
    #                     cn.state = 'sppb'
    #                 elif cn.kode_respon not in ('000','001','002','003') and cn.state != 'spjm' :
    #                     cn.state = 'sent'

    # def refresh_bill_pungutan(self):
    #     for rec in self :
    #         for cn in rec.cn_ids :
    #             cn.get_bill()

    # @api.depends('cn_ids')
    # def get_pungutan_total(self):
    #     for rec in self:
    #         total_pungutan = sum(rec.cn_ids.mapped('total_pungutan'))
    #         rec.total_pungutan = total_pungutan

    # @api.depends('cn_ids.total_dibayar')
    # def get_total_dibayar(self):
    #     for rec in self:
    #         rec.total_dibayar = sum(rec.cn_ids.mapped('total_dibayar'))

    # def update_kurs(self):
    #     self.ensure_one()
    #     return {
    #         'name': _("Update Data"),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'dps.wiz.update',
    #         'view_id': self.env.ref("dps_cn_pibk.view_wiz_update_form").id,
    #         'target': 'new',
    #         'context': {
    #             'default_shipment_id': self.id,
    #         }}

    
    # def set_data_lama(self) :
    #     for rec in self :
    #         rec.state = 'kirim'
    #         for cn in rec.cn_ids :
    #             cn.state = 'sent'
    
    # @api.depends('cn_ids.state', 'cn_ids.end_respon')
    # def get_status(self):
    #     for rec in self:
    #         spjm = 0
    #         sppb = 0
    #         total40x = 0
    #         other_status = 0
    #         if rec.cn_ids:
    #             for cn in rec.cn_ids:
    #                 if cn.state == 'spjm':
    #                     spjm += 1
    #                 elif cn.state == 'sppb':
    #                     sppb += 1

    #                 if not cn.end_respon:
    #                     continue

    #                 if cn.end_respon[:2] == '40':
    #                     total40x += 1
    #                 else:
    #                     other_status += 1

    #         rec.total_spjm = spjm
    #         rec.total_hijau = sppb
    #         rec.total40x = total40x
    #         rec.other_status = other_status

    # def action_see_cn(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
        
    #     return {
    #         'name':_('Dokumen CN / PIBK'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
    
    # def action_see_kemasan(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
        
    #     return {
    #         'name':_('Inventori Kemasan'),
    #         'domain':list_domain,
    #         'res_model':'dps.kemasan',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
    
    # def action_see_plp(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         for rec in self :
    #             if rec.id == self.env.context['active_id'] :
    #                 list_domain.append(('no_container', '=', rec.no_container))
    #     return {
    #         'name':_('PLP Container'),
    #         'domain':list_domain,
    #         'res_model':'dps.plp.container',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
    
    # def action_see_ci(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         kd_dok_id = self.env['dps.reference'].sudo().search([('kode_master', '=', 16),('name', '=', '5')]).id
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
    #         list_domain.append(('kd_dok_id', '=',  kd_dok_id))
    #     return {
    #         'name':_('Gate In Container'),
    #         'domain':list_domain,
    #         'res_model':'dps.coco.container',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def action_see_co(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         kd_dok_id = self.env['dps.reference'].sudo().search([('kode_master', '=', 16),('name', '=', '6')]).id
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
    #         list_domain.append(('kd_dok_id', '=',  kd_dok_id))
    #     return {
    #         'name':_('Gate Out Container'),
    #         'domain':list_domain,
    #         'res_model':'dps.coco.container',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def action_see_ki(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         kd_dok_id = self.env['dps.reference'].sudo().search([('kode_master', '=', 16),('name', '=', '5')]).id
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
    #         list_domain.append(('kd_dok_id', '=',  kd_dok_id))
    #     return {
    #         'name':_('Gate In Kemasan'),
    #         'domain':list_domain,
    #         'res_model':'dps.coco.kemasan',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
    
    # def action_see_ko(self):
    #     list_domain = []
    #     if 'active_id' in self.env.context:
    #         kd_dok_id = self.env['dps.reference'].sudo().search([('kode_master', '=', 16),('name', '=', '6')]).id
    #         list_domain.append(('shipment_id', '=', self.env.context['active_id']))
    #         list_domain.append(('kd_dok_id', '=',  kd_dok_id))
    #     return {
    #         'name':_('Gate Out Kemasan'),
    #         'domain':list_domain,
    #         'res_model':'dps.coco.kemasan',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
    
    # def tot_spjm(self):
    #     list_domain = [('shipment_id', '=', self.id),('state','=','spjm')]
    #     return {
    #         'name':_('Dokumen CN / PIBK'),
    #         'domain': list_domain , 
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def tot_sppb(self):
    #     list_domain = [('shipment_id', '=', self.id),('state','=','sppb')]
    #     return {
    #         'name':_('Dokumen CN / PIBK'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }
   
    # def tot_401(self):
    #     list_domain = [('shipment_id', '=', self.id),('kode_respon','=','401')]
        
    #     return {
    #         'name':_('Dokumen CN / PIBK 401'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def tot_405(self):
    #     list_domain = [('shipment_id', '=', self.id),('kode_respon','=','405')] 
    #     return {
    #         'name':_('Dokumen CN / PIBK 405'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def tot_306(self):
    #     list_domain = [('shipment_id', '=', self.id),('kode_respon','=','306')]    
    #     return {
    #         'name':_('Dokumen CN / PIBK 306'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def tot_other(self):
    #     list_domain = [('shipment_id', '=', self.id),('kode_respon','not in',('401','405','408','403','404'))]
        
    #     return {
    #         'name':_('Dokumen CN / PIBK'),
    #         'domain':list_domain,
    #         'res_model':'dps.cn.pibk',
    #         'view_mode':'tree,form',
    #         'type':'ir.actions.act_window',
    #     }

    # def gate_in(self):
    #     self.ensure_one()
    #     kurs = self.getkurs()
    #     if kurs == 0:
    #         raise ValidationError(_("Get Kurs Tidak Berhasil, Harap Coba Lagi"))
    #     if self.call_sign:
    #         call_sign = 1
    #     else:
    #         call_sign = 0
    #     if self.ukuran_container:
    #         ukuran_container = 1
    #     else:
    #         ukuran_container = 0
    #     if self.no_plp:
    #         no_plp = 1
    #     else:
    #         no_plp = 0
    #     if self.tgl_plp:
    #         tgl_plp = 1
    #     else:
    #         tgl_plp = 0

    #     return {
    #         'name': _("Gate In"),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'wiz.gate.in',
    #         'view_id': self.env.ref("dps_cn_pibk.wizard_form_gate_in_id").id,
    #         'target': 'new',
    #         'context': {
    #             'default_cn': self.id,
    #             'default_call_sign': self.call_sign,
    #             'default_no_plp': self.no_plp,
    #             'default_tgl_plp': self.tgl_plp,
    #             'default_kurs': kurs,
    #             'default_ukuran_container': self.ukuran_container.id,
    #             'default_no_container': self.no_container,
    #             'read_call_sign': call_sign,
    #             'read_ukuran_container': ukuran_container,
    #             'read_no_plp': no_plp,
    #             'read_tgl_plp': tgl_plp,
    #         }}
    
    # def gate_out(self):
    #     self.ensure_one()
    #     if self.gateout_time:
    #         gateout_time = 1
    #     else:
    #         gateout_time = 0

    #     return {
    #         'name': _("Gate Out"),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'wiz.gate.out',
    #         'view_id': self.env.ref("dps_cn_pibk.wizard_form_gate_out_id").id,
    #         'target': 'new',
    #         'context': {
    #             'default_shipment': self.id,
    #             'default_wk_gate_out': self.gateout_time,
    #             'read_wk_gate_out': gateout_time,
    #         }}

    # def btn_kirim10(self):
    #     self.action_kirim(10)

    # def btn_kirim(self):
    #     self.action_kirim(100)

    # def action_kirim(self,jum) :
    #     a = 0
    #     for cn in self.cn_ids :
    #         if cn.state == 'ready' :
    #             kirim = False
    #             i = 0
    #             while not kirim  or i == 5:
    #                 kirim = cn.btn_kirim()
    #                 i += 1
    #             if kirim :
    #                 cn.kode_respon = '001'
    #                 a += 1
    #             if a == jum :
    #                 break

    # def btn_status(self) :
    #     for cn in self.cn_ids :
    #         if cn.kode_respon not in  ('000','901','902','903','904','905') or cn.state == 'sent':
    #             kode = False
    #             while not kode :
    #                 kode = cn.get_status()

    # def btn_respon(self) :
    #     a = 0
    #     for cn in self.cn_ids :
    #         if cn.kode_respon not in  ('000','901','902','903','904','905') :
    #             respon = False
    #             while not respon :
    #                 respon = cn.get_all_respon()
    #             # if respon :
    #             #     a += 1
    #             # if a == 10 :
    #             #     break

    # def get_token(self):
    #     config_param = self.env['ir.config_parameter'].sudo()
    #     username = config_param.get_param('beacukai.api.username')
    #     password = config_param.get_param('beacukai.api.password')
    #     cookie = config_param.get_param('beacukai.api.cookie')
    #     if not all([username, password, cookie]):
    #         raise UserError(
    #             _("Bea Cukai API credentials are not configured in system parameters."))

    #     conn = http.client.HTTPSConnection("apis-gw.beacukai.go.id")
    #     payload = json.dumps({
    #         "username": username,
    #         "password": password
    #     })
    #     headers = {
    #         'Content-Type': 'application/json',
    #         'Cookie': cookie
    #     }
    #     conn.request("POST", "/nle-oauth/v1/user/login", payload, headers)
    #     res = conn.getresponse()
    #     data = res.read()
    #     res = data.decode("utf-8")
    #     data = json.loads(res)
    #     return data['item']['access_token']

    # def getkurs(self):
    #     config_param = self.env['ir.config_parameter'].sudo()
    #     origin = config_param.get_param('beacukai.api.origin')
    #     platform_id = config_param.get_param('beacukai.api.platform_id')
    #     api_key = config_param.get_param('beacukai.api.key')
    #     cookie = config_param.get_param('beacukai.api.cookie')

    #     if not all([origin, platform_id, api_key, cookie]):
    #         raise UserError(
    #             _("Bea Cukai API settings are not fully configured in system parameters."))

    #     try:
    #         conn = http.client.HTTPSConnection("apis-gw.beacukai.go.id")
    #         payload = ''
    #         auth = 'Bearer ' + self.get_token()
    #         headers = {
    #             'Host': 'apis-gw.beacukai.go.id',
    #             'Content-Type': ' application/json',
    #             'Origin': origin,
    #             'id_platform': platform_id,
    #             'Beacukai-Api-Key': api_key,
    #             'Authorization': auth,
    #             'Cookie': cookie
    #         }
    #         conn.request("GET", "/openapi/kurs/USD", payload, headers)
    #         res = conn.getresponse()
    #         data = res.read()
    #         res = data.decode("utf-8")
    #         result = json.loads(res)
    #         hasil = float(result['data'][0]['nilaiKurs'])
    #     except Exception as e:
    #         _logger.error("Error Get Kurs : %s", e)
    #         hasil = 0
    #     return hasil
        

    # def updatekurs(self):
    #     kurs = self.getkurs()
    #     for rec in self :
    #         if rec.cn_ids :
    #             for cn in rec.cn_ids :
    #                 cn.ndpbm = kurs
    #                 update_pungut(self,cn)
