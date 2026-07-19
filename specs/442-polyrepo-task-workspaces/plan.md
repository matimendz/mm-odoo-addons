# Plan

Odoo task: 442
Catalog: not required
Repo: odoo-addons
Change class: A3
Approval: Odoo #442 approved by user 2026-07-19

## Goal
Require isolated Odoo task workspaces for public Odoo addon changes based on
branch `19.0`.

## Approach
Add contribution instructions, PR metadata, hooks and CI contract checks
without touching the existing dirty permanent checkout.

## Data And Contracts
No addon model or view changes. The contribution contract protects `19.0` and
requires complete SDD for durable Odoo behavior.

## Risks And Approvals
The A3 approval covers workflow enforcement only and does not authorize an
addon deploy or Odoo database write.

## Rollout
Merge the clean workspace PR into `19.0` after compile and manifest checks.

## Rollback
Revert the PR; no module upgrade or migration is part of this change.

## Validation
Compile Python, parse manifests, validate hooks and execute both CI jobs.

## Acceptance Mapping
The PR proves mixed base-branch support and leaves the permanent dirty checkout
untouched.
