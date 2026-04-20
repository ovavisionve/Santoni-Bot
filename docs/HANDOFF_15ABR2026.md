# Handoff SantoniBot — 15/Abr/2026

**Branch:** `claude/amazing-brown-R5Yzm`
**Último commit:** `b02831e` (CxC scope fix con subquery correlacionada escalar)
**Filosofía del proyecto:** fixes MACRO por patrón, NO caso-por-caso. Ver `CLAUDE.md`.

---

## Estado actual

| Dominio | Estado | Tasa éxito última corrida |
|---|---|---:|
| RRHH (53 preguntas) | ✅ Estable | 100% (retest targeted) |
| CxC / Aging | ✅ Estable | 100% (4/4 retest) |
| Ventas (48 preguntas) | ⚠️ 63.64% → fix aplicado, **falta re-correr** | Pendiente |
| Contabilidad (38 preguntas) | ❓ NO corrido todavía | Pendiente |

## Cambio de costo pendiente (MUY IMPORTANTE)

SantoniBot gastó **$12.68 en 2 días** usando Sonnet 4.6. El plan para bajar costo:

1. **Switch a DeepSeek vía OpenRouter** en SantoniBot:
   ```bash
   cd /opt/santonibot
   sed -i 's/^USE_CLAUDE_FOR_SQL=.*/USE_CLAUDE_FOR_SQL=false/' .env
   docker compose restart backend && sleep 15
   ```
   Costo estimado: ~$0.003 por query (vs ~$0.08 con Sonnet). Las REGLAs del catálogo deberían guiar a DeepSeek.

2. **Si DeepSeek falla mucho**, activar híbrido fino:
   ```bash
   sed -i 's/^USE_CLAUDE_ONLY_FOR_COMPLEX=.*/USE_CLAUDE_ONLY_FOR_COMPLEX=true/' .env
   ```
   Claude solo para queries complejas (agregados, financial, aging). DeepSeek para simples.

## Siguiente corrida recomendada

```bash
cd /opt/santonibot && git pull origin claude/amazing-brown-R5Yzm
# (hacer el switch a DeepSeek primero)
docker compose restart backend && sleep 15

# a) Re-correr ventas (tras fix CxC)
docker compose exec backend python scripts/qa/batch_test.py scripts/qa/preguntas_ventas.txt --delay 2

# b) Contabilidad (38 preguntas, nunca corrido)
docker compose exec backend python scripts/qa/batch_test.py scripts/qa/preguntas_contabilidad.txt --delay 2
```

Después del batch, analizar patrones:
```bash
docker compose exec backend python scripts/qa/analyze_sql_audit.py --last 40
```

## REGLAs actuales del catálogo SQL Directo (`backend/app/services/sql_direct.py`)

| # | Tema |
|---|---|
| #1 | Desglose obligatorio por org |
| #2 | Separar ARI (facturas) vs ARC (NC) |
| #3 | Destacar anulatorias grandes |
| #4 | Sos la fuente de datos (no derivar) |
| #5 | Desgloses completos |
| #6 | Mapeo columna→tabla + anti-QUALIFY + alias obligatorios + scope CTE |
| #7 | No aritmética mental (UNION ALL con sort_order) |
| #8 | ProForma vs Factura (dt.name discriminador) |

## Bugs macro resueltos en esta sesión (15/Abr)

1. Batch_test reportaba 0% SQL Directo (fantasma — fix en `chat.py`)
2. CardinalityViolation con ILIKE (`IN (SELECT)` obligatorio)
3. Timeout en AVG(total) → preferir AVG(sueldo)
4. AmbiguousColumn `name` → alias `v.` obligatorio
5. QUALIFY (no PostgreSQL) → usar ROW_NUMBER en subquery
6. Columnas inexistentes en c_invoice (duedate, netdays) → calcular con c_paymentterm
7. Scope de CTEs → subquery correlacionada escalar para casos con `i`

## Filosofía consolidada

> **No arreglar pregunta por pregunta. Arreglar PATRONES.** Una REGLA en el catálogo cubre N queries futuras. Cuando Claude viola la MISMA regla 3 veces, la regla está incompleta — hay que ofrecer el patrón que satisface el instinto del LLM, no solo prohibir.

## Archivos clave

- `backend/app/services/sql_direct.py` — SQL Directo + catálogo + REGLAs
- `backend/app/agents/orchestrator.py` — routing + `_try_sql_direct`
- `backend/app/api/routes/chat.py` — stream endpoint (fix reporting aplicado)
- `backend/scripts/qa/batch_test.py` — runner de pruebas batch
- `backend/scripts/qa/analyze_sql_audit.py` — clasificador de patrones de error
- `backend/scripts/qa/preguntas_{ventas,rrhh,contabilidad}.txt` — 139 preguntas de batch
- `backend/scripts/qa/retest_cxc.txt` — retest targeted CxC (4 preguntas)
- `docs/CUESTIONARIO_LEVANTAMIENTO_TRANSCRIPCION.md` — transcripción literal del doc grande
- `docs/MAPA_PRUEBAS_CUESTIONARIOS.md` — mapa curado por agente
- `CLAUDE.md` — filosofía + historial de sesiones

## Queda pendiente de discutir

- Diagrama ASCII de arquitectura del bot (el "mapa visual" que pediste — postergado)
- Extracción de TODAS las preguntas de los 5 .docx (hice curado parcial, no exhaustivo)
- Si la tasa de Claude vs DeepSeek diverge mucho, evaluar cuál queda en producción

## Comando para arrancar nueva sesión

```bash
# En tu terminal local
cd ~/Santoni-Bot  # o donde tengas el repo local
claude --model claude-opus-4-6
```

En la sesión nueva, abrir este archivo y pedir:
> "Leé `docs/HANDOFF_15ABR2026.md` y seguí donde quedamos. Arrancá con el switch a DeepSeek."
