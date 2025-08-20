# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class DpsKemasan(models.Model):
    """
    Manages individual packaging items (Kemasan) within a container.
    Each kemasan is linked to a CN/PIBK document.
    """
    _name = 'dps.kemasan'
    _description = 'Kemasan (Packaging Item)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # === Core Fields ===
    name = fields.Char(
        string='Nomor Kemasan',
        required=True,
        help="The packaging number, typically derived from the CN/PIBK number."
    )

    # === Relational Field ===
    container_id = fields.Many2one(
        'dps.container',
        string='Container',
        tracking=True,
        help="The container this item belongs to."
    ) 

    shipment_id = fields.Many2one(
        'dps.shipment',
        string='Shipment',
        tracking=True,
        help="The shipment this item is part of."
    )

    # === Details from CN/PIBK (Related Fields) ===
    # uraian_barang = fields.Text(
    #     string='Uraian Barang',
    #     compute='_compute_uraian_barang',
    #     store=True,
    #     help="Description of the goods from the first line of the CN/PIBK."
    # )

    nama_pengirim = fields.Char(
        string='Nama Pengirim',
        tracking=True,
        required=True
    )
    nama_penerima = fields.Char(
        string='Nama Penerima',
        tracking=True,
        required=True
    )
    
    # no_sppb = fields.Char(string='No SPPB', related="cn_id.no_sppb", readonly=True)
    # tgl_sppb = fields.Date(string='Tgl SPPB', related="cn_id.tgl_sppb", readonly=True)
    
    # status_akhir = fields.Char(string='Status Akhir', related="cn_id.end_respon", readonly=True)

    # === Gate and Location Information ===
    waktu_gatein = fields.Datetime(
        string='Waktu Gate In',
        readonly=True
    )

    waktu_gateout = fields.Datetime(
        string='Waktu Gate Out', 
        tracking=True,
    )

    # lokasi_id = fields.Many2one(
    #     'dps.reference',
    #     string='Lokasi Gudang',
    #     domain="[('kode_master', '=', 17)]", # Assuming 17 is for Gudang locations
    #     default=lambda self: self.env['dps.reference'].search([('kode_master', '=', 17), ('name', '=', 'L1')], limit=1).id
    # )

    # === State Management ===
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in', 'Gate In'),
            ('xray', 'X-Ray'),
            ('atensi', 'Atensi'),
            ('spjm', 'SPJM'),
            ('completed', 'Completed'),
            ('out', 'Gate Out'),
        ], string='Status', default='draft', tracking=True)

    _sql_constraints = [
        ('cn_id_uniq', 'unique(cn_id)', 'A Kemasan record already exists for this CN/PIBK.'),
    ]

    # @api.depends('cn_id.barang_ids')
    # def _compute_uraian_barang(self):
    #     """Get the description from the first barang line."""
    #     for rec in self:
    #         if rec.cn_id and rec.cn_id.barang_ids:
    #             rec.uraian_barang = rec.cn_id.barang_ids[0].uraian_barang
    #         else:
    #             rec.uraian_barang = False
