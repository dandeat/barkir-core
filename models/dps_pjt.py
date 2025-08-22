import logging
import xmlrpc.client
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class DpsPJT(models.Model):
    _name = 'dps.pjt'
    _description = 'PJT'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # === Core Fields ===
    code = fields.Char(
        string='Kode PJT',
        required=True,
        index=True,
        tracking=True,
        help='Unique PJT identifier'
    )
    jenis_id_pemberitahu = fields.Many2one(
        'dps.reference',
        string='Jenis Identitas Pemberitahu',
        domain="[('kode_master', '=', 7)]",
        tracking=True,
        help='Type of identity for the notifier'
    )
    no_id_pemberitahu = fields.Char(
        string='ID Pemberitahu',
        required=True,
        tracking=True,
        help='Identifier for the notifier, such as NPWP or NIK'
    )
    nama_pjt = fields.Char(
        string='Nama PJT',
        required=True,
        tracking=True,
        help='Name of the PJT (Penyelenggara Jasa Titipan)'
    )

    # === Authentication Fields ===
    username_ceisa40 = fields.Char(
        string='Username CEISA40',
        required=True,
        tracking=True,
        help='Username for CEISA40 system'
    )
    password_ceisa40 = fields.Char(
        string='Password CEISA40',
        required=True,
        tracking=True,
        help='Password for CEISA40 system'
    )
    token_ceisa = fields.Char(
        string='Token CEISA',
        required=False,
        tracking=True,
        help='Token for CEISA system authentication'
    )

    # === Odoo Sync Credentials ===
    odoo_api_url = fields.Char(
        string='Odoo API URL',
        required=True,
        tracking=True,
        help='URL for Odoo API access'
    )
    odoo_db_name = fields.Char(
        string='Odoo Database Name',
        required=True,
        tracking=True,
        help='Name of the Odoo database to connect to'
    )
    odoo_api_key = fields.Char(
        string='Odoo API Key',
        required=True,
        tracking=True,
        help='API key for Odoo access'
    )

    # === Contact Information ===
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
        help='Contact email for the PJT'
    )
    phone = fields.Char(
        string='Phone',
        required=True,
        tracking=True,
        help='Contact phone number for the PJT'
    )

    # === Address Fields ===
    alamat = fields.Text(
        string='Alamat',
        required=True,
        tracking=True,
        help='Address of the PJT'
    )
    
    # === License Detail ===
    no_ijin = fields.Char(
        string='Nomor Ijin',
        required=True,
        tracking=True,
        help='License number for the PJT'
    )
    tgl_ijin = fields.Date(
        string='Tanggal Ijin',
        required=True,
        tracking=True,
        help='Date of the PJT license'
    )
    kode_valuta = fields.Many2one(
        'dps.reference',
        string='Kode Valuta',
        domain="[('kode_master', '=', 8)]",
        tracking=True,
        help='Currency code for financial transactions'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    notes = fields.Text(string='Notes')

    # === Computed Fields ===
    total_kemasan = fields.Integer(
        string='Total Kemasan',
        # compute='_compute_total_kemasan',
        help='Total number of kemasan items associated with this PJT'
    )
    total_cn = fields.Integer(
        string='Total CN',
        # compute='_compute_total_cn',
        help='Total number of CN items associated with this PJT'
    )
    total_container = fields.Integer(
        string='Total Container',
        # compute='_compute_total_container',
        help='Total number of containers associated with this PJT'
    )

    # Add the compute method for total_kemasan
    # @api.depends('kemasan_ids')
    # def _compute_total_kemasan(self):
    #     for record in self:
    #         kemasans = self.env['dps.kemasan'].search([('pjt_id', '=', record.id)])
    #         record.total_kemasan = len(record.kemasan_ids)

    # ... (other methods) ...
    def action_view_kemasan(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kemasan Items'),
            'res_model': 'dps.kemasan',
            'view_mode': 'list,form',  # Use 'list,form' for Odoo 18
            'domain': [('pjt_id', '=', self.id)],
            'context': {'default_pjt_id': self.id}
        }