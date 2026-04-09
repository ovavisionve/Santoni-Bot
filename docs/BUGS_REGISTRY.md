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

**Última actualización:** 2026-04-09 (post-run Tranche 2)

| Agente | 🔴 Abiertos | 🟠 Abiertos | 🟡 Abiertos | 🟢 Abiertos | ✅ Resueltos | Total |
|---|---:|---:|---:|---:|---:|---:|
| ventas              | 0 | 1 | 0 | 0 |  9 | 10 |
| rrhh                | 1 | 0 | 0 | 0 |  7 |  8 |
| finanzas            | 1 | 0 | 0 | 0 |  0 |  1 |
| contabilidad        | 0 | 0 | 0 | 0 |  0 |  0 |
| produccion          | 1 | 0 | 0 | 0 |  0 |  1 |
| compras_insumos     | 2 | 0 | 0 | 0 |  7 |  9 |
| compras_productores | 4 | 0 | 0 | 0 |  0 |  4 |
| orchestrator        | 1 | 1 | 0 | 0 |  0 |  2 |
| base_agent          | 0 | 0 | 0 | 0 |  1 |  1 |
| infraestructura     | 2 | 0 | 0 | 0 |  0 |  2 |
| **TOTAL**           | **12** | **2** | **0** | **0** | **24** | **38** |

### Indicadores clave

- **Precisión medida (golden tests):**
  - Tranche 1 (datos): 10/10 PASS hasta el baseline de Tranche 2. El re-run con 24 casos dio 8/10 PASS por bug de parser (INFR-100); post-fix del parser esperado 10/10.
  - Tranche 2 (routing): 5/14 PASS en baseline (2 routing bugs confirmados vivos, 7 timeouts por INFR-101, 3 baselines positivos OK + 2 tickets silenciosamente arreglados antes del Tranche 2)
- **Cobertura del golden suite:** **7 de 7 agentes** (ventas, rrhh, compras_insumos, compras_productores, finanzas, contabilidad, produccion). ✅
- **Bugs críticos detectados por logs + golden tests:**
  - 4 en compras_insumos wrappers (COMP-100/103/104/105) — resueltos
  - 2 routing bugs confirmados vivos (RRHH-101, COMP-101)
  - 3 routing bugs resueltos silenciosamente antes del Tranche 2 (RRHH-100, RRHH-102, RRHH-103)
  - 2 bugs de infraestructura descubiertos por el golden test mismo (INFR-100 parser, INFR-101 timeouts)
  - 6 routing bugs no evaluados por culpa de INFR-101 (FIN-100, AGRI-100..103, PRDC-100) — re-evaluar tras fix de timeouts
- **Deuda técnica crítica:** 12 bugs 🔴 abiertos.
- **Efectividad del cross-agent review:** COMP-100 destapó 3 bugs idénticos en el mismo commit. 75% de los bugs hubieran seguido vivos sin el proceso.
- **Efectividad del golden suite:** en el run del Tranche 2 el suite reveló 3 bugs silenciosamente arreglados (imposibles de saber sin medir) y 2 bugs de su propia infraestructura (INFR-100 parser, INFR-101 saturación del bot). El framework se corrige a sí mismo mientras ilumina bugs del bot.

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

#### 🔴 Abiertos (1)

##### RRHH-101: "quienes cumplen años" se rutea a general (confirmado vivo en Tranche 2)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas, y reconfirmado en Tranche 2 del golden test)
- **Resuelto:** —
- **Commit del fix:** —
- **Test de regresión:** `routing_rrhh_cumples_abril_inproa` en `backend/tests/golden/cases.yaml`

##### Síntoma observable (del golden test run)
Pregunta: `"Me puedes indicar quienes cumplen años en abril de inproa santoni"`
Resultado: **FAIL** — routing incorrecto: esperado `'rrhh'`, ruteado a `'general'`.
Respuesta real del bot (citada verbatim):
> "Lo siento, pero no tengo acceso a información personal como cumpleaños de empleados en Alimentos Santoni. Si necesitas ayuda con consultas relacionadas con Finanzas, Contabilidad, Ventas, RRHH, Producción o Compras, estaré encantado de asistirte."

**Observación secundaria grave:** El mensaje `"no tengo acceso"` **viola la regla del system
prompt global** que prohíbe esa frase (bug histórico RRHH-001). El agente `general` no tenía
esa regla aplicada — solo los 7 agentes especializados.

##### Causa raíz (hipótesis, pendiente de confirmación)
1. El orchestrator clasifica `"cumplen años"` como no-categorizable y lo manda al agente `general`.
2. El agente `general` no sabe qué hacer con una pregunta de RRHH y responde con el disclaimer.
3. Aunque el agente `rrhh` tiene capability para cumpleaños (`build_birthday_list`), el
   orchestrator nunca lo ve porque el routing falla antes.

Revisar:
- `backend/app/agents/orchestrator.py`: keywords/matchers para rrhh. `"cumpleañ"` podría estar
  pero `"cumplen años"` (2 palabras) no matchea el substring.
- `backend/app/agents/rrhh.py`: `_ORG_MAP` y `_KEYWORDS` del agente.
- Agente `general`: agregar frase "no tengo acceso" a la lista de frases prohibidas
  (consistencia con RRHH-001).

##### Cross-Agent Review
Pendiente. Al arreglar, buscar el mismo patrón:
- ¿Los otros agentes normalizan "cumplen años" → "cumpleaños" antes de matchear?
- ¿Hay keywords de 2+ palabras que se pierden por matching de substring simple?
- ¿El agente `general` tiene la misma omisión de "no tengo acceso" en otros contextos?

---

#### ✅ Resueltos (7)

##### RRHH-100: "fecha de nacidos en abril" → rutea bien a rrhh (resuelto silenciosamente)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (análisis de logs del supervisor esalas)
- **Resuelto:** **antes del 09/Abr/2026 17:00 UTC — sin commit identificado**
- **Commit del fix:** ? (se arregló en algún commit entre Marzo y Abril que no documenté)
- **Test de regresión:** `routing_rrhh_nacidos_abril` en `backend/tests/golden/cases.yaml` (PASS)

##### Síntoma histórico
Pregunta real de esalas (de los logs históricos): `"Dame la fecha de los nacidos en el mes de
abril"` → ruteada a **ventas** en los logs. Ya no reproduce.

##### Confirmación de resolución
En el baseline de Tranche 2 (09/Abr/2026), el golden test `routing_rrhh_nacidos_abril` pasó:
```
[PASS] routing_rrhh_nacidos_abril  (rrhh)
       detalle:  Routing OK: rrhh
```

El bug fue arreglado antes de que lo cazáramos formalmente. Probable mitigación indirecta:
los refactors de `orchestrator.py` del 02/Abr/2026 (commit `89b612f` de auditoría global).

##### Cross-Agent Review
No aplica retrospectivamente (el fix original no se tracea).

---

##### RRHH-102: "control vacacional" → rutea bien a rrhh (resuelto silenciosamente)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas)
- **Resuelto:** antes del 09/Abr/2026 17:00 UTC — sin commit identificado
- **Test de regresión:** `routing_rrhh_control_vacacional` (PASS)

##### Síntoma histórico
`"me puedes dar el control vacacional al 31/03/2026?"` → iba a **general**. Ya no.

##### Confirmación
```
[PASS] routing_rrhh_control_vacacional  (rrhh)
       detalle:  Routing OK: rrhh
```

---

##### RRHH-103: "fecha de ingreso de Geovanna Quintero" → rutea bien a rrhh (resuelto silenciosamente)
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (esalas — múltiples ocurrencias en logs)
- **Resuelto:** antes del 09/Abr/2026 17:00 UTC
- **Test de regresión:** `routing_rrhh_fecha_ingreso_empleado` (PASS)

##### Síntoma histórico
`"dime la fecha de ingreso de Geovanna Quintero"` → iba a **compras_insumos** (confundido por
la palabra "ingreso" ≈ "ingreso de mercadería"). Ya no.

##### Confirmación
```
[PASS] routing_rrhh_fecha_ingreso_empleado  (rrhh)
       detalle:  Routing OK: rrhh
```

---

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
✅ Aplicado a los 7 agentes en el mismo commit. **⚠️ Regresión encontrada en RRHH-101 (09/Abr/2026):**
el fix original NO cubrió al agente `general`, que sigue emitiendo "no tengo acceso" cuando el
orchestrator le manda una pregunta de RRHH que no supo clasificar.

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

#### 🔴 Abiertos (2)

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

#### ✅ Resueltos (7)

##### COMP-100: Compras de insumos devolvía "no hay datos" por TypeError silencioso en wrapper
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (golden test `compras_insumos_total_2025_ves` + `compras_insumos_facturas_count_2025_ves` → ambos FAIL)
- **Resuelto:** 2026-04-09
- **Commit del fix:** (ver commit siguiente)
- **Test de regresión:** `compras_insumos_total_2025_ves`, `compras_insumos_facturas_count_2025_ves` en `backend/tests/golden/cases.yaml`

##### Síntoma observable
Pregunta: `"¿Cuánto se compró en insumos en 2025 en bolívares?"`
Respuesta real del bot:
> "No se encontraron datos de compras de insumos para el año 2025 en bolívares (VES). Si necesitas datos de otro período o moneda, indícame el año, mes o rango de fechas específico. **Nota:** Los datos disponibles corresponden al año actual (2026) por defecto."

Ground truth SQL directo contra iDempiere: **Bs. 8,212,602,071.70** en 7,426 facturas.
Los datos EXISTEN, el bot NO los encuentra.

##### Causa raíz (a nivel de código)
El agente `compras_insumos.py:599-605` llama a `build_supply_purchases(org_name=org_name, ...)`
importándolo de `query_service.py` (NO directamente de `idempiere_queries.py`).

El wrapper en `backend/app/services/query_service.py:1134-1145` (pre-fix) NO declaraba `org_name`
en su firma, ni lo forwardeaba a la función subyacente. Resultado:

```python
# query_service.py (pre-fix)
def build_supply_purchases(
    mes=None, anio=None, org_ids=None,
    date_from=None, date_to=None, currency_ids=None,
    # <<< falta org_name
) -> dict:
    if _is_production():
        from app.services.idempiere_queries import build_supply_purchases as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids,
                     date_from=date_from, date_to=date_to,
                     currency_ids=currency_ids)  # <<< no forwardea org_name
```

Cuando el agente llamaba con `org_name=None` (caso normal, la mayoría de preguntas):
```python
>>> build_supply_purchases(mes=None, anio=2025, currency_ids=[205], org_name=None)
TypeError: build_supply_purchases() got an unexpected keyword argument 'org_name'
```

El `try/except` del agente (línea 608-614) capturaba el TypeError y añadía a las secciones:
```
## Error al consultar datos
Se produjo un error al consultar la base de datos: TypeError.
```

El LLM (DeepSeek v3) recibía eso + el system prompt que dice "Los datos corresponden al año
actual por defecto" y construía una respuesta engañosamente amable: "No se encontraron datos
de compras de insumos para el año 2025 en bolívares". Nada indicaba que había un error real.

**Este es un bug SILENCIOSO clásico**: el error se enmascara como "no data" y los usuarios asumen
que iDempiere no tiene el dato. Los supervisores llevaban quién sabe cuánto tiempo sin poder
hacer consultas históricas de compras de insumos sin saber que era un bug del código.

##### Diagnóstico
Llamada directa desde dentro del contenedor backend:
```bash
docker compose exec -T backend python -c "
from app.services.query_service import build_supply_purchases
r = build_supply_purchases(mes=None, anio=2025, currency_ids=[205], org_name=None)
print(r['totales'])
"
# → TypeError: build_supply_purchases() got an unexpected keyword argument 'org_name'
```

##### Fix aplicado
Agregado `org_name: str | list[str] | None = None` a la firma de `build_supply_purchases` en
`query_service.py` y forwardeado a `_prod()`.

```python
# query_service.py (post-fix)
def build_supply_purchases(
    mes=None, anio=None, org_ids=None,
    date_from=None, date_to=None, currency_ids=None,
    org_name: str | list[str] | None = None,  # <<< nuevo
) -> dict:
    if _is_production():
        from app.services.idempiere_queries import build_supply_purchases as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,  # <<< forwardeado
        )
```

##### Cross-Agent Review — HALLAZGO CRÍTICO
**La revisión cruzada destapó 3 bugs idénticos** en el mismo archivo `query_service.py`, todos
en funciones que el agente `compras_insumos.py` llama. Script usado:

```python
# Compara firmas prod vs wrapper buscando org_name faltante
for name in funciones_prod_con_org_name:
    if wrapper_sigs[name] doesn't contain 'org_name':
        print(f'BUG: {name}')
```

Resultado inicial (pre-fix):

| Función | Estado |
|---|---|
| build_sales_summary | OK |
| build_collection_summary | OK |
| build_top_clients | OK |
| build_sales_by_product | OK |
| build_sales_orders | OK |
| build_sales_tax_summary | OK |
| build_sales_by_branch | OK |
| build_producer_purchases | OK |
| **build_supply_purchases** | 🔴 **BUG (COMP-100)** |
| build_product_purchase_history | OK |
| **build_pending_purchase_orders** | 🔴 **BUG (COMP-103)** |
| build_supplier_price_comparison | OK |
| **build_purchase_payment_status** | 🔴 **BUG (COMP-104)** |
| **build_inventory_stock** | 🔴 **BUG (COMP-105)** |

**14/14 funciones con `org_name` prod, 10 wrappers OK, 4 wrappers con bug.** Los 4 bugs son
del mismo archivo y del mismo patrón: wrappers creados en fase temprana del proyecto antes
que `org_name` existiera, nunca actualizados cuando `org_name` se agregó a las funciones
subyacentes.

Se abrieron COMP-103, COMP-104, COMP-105 y se arreglaron en el mismo commit que COMP-100,
siguiendo el proceso obligatorio de cross-agent review documentado en `docs/BUGS_REGISTRY.md`
sección 2.

| Agente (consumidor) | Estado | Nota |
|---|---|---|
| ventas | ✅ No aplica | ventas usa `build_sales_*` que todos tienen org_name correctamente |
| rrhh | ✅ No aplica | rrhh no usa funciones de compras |
| finanzas | ⚠️ Aplica parcial | finanzas usa `build_supplier_balance` — revisar en próxima sesión |
| contabilidad | ✅ No aplica | contabilidad usa `build_accounting_summary` (OK) |
| produccion | ⚠️ Aplica parcial | produccion también usa `build_inventory_stock` → COMP-105 beneficia también a produccion |
| compras_insumos | 🔴 **Agente afectado** | 4 de sus funciones estaban rotas |
| compras_productores | ✅ No aplica | usa `build_producer_*` que tienen org_name OK |
| orchestrator | N/A | no llama funciones de query |
| base_agent | N/A | idem |

##### Verificación post-fix
Re-correr el golden suite:
```bash
docker compose exec -e BOT_USERNAME=admin -e BOT_PASSWORD='...' -e IDEMPIERE_PASSWORD='...' backend python -m tests.golden.runner
```
Esperado: los 2 casos `compras_insumos_*_2025_ves` deben pasar de FAIL a PASS.

---

##### COMP-103: `build_pending_purchase_orders` wrapper no forwardea `org_name`
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (cross-agent review de COMP-100)
- **Resuelto:** 2026-04-09 (mismo commit que COMP-100)
- **Test de regresión:** pendiente (Tranche 2 agregará un caso para "órdenes de compra pendientes")

##### Síntoma (inferido, no observado directamente)
Cualquier pregunta que hiciera el agente `compras_insumos.py` sobre órdenes pendientes (keywords:
"orden de compra", "pendiente", "por recibir", "por recepcionar", "solicitado") reventaría con
`TypeError` cuando llegara a `build_pending_purchase_orders` con `org_name=<cualquier valor>`.

El error se enmascaraba como "no hay datos" por el mismo mecanismo que COMP-100.

##### Causa raíz
Mismo patrón que COMP-100. `query_service.py:1191-1212` (pre-fix) no declaraba `org_name`:
```python
def build_pending_purchase_orders(
    mes, anio, org_ids, date_from, date_to, currency_ids, product_search,
    # <<< falta org_name
) -> dict:
    if _is_production():
        from app.services.idempiere_queries import build_pending_purchase_orders as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, product_search=product_search,
            # <<< no forwardea org_name
        )
```

##### Fix aplicado
Agregado `org_name` a la firma del wrapper y forwardeado a `_prod()`.

##### Cross-Agent Review
Idéntico al de COMP-100 — todos los bugs se descubrieron en la misma iteración cross-agent.

---

##### COMP-104: `build_purchase_payment_status` wrapper no forwardea `org_name`
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (cross-agent review de COMP-100)
- **Resuelto:** 2026-04-09 (mismo commit que COMP-100)
- **Test de regresión:** pendiente

##### Síntoma (inferido)
Cualquier pregunta sobre estado de pago de facturas de compra ("estado de pago", "pagada",
"pagadas", "pendiente de pago", "por pagar", "facturas vencidas", "morosidad", "cuentas por
pagar", "deuda", "adeudado") reventaría con `TypeError`, enmascarado como "no hay datos".

##### Causa raíz
Mismo patrón. `query_service.py:1234-1248` no declaraba `org_name`.

##### Fix aplicado
Agregado `org_name` a la firma del wrapper y forwardeado a `_prod()`.

---

##### COMP-105: `build_inventory_stock` wrapper no forwardea `org_name`
- **Severidad:** 🔴 CRÍTICO
- **Reportado:** 2026-04-09 (cross-agent review de COMP-100)
- **Resuelto:** 2026-04-09 (mismo commit que COMP-100)
- **Test de regresión:** pendiente

##### Síntoma (inferido)
Cualquier pregunta de inventario/stock ("inventario", "stock", "existencia", "almacén",
"disponible", "cuánto hay", "cuánto queda", "cuánto tenemos") reventaría con `TypeError`,
enmascarado como "no hay datos". Este bug también afecta al agente `produccion.py` si ese
agente comparte `build_inventory_stock`.

##### Causa raíz
Mismo patrón. `query_service.py:1335-1347` no declaraba `org_name`.

##### Fix aplicado
Agregado `org_name` a la firma del wrapper y forwardeado a `_prod()`.

---

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

### Infraestructura / Runner de tests

#### 🔴 Abiertos (2)

##### INFR-100: Parser de runner lee "1.730" como 1.73 en vez de 1730
- **Severidad:** 🔴 CRÍTICO (al framework de tests, no al bot)
- **Reportado:** 2026-04-09 (Tranche 2 del golden suite)
- **Resuelto:** 2026-04-09 (fix en este mismo commit)
- **Commit del fix:** (ver commit siguiente)

##### Síntoma observable
En el run del Tranche 2, el caso `facturas_venta_bolivares_feb_2026` (Tranche 1) pasó de PASS
a FAIL. El bot respondió correctamente:
> "Total facturas emitidas: **1.730**"

Pero `compare_count_exact` reportó:
> "Esperado 1730. Top-3 enteros candidatos: [380]"

El parser leía `"1.730"` como `1.73` (punto como decimal ISO). En `compare_count_exact` solo
se consideran números que son enteros exactos (`n == int(n)`), así que 1.73 quedaba excluido
del conjunto de candidatos. Solo quedaba 380 (el conteo de notas de crédito).

Mismo síntoma con `compras_insumos_facturas_count_2025_ves`: el bot decía "7.426 facturas de
compra", parser leía 7.426, test FAIL.

##### Causa raíz (a nivel de código)
`backend/tests/golden/runner.py:parse_number()` manejaba 3 ramas:
1. `"." in s and "," in s` — mixto, con heurística por última posición
2. `"," in s` — solo comas, con heurística por cantidad de dígitos
3. Fallthrough a `float(s)` para cualquier otra cosa

La rama (3) no distinguía entre `"1.730"` (venezolano miles) y `"1.73"` (decimal ISO). Ambos
iban a `float(s)` que siempre interpreta el punto como decimal.

##### Fix aplicado
Nueva rama explícita `elif "." in s:` con heurística:
- Múltiples puntos → miles venezolano ("1.234.567" = 1234567)
- Un solo punto con "N.NNN" (izquierda 1-3 dígitos no-cero, derecha exactamente 3 dígitos
  y no es "0.XXX") → miles venezolano
- Cualquier otra cosa (`"3.14"`, `"0.500"`, `"3.14159"`) → decimal ISO

Validado con 15 tests unitarios incluyendo casos patológicos:
```
1.730   → 1730    ✓   3.14    → 3.14      ✓
7.426   → 7426    ✓   0.5     → 0.5       ✓
1.234.567 → 1234567 ✓  0.500   → 0.5       ✓  (protegido contra falso positivo)
123.456 → 123456  ✓   3.14159 → 3.14159   ✓
```

##### Cross-Agent Review
N/A — es un bug del runner de tests, no de un agente. Sin embargo, vale la pena nota que este
bug fue **silencioso y regresivo**: los 2 casos pasaban en Tranche 1 porque el bot los formateaba
en otro formato (con coma como separador decimal). Entre Tranche 1 y Tranche 2 el bot cambió el
formato de salida (o la pregunta disparó una rama distinta del LLM), y el parser expuso su
debilidad. Esto sugiere que el parser debería tener un suite de tests unitarios dedicado en
`backend/tests/golden/test_parser.py` para cazar regresiones parser-vs-bot-format más temprano.

---

##### INFR-101: Timeouts masivos del bot después de ~14 preguntas consecutivas
- **Severidad:** 🔴 CRÍTICO (bloquea medición del Tranche 2)
- **Reportado:** 2026-04-09 (Tranche 2 del golden suite)
- **Resuelto:** —
- **Commit del fix (mitigación temporal):** (este commit agrega `--delay` al runner)
- **Fix definitivo:** pendiente de investigación

##### Síntoma observable
En el baseline de Tranche 2 (24 casos), los casos [15..22] dieron `Bot error: ReadTimeout:
timed out` consecutivamente:

```
[PASS] routing_compras_empaque_inproa_2025         (caso 14, 12s)
[FAIL] routing_finanzas_saldo_cxp_proveedores      (caso 15, TIMEOUT)
[FAIL] routing_agri_deuda_productor_especifico     (caso 16, TIMEOUT)
[FAIL] routing_agri_deuda_maiz_buque               (caso 17, TIMEOUT)
[FAIL] routing_agri_maiz_acondicionado_inpromaiz   (caso 18, TIMEOUT)
[FAIL] routing_agri_compras_maiz_mes_actual        (caso 19, TIMEOUT)
[FAIL] routing_ventas_clientes_aperturados         (caso 20, TIMEOUT)
[FAIL] routing_finanzas_saldos_bancarios_baseline  (caso 21, TIMEOUT)
[PASS] routing_contabilidad_balance_dic_2025_baseline  (caso 22, 17s)
[PASS] routing_produccion_ordenes_ene_2026_baseline    (caso 23, 10s)
```

Nótese que los últimos 2 casos volvieron a responder. Eso descarta "bot colgado permanentemente".

##### Causa raíz (hipótesis, pendiente)
1. **Rate limit del proveedor LLM (OpenRouter/DeepSeek).** 14 requests consecutivos en < 3
   minutos puede disparar throttling. Los últimos 2 casos pasaron porque hubo ~30s de espera
   por los timeouts anteriores, dándole tiempo al rate limit a resetearse.
2. **Saturación de memoria en el backend.** Las conversaciones se acumulan en memoria + DB.
3. **Contención en iDempiere.** Cada caso dispara queries contra la DB de producción.
4. **ChromaDB rate limit interno.** Los logs de inicio muestran errores `'_type'` en ChromaDB.

##### Mitigación temporal (este commit)
`runner.py` ahora soporta:
- `--delay N`: esperar N segundos entre casos (reduce ritmo de queries al LLM).
- `--retry-timeout`: si un caso da timeout, esperar 30s y reintentar una vez.

Ejemplo de uso:
```bash
docker compose exec ... backend python -m tests.golden.runner --delay 3 --retry-timeout
```

Con esto podemos reconfirmar si los 7 casos que fallaron por timeout son bugs reales o
simplemente fueron víctimas de la saturación temporal.

##### Fix definitivo (pendiente)
Para arreglar el bug de raíz (que el bot no se sature con 14+ queries):
1. Diagnosticar qué se satura exactamente (LLM, DB, memoria).
2. Si es rate limit del LLM, agregar retry exponencial en el llm_factory del backend.
3. Si es memoria, investigar la cache de conversaciones y agregar límites.
4. Agregar monitoreo estructurado (latencia por proveedor, rate de errores).

##### Cross-Agent Review
N/A — es bug de infraestructura. Aplica a todos los agentes de la misma manera.

---

## 7. Changelog del registro

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-04-09 | Creación del registro, backfill completo de ventas (9 resueltos), y apertura de 14 bugs nuevos detectados en análisis de logs reales | Claude + Sergio |
| 2026-04-09 | Diagnóstico y fix de COMP-100 (TypeError silencioso en `query_service.build_supply_purchases`). **Primer uso del proceso obligatorio de cross-agent review** → destapó COMP-103, COMP-104, COMP-105 (bugs idénticos en otros 3 wrappers del mismo archivo). Los 4 bugs se resolvieron en el mismo commit `beef39a`. Sin el proceso, solo se habría arreglado COMP-100 y los otros 3 habrían quedado silenciosos indefinidamente. | Claude + Sergio |
| 2026-04-09 | **Tranche 1 cerrado con 10/10 PASS (100% precisión medida).** Re-run del golden suite post-fix confirmó que los 2 FAILs de `compras_insumos_*_2025_ves` pasaron a PASS con match exacto. Timings promedio 10.9s, máximo 21.9s (top 10 vendedores). Primer cierre formal de un tranche con métrica verificable. | Claude + Sergio |
| 2026-04-09 | **Tranche 2 baseline** (14 casos nuevos de routing). Resultado: 13/24 PASS, 11/24 FAIL. Análisis: (a) 3 tickets silenciosamente resueltos antes del Tranche 2 (RRHH-100/102/103 movidos a Resueltos); (b) 2 bugs de routing confirmados vivos (RRHH-101, COMP-101); (c) 2 bugs propios del framework descubiertos por el mismo golden test (INFR-100 parser, INFR-101 saturación/timeouts); (d) 6 tickets no evaluables por los timeouts (FIN-100, AGRI-100..103, PRDC-100) — requieren re-run con `--delay`. El framework detectó 3 arreglos invisibles y 2 bugs de sí mismo, demostrando su valor auto-correctivo. | Claude + Sergio |

