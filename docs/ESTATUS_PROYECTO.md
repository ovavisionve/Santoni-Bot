# SantoniBot - Estatus del Proyecto

**Fecha:** 16 de marzo 2026
**Avance general:** ~97% Fase 1 completada
**Estado:** Sistema desplegado en servidor, conectado a iDempiere real, en fase de validacion con datos reales

---

## Resumen Ejecutivo

| Area | Estado | % |
|------|--------|---|
| Backend - Core (API, Auth, RBAC) | ✅ Completo | 100% |
| Backend - 7 Agentes IA | ✅ Completo, conectados a iDempiere real | 100% |
| Backend - Datos demo | ✅ Completo (usado para dev/testing) | 100% |
| Frontend - Core (Chat, Admin, Export) | ✅ Completo | 100% |
| Selector de agentes (reemplazo orchestrator) | ✅ Completo | 100% |
| Conexion iDempiere real | ✅ Completo (7/7 agentes conectados) | 100% |
| Permisos iDempiere (roles/ventanas) | ✅ Completo | 100% |
| Docker / Deploy / Servidor | ✅ Desplegado en 192.168.1.26 | 100% |
| Seguridad | ✅ Hardened | 100% |
| Testing | ✅ 150+ tests | 95% |
| CI/CD | ✅ GitHub Actions + Coolify | 100% |
| Documentacion | ✅ Completa | 100% |
| **Validacion con datos reales** | **🔄 En curso** | **60%** |
| WhatsApp | ⏳ Fase 2, post-lanzamiento | 0% |

> **Estado actual:** El sistema esta desplegado y funcionando en el servidor de Santoni
> (192.168.1.26), conectado al iDempiere real (192.168.1.73). Los 7 agentes consultan
> datos reales. Estamos en **fase de validacion**: comparando las respuestas del bot
> contra datos verificados de iDempiere para asegurar precision antes de liberar a usuarios finales.

---

## Cambios Recientes (Febrero - Marzo 2026)

### Marzo 2026 (semana del 10-16)

- **Fix critico saldos bancarios**: Las cuentas USD en iDempiere usan iso_codes distintos por organizacion (DOL, DoL, Dol, USA, dol, DLA, Dla, US.). Se corrigio la agrupacion usando c_currency_id en vez de iso_code. Ahora todas las cuentas USD se muestran correctamente.
- **Fix alucinacion morosos**: Antes el LLM recibia 50 facturas individuales e inventaba los nombres de clientes y montos al agregar. Se creo `build_top_delinquent_clients` que agrega en SQL (GROUP BY cliente). Ahora los nombres y montos son 100% reales.
- **Fix alucinacion proveedores CxP**: El LLM inventaba un "Top 5 Proveedores" con nombres falsos. Se agrego top 10 proveedores y top 10 clientes morosos reales al resumen financiero.
- **Fix keyword "deben"**: "¿Cuanto nos deben los clientes?" caia al fallback de ventas. Se agrego "deben" y "moroso" a las keywords de cuentas vencidas.
- **Eliminacion del orquestador**: El usuario ahora selecciona el agente directamente desde pestanas en la UI. El orquestador solo se usa como fallback para API externas.
- **Permisos iDempiere**: Roles y ventanas de iDempiere se mapean a permisos del bot. 31 capabilities mapeadas a 7 agentes. Importacion masiva de usuarios.
- **Anti-alucinacion nivel 4**: Deteccion de documentos falsos, lotes falsos, "no tengo acceso", tablas inventadas, y re-invocacion con prompt reforzado.
- **Expansion compras_insumos**: Ordenes de compra pendientes, comparacion de precios entre proveedores, estado de pago de facturas, fallback sin fecha.
- **Fix docstatus**: `docstatus = 'CO'` expandido a `docstatus IN ('CO', 'CL')` en TODAS las queries (facturas pagadas cambian a 'CL' en iDempiere).
- **Datos historicos locales**: Sistema de cache para datos anteriores a marzo 2026 en DB local.
- **Script de verificacion**: `verify_data.py` y `check_finanzas` para comparar datos del bot vs SQL directo.

### Febrero 2026

- Conexion exitosa a iDempiere real (queries de nomina, ventas, compras)
- Follow-ups inteligentes con herencia de contexto temporal
- Confidence score + dataset de 356 escenarios de validacion
- Separacion de compras por moneda (VES/USD)
- Inventario desde m_storageonhand
- Correccion de multiples bugs reportados por usuarios reales
- Script de pruebas en vivo (65 preguntas, 7 agentes)

---

## Validacion de Agentes con Datos Reales

Cada agente se valida comparando las respuestas del bot contra consultas SQL directas a iDempiere.

### Estado de Validacion por Agente

| Agente | Funciones | Validado | Resultado | Notas |
|--------|-----------|----------|-----------|-------|
| **Ventas** | 4 funciones | ✅ Completo | ✅ Datos correctos | Top clientes, facturacion, cobranza, CxC vencidas |
| **Finanzas** | 2 funciones | ✅ Completo | ✅ Datos correctos | Saldos bancarios, CxC, CxP, top morosos/proveedores |
| **Contabilidad** | 2 funciones | ✅ Previamente | ✅ Funcional | Balance, estado de resultados |
| **RRHH** | 7 funciones | ✅ Previamente | ✅ Funcional | Empleados, nomina, vacaciones, cumpleaneros |
| **Produccion** | 3 funciones | ✅ Previamente | ✅ Funcional | Ordenes, inventario |
| **Compras Insumos** | 6 funciones | 🔄 Pendiente | - | Siguiente en validar |
| **Compras Productores** | 4 funciones | 🔄 Pendiente | - | Siguiente en validar |

### Bugs Encontrados y Corregidos en Validacion

| Bug | Agente | Impacto | Estado |
|-----|--------|---------|--------|
| iso_code bancario (DOL/DoL/etc no agrupaban como USD) | Finanzas | 17 de 24 cuentas USD aparecian en "Otras Monedas" | ✅ Corregido |
| Keyword "deben" no activaba CxC vencidas | Ventas | Pregunta "cuanto nos deben" devolvia datos de ventas (alucinacion total) | ✅ Corregido |
| Top morosos inventados por el LLM | Ventas | Nombres y montos 100% falsos al agregar facturas | ✅ Corregido |
| Top proveedores CxP inventados por el LLM | Finanzas | Nombres falsos como "Agroinsumos del Lago" | ✅ Corregido |
| docstatus excluia facturas cerradas | Todos | Facturas pagadas (CL) no aparecian en reportes | ✅ Corregido |
| Acentos en busqueda de productos | Compras | "maiz" no encontraba "Maiz" | ✅ Corregido |

---

## Preguntas de Prueba para Validacion por Departamento

**Instrucciones para los evaluadores:** Seleccione la pestana del agente correspondiente en el chat, haga la pregunta, y compare la respuesta del bot contra los datos reales que usted maneja. Anote cualquier diferencia en montos, nombres, o datos faltantes.

### VENTAS (Pestana: Ventas)

#### Preguntas basicas
1. "¿Cuales son los top 20 clientes del 2026?"
2. "¿Cuales son los top 20 clientes en dolares?"
3. "¿Cuales son los top 10 clientes de enero 2026?"
4. "¿Cuanto se ha facturado en 2026?"
5. "¿Cuanto se ha facturado en bolivares en 2026?"

#### Preguntas por zona y organizacion
6. "Top 10 clientes de la zona Portuguesa"
7. "Top 10 clientes de la zona Falcon"
8. "Ventas de INPROA SANTONI en febrero 2026"
9. "Ventas de InproMaiz en enero 2026"
10. "Resumen de ventas por zona en 2026"

#### Cobranza y morosos
11. "¿Cuanto se ha cobrado en marzo 2026?"
12. "¿Cuanto se ha cobrado en dolares en 2026?"
13. "¿Cuanto nos deben los clientes?"
14. "¿Quienes son los morosos?"
15. "¿Cuales son las cuentas por cobrar vencidas?"

#### Follow-ups (hacer despues de una pregunta anterior)
16. Despues de preguntar por enero: "¿y en febrero?"
17. Despues de preguntar top clientes: "¿y en dolares?"
18. Despues de preguntar una zona: "¿y por region?"

#### Que verificar
- [ ] Los nombres de clientes coinciden con iDempiere
- [ ] Los montos totales son correctos (comparar con reportes del ERP)
- [ ] Las zonas asignadas son correctas
- [ ] La separacion VES/USD es correcta
- [ ] Los follow-ups mantienen el contexto (mes, zona, etc.)

---

### FINANZAS (Pestana: Finanzas)

#### Preguntas basicas
1. "¿Cuales son los saldos bancarios?"
2. "¿Cuales son las cuentas por cobrar?"
3. "¿Cuales son las cuentas por pagar?"
4. "Resumen financiero de febrero 2026"
5. "Resumen financiero de enero 2026"

#### Morosos y proveedores
6. "¿Quienes son los principales morosos?"
7. "¿Cuales son las facturas vencidas por cobrar?"
8. "¿A quienes les debemos mas?"

#### Que verificar
- [ ] Saldos bancarios coinciden con los del sistema (VES y USD por separado)
- [ ] Total VES y USD son correctos
- [ ] Cuentas bancarias muestran nombre del banco, numero y organizacion correctos
- [ ] Top morosos coinciden con datos reales (ALIMENTOS PARADAYS, GRUPO SONREIR 123, etc.)
- [ ] Top proveedores CxP coinciden (ANTONIO JUAN PLASENCIA RIVAS, MONTANA GRAFICA, etc.)
- [ ] No aparecen nombres de empresas que no existen en el sistema

---

### CONTABILIDAD (Pestana: Contabilidad)

#### Preguntas basicas
1. "Balance general de febrero 2026"
2. "Estado de resultados de enero 2026"
3. "Detalle de la cuenta 1.01.01"
4. "Movimientos de la cuenta 4.01.01 en febrero 2026"
5. "Libro mayor de enero 2026"

#### Que verificar
- [ ] Las cuentas contables coinciden con el plan de cuentas de iDempiere
- [ ] Los montos debito/credito son correctos
- [ ] El balance cuadra (Activo = Pasivo + Capital)

---

### RRHH (Pestana: RRHH)

#### Preguntas basicas
1. "¿Cuantos empleados activos hay?"
2. "Listado de empleados del departamento de produccion"
3. "¿Quienes cumplen anos en marzo?"
4. "Resumen de nomina de febrero 2026"
5. "¿Cuantos empleados se han retirado en 2026?"

#### Preguntas especificas
6. "Empleados con cargo de operador"
7. "Resumen de vacaciones pendientes"
8. "Nomina de enero 2026"
9. "¿Cuantos empleados hay por departamento?"

#### Que verificar
- [ ] Cantidad de empleados activos coincide con iDempiere
- [ ] Nombres y cargos son correctos
- [ ] Montos de nomina coinciden
- [ ] Cumpleaneros del mes son correctos
- [ ] No aparecen empleados que ya no estan en la empresa

---

### PRODUCCION (Pestana: Produccion)

#### Preguntas basicas
1. "Ordenes de produccion de febrero 2026"
2. "Ordenes de produccion de enero 2026"
3. "¿Cual es el inventario actual?"
4. "Inventario de productos terminados"
5. "Resumen de produccion del 2026"

#### Que verificar
- [ ] Ordenes de produccion coinciden con el sistema
- [ ] Cantidades producidas son correctas
- [ ] Stock de inventario coincide con iDempiere (m_storageonhand)

---

### COMPRAS INSUMOS (Pestana: Compras Insumos)

#### Preguntas basicas
1. "¿Cuanto se ha comprado en insumos en 2026?"
2. "Compras de insumos de febrero 2026"
3. "Compras de insumos en dolares en 2026"
4. "¿Cuales son las ordenes de compra pendientes?"
5. "Historial de compras de polietileno"

#### Preguntas avanzadas
6. "Comparacion de precios de polietileno entre proveedores"
7. "¿Cuales facturas de compra estan pendientes de pago?"
8. "Compras de insumos de INPROA SANTONI en febrero 2026"
9. "¿Que facturas de compra estan vencidas?"
10. "Historial de compras de sal en 2025"

#### Que verificar
- [ ] Montos de compras coinciden con iDempiere
- [ ] Nombres de proveedores son correctos
- [ ] Productos coinciden con los del sistema
- [ ] Separacion VES/USD es correcta
- [ ] Ordenes de compra pendientes coinciden con el modulo de compras

---

### COMPRAS PRODUCTORES (Pestana: Compras Productores)

#### Preguntas basicas
1. "¿Cuanto se ha comprado a productores en 2026?"
2. "Compras de arroz a productores en febrero 2026"
3. "Compras de maiz a productores en 2026"
4. "¿Cuales productores estan registrados?"
5. "¿Cuales productores tienen pagos pendientes?"

#### Preguntas especificas
6. "Analisis de precios de arroz por productor en 2026"
7. "Compras de productores de INPROA SANTONI"
8. "Compras de productores de InproMaiz en enero 2026"
9. "¿Cuanto se le debe al productor [nombre]?"

#### Que verificar
- [ ] Nombres de productores coinciden con iDempiere
- [ ] Montos y cantidades de compra son correctos
- [ ] Precios por kilogramo son razonables
- [ ] Pagos pendientes coinciden con el sistema
- [ ] Separacion arroz/maiz es correcta

---

## Formato del Reporte de Validacion

Para cada pregunta de prueba, el evaluador debe reportar:

| Campo | Descripcion |
|-------|-------------|
| **Pregunta** | La pregunta exacta que hizo |
| **Agente** | Pestana que selecciono |
| **Respuesta correcta?** | Si / No / Parcial |
| **Diferencias encontradas** | Montos incorrectos, nombres que no existen, datos faltantes |
| **Dato esperado** | El valor correcto segun iDempiere |
| **Comentarios** | Observaciones adicionales |

---

## Arquitectura Actual del Sistema

```
Usuario → Frontend (Next.js) → API (FastAPI) → Agente seleccionado → SQL a iDempiere → Respuesta
                                    ↓
                              Permisos RBAC + iDempiere roles
                                    ↓
                              Auditoria (cada consulta)
```

### Flujo de una consulta:
1. Usuario selecciona pestana del agente (ej: "Ventas")
2. Escribe su pregunta en lenguaje natural
3. El agente extrae parametros (fecha, zona, moneda, organizacion)
4. Ejecuta queries SQL contra iDempiere (read-only)
5. Formatea los datos reales en tablas markdown
6. El LLM presenta los datos con contexto y sugerencias
7. El usuario puede exportar a CSV, Excel o PDF

### Proveedores de IA

| Proveedor | Modelo | Uso |
|-----------|--------|-----|
| OpenRouter | DeepSeek Chat v3 | Produccion (recomendado) |
| Groq | Llama 3.3 70B | Alternativa gratuita |
| Anthropic | Claude | Analisis de documentos |

---

## Datos Reales Verificados (Referencia para Validacion)

Estos son datos reales extraidos directamente de iDempiere el 14 de marzo de 2026,
para que los evaluadores tengan referencia de lo que el bot deberia responder:

### Saldos Bancarios
- **Total VES**: Bs. 54.185.392,67 (322 cuentas activas)
- **Total USD**: $146.133,86 (24 cuentas, 4 con saldo > 0)
- Mayor saldo positivo VES: BANCO DE VENEZUELA - INPROA SANTONI (Bs. 41.787.671,76)
- Mayor saldo negativo VES: BANCO BANESCO - INPROA SANTONI (-Bs. 37.069.676,54)

### Cuentas por Cobrar (CxC)
- **Total pendiente**: 11.200 facturas = Bs. 7.866.915.791,82
  - VES: 7.963 facturas (Bs. 7.800M)
  - USD: 3.236 facturas ($18.5M)
- **Vencidas**: 9.284 facturas (81% del total)
- **Top 3 morosos**: ALIMENTOS PARADAYS (Bs. 570M), GRUPO SONREIR 123 (Bs. 389M), LACTEOS JUNIOR (Bs. 250M)

### Cuentas por Pagar (CxP)
- **Total pendiente**: 1.419 facturas = Bs. 69.347.164,24
  - VES: 331 facturas (Bs. 61.5M)
  - USD: 1.088 facturas ($7.9M)
- **Vencidas**: 918 facturas (65% del total)
- **Top 3 proveedores**: ANTONIO JUAN PLASENCIA RIVAS (Bs. 24.1M), MONTANA GRAFICA (Bs. 11.0M), ALVARO LUIS RIERA YEPEZ (Bs. 3.7M)

### Facturacion 2026 (ene-mar YTD)
- **Ventas VES**: 5.494 facturas por Bs. 8.700M
- **Ventas USD**: 5.427 facturas por $21.0M
- **Compras VES**: 1.089 facturas por Bs. 3.000M
- **Compras USD**: 2.991 facturas por $6.1M

> **Nota**: Estos datos son del 14 de marzo. Los datos del bot pueden variar ligeramente
> si se consultan en una fecha posterior porque iDempiere se actualiza en tiempo real.

---

## Pendiente

### Validacion en curso (prioridad alta)
- [ ] Completar validacion de Compras Insumos (6 funciones)
- [ ] Completar validacion de Compras Productores (4 funciones)
- [ ] Reducir alucinaciones residuales del LLM (embellecimiento menor con stats inventadas)

### Pendiente tecnico (prioridad media)
- [ ] Tests E2E (login -> chat -> export)
- [ ] Integrar Sentry (monitoreo de errores en produccion)
- [ ] Mapeo completo de tablas iDempiere (algunas queries en ajuste)

### Fase 2 (post-lanzamiento)
- [ ] Integracion WhatsApp Business API
- [ ] Analisis de documentos con Claude API

---

## Como Desplegar Cambios

```bash
# En el servidor 192.168.1.26:
cd /opt/santonibot
git pull origin main              # o la rama con los cambios
docker compose build --no-cache backend frontend
docker compose up -d
docker compose logs backend --tail 50   # Verificar que arranco bien
```

---

## Contacto

- **Desarrollo**: OVA Agency
- **Repositorio**: GitHub (privado)
- **Servidor**: 192.168.1.26 (requiere VPN FortiClient para acceso remoto)
