from odoo import models, fields, _
from odoo.exceptions import MissingError


class wizGateIn(models.TransientModel):
    _name = 'wiz.gate.in'
    _description = 'Wizard Gate In'

    wk_gate_in = fields.Datetime(string='Waktu Gate In')
    no_pol = fields.Char(string='Nomor Polisi')
    call_sign = fields.Char(string='Call Sign')
    no_plp = fields.Char(string='No PLP')
    tgl_plp = fields.Date(string='Tanggal PLP')
    no_segel_bc = fields.Char(string='No Segel BC')
    tgl_segel_bc = fields.Date(
        string='Tanggal Segel BC', default=fields.Date.today())
    kurs = fields.Float(string='Kurs Hari Ini')
    ukuran_container = fields.Many2one(
        'dps.reference', string='Ukuran Container', domain="[('kode_master', '=', 14)]")
    no_container = fields.Char(string='No Container')

    cn = fields.Integer(string='CN')

    def submit(self):
        shipment_obj = self.env['dps.shipment'].search([('id', '=', self.cn)])
        if shipment_obj:
            shipment_obj.gatein_time = self.wk_gate_in
            shipment_obj.call_sign = self.call_sign
            shipment_obj.no_plp = self.no_plp
            shipment_obj.tgl_plp = self.tgl_plp
            shipment_obj.no_segel_bc = self.no_segel_bc
            shipment_obj.tgl_segel_bc = self.tgl_segel_bc
            shipment_obj.ukuran_container = self.ukuran_container.id
            shipment_obj.no_container = self.no_container
            shipment_obj.state = 'in'
            self.env.cr.execute(
                "UPDATE dps_cn_pibk SET ndpbm=%s WHERE shipment_id=%s",
                (self.kurs, self.cn))

            self.env.cr.execute(
                "SELECT \"AddDpsKemasan\"(%s) as total", (self.cn,))
            amount_total = self.env.cr.dictfetchone()

            _logger.debug("Masuk dps_kemasan: %s", amount_total['total'])
            if shipment_obj.tot_ci == 0:
                shipment_obj.create_coco_in(self.no_pol)
                shipment_obj.create_coke_in()


class wizGateOut(models.TransientModel):
    _name = 'wiz.gate.out'
    _description = 'Wizard Gate Out'

    wk_gate_out = fields.Datetime(string='Waktu Gate Out')
    shipment = fields.Integer(string='Shipment')

    def submit(self):
        shipment_obj = self.env['dps.shipment'].search(
            [('id', '=', self.shipment)])
        if shipment_obj:
            shipment_obj.gateout_time = self.wk_gate_out
            if shipment_obj.tot_co == 0:
                coco = self.env['dps.coco.container'].search([('shipment_id', '=', self.shipment), (
                    'kd_dok_id.name', '=', 5)], limit=1, order='name desc')
                if coco:
                    if coco.state != 'completed':
                        raise MissingError(_("Gate In Container belum terkirim"))
                else:
                    raise MissingError(_("Gate In Container belum ada"))
                if not shipment_obj.gateout_time:
                    raise MissingError(_("Tanggal Waktu Gate Out Belum di isi"))
                for con in coco.detail_ids:
                    if not con.no_pol:
                        raise MissingError(_("Nomor Polisi Gate In Belum di isi"))
                if not coco.call_sign:
                    raise MissingError(_("Call Sign Belum di isi"))
                if not shipment_obj.ukuran_container:
                    raise MissingError(_("Ukuran Container Belum di isi"))

                coco.create_coco_out()
