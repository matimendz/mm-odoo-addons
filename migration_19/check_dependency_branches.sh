#!/usr/bin/env bash
set -euo pipefail

branches=(16.0 17.0 18.0 19.0)
repos=(
    "https://github.com/OCA/OpenUpgrade.git"
    "https://github.com/ingadhoc/odoo-argentina.git"
    "https://github.com/ingadhoc/account-payment.git"
    "https://github.com/OCA/reporting-engine.git"
    "https://github.com/OCA/web.git"
    "https://github.com/OCA/stock-logistics-workflow.git"
    "https://github.com/ingadhoc/stock.git"
    "https://github.com/ingadhoc/account-financial-tools.git"
    "https://github.com/ingadhoc/argentina-sale.git"
    "https://github.com/ingadhoc/odoo-argentina-ee.git"
    "https://github.com/ingadhoc/odoo-argentina-ce.git"
)

for repo in "${repos[@]}"; do
    printf '== %s\n' "$repo"
    for branch in "${branches[@]}"; do
        if git ls-remote --exit-code --heads "$repo" "refs/heads/$branch" >/dev/null; then
            printf '  %-4s yes\n' "$branch"
        else
            printf '  %-4s no\n' "$branch"
        fi
    done
done
