-- Disable orphaned Odoo 15 settings views that break Odoo 19 settings.
--
-- account_payment_group is no longer installed after the Community 19 cutover,
-- but its res.config.settings inherited view can remain active in the database.
-- The view targets legacy <div id="bank_cash"> nodes that do not exist in
-- Odoo 19, causing res.config.settings.get_views() to fail.

update ir_ui_view
   set active = false,
       write_date = now()
 where id in (
       select res_id
         from ir_model_data
        where model = 'ir.ui.view'
          and module = 'account_payment_group'
          and name = 'res_config_settings_view_form'
 );
