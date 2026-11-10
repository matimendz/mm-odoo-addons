\pset pager off
set lock_timeout = '30s';
set statement_timeout = '20min';

\echo '== before truncate =='
select
    pg_size_pretty(pg_total_relation_size('account_move_line_payment_group_to_pay_rel')) as total_size,
    (select reltuples::bigint from pg_class where relname = 'account_move_line_payment_group_to_pay_rel') as estimated_rows;

\echo '== truncating account_move_line_payment_group_to_pay_rel =='
truncate table account_move_line_payment_group_to_pay_rel;

\echo '== refreshing stats =='
analyze account_move_line_payment_group_to_pay_rel;

\echo '== after truncate =='
select
    pg_size_pretty(pg_total_relation_size('account_move_line_payment_group_to_pay_rel')) as total_size,
    (select reltuples::bigint from pg_class where relname = 'account_move_line_payment_group_to_pay_rel') as estimated_rows;
