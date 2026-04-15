# Mapa de Pruebas — Cuestionarios de Validación SantoniBot

**Fecha:** 15/Abr/2026
**Branch:** `claude/amazing-brown-R5Yzm`
**Alcance:** Pruebas batch por terminal contra SQL Directo (Claude + prompt caching)
**Prioridad del cliente:** Ventas, RRHH, Contabilidad (luz verde de Santoni 14/Abr)

---

## 1. Propósito

Mapear cada pregunta de los cuestionarios formales de Santoni (llenados por los
responsables de cada área: Darwin, esalas, Emelin, Johan) con:

- La pregunta exacta que debe dispararse contra el bot
- El valor esperado según el documento (cuando esté disponible)
- La función de `idempiere_queries.py` o la query SQL esperada
- Observaciones sobre bugs históricos relacionados

Los archivos `.txt` en `backend/scripts/qa/` son la fuente de verdad ejecutable
para el runner `batch_test.py`.

---

## 2. Flujo de validación

```
1. batch_test.py --file preguntas_<area>.txt
2. Captura respuestas + SQL generado + tiempo
3. analyze_sql_audit.py --last N (clasifica fallos)
4. Humano compara respuestas vs cuestionario formal
5. Bug encontrado → fix macro en catálogo + REGLA (no caso-por-caso)
6. Re-ejecutar batch y medir mejora
```

---

## 3. REGLAS CRÍTICAS del catálogo SQL Directo (referencia)

| # | Regla | Tema |
|---|-------|------|
| #1 | Desglose obligatorio por org | Ambigüedad consolidado vs principal |
| #2 | Separar facturas (ARI) vs NC (ARC) | Doble conteo mal |
| #3 | Destacar anulatorias grandes | Transparencia |
| #4 | Sos la fuente de datos | No derivar/placeholder |
| #5 | Desgloses completos, no resúmenes | Sanity check sum = total |
| #6 | Mapeo columna → tabla | Santoni específico |
| #7 | No hacer aritmética mental | UNION ALL con sort_order |
| **#8** | **Flujo Orden → ProForma → Factura** | **15/Abr — distinguir USD real vs legal** |

---

## 4. VENTAS — Cuestionario 01 (Darwin / esalas)

### 4.1 Bug principal reportado

> "Top 10 clientes" sumaba ProFormas + NC sin restar, contaminando el ranking.

**Fix macro (15/Abr):** REGLA #8 distingue doctype `Proforma*/ProDolares*`
vs facturas legales. SQL Directo ya lo soporta; agentes clásicos lo
documentan como fallback combinado.

### 4.2 Preguntas clave

| # | Pregunta | Esperado | Función / Tabla |
|---|---------|---------|-----------------|
| V-01 | Total de ventas en bolívares de INPROA SANTONI en febrero 2026 | Bs 2.646M (sin IVA) | `c_invoice` issotrx=Y, totallines, VES |
| V-02 | Total de ventas en dólares de marzo 2026 (todas las orgs) | Desglose Proforma vs Factura Legal | REGLA #8 — separar dt.name |
| V-03 | Top 10 clientes por facturación neta febrero 2026 en bolívares | 10 filas clientes + monto neto | `build_top_clients` currency=VES |
| V-04 | Top 10 vendedores por venta neta INPROA SANTONI feb 2026 | Tabla pre-formateada `_format_vendedores_table` | ver bugs 08/Abr |
| V-05 | ¿Cuánto se cobró en bolívares en febrero 2026? | Bs 12,105M (coincide golden test) | `c_payment` isreceipt=Y |
| V-06 | Ventas por zona comercial en marzo 2026 INPROA | Desglose por c_salesregion | join via c_bpartner_location |
| V-07 | Ventas por tipología de cliente (c_bp_group) | Desglose categorías | c_bp_group join |
| V-08 | Ventas por categoría de producto (G05 ARROZ, G15 BEBIDA, G17 CEREAL, G03 HARINA) | Desglose por m_product_category | `build_sales_by_product` |
| V-09 | Órdenes de compra pendientes (C-Order) de clientes | Lista con cliente, monto, fecha | `c_order` docstatus no CL |
| V-10 | ¿Qué facturas tiene el cliente X pendientes de pagar? | Lista + saldo pendiente | c_allocationline gap |

### 4.3 Regiones vs Zonas

Región geográfica (`c_region`): estado venezolano (Lara, Zulia, etc.)
Zona comercial (`c_salesregion`): ruta de ventas (ZONA BARQUISIMETO, ZONA MARACAIBO)

Ambos se alcanzan vía `c_bpartner_location`. Ver REGLA #6 en el catálogo.

### 4.4 Follow-ups críticos a validar

- "¿y en dólares?" → hereda mes/año, cambia currency_ids a USD
- "¿y de InproMaiz?" → hereda periodo, cambia org
- "ahora top 5 en vez de 10" → hereda todo, cambia LIMIT
- "dame también marzo" → extiende rango de fechas

---

## 5. RRHH — Cuestionario 02 (Emelin Salas)

### 5.1 Números de referencia oficiales (de esalas, abril 2026)

| Organización | Empleados activos |
|--------------|-------------------|
| INPROA SANTONI | 258 (era 457 inflado antes de migrar a `lve_empleadosactivos`) |
| InproMaiz | 101 (era 217) |
| AGROINPROA | 143 + 90 + 27 = 260 empleados INPROA SANTONI según Emelin |
| AGA AGRICOLA | 15 (era 91) |
| **Grupo total** | **544 (antes 1,056)** |

### 5.2 Preguntas clave

| # | Pregunta | Esperado | Fuente |
|---|---------|---------|--------|
| R-01 | ¿Cuántos empleados activos hay en INPROA SANTONI? | 258 | `lve_empleadosactivos` |
| R-02 | ¿Cuántos empleados por departamento en INPROA SANTONI? | 35 departamentos | GROUP BY departamento |
| R-03 | ¿Cuántos empleados hay en EMPAQUE de INPROA SANTONI? | 17 | filtro departamento='EMPAQUE' |
| R-04 | ¿Quiénes cumplen años en mayo en INPROA SANTONI? | 19 empleados reales (TERAN ORTIZ, CASTRO VALERO...) | EXTRACT(MONTH FROM birthday)=5 |
| R-05 | Sueldo promedio en InproMaiz | AVG(total) de lve_empleadosactivos | `total` = sueldo+bonos |
| R-06 | Ausentismo de AGROINPROA en marzo 2026 | Desglose por concepto + TOTAL GENERAL | `hr_movement` + UNION ALL |
| R-07 | Resumen de nómina INPROA marzo 2026 | Desglose por tipo de nómina + TOTAL | hr_movement + hr_payroll |
| R-08 | Trabajadores con Faltas y Atrasos en marzo 2026 AGROINPROA | Lista nombres + ocurrencias + monto | hr_movement + c_bpartner |
| R-09 | Empleados con antigüedad >= 5 años en INPROA SANTONI | Lista ordenada DESC | EXTRACT(YEAR FROM AGE(...)) |
| R-10 | Control vacacional marzo 2026 INPROA | Lista empleado/periodo/días | concepto ILIKE '%vacacion%' |

### 5.3 Reglas específicas de RRHH

- **`lve_empleadosactivos` es la fuente oficial**, NUNCA `hr_employee` (3x inflado)
- **`hr_movement` para movimientos de nómina**: usar `m.validfrom` para filtrar fechas
- **`c_bpartner.name` es el nombre del empleado**, NO `hr_employee` (que no tiene name)
- **Tablas que NO existen**: `hr_payslip`, `hr_rule`, `hr_payroll_employee`
- **`tservicio` y `edad` en `lve_empleadosactivos` son TEXT**: usar `EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))` para años de servicio numérico

---

## 6. CONTABILIDAD — Cuestionario no formal (incluido en RRHH/Finanzas)

Las preguntas de contabilidad suelen venir como parte de Finanzas pero se pueden
probar por separado:

| # | Pregunta | Esperado | Fuente |
|---|---------|---------|--------|
| C-01 | Balance general diciembre 2025 | Activos, pasivos, patrimonio | `fact_acct` + `c_elementvalue` |
| C-02 | Estado de resultados marzo 2026 INPROA | Ingresos − Egresos | fact_acct GROUP BY acctschema |
| C-03 | Libro diario marzo 2026 | Listado asientos | fact_acct ORDER BY dateacct |
| C-04 | Libro mayor cuenta X marzo 2026 | Movimientos cuenta específica | fact_acct WHERE c_elementvalue = X |
| C-05 | Balance de comprobación marzo 2026 | Cuentas + débito + crédito + saldo | `lve_trialbalance` (view LVE oficial) |
| C-06 | Asientos del usuario admin en abril | fact_acct filtro por creador | fact_acct |

### 6.1 Views LVE oficiales de contabilidad

- `lve_fact_acct` — hechos contables normalizados
- `lve_trialbalance` — balance de comprobación
- `lve_sales_book` / `lve_sales_books` — libro de ventas SENIAT
- `lve_buy_book` / `lve_buy_book_sumary` — libro de compras SENIAT

---

## 7. FINANZAS — Cuestionario 04 (no prioridad, incluido por completitud)

| # | Pregunta | Esperado | Fuente |
|---|---------|---------|--------|
| F-01 | Saldos bancarios actuales | Desglose por banco | `lve_disponibilidadbancaria` |
| F-02 | Cuentas por cobrar a marzo 2026 | Lista clientes + saldo | `lve_saldosclientes` |
| F-03 | Cuentas por pagar a marzo 2026 | Lista proveedores + saldo | `lve_saldosproveedor` |
| F-04 | Análisis vencimiento INPROA | Buckets 30/60/90 días | `lve_analisisvencimientoinproa` |
| F-05 | Anticipos a productores pendientes | Lista + monto | `lve_anticipoproductor` |

---

## 8. PRODUCCIÓN Y COMPRAS (no prioridad pero disponibles)

Ver `docs/Cuestionario_SantoniBot_05_Produccion.docx` y
`docs/Cuestionario_SantoniBot_06_Compras_Insumos.docx`. Las views LVE cubren:

- Inventario: `lve_inventario_terminado`, `lve_inventario_paddy`,
  `lve_inventario_maiz`, `lve_inventario_empaque`, `lve_inventario_granos`,
  `lve_inventario_repuesto`, `lve_inventario_comercial`, `lve_inventario_semilla`,
  `lve_inventario_proceso`, `lve_inventario_procmaiz`, `lve_inventario_costo`,
  `lve_inventario_maquinaria`
- Compras: `lve_buy_book`, `lve_buy_book_sumary`, `lve_anticipoproveedor`
- Productores: `lve_saldosproductor`, `lve_anticipoproductor`,
  `lve_guiasmovilizacion`, `lve_guiagranelsindespacho`, `lve_guiacaleta`

---

## 9. Archivos ejecutables

| Archivo | Área | Cantidad |
|---------|------|---------|
| `backend/scripts/qa/preguntas_esalas.txt` | RRHH (histórico Emelin) | 36 |
| `backend/scripts/qa/preguntas_ventas.txt` | Ventas (Darwin) | ~20 |
| `backend/scripts/qa/preguntas_rrhh.txt` | RRHH (completo) | ~25 |
| `backend/scripts/qa/preguntas_contabilidad.txt` | Contabilidad | ~10 |

---

## 10. Pendientes para el cierre Fase 1

- [ ] Validar con Darwin/esalas si "AR Invoice ProDolares" son preliminares
      o facturas reales en USD (esto define si el catálogo filtra o no).
- [ ] Actualizar `docs/DATOS_VERIFICACION_IDEMPIERE.md` con los datos de
      marzo 2026 completo (la sección 16.4 está a 14/Mar).
- [ ] Ejecutar batch completo de los 4 archivos y registrar tasa de éxito.
- [ ] Por cada fallo, aplicar fix MACRO (catálogo o regla), no caso-por-caso.
- [ ] Actualizar `docs/BUGS_REGISTRY.md` con tickets nuevos descubiertos.
