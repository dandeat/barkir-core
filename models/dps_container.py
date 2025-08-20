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
    
    no_master = fields.Char(string='Master BL/AWB Number')
    pjt = fields.Char(
        string='PJT Provider',
        tracking=True,
        help='Penyelenggara Jasa Titipan (Custodian Service Provider)'
    )
    
    # === Transport & Arrival Fields ===
    tanggal_tiba = fields.Datetime(
        string='Arrival Date',
        index=True,
        tracking=True,
        help='Date and time when the container arrived'
    )

    nama_pengangkut = fields.Char(
        string='Vessel Name',
        tracking=True,
        help='Name of the vessel/ship carrying the container'
    )
    asal_negara = fields.Char(
        string='Country of Origin',
        tracking=True,
        help='Country where the container originated from'
    )

    # === Gate Operations ===
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
        inverse_name='container_id',  # <-- Corrected this line
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
        compute='_compute_total_kemasan',
        store=True, # Add store=True to make it searchable/sortable
        help='Total number of kemasan items inside the container'
    )

    sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        help='Date and time of the last synchronization with the external system.'
    )

    # Add the compute method for total_kemasan
    @api.depends('kemasan_ids')
    def _compute_total_kemasan(self):
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