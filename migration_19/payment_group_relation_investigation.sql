\pset pager off
set statement_timeout = '5min';

\echo '== field metadata =='
select model, name, relation, relation_table, column1, column2, compute, store
from ir_model_fields
where relation_table = 'account_move_line_payment_group_to_pay_rel'
   or name ilike '%to_pay%'
order by model, name;

\echo '== largest payment groups by to-pay lines =='
select rel.payment_group_id, count(*) as to_pay_lines
from account_move_line_payment_group_to_pay_rel rel
group by rel.payment_group_id
order by count(*) desc
limit 50;

\echo '== payment group details for largest groups =='
with largest as (
    select rel.payment_group_id, count(*) as to_pay_lines
    from account_move_line_payment_group_to_pay_rel rel
    group by rel.payment_group_id
    order by count(*) desc
    limit 50
)
select
    pg.id,
    pg.name,
    pg.state,
    pg.payment_date,
    pg.partner_id,
    largest.to_pay_lines
from largest
join account_payment_group pg on pg.id = largest.payment_group_id
order by largest.to_pay_lines desc, pg.id;

\echo '== relation age distribution by payment group date =='
select
    date_trunc('month', pg.payment_date)::date as month,
    count(distinct pg.id) as payment_groups,
    count(*) as relation_rows
from account_move_line_payment_group_to_pay_rel rel
join account_payment_group pg on pg.id = rel.payment_group_id
group by date_trunc('month', pg.payment_date)::date
order by month desc nulls last
limit 80;

\echo '== candidate reduction if only draft groups keep to-pay lines =='
select
    pg.state,
    count(distinct pg.id) as payment_groups,
    count(*) as relation_rows,
    pg_size_pretty((count(*) * 110)::bigint) as rough_heap_and_index_estimate
from account_move_line_payment_group_to_pay_rel rel
join account_payment_group pg on pg.id = rel.payment_group_id
group by pg.state
order by relation_rows desc;
