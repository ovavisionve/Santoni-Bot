# Reporte de Confidence Score - SantoniBot
### Alimentos Santoni, C.A. | OVA Agency
**Fecha:** 23 de marzo de 2026

---

## 1. ¿Qué es el Confidence Score?

El Confidence Score es un indicador numérico (0.0 a 1.0) que mide qué tan seguro está el bot de que su respuesta es correcta. Se compone de dos factores:

| Factor | Peso | Rango | Descripción |
|--------|------|-------|-------------|
| **Routing** | 60% | 0.3 - 1.0 | Confianza en que se seleccionó el agente correcto para la pregunta |
| **Datos** | 40% | 0.2 - 1.0 | Si la consulta a iDempiere devolvió datos reales |

**Fórmula:** `score = routing × 0.6 + datos × 0.4`

**Umbral de fallo:** score < 0.5

---

## 2. Clasificación de Routing (cómo se asigna el puntaje de routing)

| Tipo de match | Puntaje routing | Descripción |
|---------------|-----------------|-------------|
| Keyword exacto | 1.0 | La pregunta contiene palabras clave directas del agente (ej: "facturación" → Ventas) |
| Follow-up al último agente | 0.6 - 0.7 | No hay keywords claros pero el contexto sugiere continuar con el agente anterior |
| Fallback a ventas | 0.4 | Palabras genéricas sin match claro, se asume ventas |
| Sin match | 0.3 | No se pudo clasificar, va al agente general |

---

## 3. Tipos de Fallo Diagnosticados

El sistema diagnostica automáticamente la causa probable de cada interacción con baja confianza:

| Causa probable | Descripción | ¿Es problema del dataset? | ¿Es problema del umbral? |
|----------------|-------------|---------------------------|--------------------------|
| **Sin keywords reconocidos** | La pregunta no matcheó ningún agente y fue al agente general | ✅ Sí — faltan variantes en el dataset | ❌ No |
| **Follow-up sin datos** | Se perdió el contexto temporal de un follow-up | ❌ No — es un bug de herencia de contexto | ❌ No |
| **Agente correcto pero sin datos** | El agente correcto fue seleccionado, pero el período consultado no tiene datos en iDempiere | ❌ No | ⚠️ Parcial — el score baja por falta de datos, no por mala clasificación |
| **Keyword bloqueado, fallback** | El bot detectó el departamento correcto pero el usuario no tiene permisos | ❌ No — es restricción de RBAC | ❌ No |
| **Fallback ventas** | Palabras demasiado genéricas, se asumió ventas como fallback | ✅ Sí — faltan keywords específicos | ❌ No |
| **Saludo o pregunta general** | El usuario hizo una pregunta que no requiere datos (ej: "hola", "qué puedes hacer") | ❌ No — comportamiento esperado | ❌ No |
| **Acceso denegado** | Clasificación correcta pero el usuario no tiene permisos al departamento | ❌ No | ❌ No |

---

## 4. Cómo acceder al reporte de interacciones fallidas

### Endpoint directo (requiere usuario supervisor o admin):

```
GET /api/admin/confidence-report/low?limit=50&threshold=0.5
```

**Parámetros configurables:**

| Parámetro | Default | Rango | Descripción |
|-----------|---------|-------|-------------|
| `limit` | 50 | 1 - 500 | Cantidad de interacciones a devolver |
| `threshold` | 0.5 | 0.0 - 1.0 | Score máximo para considerar "fallida" |

**Ejemplo de respuesta por interacción:**

```json
{
  "message_id": 1234,
  "timestamp": "2026-03-22T14:35:00",
  "user": "Juan Pérez",
  "pregunta": "¿Cuánto se compró de harina el mes pasado?",
  "agent_used": "general",
  "confidence_score": 0.38,
  "routing_score": 0.3,
  "data_score": 0.2,
  "match_type": "sin_match",
  "causa_probable": "Sin keywords reconocidos - pregunta fue al agente general sin datos"
}
```

### Reporte general (todas las interacciones con estadísticas):

```
GET /api/admin/confidence-report?limit=50
```

Este endpoint devuelve adicionalmente un resumen con:
- Score promedio, mínimo y máximo
- Cantidad de interacciones con baja confianza
- Desglose por agente (total y promedio por cada uno)

---

## 5. Respuesta a la pregunta del equipo Santoni

> "¿El error es porque el bot tiene un umbral de confianza muy bajo o porque el dataset de entrenamiento no cubre las variantes básicas?"

### Cómo distinguirlo en el reporte:

**Si la mayoría de fallos tienen `causa_probable` = "Sin keywords reconocidos" o "Fallback ventas":**
→ El problema es el **dataset**. Faltan variantes de preguntas que el clasificador no reconoce. Se resuelve agregando más escenarios al `training_dataset.json` (actualmente 356 escenarios, v2.5).

**Si la mayoría de fallos tienen `causa_probable` = "Agente correcto pero sin datos":**
→ El problema **NO** es el dataset ni el umbral. El bot clasifica bien, pero el período consultado no tiene datos en iDempiere. El score baja por el factor de datos (40%), no por mala clasificación.

**Si la mayoría de fallos tienen `routing_score` > 0.7 pero `data_score` = 0.2:**
→ El **umbral** podría ser demasiado estricto. El routing es bueno pero la falta de datos arrastra el score por debajo de 0.5. Se podría considerar subir el peso del routing o bajar el umbral a 0.4.

**Si la mayoría de fallos tienen `routing_score` < 0.4:**
→ El clasificador no está entendiendo las preguntas → problema de **dataset**.

---

## 6. Dataset actual (v2.5)

| Métrica | Valor |
|---------|-------|
| Total de escenarios | 356 |
| Follow-ups | 78 |
| Escenarios de alucinación | 22 |
| Escenarios con error de routing | 11 |
| Por agente (top 3) | Compras Insumos: 85, RRHH: 65, Ventas: 58 |
| Fuentes | Cuestionario Word: 107, Conversación real: 89, Corrección bug: 52 |

### Tipos de error rastreados en el dataset:

| Tipo de error | Cantidad | Descripción |
|---------------|----------|-------------|
| Alucinación | 22 | El LLM inventó datos sin tener información real |
| Routing general | 11 | Pregunta fue al agente general en vez del especializado |
| Follow-up perdido | 8 | Se perdió el contexto del follow-up |
| Sin datos | 5 | Agente correcto pero período vacío |
| Dato no disponible | 3 | El dato existe pero no es accesible |
| Acceso denegado | 2 | Permisos insuficientes |
| Funcionalidad no disponible | 2 | El agente no puede hacer lo que se pidió |
| Error de programación | 1 | Bug en el código del agente |
| Privacidad | 1 | Restricción de datos sensibles |
| Datos incorrectos | 1 | Respuesta con datos equivocados |

---

## 7. Recomendaciones

1. **Ejecutar el endpoint** `/api/admin/confidence-report/low?limit=50` y revisar la columna `causa_probable` para determinar la categoría dominante de fallos.

2. **Si dominan fallos de routing** (sin keywords / fallback): Ampliar el dataset con las preguntas reales que están fallando. Cada pregunta nueva se agrega como escenario en `training_dataset.json`.

3. **Si dominan fallos de datos**: Verificar que los períodos consultados por los usuarios tengan datos cargados en iDempiere. No es un problema del bot.

4. **Si el score está consistentemente entre 0.4-0.5**: Considerar ajustar el umbral de fallo de 0.5 a 0.4, o modificar los pesos (actualmente 60/40 routing/datos).

---

*Documento generado por OVA Agency para Alimentos Santoni, C.A.*
*Sistema SantoniBot v1.0 — Marzo 2026*
