# Registro de Bugs — SantoniBot

> **Documento vivo.** Actualizar en cada sesión donde se detecte o arregle un bug.
> **Autoridad:** este archivo es la fuente de verdad para el estado de calidad del bot.
> **Ubicación:** `docs/BUGS_REGISTRY.md` (referenciado desde `CLAUDE.md`).

---

## 1. Propósito

Este registro existe porque el proyecto llegó a un punto donde:

1. Los bugs se arreglaban sin documentación formal → mismos bugs volvían a aparecer en otros agentes.
2. No había forma de medir el progreso real de calidad ("¿cuántos bugs nos quedan?").
3. Los fixes se aplicaban a un agente a la vez sin chequear el mismo patrón en los otros 6.
4. Los supervisores reportaban bugs que ya habíamos "arreglado" (en otro contexto).

El registro formaliza el ciclo: **detectar → documentar → arreglar → verificar cross-agent → cerrar**.

---

## 2. PROCESO OBLIGATORIO — Cross-Agent Review

**Cada vez que se arregla un bug en un agente, es OBLIGATORIO revisar si el mismo patrón existe en los otros agentes.**

Esta regla existe porque muchos bugs son patrones compartidos (ej. default incorrecto de moneda,
extracción errada de fecha, routing por keywords frágiles) que viven en múltiples archivos.

### Flujo obligatorio al arreglar un bug

1. **Abrir ticket en el registro** con el formato del template (sección 4).
2. **Identificar el patrón general del bug.** No el síntoma: el patrón.
   - Ejemplo: síntoma = "Ventas suma Bs + USD". Patrón = "agente no defaultea moneda cuando usuario no la especifica".
3. **Buscar el patrón en los otros 6 agentes** usando `Grep` / lectura de código.
4. **Por cada agente revisado**, anotar en el ticket una de estas 3 cosas:
   - ✅ **No aplica** — el patrón no existe en ese agente porque [razón técnica concreta].
   - ⚠️ **Aplica pero con menor severidad** — anotar y crear ticket separado si amerita fix.
   - 🔴 **Aplica con misma severidad** — crear ticket duplicado inmediatamente y arreglarlo en el mismo commit (o commit adyacente).
5. **Aplicar el fix** al agente principal + a los afectados encontrados en el paso 4.
6. **Mover el ticket a "Resueltos"** con la fecha, commit hash, y el resultado del cross-agent review.
7. **Actualizar la tabla resumen** (sección 5).

### Por qué es obligatorio y no opcional

Ejemplo real (sesión 08/Abr/2026): El bug de default VES se detectó en ventas. Sin cross-agent review
sistemática, habríamos arreglado solo `ventas.py`. Pero `compras_insumos.py` tiene exactamente el
mismo patrón (default a `None` = mezcla todas las monedas). Ese bug sigue vivo hoy como **COMP-003**.
Si hubiéramos hecho el cross-agent review cuando arreglamos ventas, COMP-003 se habría cazado en la
misma sesión.

---

## 3. Niveles de Severidad

| Emoji | Nivel | Criterio |
|---|---|---|
| 🔴 | CRÍTICO | Bot devuelve datos **incorrectos** con confianza alta, o bloquea casos de uso frecuentes. Ejemplos: mezcla monedas, rutea a agente equivocado, oculta datos que existen. |
| 🟠 | ALTO | Bot devuelve datos correctos pero mal presentados, o falla en casos comunes. Ejemplos: LLM reordena tabla, confunde posición/valor, latencia > 30s. |
| 🟡 | MEDIO | Afecta UX pero no la veracidad de los datos. Ejemplos: mensaje de error poco amigable, formato de moneda inconsistente, headers confusos. |
| 🟢 | BAJO | Cosmético, edge case, o no bloquea el flujo principal. |

**Regla de priorización:** se arreglan primero los 🔴, después 🟠, después 🟡, y 🟢 al final o en
sesiones de cleanup. **Nunca dejar bugs 🔴 abiertos entre sesiones sin una razón documentada.**

---

## 4. Template de Bug

Cada bug nuevo se documenta con este template. Copiar-pegar y llenar todos los campos.

```markdown
#### [AGENTE-NNN]: Título corto del bug
- **Severidad:** 🔴/🟠/🟡/🟢 [NIVEL]
- **Reportado:** YYYY-MM-DD por [nombre/fuente: Darwin, golden test, log análisis, supervisor X]
- **Resuelto:** YYYY-MM-DD (vacío si está abierto)
- **Commit del fix:** `hash` (vacío si está abierto)
- **Test de regresión:** `id_del_caso_en_cases.yaml` (crear si no existe)

##### Síntoma observable
Descripción desde la perspectiva del usuario: "cuando pregunto X, el bot responde Y en vez de Z".
Incluir snippet de la respuesta real del bot si está disponible (de los logs o del test).

##### Causa raíz (a nivel de código)
Explicación técnica: qué función, qué línea, qué lógica está mal. Incluir referencias a
archivos con formato `backend/app/agents/ventas.py:551-552`.

##### Fix aplicado
Descripción del cambio + diff conceptual (no pegar el diff completo, solo lo esencial).

##### Cross-Agent Review
Para cada uno de los otros agentes, marcar el resultado de la verificación:

| Agente | Estado | Nota |
|---|---|---|
| ventas | ✅ No aplica | razón |
| rrhh | ⚠️ Aplica parcial | ticket [AGENTE-NNN] |
| finanzas | 🔴 Mismo patrón | ticket [FIN-NNN] creado, fix en mismo commit |
| contabilidad | ✅ No aplica | razón |
| produccion | ✅ No aplica | razón |
| compras_insumos | ✅ No aplica | razón |
| compras_productores | ✅ No aplica | razón |
| orchestrator | N/A | no aplica a routing |
| base_agent | N/A | no aplica a lógica compartida |

##### Verificación post-fix
Cómo se validó que el bug está efectivamente arreglado. Idealmente: golden test que pasó.
```

### Convención de IDs

- **VENT-NNN** — Ventas
- **RRHH-NNN** — Recursos Humanos
- **FIN-NNN** — Finanzas
- **CONT-NNN** — Contabilidad
- **PRDC-NNN** — Producción
- **COMP-NNN** — Compras de Insumos
- **AGRI-NNN** — Compras a Productores (agrícolas)
- **ORCH-NNN** — Orchestrator / routing
- **BASE-NNN** — base_agent / lógica compartida
- **FRNT-NNN** — Frontend (React/Next.js)
- **INFR-NNN** — Infraestructura (Docker, DB, deploy)

Numeración secuencial por agente, sin reiniciar. Los IDs son inmutables — un bug mantiene su ID
desde que se abre hasta que se resuelve (solo cambia de lista).

---

## 5. Tabla Resumen Global

**Última actualización:** 2026-04-09

| Agente | 🔴 Abiertos | 🟠 Abiertos | 🟡 Abiertos | 🟢 Abiertos | ✅ Resueltos | Total |
|---|---:|---:|---:|---:|---:|---:|
| ventas              | 0 | 1 | 0 | 0 | 9 | 10 |
| rrhh                | 4 | 0 | 0 | 0 | 4 |  8 |
| finanzas            | 1 | 0 | 0 | 0 | 0 |  1 |
| contabilidad        | 0 | 0 | 0 | 0 | 0 |  0 |
| produccion          | 1 | 0 | 0 | 0 | 0 |  1 |
| compras_insumos     | 3 | 0 | 0 | 0 | 3 |  6 |
| compras_productores | 4 | 0 | 0 | 0 | 0 |  4 |
| orchestrator        | 1 | 1 | 0 | 0 | 0 |  2 |
| base_agent          | 0 | 0 | 0 | 0 | 1 |  1 |
| **TOTAL**           | **14** | **2** | **0** | **0** | **17** | **33** |

### Indicadores clave

- **Precisión medida (golden tests):** 8/10 PASS = **80%** (Tranche 1, 09/Abr/2026)
- **Cobertura del golden suite:** 4 de 7 agentes (ventas, rrhh, compras_insumos, compras_productores)
- **Bugs críticos detectados por logs:** 10 (ver sección por agente)
- **Bugs críticos detectados por golden tests:** 2 (COMP-100, COMP-101)
- **Deuda técnica crítica:** 14 bugs 🔴 abiertos.

---

## 6. Bugs por Agente

### Agente: Ventas

#### 🔴 Abiertos (1)

##### VENT-100: Follow-ups parciales de moneda no heredan contexto
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-09 (análisis de logs reales, 1,273 mensajes)
- **Resuelto:** —
- **Commit del fix:** —
- **Test de regresión:** pendiente (Tranche 3, requiere soporte multi-turno en runner)

##### Síntoma observable
En los logs reales hay múltiples preguntas follow-up que no heredan el agente/contexto del turno anterior:

- `"me lo puedes dar en dolares"` → confidence 0.50, el bot lo ruteó a ventas pero sin el período anterior
- `"ok damelo en febrero 2026"` → confidence 0.64
- `"en moneda DOL"` (jalvarez) → ruteado a compras_insumos en vez del agente del turno anterior
- `"considera la moneda dol"` (jalvarez) → sí heredó contabilidad (funciona)

El comportamiento es inconsistente: a veces hereda, a veces no.

##### Causa raíz (a nivel de código)
`base_agent.py` pasa el `history` a los agentes vía `fetch_data(..., history=history)`, pero cada
agente implementa su propia lógica de `_extract_context_from_history`. Algunos heredan moneda, otros
no. El orchestrator además re-rutea basado solo en el mensaje actual, por lo que un follow-up corto
como "en dólares" puede terminar en un agente distinto al de la pregunta original.

##### Fix aplicado
Pendiente. Propuesta: centralizar herencia de contexto en `base_agent.py` y forzar al orchestrator
a mantener el agente anterior si el mensaje nuevo es "corto + ambiguo" (heurística: < 30 caracteres
sin menciones de dominio).

##### Cross-Agent Review
Pendiente — aplicar cuando se trabaje el fix. **Es muy probable que todos los agentes tengan este bug.**

---

#### ✅ Resueltos (9)

##### VENT-001: Default mezclaba VES + USD como bolívares (CRÍTICO)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-08 (Darwin vía validación de Excel)
- **Resuelto:** 2026-04-08
- **Commit del fix:** `483698a`
- **Test de regresión:** `top_10_vendedores_inproa_usd_feb_2026` en `backend/tests/golden/cases.yaml`

##### Síntoma observable
Consulta "top vendedores febrero 2026 en inproa" sin especificar moneda sumaba Bs + USD como números
pelados y etiquetaba el total como "Bolívares". Matemática verificada:
`Bs 738,438,895.74 + USD 1,008,658.65 + USD 421,741.40 = 739,869,295.79` = exactamente el valor
erróneo que el bot mostraba para ANTONINO RUSSO.

##### Causa raíz
`ventas.py` pasaba `currency_ids=None` a `build_sales_summary` cuando el usuario no mencionaba
moneda. `build_sales_summary` no filtraba por moneda → `SUM(i.totallines)` mezclaba todas las
monedas activas en iDempiere (205 VES + 9 variantes de USD + euros).

Archivo: `backend/app/agents/ventas.py:551-552` (estado pre-fix)

##### Fix aplicado
Default a `currency_ids = [205]` (VES) cuando el usuario no especifica moneda. Usuarios que quieran
USD deben decirlo explícitamente ("en dólares", "en usd").

##### Cross-Agent Review
**⚠️ No se hizo en su momento (el proceso se formalizó después, 09/Abr).** Pendiente para sesión
siguiente. Evidencia circunstancial de que `compras_insumos.py` tiene el mismo patrón — ver
**COMP-003**.

---

##### VENT-002: Vendedores duplicados (ROJAS OBANDO vs RENEE ROJAS OBANDO)
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-08 (Darwin vía Excel)
- **Resuelto:** 2026-04-08
- **Commit del fix:** `483698a`
- **Test de regresión:** `top_10_vendedores_inproa_usd_feb_2026`

##### Síntoma observable
"ROJAS OBANDO RENEE DE JESUS" (36 facturas) y "RENEE DE JESUS ROJAS OBANDO" (20 facturas) aparecían
como 2 filas separadas en el top de vendedores. Son la misma persona con 2 registros `ad_user`
distintos en iDempiere con el mismo nombre en orden permutado.

##### Causa raíz
`build_sales_summary.por_vendedor` agrupa por `sr.name`, y nombres permutados generan filas
distintas. No había lógica de consolidación por contenido de tokens.

##### Fix aplicado
Helper `_dedupe_salesrep_rows()` en `backend/app/services/idempiere_queries.py:455` que:
1. Normaliza el nombre a tokens UPPER ordenados alfabéticamente (`_norm()`).
2. Agrupa las filas con la misma clave normalizada.
3. Suma las columnas numéricas especificadas.
4. Preserva el nombre de la primera fila (la de mayor bruto, por el `ORDER BY` del SQL).

Aplicado en `build_sales_summary` (línea 671) y `build_sales_orders` (revisar línea equivalente).

##### Cross-Agent Review
**⚠️ Pendiente.** Posible aplicación en:
- `rrhh.py` / `build_employee_list` — ¿hay empleados con nombres duplicados en `ad_user`? Probable.
- `compras_productores.py` / `build_producer_purchases` → `por_productor` — ¿hay productores con nombres en orden permutado en `c_bpartner`? Posible.

---

##### VENT-003: "inproa" ambiguo se adivinaba en vez de clarificar
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-08 (Darwin)
- **Resuelto:** 2026-04-08
- **Commit del fix:** `3c74770`
- **Test de regresión:** manual (requiere multi-turno)

##### Síntoma observable
"top vendedores feb 2026 en inproa" se interpretaba automáticamente como "INPROA SANTONI",
pero "inproa" puede referirse a INPROA SANTONI C.A., InproMaiz C.A., AGROINPROA C.A. o al
grupo completo. Darwin esperaba ver datos del grupo pero el bot le mostraba solo INPROA SANTONI.

##### Causa raíz
`_ORG_MAP` de `ventas.py` tenía `"inproa" → "INPROA SANTONI"` como mapping hardcoded.

##### Fix aplicado
1. Removido el mapping `"inproa" → "INPROA SANTONI"` de `_ORG_MAP`.
2. Agregado `_AMBIGUOUS_ORG_KEYWORDS = ("inproa",)`.
3. Agregado helper `_is_ambiguous_org(msg)` que detecta keywords ambiguos sin calificador.
4. En `fetch_data`, si el mensaje es ambiguo y no hay org específica en historial → devolver
   mensaje de clarificación con las 3 opciones (SANTONI, InproMaiz, AGROINPROA).

Archivos: `backend/app/agents/ventas.py:214-228, 324-329, 529-545`

##### Cross-Agent Review
**⚠️ Pendiente.** `compras_insumos.py:162-174` tiene un `_ORG_MAP` con el mismo mapping
`"inproa" → "INPROA SANTONI"` (posible mismo bug). Ver ticket **COMP-100** candidato.

---

##### VENT-004: LLM reordenaba tabla de vendedores (posiciones vs valores)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-08 (Darwin vía screenshot de respuesta del bot)
- **Resuelto:** 2026-04-08
- **Commit del fix:** `2439a96`
- **Test de regresión:** `top_10_vendedores_inproa_usd_feb_2026`

##### Síntoma observable
El LLM recibía la tabla `por_vendedor` con 6 columnas similares (total_bruto, monto_nc, total,
facturas, notas_credito) y al re-renderizarla mezclaba pairings vendedor↔monto. Ejemplo real
del bot: posición 5 tenía valor $71M, posición 6 tenía $102M, posición 7 tenía $88M — orden
descendente roto.

##### Causa raíz
El LLM (DeepSeek v3) no es determinista al renderizar tablas con muchas columnas similares.
No hay control sobre cómo formatea la salida si se le pasa el JSON crudo.

##### Fix aplicado
Helper `_format_vendedores_table()` en `backend/app/agents/ventas.py:437-484` que pre-formatea
la tabla con:
- Orden por venta neta DESC (consistente con el header "Venta Neta").
- Columna `#` con posición ya calculada.
- Formato venezolano: `503.174.967,88` (punto=miles, coma=decimal).
- Headers explícitos: `Venta Bruta (Bs.)`, `Monto NC (Bs.)`, `Venta Neta (Bs.)`.
- Instrucción blindada al LLM: "TABLA FINAL PRE-FORMATEADA — COPIA EXACTA, NO reordenes".

##### Cross-Agent Review
**⚠️ Pendiente.** Las demás tablas (top clientes, por zona, por región, por moneda) siguen
usando `_format_table` genérico y son candidatas al mismo bug. Ver tickets potenciales:
- **VENT-005** (candidato): top clientes pre-formato
- **VENT-006** (candidato): por zona pre-formato
- **COMP-NNN** (candidato): compras_insumos tablas por proveedor / producto

---

##### VENT-005 (histórico): `grandtotal` incluía IVA en totales ventas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-03-26 (equipo Santoni)
- **Resuelto:** 2026-03-26
- **Commit del fix:** (ver `cd22cbd` en histórico)
- **Test de regresión:** `ventas_total_neto_ves_feb_2026`

##### Síntoma / Causa / Fix (resumen histórico)
Ventas usaban `i.grandtotal` (con IVA) en vez de `i.totallines` (sin IVA). Santoni reporta sin IVA.
Fix aplicado en todas las queries de ventas. Ver commit para detalle.

##### Cross-Agent Review
**⚠️ Pendiente (backfill).** Compras de insumos también migraron a `totallines` en commit
`89b612f` (auditoría). Revisar que compras_productores y otros agentes no tengan residuos.

---

##### VENT-006 (histórico): `docstatus='CO'` excluía facturas pagadas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-03-11 (Santoni)
- **Resuelto:** 2026-03-11
- **Commit del fix:** histórico (ver `89b612f` para auditoría completa)

##### Síntoma / Causa / Fix (resumen histórico)
Queries filtraban `docstatus = 'CO'` creyendo que 'CL' (cerrada) significaba "sin efecto".
Realmente 'CL' también es completada y debe incluirse. Fix: `docstatus IN ('CO', 'CL')` en todos
los agentes. Verificado en auditoría del 08/Abr/2026.

##### Cross-Agent Review
✅ Aplicado globalmente en commit `89b612f` (auditoría sistemática 02/Abr/2026). Los agentes
afectados incluyen ventas, compras_insumos, compras_productores, finanzas.

---

##### VENT-007 (histórico): `invoiceopen()` PL/pgSQL mataba performance (~100x slowdown)
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-02 (QA de performance)
- **Resuelto:** 2026-04-02
- **Commit del fix:** `503b232`

##### Síntoma / Causa / Fix (resumen histórico)
`invoiceopen(c_invoice_id, 0)` es VOLATILE en iDempiere, lo que impide que PostgreSQL empuje
filtros WHERE. Consultas de deudas tardaban minutos. Fix: reemplazado con `_ALLOC_JOIN` +
`_OPEN_EXPR` en `idempiere_queries.py:256-267` — agregación única por invoice con JOIN a
`c_allocationline`. Speedup ~100x.

##### Cross-Agent Review
✅ Aplicado a todas las queries que usaban invoiceopen() en el mismo commit.

---

##### VENT-008 (histórico): Notas de crédito incluidas en totales de ventas como positivas
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-03-26
- **Resuelto:** 2026-03-26
- **Commit del fix:** histórico

##### Síntoma / Causa / Fix (resumen histórico)
Las NC (documento ARC) se sumaban como si fueran facturas (ARI), inflando los totales de ventas.
Fix: separar ARI de ARC usando `CASE WHEN dt.docbasetype` en todas las agregaciones, mostrar
bruto + NC + neto por separado. Ver `build_sales_summary` para el patrón.

##### Cross-Agent Review
**⚠️ Revisar:** ¿compras de insumos tiene el mismo patrón con facturas de compra (API) vs notas
de crédito de compra (APC)? Probable. Ticket candidato **COMP-NNN**.

---

##### VENT-009 (histórico): Latencia severa en queries de ventas (> 30s)
- **Severidad:** 🟠 ALTO
- **Reportado:** Mar/2026
- **Resuelto:** Mar/2026 + 02/Abr/2026 (VENT-007)

##### Resumen histórico
Múltiples causas: invoiceopen() (VENT-007), JOINs multiplicativos con `c_bpartner_location`,
queries sin índices. Fixes aplicados: CTE `client_zone` con DISTINCT ON, _ALLOC_JOIN, y ajustes
específicos por tipo de query.

##### Cross-Agent Review
✅ La auditoría del 02/Abr (`89b612f`) revisó todos los agentes.

---

### Agente: RRHH

#### 🔴 Abiertos (4)

##### RRHH-100: "fecha de nacidos en abril" se rutea a ventas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (análisis de logs reales — supervisor esalas)
- **Resuelto:** —
- **Commit del fix:** —
- **Test de regresión:** pendiente (Tranche 2)

##### Síntoma observable
Pregunta real de esalas: `"Dame la fecha de los nacidos en el mes de abril"` → ruteada a **ventas** por el orchestrator. Respuesta sin sentido (o error).

##### Causa raíz (a nivel de código)
Pendiente diagnóstico. Hipótesis: el orchestrator clasifica por keywords y "fecha" sin
calificador rutea a ventas (que tiene keywords de "fecha de factura"). "nacidos" debería
ser suficiente para rutear a rrhh pero no está en la lista de keywords del rrhh agent.
Revisar `backend/app/agents/orchestrator.py` y `backend/app/agents/rrhh.py`.

##### Cross-Agent Review
Pendiente. Buscar si "nacidos" / "nacimiento" / "cumpleañ" están en las listas de keywords
de otros agentes por error.

---

##### RRHH-101: "quienes cumplen años en abril" se rutea a general
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas)
- **Resuelto:** —

##### Síntoma
`"Me puedes indicar quienes cumplen años en abril de inproa santoni"` → ruteado a **general** (que no hace nada útil, confidence 0.50).

##### Causa raíz
Pendiente. Hipótesis: keyword "cumplen años" no disparó matching en rrhh agent. El agente rrhh tiene "cumpleañ" en sus keywords, pero "cumplen años" (2 palabras) puede no matchear el substring `"cumpleañ"` porque no se normaliza.

##### Cross-Agent Review
Pendiente.

---

##### RRHH-102: "control vacacional" se rutea a general
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas)

##### Síntoma
`"me puedes dar el control vacacional al 31/03/2026?"` → ruteado a **general**.

##### Causa raíz
Pendiente. El rrhh agent SÍ tiene funcionalidad de vacaciones (`build_vacation_summary`), pero "control vacacional" no está en los keywords de routing.

---

##### RRHH-103: "fecha de ingreso de Geovanna Quintero" se rutea a compras_insumos
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas — múltiples ocurrencias en logs)

##### Síntoma
`"dime la fecha de ingreso de Geovanna Quintero"` → ruteado a **compras_insumos**. Respuesta
sin sentido (Geovanna Quintero es una empleada, no un proveedor).

##### Causa raíz
Hipótesis: la palabra "ingreso" está en la lista de keywords de compras_insumos (como en "precio
de ingreso de mercadería"). El routing de compras_insumos captura la palabra antes que rrhh
capture "fecha de ingreso" (como "hire date").

##### Cross-Agent Review
Pendiente. Buscar "ingreso" en keywords de todos los agentes.

---

#### ✅ Resueltos (4)

##### RRHH-001 (histórico): "no tengo acceso" en respuestas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-03-10
- **Resuelto:** 2026-03-10
- **Commit del fix:** histórico

##### Resumen
El LLM respondía "no tengo acceso a la base de datos" en consultas que SÍ tenían datos disponibles.
Fix: instrucción explícita en el system prompt de cada agente prohibiendo esa frase + mensaje
alternativo cuando realmente no hay datos.

##### Cross-Agent Review
✅ Aplicado a los 7 agentes en el mismo commit.

---

##### RRHH-002 (histórico): Herencia temporal rota en follow-ups
- **Severidad:** 🟠 ALTO
- **Resuelto:** Mar/2026

##### Resumen
Follow-ups como "y en mayo?" no heredaban el contexto temporal del turno anterior. Fix aplicado
en `base_agent.py` + cada agente.

---

##### RRHH-003 (histórico): Cumpleañeros duplicados con LATERAL subquery
- **Severidad:** 🟡 MEDIO
- **Resuelto:** commit histórico `31cd742`

##### Resumen
El query de cumpleañeros devolvía duplicados por JOIN con múltiples direcciones. Fix: usar LATERAL
subquery para una sola fila por empleado.

---

##### RRHH-004 (histórico): Cumpleañeros usaba columna incorrecta
- **Severidad:** 🟡 MEDIO
- **Resuelto:** commit histórico `7ddfcc9`

##### Resumen
La query buscaba la fecha de nacimiento autodetectando la columna (birthday vs birthdate). Fix:
usar directamente `ad_user.birthday` que es la columna real en iDempiere.

---

### Agente: Compras Insumos

#### 🔴 Abiertos (3)

##### COMP-100: Compras de insumos 2025 devuelve "no hay datos" (bug activo, diagnóstico en curso)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (golden test `compras_insumos_total_2025_ves` + `compras_insumos_facturas_count_2025_ves` → ambos FAIL)
- **Resuelto:** —
- **Commit del fix:** —
- **Test de regresión:** ya existe en `backend/tests/golden/cases.yaml` (Tranche 1)

##### Síntoma observable
Pregunta: `"¿Cuánto se compró en insumos en 2025 en bolívares?"`
Respuesta real del bot:
> "No se encontraron datos de compras de insumos para el año 2025 en bolívares (VES). Si necesitas datos de otro período o moneda, indícame el año, mes o rango de fechas específico. **Nota:** Los datos disponibles corresponden al año actual (2026) por defecto."

Ground truth SQL directo contra iDempiere: **Bs. 8,212,602,071.70** en 7,426 facturas.
Los datos EXISTEN, el bot NO los encuentra.

Datos adicionales confirmados (2026-04-09):
- `HISTORICAL_DATA_ENABLED=false` → el bot va a iDempiere vivo, no a DB local
- La DB local sí tiene `c_invoice` para `issotrx='N'` en 2025 (23,852 filas) pero no se usa
- Mi hipótesis inicial de routing histórico era **incorrecta**

##### Causa raíz (a nivel de código) — DIAGNÓSTICO EN CURSO
Pendiente. El bot devuelve "no hay datos" con confianza alta. El system prompt de compras_insumos
(línea 110) menciona "Los datos corresponden al año actual por defecto" y el LLM lo cita
literalmente. Pero ese mensaje es solo la excusa del LLM cuando recibe dict vacío — la pregunta
real es **por qué la query devuelve vacío si los datos existen en iDempiere**.

Hipótesis a probar:
1. ¿El agente extrae `anio=2025` correctamente, o lo sobreescribe a 2026?
2. ¿La query entra en una rama distinta a `build_supply_purchases` (ej: `is_inventory`, `is_payment`)?
3. ¿`_detect_currency` devuelve lo esperado para "en bolívares"?
4. ¿Hay un filtro extra que elimina los resultados (ej: filtro por org implícito)?

##### Fix aplicado
—

##### Cross-Agent Review
Se aplicará cuando se identifique el patrón. Candidatos a revisar:
- `finanzas.py` — ¿misma lógica de extracción de año para queries históricas?
- `contabilidad.py` — idem
- `ventas.py` — el caso `ventas_total_neto_ves_enero_2026` SÍ PASA en 2026, no sabemos 2025

---

##### COMP-101: "cuánto se ha comprado de empaque" se rutea a produccion
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (análisis de logs — admin repite varias veces)

##### Síntoma
`"¿Cuánto se ha comprado de empaque en INPROA SANTONI en 2025?"` → ruteado a **produccion**.
La palabra "comprado" debería disparar compras_insumos, pero "empaque" está en algún keyword
de producción (tal vez "empaquetado" o "empacadora").

##### Causa raíz
Pendiente. Revisar keywords de produccion agent.

##### Cross-Agent Review
Pendiente.

---

##### COMP-102: "saldo de cuentas por pagar" se rutea a compras_insumos
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-09 (jalvarez en logs)

##### Síntoma
`"cual es el saldo de las cuentas por pagar a proveedores de inproa santoni al 28 de febrero de 2026"` → compras_insumos.

El usuario esperaba una vista financiera/contable (saldo, allocation), no una lista de compras
por proveedor. Aunque "proveedores" es de compras, "saldo de cuentas por pagar" es terminología
contable/financiera.

##### Causa raíz
Pendiente. Probablemente el keyword "proveedores" gana contra "saldo"/"cuentas por pagar" en el
orchestrator.

##### Cross-Agent Review
Pendiente.

---

#### ✅ Resueltos (3)

##### COMP-001 (histórico): `org_name` no se extraía en compras
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-03-11
- **Resuelto:** 2026-03-11
- **Commit del fix:** histórico

##### Resumen
"compras en INPROA SANTONI" no filtraba por organización porque `_extract_org_name` no existía
en `compras_insumos.py`. Fix: agregado helper + aplicado en todas las queries.

##### Cross-Agent Review
✅ El mismo patrón se aplicó a ventas en su momento.

---

##### COMP-002 (histórico): docstatus='CO' excluía facturas pagadas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-03-11
- **Resuelto:** 2026-03-11

##### Resumen
Mismo bug que VENT-006 pero en queries de compras. Fix: `docstatus IN ('CO', 'CL')`.

##### Cross-Agent Review
✅ Aplicado globalmente en commit `89b612f`.

---

##### COMP-003 (histórico): Expansión de capacidades compras_insumos
- **Severidad:** 🟡 MEDIO
- **Reportado:** 2026-03-10
- **Resuelto:** 2026-03-10

##### Resumen
El agente no soportaba varias consultas que Santoni necesitaba: órdenes de compra pendientes,
comparación de precios entre proveedores, estado de pago. Fix: agregadas funciones
`build_pending_purchase_orders`, `build_supplier_price_comparison`, `build_purchase_payment_status`.

---

### Agente: Compras Productores (agrícolas)

#### 🔴 Abiertos (4)

##### AGRI-100: "deuda por pagar a productor Jose Luis Perez" → SIN_AGENTE
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (mfigueredo, 2 ocurrencias)

##### Síntoma
`"cuanto es la deuda por pagar a productor Jose Luis Perez del Palomar"` → el orchestrator no
rutea a ningún agente (`SIN_AGENTE` en los logs). mfigueredo no recibe respuesta útil.

##### Causa raíz
Pendiente. La palabra "productor" sí está en los keywords de compras_productores pero el
orchestrator puede estar confundiéndose con "pagar" (finanzas) y "Jose Luis Perez del Palomar"
(nombre propio no clasificado).

##### Cross-Agent Review
Pendiente.

---

##### AGRI-101: "deuda con maiz de buque de inpromaiz" → ventas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (mfigueredo)

##### Síntoma
`"deuda con maiz de buque de inpromaiz"` → ruteado a **ventas**. La pregunta es sobre lo que
Santoni debe a productores/proveedores de un buque de maíz, debería ser compras_productores.

##### Causa raíz
Pendiente. Posible culpable: "deuda" dispara ventas porque tiene "deudas vencidas" en keywords.

---

##### AGRI-102: "monto a pagar en recepción de maíz" → ventas/finanzas
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (mfigueredo, 6 ocurrencias con variantes)

##### Síntoma
Múltiples preguntas de mfigueredo sobre pagos a productores de maíz en InproMaiz se rutearon
a ventas o finanzas en vez de compras_productores:
- `"cuanto es el monto por pagar de maiz"` → finanzas
- `"cuanto es el monto en dolares a pagar en recepcion de maiz"` → finanzas
- `"cuanto es el monto en dolares a pagar de maiz acondicionado de inpromaiz"` → ventas
- `"cuanto es el monto en recepcion de maiz acondicionado en impromaiz"` → ventas

##### Causa raíz
Pendiente. Patrón: cuando el mensaje incluye "monto a pagar" o "dólares", el orchestrator parece
priorizar ventas/finanzas sobre compras_productores, aunque el contexto explícitamente menciona
maíz y recepción (compras agrícolas).

##### Cross-Agent Review
Pendiente. Este bug tiene alta probabilidad de ser un problema de ordering en el orchestrator:
si varios agentes tienen scores similares, el primero gana. compras_productores podría estar
al final de la lista.

---

##### AGRI-103: "Compras de maíz del mes actual" → compras_insumos
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-09 (mfigueredo)

##### Síntoma
`"Compras de maíz del mes actual"` → ruteado a **compras_insumos** (mal). Maíz es compra agrícola
(a productores), no un insumo industrial. Santoni hace 2 tipos de compras:
1. Compras de insumos industriales (empaque, químicos, etc.) → `compras_insumos`
2. Compras agrícolas a productores (maíz, arroz paddy) → `compras_productores`

Si el usuario dice "maíz" o "arroz paddy", debería ir al segundo.

##### Causa raíz
Pendiente. La palabra "Compras" probablemente dispara compras_insumos con más fuerza que
compras_productores porque ese es el agente más genérico.

##### Cross-Agent Review
Pendiente. Al arreglar, revisar que "arroz paddy" tampoco caiga en compras_insumos por el mismo
motivo.

---

#### ✅ Resueltos (0)

Ninguno formalmente registrado. El agente fue creado en los commits iniciales del proyecto y
sus bugs históricos no fueron trackeados (pre-proceso de registry).

---

### Agente: Finanzas

#### 🔴 Abiertos (1)

##### FIN-100: "saldo de cuentas por pagar" no rutea a finanzas
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-09 (jalvarez)

##### Síntoma
`"cual es el saldo de las cuentas por pagar a proveedores de inproa santoni al 28 de febrero de 2026"` → ruteado a **compras_insumos** (ver también COMP-102, mismo síntoma desde la otra perspectiva).

El supervisor de contabilidad esperaba que "saldo de cuentas por pagar" fuera a finanzas o
contabilidad.

##### Causa raíz
Mismo que COMP-102. Pendiente diagnóstico del orchestrator.

---

#### ✅ Resueltos (0)

Ninguno trackeado. Hubo fixes históricos en `build_overdue_receivables` y afines pero no
están documentados formalmente aquí.

---

### Agente: Contabilidad

#### 🔴 Abiertos (0)

Ninguno identificado hasta ahora. **Nota:** el golden suite todavía no cubre contabilidad —
puede haber bugs latentes no detectados.

#### ✅ Resueltos (0)

---

### Agente: Producción

#### 🔴 Abiertos (1)

##### PRDC-100: "CUANTOS CLIENTES SE APERTURARON EN 2025" → produccion
- **Severidad:** 🟡 MEDIO
- **Reportado:** 2026-04-09 (admin en logs)

##### Síntoma
`"CUANTOS CLIENTES SE APERTURARON EN EL AÑO 2025"` → ruteado a **produccion**. Es una pregunta
de ventas (nuevos clientes = tabla c_bpartner con fecha de creación).

##### Causa raíz
Pendiente. Hipótesis: "apertura" está en keywords de producción (como "apertura de orden de
producción") y gana contra "clientes".

##### Cross-Agent Review
Pendiente.

---

#### ✅ Resueltos (0)

---

### Agente: Orchestrator

#### 🔴 Abiertos (1)

##### ORCH-100: Routing inconsistente cuando palabras ambiguas aparecen (patrón general)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (meta-análisis de RRHH-100..103, COMP-101, COMP-102, AGRI-100..103, PRDC-100, FIN-100)

##### Síntoma
Patrón general detectado en los 10+ bugs de routing encontrados en los logs: el orchestrator
clasifica por keywords sin entender el contexto real de la pregunta. Palabras que pueden pertenecer
a varios dominios ("saldo", "pagar", "fecha", "monto", "ingreso", "apertura", "compras") terminan
en el agente equivocado dependiendo de qué keyword pesó más.

Los bugs individuales (RRHH-100, COMP-102, AGRI-100..103, etc.) son todos **manifestaciones** de
este problema de fondo.

##### Causa raíz
`backend/app/agents/orchestrator.py` usa un esquema de keyword matching con scoring. El scoring
no considera:
- Calificadores adyacentes (ej: "productor" → compras_productores debería ser fuerte)
- Contexto de dominio (ej: si hay "maíz" o "arroz paddy" → siempre agrícola)
- Preferencia por especificidad (agentes más específicos deberían ganar contra "generalistas")

##### Fix aplicado
—

##### Plan de fix propuesto
1. Agregar una capa de scoring por dominio (palabras inequívocas): "maíz", "arroz paddy",
   "productor", "empleado", "nómina", "vacaciones", "cumpleaños" → peso muy alto.
2. Reordenar agentes por especificidad: compras_productores > compras_insumos.
3. Cuando el score es cerrado (< 0.2 de diferencia), aplicar la regla de desempate por dominio.

##### Cross-Agent Review
N/A — este es un bug del orchestrator, no de un agente.

---

#### 🟠 Abiertos (1)

##### ORCH-101: Follow-ups cortos heredan agente inconsistentemente
- **Severidad:** 🟠 ALTO
- **Reportado:** 2026-04-09 (análisis logs)

##### Síntoma
Mismo síntoma que VENT-100 pero visto desde el orchestrator. Los follow-ups "en dólares", "ok
damelo en febrero", "considera la moneda dol" a veces heredan el agente del turno anterior y a
veces no. Inconsistente.

##### Causa raíz
El orchestrator clasifica solo con el mensaje actual, ignorando que si el mensaje es corto y no
tiene un agente obvio, debería preservar el del turno anterior.

##### Fix propuesto
Cuando el mensaje tiene < 30 chars y no dispara matchers de alto peso, devolver `last_agent` del
historial en vez de re-clasificar.

---

#### ✅ Resueltos (0)

---

### Agente: base_agent / lógica compartida

#### 🔴 Abiertos (0)

#### ✅ Resueltos (1)

##### BASE-001 (histórico): Error handling inconsistente entre agentes
- **Severidad:** 🟠 ALTO
- **Resuelto:** Mar/2026

##### Resumen
Varios agentes crasheaban sin manejo cuando iDempiere estaba lento o daba timeout. Fix:
try/except global en `base_agent._build_messages` + try/except interno en cada `fetch_data`
con mensaje de error amigable al usuario. Loggeo estructurado con `logger.error()`.

---

## 7. Changelog del registro

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-04-09 | Creación del registro, backfill completo de ventas (9 resueltos), y apertura de 14 bugs nuevos detectados en análisis de logs reales | Claude + Sergio |

