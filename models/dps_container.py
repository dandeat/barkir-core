import logging
import xmlrpc.client
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DpsContainer(models.Model):

    _name = 'dps.container'
    _description = 'Container'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'


    # === Core Fields ===
    no_container = fields.Char(
        string='Container Number',
        required=True,
        index=True,
        tracking=True,
        help='Unique container identification number'
    )
    jenis_container = fields.Many2one(
        comodel_name='dps.reference',
        string='Container Type',
        required=True,
        domain="[('kode_master', '=', 15)]",
        tracking=True,
        help='Type of the container, e.g., 20ft, 40ft, etc.'
    )
    ukuran_container = fields.Many2one(
        comodel_name='dps.reference',
        string='Container Size',
        required=True,
        domain="[('kode_master', '=', 16)]",
        tracking=True,
        help='Size of the container, e.g., standard, high cube, etc.'
    )
    pjt_id = fields.Many2one(
        comodel_name='dps.pjt',
        string='PJT',
        required=True,
        tracking=True,
        help='Link to the associated PJT record'
    )
    
    # === Shipment Details ===
    shipment_id = fields.Many2one(
        comodel_name='dps.shipment',
        string='Shipment',
        required=True,
        tracking=True,
        help='Link to the associated shipment record'
    )
    no_master = fields.Char(
        related='shipment_id.no_master',
        string='Master BL/AWB Number',
        help='Master Bill of Lading or Air Waybill number for the shipment'
    )
    tgl_master = fields.Date(
        related='shipment_id.tgl_master',
        string='Master BL/AWB Date',
        help='Date of the Master Bill of Lading or Air Waybill'
    )
    no_bc11 = fields.Char(
        related='shipment_id.no_bc11',
        string='BC 1.1 Number',
        help='Customs declaration number for the shipment'
    )
    tgl_bc11 = fields.Date(
        related='shipment_id.tgl_bc11',
        string='BC 1.1 Date',
        help='Date of the customs declaration for the shipment'
    )
    no_voy_flight = fields.Char(
        related='shipment_id.no_voy_flight',
        string='Voyage/Flight Number',
        help='Voyage or flight number associated with the shipment'
    )
    shipment_number = fields.Char(
        related='shipment_id.shipment_number',
        string='Shipment Number',
        help='Unique identifier for the shipment'
    )
    nama_pengangkut = fields.Char(
        related='shipment_id.nama_pengangkut',
        string='Carrier Name',
        help='Name of the carrier responsible for the shipment'
    )
    
    # === Other Fields ===
    tanggal_tiba = fields.Datetime(
        string='Arrival Date',
        index=True,
        tracking=True,
        help='Date and time when the container arrived'
    )
    asal_negara = fields.Char(
        string='Country of Origin',
        tracking=True,
        help='Country where the container originated from'
    )

    # === TPS Gate Operations ===
    gate_in = fields.Datetime(
        string='Gate In TPS',
        tracking=True,
        help='Date and time the container entered the facility'
    )

    gate_out = fields.Datetime(
        string='Gate Out TPS',
        tracking=True,
        help='Date and time the container left the facility'
    )

    # === Relational Fields ===
    kemasan_ids = fields.One2many(
        comodel_name='dps.kemasan',
        inverse_name='container_id', 
        string='Kemasan Items'
    )
    
    shipment_id = fields.Many2one(
        'dps.shipment',
        string='Shipment',
        tracking=True,
        help="Direct link to the parent shipment record."
    )

    # === Status & Management Fields ===
    state = fields.Selection([
        ('draft', 'Draft'),
        ('arrived', 'Arrived'),
        ('gate_in', 'Gate In'),
        ('gate_out', 'Gate Out'),
        ('completed', 'Completed'), # Add 'completed' to the selection list
    ], string='Status', default='draft', tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    notes = fields.Text(string='Notes')

    # === Computed Fields & Synchronization ===
    total_kemasan = fields.Integer(
        string='Kemasan Count',
        compute='_compute_total',
        store=True, 
        help='Total number of kemasan items inside the container'
    )

    sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        help='Date and time of the last synchronization with the external system.'
    )

    # Add the compute method for all Total
    @api.depends('kemasan_ids')
    def _compute_total(self):
        for record in self:
            record.total_kemasan = len(record.kemasan_ids)

    # ... (other methods) ...
    def action_gate_in(self):
        self.ensure_one()
        # Change state check to allow 'arrived' state
        if self.state not in ['arrived']:
            raise UserError(_('Container must be in Arrived state for Gate In.'))
        self.write({'state': 'gate_in', 'gate_in': fields.Datetime.now()})

    def action_gate_out(self):
        self.ensure_one() # Use ensure_one() for single record actions
        if self.state != 'gate_in':
            raise UserError(_('Container must be in Gate In state for Gate Out.'))
        self.write({'state': 'gate_out', 'gate_out': fields.Datetime.now()})
    
    def action_set_arrived(self):
        self.ensure_one()
        if self.state == 'draft':
            self.write({'state': 'arrived'})
        else:
            raise UserError(_('Container must be in Draft state to be set as Arrived.'))

    def action_complete(self):
        self.ensure_one()
        if self.state == 'gate_out':
            self.write({'state': 'completed'})
        else:
            raise UserError(_('Container must be in Gate Out state to be Completed.'))

    def action_reset_to_draft(self):
        # Allow resetting from any state other than 'draft'
        self.write({'state': 'draft', 'gate_in': False, 'gate_out': False})
    
    def action_view_kemasan(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kemasan Items'),
            'res_model': 'dps.kemasan',
            'view_mode': 'list,form',  # Use 'list,form' for Odoo 18
            'domain': [('container_id', '=', self.id)],
            'context': {'default_container_id': self.id}
        }