# CUESTIONARIO DE VALIDACIÓN POR AGENTE
## Sistema SantoniBot – Alimentos Santoni, C.A.

**Fecha:** _______________
**Instrucciones:** Cada responsable de área debe escribir las preguntas EXACTAS que le haría al bot, tal como las escribiría en el chat. Para cada pregunta, indique la respuesta correcta esperada (el dato real). Esto nos permite verificar que el bot responde correctamente antes de la puesta en producción.

> **IMPORTANTE:** Escriba las preguntas tal como las escribiría en el chat del bot. Ejemplos:
> - "¿Cuántos empleados activos hay en INPROA SANTONI?"
> - "Dame el top 20 de clientes de InproMaiz"
> - "¿Cuál fue la producción de arroz en enero 2025?"

---

## 1. AGENTE DE VENTAS
**Responsables:** Carlos Matias / Lenny Silva / Yuleidys Gutierrez

**Capacidades actuales del agente:**
- Top clientes por ventas (general, por zona, por organización, por vendedor)
- Resumen de ventas por período (mes, año, rango de fechas)
- Resumen de cobranza por período
- Cuentas por cobrar vencidas
- Filtros: por zona, por moneda (Bs/USD), por organización (InproMaiz, INPROA, etc.)
- Períodos: mes y año, rangos de fecha, año completo

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuáles son los top 20 clientes por ventas del 2025?" | (Escriba los nombres y montos correctos) | |
| 2 | Ej: "Top 10 clientes de InproMaiz en enero 2026" | | |
| 3 | Ej: "Ranking de ventas por zona del mes de enero 2026" | | |
| 4 | Ej: "¿Cuánto se facturó en dólares en febrero 2026?" | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## 2. AGENTE DE RECURSOS HUMANOS
**Responsables:** Emelin Salas / Leonardo Rivero / Daniela López

**Capacidades actuales del agente:**
- Resumen de empleados por organización, departamento y cargo
- Búsqueda de empleados por cargo (ej: "cuantos obreros integrales hay")
- Indicadores de ausentismo (por concepto de nómina: inasistencia, falta, permiso, reposo)
- Resumen de nómina por período
- Indicadores de rotación (bajas por año)
- Filtros: por organización, por rango de fechas, por cargo

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuántos empleados activos hay en INPROA SANTONI?" | (Escriba el número correcto) | |
| 2 | Ej: "¿Cuántos empleados hay por departamento?" | (Lista con los números correctos) | |
| 3 | Ej: "¿Cuántos obreros integrales hay?" | | |
| 4 | Ej: "¿Cuántos choferes tiene la empresa?" | | |
| 5 | Ej: "Indicadores de ausentismo de INPROA SANTONI de septiembre 2025" | | |
| 6 | Ej: "¿Cuántos empleados ingresaron entre enero y junio 2025?" | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | Ej: "Cumpleañeros del mes de marzo" | Fecha de nacimiento | ¿Está cargada en iDempiere? ¿En otro sistema? |
| 2 | Ej: "Productividad laboral" | Fórmula: ventas / # empleados | |
| 3 | Ej: "Costo de rotación" | Costos de salida + reclutamiento + capacitación | |
| 4 | Ej: "Asistencias del día de hoy" | Datos de k-asistencia (biométrico) | ¿Cómo se conecta? ¿BD? ¿API? |
| 5 | | | |

---

## 3. AGENTE DE CONTABILIDAD
**Responsable:** Johan Alvarez

**Capacidades actuales del agente:**
- Balance general / Estado de resultados
- Libro diario / Libro mayor
- Detalle de cuentas contables por código
- Filtros: por período, por organización, por moneda

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "Muéstrame el balance general de enero 2026" | | |
| 2 | Ej: "¿Cuál es el saldo de la cuenta 1101 en febrero 2026?" | | |
| 3 | Ej: "Costos de productos a fecha 31/01/2026" | | |
| 4 | Ej: "Análisis de las partidas de gastos de enero a marzo 2026" | | |
| 5 | Ej: "Situación financiera de InproMaiz" | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

---

## 4. AGENTE DE FINANZAS
**Responsables:** Angela Russo / Orlando Artahona

**Capacidades actuales del agente:**
- Saldos bancarios
- Cuentas por cobrar (total, vencidas)
- Cuentas por pagar (total, vencidas)
- Filtros: por período, por organización

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuáles son los saldos bancarios actuales?" | | |
| 2 | Ej: "¿Cuánto tenemos en cuentas por cobrar vencidas?" | | |
| 3 | Ej: "Flujo de caja de enero 2026" | | |
| 4 | Ej: "¿Cuánto debemos en cuentas por pagar?" | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

---

## 5. AGENTE DE PRODUCCIÓN
**Responsables:** Mayra Bolivar / Eilen Perez / Elymar Davila
**Coordinadores:** Jorge Galíndez (Molino), Jocsan Castro (Empaque), Jhoan Paredes (Extrusora)

**Capacidades actuales del agente:**
- Órdenes de producción por período
- Resumen de producción (cantidades, desperdicios)
- Filtros: por período, por organización

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuánto se produjo en enero 2026?" | | |
| 2 | Ej: "¿Cuáles son las órdenes de producción del mes?" | | |
| 3 | Ej: "Inventario de materia prima actual" | | |
| 4 | Ej: "Producción de arroz blanco en enero 2026" | | |
| 5 | Ej: "¿Cuánto desperdicio hubo en empaque este mes?" | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | Ej: "Inventario inicial del mes" | Datos de inventario | ¿m_storage? ¿m_transaction? |
| 2 | Ej: "Rendimiento de materia prima" | Fórmula específica | |
| 3 | Ej: "Pedidos pendientes por despachar" | Órdenes en cola | |
| 4 | | | |

---

## 6. AGENTE DE COMPRAS DE INSUMOS
**Responsables:** Onofrio Gueccia / Jorge Chahine

**Capacidades actuales del agente:**
- Resumen de compras de insumos por período
- Historial de compras por producto (ej: "compras de cajas de carton este mes")
- Desglose por proveedor
- Filtros: por período, por organización, por producto

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuántas cajas de cartón compramos en enero 2026?" | | |
| 2 | Ej: "Dame el historial de compras de azúcar del último trimestre" | | |
| 3 | Ej: "¿Cuáles son los principales proveedores de material de empaque?" | | |
| 4 | Ej: "¿Cuál es el inventario actual de todos los insumos?" | | |
| 5 | Ej: "Precio de las últimas 6 compras de harina de avena" | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | Ej: "Máximo y mínimo de cada insumo" | Niveles min/max | ¿m_replenish? ¿m_warehouse? |
| 2 | Ej: "Alerta cuando un insumo esté en mínimo" | Stock actual vs mínimo | |
| 3 | Ej: "Tiempo de entrega por proveedor" | Historial de entregas | |
| 4 | Ej: "Para cuántos días de producción tenemos stock" | Consumo diario promedio + stock | |
| 5 | | | |

---

## 7. AGENTE DE COMPRAS A PRODUCTORES
**Responsable:** Marlenis Figueredo

**Capacidades actuales del agente:**
- Resumen de compras a productores (arroz, maíz) por período
- Productores registrados
- Pagos pendientes a productores
- Análisis de precios por producto
- Filtros: por período, por organización, por producto

### Preguntas de validación

| # | Pregunta exacta para el bot | Respuesta correcta esperada | Validado (Sí/No) |
|---|---|---|---|
| 1 | Ej: "¿Cuánto arroz paddy se compró en 2025?" | | |
| 2 | Ej: "¿Cuánto maíz se compró en 2025?" | | |
| 3 | Ej: "¿Cuántos productores de arroz hay registrados?" | (Escriba: 1679) | |
| 4 | Ej: "¿Cuántos productores de maíz hay registrados?" | (Escriba: 168) | |
| 5 | Ej: "¿Cuáles son los pagos pendientes a productores?" | | |
| 6 | Ej: "Precio promedio del kilo de arroz en 2025" | | |
| 7 | | | |
| 8 | | | |

**Preguntas que necesitan y el bot NO puede responder aún:**

| # | Pregunta | Dato necesario | ¿Dónde está la información? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

---

## INSTRUCCIONES PARA LOS RESPONSABLES DE ÁREA

1. **Escriba las preguntas tal como se las haría al bot**, en lenguaje natural
2. **Incluya la respuesta correcta** - el número, lista o dato real que espera ver
3. **Varíe las preguntas**: pruebe con diferentes períodos, filtros, formatos de fecha
4. **Incluya follow-ups**: después de una pregunta, ¿qué preguntaría a continuación?
   - Ejemplo: primero "top 20 clientes" → luego "y de InproMaiz?" → luego "y en dólares?"
5. **Anote lo que falta**: si necesita algo que el bot no puede hacer, escríbalo en la tabla de "NO puede responder aún"
6. **Sea específico con fechas**: "enero 2025", "del 01/01/2025 al 31/03/2025", "este mes", "el mes pasado"

**Plazo de entrega:** _______________
**Enviar a:** Luis Ilarraza / OVA Agency
