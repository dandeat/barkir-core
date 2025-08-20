odoo.define('dps_cn_pibk.custom_button', function (require) {
    'use strict';

    var ListController = require('web.ListController');
    var viewRegistry = require('web.view_registry');
    var ListView = require('web.ListView');
    var core = require('web.core');

    var CustomListController = ListController.extend({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var self = this;

            if (this.modelName === 'dps.container.tps') {
                var $button = $('<button type="button" class="btn btn-primary">Refresh Data</button>');
                $button.on('click', function () {
                    self._rpc({
                        model: 'dps.container.tps',
                        method: 'get_data_container',
                        args: [],
                    }).then(function (result) {
                        var msg = result && result.message ? result.message : 'Data berhasil ditarik';
                        self.do_notify('Berhasil', msg);
                        self.reload();
                    }).fail(function (error) {
                        self.do_warn('Gagal', 'Tidak bisa tarik data');
                    });
                });
                this.$buttons.append($button);
            }
        }
    });

    var CustomListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: CustomListController,
        }),
    });

    viewRegistry.add('custom_list_dps_container_tps', CustomListView);
});
