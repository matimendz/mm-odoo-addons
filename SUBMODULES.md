# Submodules de Argentina — Estado

El repositorio `mm-odoo-addons` tiene 14 submodules declarados en `.gitmodules`.

**Estado en el servidor de producción:** ✅ Inicializados y activos en el `addons_path` de Odoo 15.
**Estado local (este repo):** ⚠️ Directorios vacíos — los submodules no están inicializados localmente.

El `odoo.conf` del servidor incluye explícitamente en `addons_path`:
`odoo-argentina`, `account-payment`, `reporting-engine`, `web`, `stock-logistics-workflow`, `stock`, `account-financial-tools`.

---

## Submodules declarados

| Submodule | Fuente | Propósito |
|-----------|--------|----------|
| `third/odoo-argentina` | ingadhoc | Localización Argentina: AFIP, facturación electrónica, liquidaciones |
| `third/odoo-argentina-ee` | ingadhoc | Versión Enterprise de la localización Argentina |
| `third/odoo-argentina-ce` | ingadhoc | Versión Community de la localización Argentina |
| `third/account-payment` | ingadhoc | Gestión de pagos (cheques, retenciones, percepciones) |
| `third/account-financial-tools` | ingadhoc | Herramientas contables adicionales |
| `third/argentina-sale` | ingadhoc | Órdenes de venta con lógica Argentina |
| `third/reporting-engine` | OCA | Motor de reportes custom (Qweb, XLS, PDF) |
| `third/stock` | ingadhoc | Gestión de stock con ajustes para Argentina |
| `third/stock-logistics-workflow` | OCA | Flujos de logística y stock |
| `third/web` | OCA | Mejoras de la interfaz web de Odoo |
| `third/sign` | fork matimendz de OCA/sign | Firma online Community con `sign_oca` para contratos |

---

## Prioridad de inicialización

### Prioridad ALTA — inicializar cuando se configure facturación electrónica

**`third/odoo-argentina-ee`** (o `odoo-argentina` si se usa versión Community)
- Habilita la facturación electrónica con AFIP (obligatoria en Argentina para empresas)
- Incluye: tipos de documentos fiscales, puntos de venta electrónicos, IIBB, padrones, reportes AFIP
- Requiere configurar las credenciales de AFIP (CUIT + certificado digital)

**`third/account-payment`**
- Cheques propios, cheques de terceros, retenciones y percepciones
- Prácticamente obligatorio si se operan pagos en Argentina

**`third/account-financial-tools`**
- Herramientas contables que complementan la localización Argentina

### Prioridad MEDIA — inicializar cuando se necesiten

**`third/reporting-engine`** (OCA)
- Permite crear reportes custom en formato XLS, PDF o QWeb
- Inicializar cuando se necesite exportar reportes que Odoo no ofrece nativamente

**`third/sign`** (fork matimendz de OCA/sign)
- Requerido por `ponton_event_contracts` para contratos de coproducción con firma online
- Usa branch `19.0-oca-port`, basado en OCA `18.0`, porque la rama `19.0` de `OCA/sign` existe pero todavía no trae `sign_oca`
- Inicializar antes de instalar `ponton_event_contracts`

**`third/argentina-sale`**
- Lógica de ventas con particularidades argentinas (condiciones de pago, etc.)

### Prioridad BAJA — evaluar necesidad real antes de inicializar

**`third/stock`**, **`third/stock-logistics-workflow`**, **`third/web`**, **`third/odoo-argentina-ce`**
- Inicializar solo si hay un caso de uso específico
- El módulo `stock` de ingadhoc agrega funcionalidad por encima del stock estándar de Odoo

---

## Cómo inicializar un submodule

```bash
# Desde la raíz del repo manso-addons
cd /home/mmendez/dev/el-ponton/odoo/manso-addons

# Inicializar un submodule específico
git submodule update --init third/odoo-argentina-ee

# Inicializar todos (no recomendado — son muchos)
git submodule update --init

# Ver el estado actual de todos los submodules
git submodule status
```

---

## Versiones de Odoo

Antes de inicializar los submodules, **verificar la versión de Odoo en producción**:
- En `odoo.elponton.com.ar`: Configuración → Información técnica → Versión de Odoo
- Los submodules de ingadhoc/OCA tienen ramas por versión (ej: `16.0`, `17.0`)
- Al inicializar, asegurarse de que el submodule apunte a la rama correcta

Para cambiar la rama de un submodule:
```bash
cd third/odoo-argentina-ee
git checkout 17.0  # o la versión que corresponda
```

---

## Configuración post-inicialización

Después de inicializar los submodules de Argentina:

1. **Agregar la ruta al `addons_path`** en el `odoo.conf` del servidor:
   ```
   addons_path = /opt/odoo/addons,/home/bitnami/manso-addons/third/odoo-argentina-ee,...
   ```

2. **Reiniciar Odoo** para que detecte los nuevos módulos

3. **Actualizar la lista de módulos** desde Odoo (Configuración → Modo desarrollador → Actualizar lista de aplicaciones)

4. **Instalar los módulos** necesarios (`l10n_ar_edi`, `account_payment`, etc.)

5. **Configurar las credenciales de AFIP** para facturación electrónica (certificado digital + CUIT)

---

## Importante: licencias

- Módulos de **ingadhoc**: LGPL-3 (open source, compatible con Odoo Enterprise)
- Módulos de **OCA**: revisar licencia por módulo; `sign_oca` usa AGPL-3
- Módulos en `third/enter/` (Odoo Enterprise): OEEL-1 (propietario, requiere suscripción activa)
