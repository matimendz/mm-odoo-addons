# manso-addons — Addons Odoo de El Pontón

Repositorio de addons para la instancia Odoo de El Pontón.

**Repositorio git:** `git@github.com:matimendz/mm-odoo-addons.git`
**Instancia Odoo:** `https://odoo.elponton.com.ar`

---

## Estructura

```
manso-addons/
└── third/
    ├── odoo-argentina/ → submodule ingadhoc — facturación electrónica AFIP (no inicializado)
    ├── odoo-argentina-ee/ → submodule ingadhoc EE (no inicializado)
    ├── odoo-argentina-ce/ → submodule ingadhoc CE (no inicializado)
    ├── account-payment/ → submodule ingadhoc (no inicializado)
    ├── account-financial-tools/ → submodule ingadhoc (no inicializado)
    ├── argentina-sale/ → submodule ingadhoc (no inicializado)
    ├── reporting-engine/ → submodule OCA (no inicializado)
    ├── stock/ → submodule ingadhoc (no inicializado)
    ├── stock-logistics-workflow/ → submodule OCA (no inicializado)
    ├── web/ → submodule OCA (no inicializado)
    ├── sign/ → fork matimendz de OCA/sign — sign_oca para firma online de contratos
    └── shift-planning/ → fork matimendz de OCA/shift-planning — hr_shift migrado a 19.0
```

Los módulos custom de El Pontón viven al nivel raíz del repositorio. En producción ya están instalados `ponton_fudo`, `ponton_event` y `ponton_reservas`; `ponton_event_contracts` agrega contratos de coproducción sobre `ponton_event` y OCA `sign_oca`. Ver `INTEGRACIONES.md` para el estado operativo de la integración Fudo → Odoo.

---

## Estado Enterprise

Odoo Enterprise fue removido de producción y del repositorio. No agregar `third/enter` ni dependencias Enterprise nuevas.

Para la migración a Odoo 19 Community, usar el runbook de [MIGRATION_19.md](MIGRATION_19.md).

---

## Cómo agregar un módulo custom

1. Crear una carpeta para el módulo en `third/` o en un directorio propio (ej: `custom/el_ponton_events/`)
2. Estructura mínima de un módulo Odoo:
   ```
   el_ponton_events/
   ├── __manifest__.py
   ├── __init__.py
   ├── models/
   │   └── __init__.py
   └── views/
   ```
3. Agregar la ruta del directorio padre al `addons_path` en el archivo de configuración de Odoo (`odoo.conf`)
4. Instalar el módulo desde la interfaz de Odoo (Configuración → Activar modo desarrollador → Actualizar lista de aplicaciones)

---

## Cómo conectarse a la instancia

- URL: `https://odoo.elponton.com.ar`
- Credenciales de admin: en la bóveda de contraseñas del equipo
- API REST de Odoo: disponible en `https://odoo.elponton.com.ar/web/dataset/call_kw`
- Documentación de la API: `https://www.odoo.com/documentation/17.0/developer/api/external_api.html`

---

## Ver también

- [INTEGRACIONES.md](INTEGRACIONES.md) — estado operativo de integración Fudo → Odoo y módulos custom
- [SUBMODULES.md](SUBMODULES.md) — estado de los submodules de Argentina y cómo inicializarlos
- [../../marketing-el-ponton/docs/secrets.md](../../marketing-el-ponton/docs/secrets.md) — gestión de credenciales
