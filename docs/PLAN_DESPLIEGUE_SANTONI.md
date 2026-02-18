# Plan de Despliegue - SantoniBot en Alimentos Santoni

**Fecha:** 18 de febrero 2026
**Preparado por:** OVA Agency

---

## Resumen

SantoniBot está **100% funcional** con datos de prueba. Para ponerlo en producción con datos reales de Santoni, se necesitan **3 pasos** que toman aproximadamente **2-3 días de trabajo**.

---

## Qué necesitamos de IT de Santoni (ANTES de empezar)

Necesitamos que IT de Santoni **confirme** estos 4 puntos. Solo toma 5 minutos:

| # | Verificación | Detalle |
|---|-------------|---------|
| 1 | **VPN activa** | Que el usuario `OVA` pueda conectarse por FortiClient al gateway `201.249.55.198` |
| 2 | **VM encendida** | Que la VM `192.168.1.26` esté corriendo y acepte SSH (puerto 22) |
| 3 | **Red interna** | Que desde la VM `192.168.1.26` se pueda llegar a `192.168.1.73:5432` (iDempiere) |
| 4 | **Usuario DB** | Que el usuario `ova` tenga permisos SELECT sobre el schema `adempiere` en `idempiere_produccion` |

> **Importante:** Necesitamos a alguien de IT disponible (por teléfono/WhatsApp) durante la primera conexión (~1-2 horas) por si hay que ajustar firewall o permisos. Después de eso, ya no necesitamos asistencia.

---

## Los 3 Pasos

### Paso 1: Conectar VPN y verificar accesos (30 min)

**Quién:** OVA (Luis)
**Requiere IT Santoni:** Sí, en standby

1. Instalar FortiClient VPN en la PC de desarrollo
2. Conectar a `201.249.55.198` con usuario `OVA`
3. Verificar ping a `192.168.1.26` (VM) y `192.168.1.73` (iDempiere)
4. Conectar por SSH a la VM: `ssh accinproa@192.168.1.26`
5. Conectar a iDempiere desde la VM: `psql -h 192.168.1.73 -U ova -d idempiere_produccion`
6. Ejecutar queries de verificación para confirmar que vemos datos reales

**Resultado:** Acceso confirmado a la red de Santoni.

### Paso 2: Explorar datos y mapear tablas (1 día)

**Quién:** OVA (Luis)
**Requiere IT Santoni:** No (solo si hay problemas de permisos)

1. Explorar las tablas de iDempiere por departamento:
   - Ventas: `c_invoice`, `c_bpartner`, `c_payment`, `c_order`
   - Finanzas: `c_bankaccount`, `c_bankstatement`
   - Contabilidad: `fact_acct`, `c_elementvalue`, `gl_journal`
   - RRHH: `c_bpartner` (empleados), `hr_*` (si existen)
   - Producción: `m_production`, `pp_order`
   - Compras: `c_order` (compras), tablas personalizadas
2. Documentar el mapeo: qué tabla de iDempiere corresponde a cada consulta de SantoniBot
3. Actualizar las queries del backend para que funcionen con datos reales
4. Probar cada agente con datos reales

**Resultado:** SantoniBot consulta datos reales de iDempiere.

### Paso 3: Desplegar en la VM (2-3 horas)

**Quién:** OVA (Luis)
**Requiere IT Santoni:** No

1. Conectar por SSH a la VM `192.168.1.26`
2. Ejecutar script de setup: instala Docker, firewall, fail2ban
3. Clonar el repositorio en `/opt/santonibot`
4. Configurar `.env` de producción (API keys, passwords generados)
5. Ejecutar script de deploy: construye y levanta todos los servicios
6. Verificar que `http://192.168.1.26` muestra SantoniBot
7. Crear usuarios para el personal de Santoni

**Resultado:** SantoniBot accesible desde cualquier PC en la red de Santoni.

---

## Después del despliegue

| Tarea | Cuándo | Quién |
|-------|--------|-------|
| Capacitar a usuarios de cada departamento | Semana siguiente | OVA + contacto de cada depto |
| Validar datos con Marlenis (Ventas/Compras) | Primera semana | OVA + Marlenis Figueredo |
| Validar datos de Producción | Primera semana | OVA + contacto de Producción |
| Configurar Claude API (mejor calidad IA) | Cuando Santoni apruebe presupuesto | OVA |
| Integración WhatsApp (Fase 2) | Post-lanzamiento | OVA |

---

## Datos de contacto y acceso (referencia)

| Recurso | IP | Puerto | Usuario |
|---------|-----|--------|---------|
| VPN Gateway | 201.249.55.198 | 443 | OVA |
| VM SantoniBot | 192.168.1.26 | 22 (SSH) | accinproa |
| iDempiere DB | 192.168.1.73 | 5432 | ova (solo lectura) |

---

## Notas técnicas

- El entorno de QA con datos demo se mantiene intacto en la PC de desarrollo
- El sistema detecta automáticamente si está en modo desarrollo (datos demo) o producción (iDempiere)
- SantoniBot **nunca** modifica datos de iDempiere (acceso de solo lectura enforced)
- La IA usa Groq (gratuito) por defecto. Claude (pago, mejor calidad) se activa cambiando una variable
- Backups automáticos de la base de datos interna cada 24 horas
