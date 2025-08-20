console.log(">>> dashboard_polling.js loaded!");

odoo.define('dps_cn_pibk.refresh', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var action_registry = require('web.action_registry');

    var DashboardPoller = AbstractAction.extend({
        start: function () {
            console.log(">>> DashboardPoller started");

            if (this.action && this.action.id === 179) {
                console.log("Auto-refresh activated for action 179");
                setInterval(function () {
                    console.log("Auto-refreshing dashboard (official)...");
                    location.reload();
                }, 10000); // setiap 10 detik
            }

            return this._super.apply(this, arguments);
        }
    });

    // Daftarkan action ke registry (jika ingin dipakai sebagai client action)
    action_registry.add('dps_cn_pibk_dashboard_poller', DashboardPoller);

    return DashboardPoller;
});

// Fallback polling jika tidak bisa lewat AbstractAction (misalnya My Dashboard)
if (window.location.hash && window.location.hash.includes('action=179')) {
    console.log("Auto-refresh fallback activated via location.hash");
    setInterval(function () {
        console.log("Auto-refreshing dashboard (fallback)...");
        location.reload();
    }, 10000); // setiap 10 detik
}
