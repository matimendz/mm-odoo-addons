\pset pager off
set statement_timeout = '5min';
\echo '== critical record counts =='
select 'res_partner' as model, count(*) from res_partner
union all select 'product_template', count(*) from product_template
union all select 'sale_order', count(*) from sale_order
union all select 'sale_order_line', count(*) from sale_order_line
union all select 'account_move', count(*) from account_move
union all select 'account_move_posted', count(*) from account_move where state = 'posted'
union all select 'account_move_line', count(*) from account_move_line
union all select 'account_payment', count(*) from account_payment
union all select 'account_payment_group', count(*) from account_payment_group
union all select 'stock_picking', count(*) from stock_picking
union all select 'stock_move', count(*) from stock_move
union all select 'pos_order', count(*) from pos_order
union all select 'event_event', count(*) from event_event
union all select 'ponton_reserva', count(*) from ponton_reserva
order by model;

\echo '== remaining enterprise-only view modes =='
select id, name, res_model, view_mode
from ir_act_window
where view_mode ~ '(^|,)(gantt|map)(,|$)'
order by id;

\echo '== installed Ponton modules =='
select name, latest_version
from ir_module_module
where state = 'installed' and name like 'ponton_%'
order by name;
