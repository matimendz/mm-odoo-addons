# Integraciones — Fudo → Odoo y Módulos Custom

## Arquitectura operativa

```
Fudo POS
  (ventas por producto, turnos, consumo por mesa)
        ↓
   fudo-ledger
  (integrado con Fudo API y puente XML-RPC hacia Odoo)
        ↓
   Odoo ERP
  (fuente de verdad: contabilidad, reportes, gestión operativa)
        ↓
  marketing-el-ponton
  (contexto de performance por noche/evento)
```

**Principio:** Fudo es el sistema operativo del día a día (POS, cocina, barra). Odoo centraliza los datos para análisis, contabilidad y gestión. El marketing usa el contexto de Odoo para medir resultados.

---

## Estado actual — Abril 2026

| Integración | Estado |
|-------------|--------|
| Fudo → fudo-ledger (facturación) | Implementado |
| fudo-kitchen-control → Fudo API | Implementado |
| Fudo → Odoo | **Implementado en fudo-ledger vía XML-RPC** |
| Módulos custom El Pontón en Odoo | **ponton_fudo instalado; ponton_event instalado** |

---

## Qué datos de Fudo deben llegar a Odoo

### Datos de ventas
- Ventas por producto / categoría por turno
- Total de consumo por noche (fecha)
- Ticket promedio
- Productos más vendidos (top 10 por semana)
- Métodos de pago

### Datos operativos
- Turnos abiertos y cerrados (horario real de operación)
- Consumo asociado a eventos especiales (con etiqueta de fecha/evento)

### Datos de facturación (ya parcialmente cubiertos por fudo-ledger)
- Facturas emitidas y su estado
- Cuentas corrientes de proveedores o clientes recurrentes

---

## Canal de integración actual

**Implementación actual: fudo-ledger + ponton_fudo**
- `fudo-ledger` ya tiene la integración con Fudo API y acceso a los datos de ventas
- Empuja los datos a Odoo via XML-RPC
- Importa ventas como pedidos de venta (`sale.order`)
- Crea y publica facturas (`account.move`) para ventas facturadas en Fudo
- Crea pagos (`account.payment`) y los concilia usando un wrapper del módulo `ponton_fudo`
- Ventaja: reutiliza el código existente, menor superficie de mantenimiento

**Alternativa futura: módulo Odoo con sync activo**
- Crear un módulo Odoo dedicado que consulte la API de Fudo periódicamente
- Ventaja: la lógica queda centralizada en Odoo
- Desventaja: Odoo necesita acceso directo a la API de Fudo (credenciales adicionales)

**Recomendación:** mantener la integración actual en `fudo-ledger` mientras siga siendo simple de operar. Migrar parte de la lógica a Odoo solo si el sync empieza a requerir workflows propios del ERP.

---

## Módulos custom

### ponton_fudo (operativo)
**Función:** soporte Odoo para trazabilidad Fudo y conciliacion segura desde XML-RPC.
**Implementación:** campos Fudo en pedidos/eventos y wrapper `ponton_fudo_reconcile_lines`.
**Datos sincronizados:** ventas, lineas por producto, facturas y pagos.
**Frecuencia:** diaria (cierre de turno) o near-real-time si la API lo permite

### ponton_event (operativo)
**Función:** vincular noches/eventos del bar con los datos de ventas de barra
**Implementación:** módulo Odoo para eventos/noches operativas
**Beneficio:** poder responder "¿las coproducciones generan más consumo que las noches regulares?"

### el_ponton_crm (prioridad: media-baja)
**Función:** pipeline de leads comerciales (cumpleaños y privados) en Odoo CRM
**Alternativa:** el sistema de issues en markdown (`marketing-el-ponton/content/issues/`) ya cubre esto operativamente; migrar a Odoo CRM solo si el volumen de leads justifica la complejidad adicional

---

## API de Odoo (referencia rápida)

Odoo expone una API XML-RPC en:
- Autenticación: `https://odoo.elponton.com.ar/xmlrpc/2/common`
- Operaciones: `https://odoo.elponton.com.ar/xmlrpc/2/object`

Ejemplo Python para autenticar:
```python
import xmlrpc.client

url = 'https://odoo.elponton.com.ar'
db = 'manso-prod'
username = 'admin'
password = 'XXX'  # desde bóveda de contraseñas

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
# Ejemplo: leer partners
partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[]], {'fields': ['name']})
```

---

## Próximos pasos

1. Agregar mapeos de pago/productos a medida que se sumen empresas o métodos nuevos
2. Monitorear corridas diarias desde `fudo-ledger` y revisar ventas con pago parcial
3. Crear credenciales de API con permisos mínimos si se reemplaza el usuario operativo actual
4. Exportar consumo por noche/evento hacia marketing memory o analytics
5. Decidir si se usa `crm_enterprise` para leads o se mantiene el sistema de issues en markdown
