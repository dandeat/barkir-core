"""DPS Reference Model

This module contains the reference model for managing various master data codes
used throughout the DPS system including document types, ports, warehouses, etc.
"""

from typing import List, Tuple, Any, Optional
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DpsReference(models.Model):
    """DPS Reference Model
    
    This model stores master reference data for various code types used in the system.
    Each record represents a specific code with its description and category.
    
    Master Code Categories:
    1  - Jenis Aju (Application Type)
    2  - Kode Jenis PIBK (PIBK Type Code)
    3  - Kode Jenis Angkut (Transport Type Code)
    4  - Kode Pelabuhan (Port Code)
    5  - Kode Gudang (Warehouse Code)
    6  - Kode Negara (Country Code)
    7  - Jenis Identitas (Identity Type)
    8  - Kode Valuta (Currency Code)
    9  - Kode Pungutan (Levy Code)
    10 - Jenis Kemasan (Package Type)
    11 - Jenis Tarif (Tariff Type)
    12 - Kode Tarif (Tariff Code)
    13 - Kode Kantor (Office Code)
    """
    
    _name = 'dps.reference'
    _description = 'DPS Reference Master Data'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'kode_master, name'
    _rec_name = 'name'

    # Core Fields
    name = fields.Char(
        string='Code',
        required=True,
        index=True,
        tracking=True,
        help='Reference code identifier'
    )
    
    uraian = fields.Char(
        string='Description',
        required=True,
        tracking=True,
        help='Detailed description of the reference code'
    )
    
    kode_master = fields.Integer(
        string='Master Code Category',
        required=True,
        index=True,
        tracking=True,
        help='Category identifier for grouping reference codes'
    )

    # Additional Fields for Better Management
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Indicates if this reference code is currently active'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence order for display purposes'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes or comments about this reference code'
    )

    # Computed Fields
    display_name_full = fields.Char(
        string='Full Display Name',
        compute='_compute_display_name_full',
        store=True,
        help='Complete display name with code and description'
    )
    
    master_category_name = fields.Char(
        string='Category Name',
        compute='_compute_master_category_name',
        help='Human readable name for the master code category'
    )

    # Constraints
    _sql_constraints = [
        ('unique_code_per_master', 
         'unique(name, kode_master)', 
         'Code must be unique within each master category!'),
        ('positive_master_code', 
         'check(kode_master > 0)', 
         'Master code must be positive!'),
    ]

    @api.depends('name', 'uraian')
    def _compute_display_name_full(self) -> None:
        """Compute full display name combining code and description."""
        for record in self:
            if record.name and record.uraian:
                record.display_name_full = f"{record.name} - {record.uraian}"
            elif record.name:
                record.display_name_full = record.name
            else:
                record.display_name_full = record.uraian or ''

    @api.depends('kode_master')
    def _compute_master_category_name(self) -> None:
        """Compute human readable category name based on master code."""
        category_mapping = {
            1: 'Jenis Aju',
            2: 'Kode Jenis PIBK',
            3: 'Kode Jenis Angkut',
            4: 'Kode Pelabuhan',
            5: 'Kode Gudang',
            6: 'Kode Negara',
            7: 'Jenis Identitas',
            8: 'Kode Valuta',
            9: 'Kode Pungutan',
            10: 'Jenis Kemasan',
            11: 'Jenis Tarif',
            12: 'Kode Tarif',
            13: 'Kode Kantor',
        }
        
        for record in self:
            record.master_category_name = category_mapping.get(
                record.kode_master, 
                f'Unknown Category ({record.kode_master})'
            )

    def name_get(self) -> List[Tuple[int, str]]:
        """Return display name as 'Code - Description' format."""
        result = []
        for record in self:
            if record.name and record.uraian:
                display_name = f"{record.name} - {record.uraian}"
            elif record.name:
                display_name = record.name
            else:
                display_name = record.uraian or f"ID: {record.id}"
            result.append((record.id, display_name))
        return result

    @api.model
    def _name_search(
        self, 
        name: str = '', 
        args: Optional[List] = None, 
        operator: str = 'ilike', 
        limit: int = 100, 
        name_get_uid: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        """Enhanced name search supporting both code and description fields."""
        args = list(args or [])
        
        if name:
            # Search in both name (code) and uraian (description) fields
            search_args = [
                '|', 
                ('name', operator, name), 
                ('uraian', operator, name)
            ]
            args.extend(search_args)
        
        # Perform search and return name_get results
        records = self.search(args, limit=limit)
        return records.name_get()

    @api.model
    def get_by_master_code(self, master_code: int, active_only: bool = True) -> 'DpsReference':
        """Get all reference records for a specific master code category.
        
        Args:
            master_code: The master code category to filter by
            active_only: Whether to return only active records
            
        Returns:
            Recordset of matching reference records
        """
        domain = [('kode_master', '=', master_code)]
        if active_only:
            domain.append(('active', '=', True))
        
        return self.search(domain, order='sequence, name')

    @api.model
    def get_code_by_name(self, code_name: str, master_code: int) -> Optional['DpsReference']:
        """Get a specific reference record by code name and master category.
        
        Args:
            code_name: The code name to search for
            master_code: The master code category
            
        Returns:
            Single reference record or None if not found
        """
        return self.search([
            ('name', '=', code_name),
            ('kode_master', '=', master_code),
            ('active', '=', True)
        ], limit=1)

    def toggle_active(self) -> None:
        """Toggle the active status of reference records."""
        for record in self:
            record.active = not record.active

    @api.constrains('name', 'kode_master')
    def _check_code_format(self) -> None:
        """Validate code format based on master category requirements."""
        for record in self:
            if not record.name or not record.name.strip():
                raise UserError(_('Code cannot be empty!'))
            
            # Add specific validation rules for different master codes if needed
            if record.kode_master in [4, 6]:  # Port codes, Country codes
                if len(record.name) < 2:
                    raise UserError(
                        _('Code for category %s must be at least 2 characters long!') 
                        % record.master_category_name
                    )

    @api.model
    def create_default_references(self) -> None:
        """Create default reference data if not exists.
        
        This method can be called during module installation to populate
        basic reference data.
        """
        # This method can be extended to create default reference data
        # based on business requirements
        pass

    def copy(self, default: Optional[dict] = None) -> 'DpsReference':
        """Override copy to ensure unique codes."""
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (Copy)") % self.name
        return super().copy(default)

    @api.model
    def search_by_category(self, category_name: str) -> 'DpsReference':
        """Search references by category name.
        
        Args:
            category_name: Name of the category to search for
            
        Returns:
            Recordset of matching reference records
        """
        category_reverse_mapping = {
            'jenis_aju': 1,
            'jenis_pibk': 2,
            'jenis_angkut': 3,
            'pelabuhan': 4,
            'gudang': 5,
            'negara': 6,
            'identitas': 7,
            'valuta': 8,
            'pungutan': 9,
            'kemasan': 10,
            'jenis_tarif': 11,
            'tarif': 12,
            'kantor': 13,
        }
        
        master_code = category_reverse_mapping.get(category_name.lower())
        if master_code:
            return self.get_by_master_code(master_code)
        else:
            return self.browse()

    def action_view_related_records(self) -> dict:
        """Action to view records that use this reference.
        
        Returns:
            Action dictionary for opening related records
        """
        # This can be extended to show related records that use this reference
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Records'),
            'res_model': 'dps.reference',
            'view_mode': 'tree,form',
            'domain': [('kode_master', '=', self.kode_master)],
            'context': {'default_kode_master': self.kode_master},
        }
