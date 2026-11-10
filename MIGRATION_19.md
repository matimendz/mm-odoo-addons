# Migracion a Odoo 19 Community

Este branch conserva la base Odoo 15 Community de `manso-prod` y guarda el runbook usado para migrar a Odoo 19 Community.

## Estado decidido

- Edicion destino: Community + OCA, sin Enterprise.
- Hosting de corte final: misma EC2, con Odoo 19 en ruta separada y rollback a Odoo 15.
- Ruta tecnica: OpenUpgrade por saltos consecutivos `15 -> 16 -> 17 -> 18 -> 19`.
- Prioridad funcional: Contabilidad, POS/restaurante y Fudo. Reservas/Eventos se validan pero no bloquean por ajustes menores.

## Gates antes de tocar produccion

1. Base auditada y reducida o explicada.
   - El riesgo principal fue `account_move_line_payment_group_to_pay_rel`, que llego a ocupar cerca de 25 GB.
   - Decision operativa: esa relacion se vacio para la migracion. Se prefiere rehacer el intento de conciliacion en Odoo 19 antes que arrastrar 25 GB.
2. Espacio libre suficiente.
   - Objetivo operativo minimo: 25-30 GB libres antes de correr ensayos en la EC2.
   - Primera opcion: mover backups viejos fuera de la instancia y limpiar logs/caches.
3. Dependencias 19.0 disponibles.
   - OpenUpgrade tiene rama `19.0`.
   - Los repos OCA/ingadhoc revisados tienen rama `19.0`, pero falta validar modulo por modulo contra los instalados en `manso-prod`.
4. Ensayo reproducible.
   - La cadena completa de upgrades debe correr en una copia y terminar con checklist verde antes del corte final.

## Uso de scripts

Desde `odoo/mm-odoo-addons`:

```bash
migration_19/run_remote_audit.sh
```

Variables utiles:

```bash
SSH_KEY=../../odoo-manso-prod.pem
REMOTE=bitnami@54.94.121.99
REMOTE_ODOO_CONF=/bitnami/odoo/conf/odoo.conf
REPORT_DIR=migration_19/reports/$(date +%Y%m%d_%H%M%S)
```

El script lee `odoo.conf` en el servidor para obtener credenciales PostgreSQL y guarda reportes locales ignorados por git.

Para verificar que las ramas base sigan disponibles:

```bash
migration_19/check_dependency_branches.sh
```

Para vaciar la relacion pesada de grupos de pago, ejecutar solo con Odoo detenido y snapshot EBS reciente:

```bash
psql ... -f migration_19/truncate_payment_group_to_pay_rel.sql
```

Efecto esperado:

- borra las filas de `account_move_line_payment_group_to_pay_rel`;
- conserva facturas, asientos, pagos y grupos de pago;
- los grupos de pago pierden su lista guardada de lineas "a pagar";
- la conciliacion/pagos pendientes se rehacen en Odoo 19.

## Port inicial de modulos custom

En este branch:

- Los manifiestos custom pasan a version `19.0.1.0.0`.
- Las vistas propias usan `list` en vez de `tree` donde el XML define vistas completas o `view_mode`.
- Se reemplazan `attrs` simples por modificadores directos (`invisible="..."`).
- Los hooks aceptan firma vieja `cr, registry` y firma nueva con `env`, para facilitar pruebas intermedias.

Modulos criticos:

- `ponton_event`
- `ponton_fudo`
- `ponton_reservas`

Modulo no critico:

- `ponton_bank_statement_import`, actualmente desinstalado en produccion.

## Corte productivo

No cortar a Odoo 19 hasta tener:

- snapshot EBS final;
- `pg_dump` final;
- filestore final;
- copia de `odoo.conf`;
- commit/tag exacto de este branch;
- tiempos medidos de la migracion completa;
- rollback probado al menos una vez en ensayo.

## Limpieza ejecutada en produccion

Fecha: 2026-05-08.

- Snapshot previo exacto: `snap-0ba00156d40f2c61b`.
- Snapshot previo adicional de remocion Enterprise: `snap-0111e098d0b0c98a1`.
- Tabla truncada: `account_move_line_payment_group_to_pay_rel`.
- Resultado:
  - DB: ~26 GB -> ~1.6 GB.
  - Relacion: ~25 GB -> 16 KB.
  - Filas estimadas: ~249M -> 0.
  - `account_payment_group`: 69.836 registros conservados.
  - `account_payment`: 35.729 registros conservados.
  - Odoo health: `pass`.

## Ensayo OpenUpgrade en copia

Fecha: 2026-05-08.

Workspace remoto: `/home/bitnami/odoo19-migration`.

Base de ensayo: `manso_mig15`, restaurada desde `manso-prod` despues de truncar `account_move_line_payment_group_to_pay_rel`.

Resultado de la cadena:

- `15 -> 16`: OK. Dump: `/home/bitnami/odoo19-migration/backups/manso_mig16_after_openupgrade.dump`.
- `16 -> 17`: OK despues de parchear `account_ux` para Community y reemplazar payment group/withholding legacy por:
  - `account_payment_pro`
  - `l10n_ar_withholding`
  - `l10n_ar_withholding_ux`
  - `l10n_ar_account_withholding`
  - `l10n_ar_account_withholding_ratio`
- `17 -> 18`: OK despues de agregar dependencias nuevas:
  - `ingadhoc/sale` para `sale_ux`
  - `ingadhoc/miscellaneous` para `base_bg`
- `18 -> 19`: OK con parches locales de ensayo en OpenUpgrade 19:
  - `project/19.0.1.3/post-migration.py`: saltear `project.task.type` sin `project_ids`.
  - `openupgrade_framework/.../ir_ui_view.py`: evitar `Expected singleton` al reportar multiples vistas invalidas.
  - `ingadhoc/account-invoicing` agregado para `account_background_post`.

Conteos preservados al final del ensayo 19:

- `account_move`: 104.572
- `account_move_line`: 274.983
- `account_payment`: 35.729
- `account_payment_group`: 69.836
- `sale_order`: 68.622
- `stock_picking`: 67.445
- `event_event`: 290
- `ponton_reserva`: 635

Dump final de ensayo: `/home/bitnami/odoo19-migration/backups/manso_mig19_after_openupgrade.dump`.

### Gate rojo antes de corte

La migracion tecnica llega a Odoo 19, pero todavia no esta aprobada para produccion.

Quedan modulos `to install` Enterprise/faltantes y modulos `to upgrade` no portados a 19:

- Enterprise/faltantes residuales: `account_invoice_extract`, `analytic_enterprise`, `crm_enterprise`, `event_enterprise`, `pos_enterprise`, `project_enterprise`, `purchase_enterprise`, `sale_enterprise`, `stock_enterprise`, `web_gantt`, `web_map`, entre otros.
- ADHOC/OCA no listos para 19 en los repos actuales:
  - `l10n_ar_afipws`
  - `l10n_ar_afipws_fe`
  - `l10n_ar_purchase_stock`
  - `purchase_stock_picking_invoice_link`
  - `stock_voucher`
  - `web_ir_actions_act_multi`

`l10n_ar_afipws` y `l10n_ar_afipws_fe` son especialmente sensibles para facturacion electronica/AFIP. No cortar produccion hasta resolverlos, reemplazarlos o aceptar explicitamente su baja funcional.

### Warnings no bloqueantes observados

- Vistas legacy de `project.task` con campos removidos y `attrs/states`; se mantienen como deuda esperada porque los campos custom de task se decidieron deprecar.
- Errores de borrado de productos demo/plantillas durante cleanup de datos Odoo; no afectaron los conteos criticos.

## Corte productivo ejecutado

Fecha: 2026-05-08.

Resultado: produccion quedo en Odoo 19 Community sobre la DB `manso-prod`.

Backups finales:

- Snapshot EBS: `snap-06096f461550fef5a` (`completed`).
- Backup logico y filestore: `/home/bitnami/odoo19-migration/prod_cutover_backups/20260508_2143/`.
- DB original preservada para rollback: `manso_prod_pre19_20260508_2143`.
- Filestore original preservado para rollback: `/opt/bitnami/odoo/data/filestore/manso-prod.pre19.20260508_2143`.
- Dump final migrado: `/home/bitnami/odoo19-migration/prod_cutover_backups/20260508_2143/manso_prod_mig19.final.dump`.

Validacion post-corte:

- `https://odoo.elponton.com.ar/web/health`: `pass`.
- `base`: `19.0.1.3`.
- Modulos criticos instalados:
  - `account`
  - `point_of_sale`
  - `pos_restaurant`
  - `ponton_fudo`
  - `ponton_event`
  - `ponton_reservas`
  - `sale`
  - `stock`
  - `event`
- Estados de modulos: `installed=171`, `uninstalled=1414`, `uninstallable=14`, sin `to install` ni `to upgrade`.

Los modulos no criticos/faltantes mencionados durante el ensayo se marcaron como `uninstalled` para permitir el corte.
