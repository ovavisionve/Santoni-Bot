"""Catálogo: views y tablas de RRHH + Nómina."""

VIEWS_RRHH = """
### RRHH — Empleados
**lve_empleadosactivos** — Empleados activos del grupo Santoni (1 fila por empleado REAL)
Columnas: ad_org_id, name (nombre completo REAL del empleado), value (cédula), c_bpartner_id,
  hr_payroll_id, nomina (tipo nómina), startdate (fecha ingreso),
  hr_department_id, departamento, hr_job_id, cargo,
  birthday (fecha de nacimiento — usar para cumpleañeros: EXTRACT(MONTH FROM birthday) = N),
  sueldo (sueldo BASE sin bonos — COLUMNA DIRECTA, agregados rápidos),
  asignacion (bonos/asignaciones),
  total (TOTAL DEVENGADO = sueldo + asignacion — COLUMNA CALCULADA per-row,
         agregados sobre esta columna son LENTOS y pueden tirar timeout),
  edad (TEXT con formato "N años M meses D dias"),
  tservicio (TEXT con formato "N años M meses D dias" — NO es numérico),
  gender
IMPORTANTE — PERFORMANCE de AVG/SUM sobre lve_empleadosactivos:
  - Para "sueldo promedio" genérico (queries rápidas): usar AVG(v.sueldo) —
    es el sueldo BASE y es mucho más rápido porque es columna directa.
  - AVG(v.total) es más preciso (incluye bonos) pero la columna `total`
    se calcula per-row dentro de la view y AVG fuerza TODOS esos cálculos,
    lo que puede tirar timeout (>30s). Usalo SOLO si el usuario pide
    explícitamente "devengado", "con bonos", "total real".
  - COUNT(*) y filtros WHERE son siempre rápidos (no evalúan `total`).
IMPORTANTE: Para cumpleañeros SIEMPRE generar SQL con SELECT name, cargo, departamento, birthday.
  NUNCA responder NO_SQL para preguntas de cumpleaños — la columna birthday está en esta view.
⚠️ tservicio y edad son TEXTO (no numérico). Si necesitás años de servicio como número,
calculalo desde startdate: `EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))`.
NO uses `FLOOR(tservicio)` ni `tservicio::numeric` — va a fallar con "invalid input syntax".
Para control de vacaciones (cálculo LOTT venezolano basado en antigüedad), usar startdate:
  `EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))` = años enteros de servicio.

**lve_empleadosinactivos** — Empleados inactivos/retirados (misma estructura)

### RRHH — Nómina (movimientos de pago)
**hr_movement** — Filas de movimientos de nómina (cada concepto por empleado por período)
Columnas: hr_movement_id, hr_process_id, hr_concept_id, c_bpartner_id, ad_org_id,
  validfrom (fecha inicio del período), validto (fecha fin),
  amount (monto en Bs para conceptos de dinero; qty (cantidad para conceptos de días/horas))
IMPORTANTE: para montos $ usar `amount`. Para días/horas, usar `qty`. Muchos conceptos tienen
  AMBOS (ej: "Días de Reposo" tiene qty=días y amount=0).

**hr_concept** — Catálogo de conceptos de nómina (sueldos, asignaciones, deducciones, etc.)
Columnas: hr_concept_id, name (ej: 'Sueldo Mensual', 'Monto a deducir por Faltas y Atrasos'),
  value (código corto), hr_concept_category_id, type (E=Earning devengado, D=Deduction, etc.)
IMPORTANTE: para filtrar por concepto, usar `c.name ILIKE '%XXX%'`.
Conceptos comunes para ausentismo (buscar con ILIKE):
  - 'Faltas y Atrasos' → monto descontado
  - 'Permiso No Remunerado'
  - 'Permiso Remunerado'
  - 'Reposo Pagado', 'Reposo Medico'
  - 'Inasistencia Injustificada'
  - 'Días de Asignación de Permiso'
  - 'Días de Asignación de Reposo'
Conceptos de ingresos: 'Sueldo Mensual', 'Salario', 'Total Asignaciones', 'Provisión Utilidades'.
Conceptos de vacaciones (buscar 'vacacion' ILIKE): muchos tipos.

**hr_process** — Proceso de nómina (un proceso = correr una nómina para un período)
Columnas: hr_process_id, name, dateacct (fecha contable del proceso), datetrx (fecha
  de transacción), hr_payroll_id, hr_period_id, ad_org_id, docstatus, c_bpartner_id
⚠️ CRÍTICO: en Santoni, la columna NO se llama `hrdate` (ese es el nombre en otras
instalaciones de iDempiere). En Santoni la fecha del proceso es **`dateacct`**.
Si usás `hrdate` va a fallar con "column does not exist".
IMPORTANTE: para filtrar nóminas de un período, usar
  `p.dateacct >= 'YYYY-MM-DD' AND p.dateacct < 'YYYY-MM-DD'`
Alternativa más segura: filtrar por `hr_movement.validfrom` que SIEMPRE tiene la
fecha del período directamente (sin necesidad de JOIN con hr_process).

**hr_payroll** — Catálogo de tipos de nómina (Nómina Semanal, Quincenal, Directivos, etc.)
Columnas: hr_payroll_id, name (ej: 'Nómina Semanal OBREROS', 'Nómina Directivos'),
  value (código)
IMPORTANTE: para desglosar un resumen por tipo de nómina, JOIN hr_process.hr_payroll_id →
  hr_payroll.hr_payroll_id.

**hr_employee** — Metadata del empleado (NO usar para contar activos — usar lve_empleadosactivos).
Columnas: c_bpartner_id (foreign key a c_bpartner que tiene el nombre),
  hr_department_id, hr_job_id, startdate, enddate, isactive

**c_bpartner** (para nómina) — el NOMBRE real del empleado está en c_bpartner.name.
  JOIN: hr_movement.c_bpartner_id = c_bpartner.c_bpartner_id para traer el nombre.
  La cédula suele estar en c_bpartner.taxid.

**hr_department** — Departamentos (hr_department_id, name, value)
**hr_job** — Cargos (hr_job_id, name, value)
"""
