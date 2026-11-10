\pset pager off
set statement_timeout = '5min';
\echo '== database size =='
select current_database() as database, pg_size_pretty(pg_database_size(current_database())) as size;

\echo '== largest tables =='
select
    relname as table,
    pg_size_pretty(pg_total_relation_size(relid)) as total,
    pg_size_pretty(pg_relation_size(relid)) as table_size,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_toast
from pg_catalog.pg_statio_user_tables
order by pg_total_relation_size(relid) desc
limit 40;

\echo '== payment group relation structure =='
select column_name, data_type
from information_schema.columns
where table_name = 'account_move_line_payment_group_to_pay_rel'
order by ordinal_position;

\echo '== payment group relation size =='
select
    c.relname,
    c.reltuples::bigint as estimated_rows,
    pg_size_pretty(pg_total_relation_size(c.oid)) as total,
    pg_size_pretty(pg_relation_size(c.oid)) as heap
from pg_class c
where c.relname = 'account_move_line_payment_group_to_pay_rel';

\echo '== payment group relation indexes =='
select indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) as size, idx_scan
from pg_stat_user_indexes
where relname = 'account_move_line_payment_group_to_pay_rel'
order by pg_relation_size(indexrelid) desc;

\echo '== approximate payment group fanout =='
select payment_group_id, count(*) as to_pay_lines
from account_move_line_payment_group_to_pay_rel
group by payment_group_id
order by count(*) desc
limit 30;

\echo '== attachments by model =='
select
    coalesce(res_model, '(none)') as res_model,
    count(*) as attachments,
    pg_size_pretty(coalesce(sum(file_size), 0)::bigint) as file_size
from ir_attachment
group by coalesce(res_model, '(none)')
order by coalesce(sum(file_size), 0) desc
limit 30;

\echo '== manual studio/custom fields still in database =='
select model, name, ttype
from ir_model_fields
where state = 'manual'
order by model, name;

\echo '== installed non-core/custom-looking modules =='
select name, latest_version
from ir_module_module
where state = 'installed'
  and (
    name like 'ponton_%'
    or name like 'l10n_ar%'
    or name like 'account_%'
    or name like 'web_%'
    or name like 'stock_%'
    or name = 'report_xlsx'
  )
order by name;
