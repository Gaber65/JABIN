from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JabinCuttingOption(models.Model):
    _name = 'jabin.cutting.option'
    _description = 'JABIN Cutting Option'
    _order = 'name'
    _inherit = ['jabin.core.mixin']

    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)

    product_ids = fields.Many2many(
        'jabin.product',
        'jabin_product_cutting_rel',
        'cutting_id',
        'product_id',
        string='Products'
    )

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if self.search_count([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_('Cutting Option name must be unique!'))