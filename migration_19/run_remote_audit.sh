#!/usr/bin/env bash
set -euo pipefail

SSH_KEY="${SSH_KEY:-../../odoo-manso-prod.pem}"
REMOTE="${REMOTE:-bitnami@54.94.121.99}"
REMOTE_ODOO_CONF="${REMOTE_ODOO_CONF:-/bitnami/odoo/conf/odoo.conf}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR="${REPORT_DIR:-$SCRIPT_DIR/reports/$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$REPORT_DIR"

run_sql() {
    local sql_file="$1"
    local out_file="$2"
    ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$REMOTE" \
        "REMOTE_ODOO_CONF='$REMOTE_ODOO_CONF' bash -s" > "$out_file" < <(
            cat <<'REMOTE_SCRIPT'
set -euo pipefail
conf="$REMOTE_ODOO_CONF"
read_conf() {
    awk -F= -v key="$1" '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
        value=$2
        sub(/^[[:space:]]*/, "", value)
        sub(/[[:space:]]*$/, "", value)
        print value
        exit
    }' "$conf"
}
db_host="$(read_conf db_host)"
db_port="$(read_conf db_port)"
db_name="$(read_conf db_name)"
db_user="$(read_conf db_user)"
db_password="$(read_conf db_password)"
export PGPASSWORD="$db_password"
psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -v ON_ERROR_STOP=1 -P pager=off
REMOTE_SCRIPT
            cat "$sql_file"
        )
}

echo "Writing migration audit reports to $REPORT_DIR"
run_sql "$SCRIPT_DIR/audit_database.sql" "$REPORT_DIR/audit_database.txt"
run_sql "$SCRIPT_DIR/critical_counts.sql" "$REPORT_DIR/critical_counts.txt"
run_sql "$SCRIPT_DIR/payment_group_relation_investigation.sql" "$REPORT_DIR/payment_group_relation_investigation.txt"

ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$REMOTE" \
    "df -h / /bitnami /opt/bitnami 2>/dev/null; echo; free -h; echo; sudo du -xh --max-depth=2 /bitnami /opt/bitnami /home/bitnami 2>/dev/null | sort -h | tail -80" \
    > "$REPORT_DIR/disk_and_memory.txt"

echo "Done."
