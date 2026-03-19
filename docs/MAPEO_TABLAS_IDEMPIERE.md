# Mapeo Completo de Tablas iDempiere - SantoniBot

**Referencia tecnica de produccion** | Ultima actualizacion: 19 Marzo 2026

---

## 1. Informacion de Conexion

| Parametro | Valor |
|-----------|-------|
| **Motor** | PostgreSQL 13 |
| **Schema** | `adempiere` |
| **Servidor** | 192.168.1.73:5432 |
| **Base de datos** | `idempiere_produccion` |
| **Usuario** | `ova` (solo lectura / SELECT unicamente) |
| **Seguridad** | `SET default_transaction_read_only = ON` |

> SantoniBot **nunca** modifica datos en iDempiere. Todas las queries son SELECT parametrizadas via SQLAlchemy `text()`.

---

## 2. Resumen de Tablas por Agente

La siguiente tabla muestra las **46 tablas** del schema `adempiere` que SantoniBot consulta activamente, agrupadas por el agente que las utiliza.

| # | Tabla | Ventas | Finanzas | Contabilidad | RRHH | Produccion | Compras Insumos | Compras Productores |
|---|-------|:------:|:--------:|:------------:|:----:|:----------:|:---------------:|:-------------------:|
| 1 | `ad_org` | x | x | x | x | x | x | x |
| 2 | `c_invoice` | x | x | - | - | - | x | x |
| 3 | `c_invoiceline` | - | - | - | - | - | x | x |
| 4 | `c_payment` | x | x | - | - | - | - | - |
| 5 | `c_bpartner` | x | x | - | x | x | x | x |
| 6 | `c_bpartner_location` | x | - | - | - | - | - | x |
| 7 | `c_salesregion` | x | - | - | - | - | - | - |
| 8 | `c_bp_group` | x | - | - | - | - | - | - |
| 9 | `c_doctype` | x | x | - | - | - | - | - |
| 10 | `c_currency` | - | x | x | - | - | - | - |
| 11 | `c_paymentterm` | x | x | - | - | - | x | - |
| 12 | `c_allocationline` | - | x | - | - | - | - | - |
| 13 | `c_bankaccount` | - | x | - | - | - | - | - |
| 14 | `c_bank` | - | x | - | - | - | - | - |
| 15 | `fact_acct` | - | x | x | - | - | - | - |
| 16 | `c_elementvalue` | - | x | x | - | - | - | - |
| 17 | `c_acctschema` | - | - | x | - | - | - | - |
| 18 | `c_period` | - | - | x | - | - | - | - |
| 19 | `hr_employee` | - | - | - | x | - | - | - |
| 20 | `hr_department` | - | - | - | x | - | - | - |
| 21 | `hr_job` | - | - | - | x | - | - | - |
| 22 | `hr_process` | - | - | - | x | - | - | - |
| 23 | `hr_movement` | - | - | - | x | - | - | - |
| 24 | `hr_concept` | - | - | - | x | - | - | - |
| 25 | `hr_payroll` | - | - | - | x | - | - | - |
| 26 | `lve_c_bpartner` | - | - | - | x | - | - | - |
| 27 | `ad_user` | - | - | - | x | - | - | - |
| 28 | `m_inout` | - | - | - | - | x | - | - |
| 29 | `m_inoutline` | - | - | - | - | x | - | - |
| 30 | `m_product` | - | - | - | - | x | x | x |
| 31 | `m_product_category` | - | - | - | - | - | x | - |
| 32 | `m_storageonhand` | - | - | - | - | x | x | - |
| 33 | `m_locator` | - | - | - | - | x | x | - |
| 34 | `m_warehouse` | - | - | - | - | x | x | - |
| 35 | `m_production` | - | - | - | - | x | - | - |
| 36 | `m_productionline` | - | - | - | - | x | - | - |
| 37 | `pp_product_bom` | - | - | - | - | x | - | - |
| 38 | `pp_product_bomline` | - | - | - | - | x | - | - |
| 39 | `m_movement` | - | - | - | - | x | - | - |
| 40 | `m_movementline` | - | - | - | - | x | - | - |
| 41 | `c_order` | - | - | - | - | - | x | x |
| 42 | `c_orderline` | - | - | - | - | - | x | x |
| 43 | `c_uom` | - | - | - | - | x | x | - |
| 44 | `c_location` | - | - | - | - | - | - | x |
| 45 | `c_city` | - | - | - | - | - | - | x |
| 46 | `c_region` | - | - | - | - | - | - | x |

---

## 3. Tablas Compartidas (usadas por multiples agentes)

### 3.1 `adempiere.ad_org` -- Organizaciones

Tabla central que define las empresas del grupo Santoni. Todos los agentes la usan para filtrar datos por organizacion.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `ad_org_id` | integer (PK) | ID de la organizacion |
| `name` | varchar | Nombre de la organizacion |
| `isactive` | char(1) | Activo: Y/N |

**Organizaciones conocidas:**

| Organizacion | Descripcion | Moneda USD (c_currency_id) |
|-------------|-------------|---------------------------|
| INPROA SANTONI | Empresa principal (procesadora de arroz) | DOL (1000000) |
| InproMaiz | Procesadora de maiz | DoL (1000011) |
| Santoni Service | Servicios | DLA (1000017) |
| AGROPECUARIA R.R. | Agropecuaria | dol (1000008) |
| AGA AGRICOLA | Agricola | Dla (1000013) |
| AGROINPROA | Agroindustrial | USA (1000003) |
| INVERSIONES AGA | Inversiones | Dol (1000006) |
| Agro Import | Importaciones | - |

**Patron de filtrado:**

```sql
-- Por lista de IDs (RBAC del usuario)
WHERE tabla.ad_org_id IN (:org_0, :org_1, ...)

-- Por nombre (busqueda desde agente)
WHERE tabla.ad_org_id IN (
  SELECT o.ad_org_id FROM adempiere.ad_org o
  WHERE o.name ILIKE :org_name_filter
)
```

---

### 3.2 `adempiere.c_bpartner` -- Socios de Negocio

Tabla maestra de todos los socios de negocio: clientes, proveedores, empleados y productores.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_bpartner_id` | integer (PK) | ID del socio de negocio |
| `name` | varchar | Nombre completo |
| `value` | varchar | Codigo del socio |
| `isactive` | char(1) | Activo: Y/N |
| `isvendor` | char(1) | Es proveedor: Y/N |
| `isemployee` | char(1) | Es empleado: Y/N |
| `isagricultor` | char(1) | Es productor agricola: Y/N (campo personalizado) |
| `ismayorista` | char(1) | Es mayorista: Y/N |
| `isclap` | char(1) | Es CLAP: Y/N |
| `ispublico` | char(1) | Es publico: Y/N |
| `codigoventas` | varchar | Codigo de ventas (personalizado) |
| `codigoproductor` | varchar | Codigo de productor (personalizado) |
| `codigocompras` | varchar | Codigo de compras (personalizado) |
| `c_bp_group_id` | integer (FK) | Grupo/tipologia del socio |
| `ad_org_id` | integer (FK) | Organizacion (puede ser wildcard '*') |

**Volumetria:** ~26,070 registros

**Roles del socio por agente:**

| Agente | Filtro | Uso |
|--------|--------|-----|
| Ventas | `c_bpartner_id` via `c_invoice.c_bpartner_id` | Clientes que compran |
| Ventas | `c_bpartner_id` via `c_invoice.salesrep_id` | Distribuidores/intermediarios |
| Finanzas | Via `c_invoice` y `c_payment` | Deudores y acreedores |
| RRHH | `isemployee = 'Y'` via `hr_employee.c_bpartner_id` | Empleados |
| Compras Insumos | `isvendor = 'Y'` via `c_invoice.c_bpartner_id` | Proveedores de insumos |
| Compras Productores | `isagricultor = 'Y'` via `c_order.c_bpartner_id` | Productores agricolas |
| Produccion | Via `m_inout.c_bpartner_id` | Socio en movimiento de inventario |

---

### 3.3 `adempiere.c_invoice` -- Facturas

Tabla central para facturas de venta y compra. Diferenciadas por `issotrx`.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_invoice_id` | integer (PK) | ID de factura |
| `ad_org_id` | integer (FK) | Organizacion |
| `c_bpartner_id` | integer (FK) | Socio de negocio (cliente/proveedor) |
| `salesrep_id` | integer (FK) | Distribuidor (apunta a `c_bpartner`) |
| `dateinvoiced` | date | Fecha de facturacion |
| `grandtotal` | numeric | Total con IVA |
| `totallines` | numeric | Total neto (sin IVA) |
| `docstatus` | char(2) | Estado: CO=Completado, VO=Anulado |
| `isactive` | char(1) | Activo: Y/N |
| `issotrx` | char(1) | Y=Venta, N=Compra |
| `ispaid` | char(1) | Pagada: Y/N |
| `c_doctypetarget_id` | integer (FK) | Tipo de documento |
| `c_currency_id` | integer (FK) | Moneda |
| `c_paymentterm_id` | integer (FK) | Terminos de pago |
| `documentno` | varchar | Numero de documento |
| `lve_controlnumber` | varchar | Numero de control fiscal (Venezuela) |
| `withholdingamt` | numeric | Monto de retenciones IVA |

**Volumetria:** ~447,386 facturas de venta (issotrx='Y')

**Uso por agente:**

| Agente | Filtro `issotrx` | Filtro adicional | Proposito |
|--------|-----------------|------------------|-----------|
| Ventas | `'Y'` | `docstatus='CO'`, `isactive='Y'` | Facturacion, ranking clientes |
| Finanzas | `'Y'` | `ispaid='N'` | Cuentas por cobrar |
| Finanzas | `'N'` | `ispaid='N'` | Cuentas por pagar |
| Compras Insumos | `'N'` | `docstatus='CO'` | Facturas de compra de insumos |
| Compras Productores | `'N'` | `ispaid='N'` | Pagos pendientes a productores |

---

### 3.4 `adempiere.m_product` -- Productos

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `m_product_id` | integer (PK) | ID del producto |
| `name` | varchar | Nombre del producto |
| `value` | varchar | Codigo del producto |
| `m_product_category_id` | integer (FK) | Categoria |
| `c_uom_id` | integer (FK) | Unidad de medida |
| `isactive` | char(1) | Activo: Y/N |

**Volumetria:** ~40,766 productos

**Usado por:** Produccion, Compras Insumos, Compras Productores

**Patron de busqueda por producto:**

```sql
-- Busqueda por codigo (ej: REP-LAMI-0037)
WHERE (p.name ILIKE :search OR p.value ILIKE :search)

-- Busqueda por texto (palabras multiples con de-pluralizacion)
WHERE (p.name ILIKE '%palabra1%' OR p.value ILIKE '%palabra1%')
  AND (p.name ILIKE '%palabra2%' OR p.value ILIKE '%palabra2%')
```

---

## 4. Detalle por Agente

### 4.1 VENTAS (Sales Agent)

**Archivo:** `backend/app/agents/ventas.py`
**Queries:** `backend/app/services/idempiere_queries.py` -- funciones `build_sales_summary`, `build_collection_summary`, `build_top_clients`, `build_overdue_receivables`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `c_invoice` | `i` | Facturas de venta (issotrx='Y') |
| `c_invoiceline` | `il` | Lineas de factura (para producto) |
| `c_payment` | `p` | Cobros recibidos (isreceipt='Y') |
| `c_bpartner` | `bp` | Clientes |
| `c_bpartner` | `sr` | Distribuidores (via `salesrep_id`) |
| `c_bpartner_location` | `bpl` | Direcciones de clientes |
| `c_salesregion` | `sreg` | Zonas/regiones de venta |
| `c_bp_group` | `bpg` | Tipologia del cliente |
| `c_doctype` | `dt` | Tipo de documento (ARI=factura, ARC=nota de credito) |
| `c_paymentterm` | `pterm` | Terminos de pago (para calcular vencimiento) |
| `c_allocationline` | `al` | Asignacion pago-factura (filtro por distribuidor en cobros) |
| `ad_org` | `o` | Organizaciones |

#### Relaciones (JOINs)

```
c_invoice (i)
  ├── JOIN c_bpartner (bp) ON i.c_bpartner_id = bp.c_bpartner_id
  ├── LEFT JOIN c_bpartner (sr) ON i.salesrep_id = sr.c_bpartner_id
  ├── JOIN c_doctype (dt) ON i.c_doctypetarget_id = dt.c_doctype_id
  ├── LEFT JOIN c_paymentterm (pterm) ON i.c_paymentterm_id = pterm.c_paymentterm_id
  └── LEFT JOIN [CTE client_zone] (cz) ON bp.c_bpartner_id = cz.c_bpartner_id
        └── CTE: c_bpartner_location (bpl)
              └── LEFT JOIN c_salesregion (sreg) ON bpl.c_salesregion_id = sreg.c_salesregion_id

c_payment (p)
  └── JOIN c_bpartner (bp) ON p.c_bpartner_id = bp.c_bpartner_id
```

#### CTE `client_zone`

Evita multiplicacion de filas cuando un cliente tiene multiples direcciones:

```sql
WITH client_zone AS (
  SELECT DISTINCT ON (bpl.c_bpartner_id)
    bpl.c_bpartner_id, sreg.name AS zona_name
  FROM adempiere.c_bpartner_location bpl
  LEFT JOIN adempiere.c_salesregion sreg
    ON bpl.c_salesregion_id = sreg.c_salesregion_id
  WHERE bpl.isactive = 'Y'
  ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
```

#### Notas de credito

Las facturas se separan por `c_doctype.docbasetype`:
- `ARI` = Factura de venta (Accounts Receivable Invoice)
- `ARC` = Nota de credito (Accounts Receivable Credit Memo)

El agente calcula **venta neta** = facturas (ARI) - notas de credito (ARC).

#### Regiones macro (mapeo en Python)

Las zonas de `c_salesregion` se agrupan en regiones via un CASE SQL generado por `_region_case_sql()`:

| Region | Zonas incluidas |
|--------|----------------|
| Llanos | Portuguesa, Barinas, Guanare, Cojedes, Apure |
| Centro-Occidente | Lara, Yaracuy, Falcon |
| Centro | Carabobo, Aragua, Valencia |
| Capital | Caracas, Miranda, Vargas, La Guaira |
| Occidente | Zulia, Maracaibo, Cabimas, Santa Barbara |
| Andes | Trujillo, Merida, Tachira, San Cristobal |
| Oriente | Margarita, Anzoategui, Sucre, Monagas |
| Guayana | Bolivar, Delta Amacuro, Amazonas |

#### Tipos de pago (tendertype en c_payment)

Verificado contra `ad_ref_list` (C_Payment Tender Type) en iDempiere el 14/Mar/2026:

| Codigo | Significado | Volumen 2025 |
|--------|-------------|-------------|
| `W` | Transferencia (Wire Transfer) | 42,770 recibos (81%) |
| `X` | Efectivo (Cash) | 5,195 recibos |
| `S` | Transferencia Empresas | 2,275 recibos |
| `T` | Cuenta (Account) | 1,101 recibos |
| `Y` | Dólar Efectivo | 1,057 recibos |
| `Z` | Dólar Transferencia | 434 recibos |
| `D` | Débito Directo (Direct Debit) | 73 recibos |
| `K` | Cheque (Check) | 3 recibos |
| `B` | Tarjeta de Débito | 2 recibos |
| `R` | Dólar IGTF | 1 recibo |
| `E` | Euro Efectivo | 1 recibo |
| `U` | Euro Transferencia | 1 recibo |
| `A` | Depósito Directo (Direct Deposit) | - |
| `C` | Tarjeta de Crédito (Credit Card) | - |
| `G` | Depósito Bancario | - |
| `I` | Débito Directo ITF | - |
| `J` | Comisión Bancaria | - |
| `P` | Impuesto | - |
| `Q` | Giro | - |

---

### 4.2 FINANZAS (Finance Agent)

**Archivo:** `backend/app/agents/finanzas.py`
**Queries:** `idempiere_queries.py` -- `build_financial_summary`, `build_cobros_pagos_summary`, `build_loan_balances`, `build_overdue_receivables`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `c_bankaccount` | `ba` | Cuentas bancarias (saldo actual) |
| `c_bank` | `b` | Bancos (nombre) |
| `c_currency` | `c` | Moneda de la cuenta (iso_code) |
| `c_invoice` | `i` | Facturas impagas (CxC y CxP) |
| `c_paymentterm` | `pt` | Terminos de pago (netdays para vencimiento) |
| `c_doctype` | `dt` | Tipo de documento (para excluir NC de CxC) |
| `c_bpartner` | `bp` | Socios (nombre del deudor/acreedor) |
| `ad_org` | `o` | Organizaciones |

#### Relaciones (JOINs)

```
c_bankaccount (ba)
  ├── JOIN c_bank (b) ON ba.c_bank_id = b.c_bank_id
  ├── LEFT JOIN c_currency (c) ON ba.c_currency_id = c.c_currency_id
  └── LEFT JOIN ad_org (o) ON ba.ad_org_id = o.ad_org_id

c_invoice (i) [CxC]
  ├── LEFT JOIN c_paymentterm (pt) ON i.c_paymentterm_id = pt.c_paymentterm_id
  └── JOIN c_bpartner (bp) ON i.c_bpartner_id = bp.c_bpartner_id
```

#### Columnas de `c_bankaccount`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_bankaccount_id` | integer (PK) | ID de cuenta |
| `c_bank_id` | integer (FK) | Banco |
| `accountno` | varchar | Numero de cuenta |
| `currentbalance` | numeric | Saldo actual |
| `c_currency_id` | integer (FK) | Moneda |
| `bankaccounttype` | char(1) | C=Corriente, S=Ahorro, I=Inversion |
| `isactive` | char(1) | Activo: Y/N |
| `ad_org_id` | integer (FK) | Organizacion |

#### Calculo de vencimiento

```sql
-- Fecha de vencimiento = fecha factura + dias de credito (default 30)
(i.dateinvoiced + CASE
  WHEN COALESCE(pt.netdays, 0) = 0 THEN 30
  ELSE pt.netdays
END)::date AS fecha_vencimiento
```

#### Funcion `build_cobros_pagos_summary` (Cobros y Pagos)

Consulta detallada de cobros (isreceipt='Y') o pagos (isreceipt='N') con desglose.

| Tabla | Alias | Rol |
|-------|-------|-----|
| `c_payment` | `p` | Registros de cobros/pagos |
| `c_bpartner` | `bp` | Socios de negocio |

**Retorna:** total_registros, por_moneda, por_metodo_pago, top_socios (top 30), por_mes (si consulta anual o >45 dias).

#### Funcion `build_loan_balances` (Prestamos y Pagares)

Consulta saldos de cuentas de prestamos/pagares via asientos contables.

| Tabla | Alias | Rol |
|-------|-------|-----|
| `fact_acct` | `fa` | Asientos contables |
| `c_elementvalue` | `ev` | Cuentas contables de prestamos |

**Cuentas predefinidas:** 2.01.01.01, 2.01.04.01, 2.02.01.01, 2.02.02.01, 2.02.03.01
**Convencion:** Saldo = haber - debe (cuentas de pasivo, naturaleza credito)
**Retorna:** lista de cuentas con {codigo, cuenta, saldo, movimientos, primer_mov, ultimo_mov}, total_obligaciones.

#### Separacion de datos por moneda

Los saldos bancarios y CxC/CxP se presentan **separados por moneda** (VES y USD). Nunca se suman montos de diferentes monedas.

---

### 4.3 CONTABILIDAD (Accounting Agent)

**Archivo:** `backend/app/agents/contabilidad.py`
**Queries:** `idempiere_queries.py` -- `build_accounting_summary`, `build_account_detail`, `search_accounts_by_name`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `fact_acct` | `fa` | Asientos contables (~7.7M registros) |
| `c_elementvalue` | `ev` | Plan de cuentas (codigo, nombre, tipo) |
| `c_acctschema` | - | Esquema contable (referencia) |
| `c_period` | - | Periodos contables (referencia) |

#### Columnas de `fact_acct`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `fact_acct_id` | integer (PK) | ID del asiento |
| `ad_org_id` | integer (FK) | Organizacion |
| `account_id` | integer (FK) | Cuenta contable (→ `c_elementvalue`) |
| `dateacct` | date | Fecha contable |
| `amtacctdr` | numeric | Monto al debe |
| `amtacctcr` | numeric | Monto al haber |
| `c_acctschema_id` | integer (FK) | Esquema contable |
| `isactive` | char(1) | Activo: Y/N |

#### Columnas de `c_elementvalue`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_elementvalue_id` | integer (PK) | ID de la cuenta |
| `value` | varchar | Codigo de cuenta (ej: `2.01.01.10`) |
| `name` | varchar | Nombre de la cuenta |
| `accounttype` | char(1) | Tipo de cuenta |
| `isactive` | char(1) | Activo: Y/N |

#### Tipos de cuenta (`accounttype`)

| Codigo | Tipo | Cantidad | Naturaleza del saldo |
|--------|------|----------|---------------------|
| `A` | Activo | 1,054 cuentas | Debito (saldo = debe - haber) |
| `L` | Pasivo | 494 cuentas | Credito (saldo = haber - debe) |
| `O` | Patrimonio | 116 cuentas | Credito (saldo = haber - debe) |
| `R` | Ingreso | 266 cuentas | Credito (saldo = haber - debe) |
| `E` | Gasto | 1,626 cuentas | Debito (saldo = debe - haber) |
| `M` | Memorandum | - | Informativo |

#### Convencion de signos

```sql
-- Cuentas de naturaleza DEBITO (A, E):
saldo = SUM(fa.amtacctdr - fa.amtacctcr)

-- Cuentas de naturaleza CREDITO (L, O, R):
saldo = SUM(fa.amtacctcr - fa.amtacctdr)
```

#### Busqueda de cuentas por nombre (`search_accounts_by_name`)

Cuando el usuario menciona una cuenta por nombre (ej: "caja chica", "bancos") sin codigo:

```sql
SELECT ev.value AS codigo, ev.name AS cuenta, ev.accounttype AS tipo
FROM adempiere.c_elementvalue ev
WHERE ev.isactive = 'Y' AND ev.issummary = 'N'
  AND (ev.name ILIKE '%caja%' AND ev.name ILIKE '%chica%')
ORDER BY ev.value
LIMIT 10
```

Si retorna multiples resultados, se muestra lista para que el usuario seleccione.

#### Detalle de cuenta especifica

Cuando el usuario consulta una cuenta por codigo (ej: `2.01.01.10`):
1. Se busca la cuenta en `c_elementvalue` por `value = :code`
2. Se calcula el saldo inicial (movimientos anteriores al periodo)
3. Se suman movimientos del periodo (debe, haber)
4. Se calcula el saldo final = saldo inicial + movimientos del periodo
5. Si `movimientos = 0`, se genera mensaje explicito (la cuenta existe pero no tuvo movimientos)

---

### 4.4 RRHH (Human Resources Agent)

**Archivo:** `backend/app/agents/rrhh.py`
**Queries:** `idempiere_queries.py` -- `build_employee_summary`, `build_employee_list`, `build_birthday_list`, `build_payroll_summary`, `build_attendance_summary`, `build_turnover_summary`, `build_vacation_summary`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `hr_employee` | `e` | Registros de empleados |
| `hr_department` | `d` | Departamentos |
| `hr_job` | `j` | Cargos/puestos |
| `hr_process` | `hp` | Procesos de nomina |
| `hr_movement` | `hm` | Movimientos de nomina (conceptos aplicados) |
| `hr_concept` | `hc` | Conceptos de nomina (salario, bonos, deducciones) |
| `hr_payroll` | `hpy` | Definiciones de nomina |
| `c_bpartner` | `bp` | Datos maestros del empleado |
| `lve_c_bpartner` | `lbp` | Extension venezolana (posible campo de cumpleanos) |
| `ad_user` | `u` | Usuarios del sistema (campo birthday para cumpleanos) |
| `ad_org` | `o` | Organizacion del empleado |

#### Relaciones (JOINs)

```
hr_employee (e)
  ├── JOIN c_bpartner (bp) ON e.c_bpartner_id = bp.c_bpartner_id
  ├── LEFT JOIN ad_org (o) ON e.ad_org_id = o.ad_org_id
  ├── LEFT JOIN hr_department (d) ON e.hr_department_id = d.hr_department_id
  └── LEFT JOIN hr_job (j) ON e.hr_job_id = j.hr_job_id

hr_process (hp)
  ├── LEFT JOIN hr_payroll (hpy) ON hp.hr_payroll_id = hpy.hr_payroll_id
  └── LEFT JOIN hr_movement (hm) ON hp.hr_process_id = hm.hr_process_id
        └── JOIN hr_concept (hc) ON hm.hr_concept_id = hc.hr_concept_id
```

#### Columnas de `hr_employee`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `hr_employee_id` | integer (PK) | ID del registro |
| `c_bpartner_id` | integer (FK) | Socio de negocio (empleado) |
| `hr_department_id` | integer (FK) | Departamento |
| `hr_job_id` | integer (FK) | Cargo/puesto |
| `startdate` | date | Fecha de ingreso |
| `enddate` | date | Fecha de egreso (NULL si activo) |
| `isactive` | char(1) | Activo: Y/N |
| `ad_org_id` | integer (FK) | Organizacion |

**NOTA IMPORTANTE:** `hr_employee` tiene **multiples registros por persona** (uno por periodo de nomina). Todas las queries usan `COUNT(DISTINCT e.c_bpartner_id)` y `DISTINCT ON (bp.c_bpartner_id)` para obtener conteos correctos.

#### Columnas de `hr_movement`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `hr_movement_id` | integer (PK) | ID del movimiento |
| `hr_process_id` | integer (FK) | Proceso de nomina |
| `c_bpartner_id` | integer (FK) | Empleado |
| `hr_concept_id` | integer (FK) | Concepto de nomina |
| `amount` | numeric | Monto (positivo=devengado, negativo=deduccion) |
| `qty` | numeric | Cantidad (siempre 0 para ausentismo en Santoni) |

#### Distribucion de empleados activos (referencia)

| Organizacion | Empleados activos |
|-------------|-------------------|
| INPROA SANTONI | ~444 |
| InproMaiz | ~206 |
| Santoni Service | ~134 |
| AGROPECUARIA R.R. | ~124 |
| AGA AGRICOLA | ~91 |
| AGROINPROA | ~38 |
| INVERSIONES AGA | ~4 |

#### Deteccion de cumpleanos

La funcion `_find_birthday_column` busca automaticamente la columna de fecha de nacimiento:
1. Busca en `c_bpartner` columnas con nombre `birthday`, `birthdate`, `fecha_nacimiento`
2. Si no encuentra, busca en `lve_c_bpartner` (extension venezolana) las mismas columnas mas `fecha_nac`, `nacimiento`
3. El resultado se cachea para el proceso

#### Conceptos de ausentismo buscados

```sql
LOWER(hc.name) LIKE '%ausent%'
  OR LOWER(hc.name) LIKE '%ausencia%'
  OR LOWER(hc.name) LIKE '%inasist%'
  OR LOWER(hc.name) LIKE '%falta%'
  OR LOWER(hc.name) LIKE '%permiso%'
  OR LOWER(hc.name) LIKE '%reposo%'
  OR LOWER(hc.name) LIKE '%incapacidad%'
  OR LOWER(hc.name) LIKE '%licencia%'
```

#### Conceptos de vacaciones buscados (`build_vacation_summary`)

```sql
LOWER(hc.name) LIKE '%vacacion%'
  OR LOWER(hc.name) LIKE '%bono vacacional%'
```

**Retorna:** total_empleados, total_monto, total_ocurrencias, por_concepto, por_organizacion, detalle_empleados (top 30).

#### Cumpleanos (`build_birthday_list`)

Usa LATERAL subquery para seleccionar UNA fecha de cumpleanos por empleado, evitando duplicados cuando hay multiples registros en `ad_user`:

```sql
LATERAL (
  SELECT u.birthday FROM adempiere.ad_user u
  WHERE u.c_bpartner_id = bp.c_bpartner_id AND u.birthday IS NOT NULL
  ORDER BY u.ad_user_id LIMIT 1
) bday
```

---

### 4.5 PRODUCCION (Production Agent)

**Archivo:** `backend/app/agents/produccion.py`
**Queries:** `idempiere_queries.py` -- `build_production_summary`, `build_production_orders`, `build_production_runs`, `build_bom_info`, `build_warehouse_movements`, `build_inventory_stock`

> **NOTA:** Santoni NO utiliza el modulo de Manufactura (`pp_order`) de iDempiere. La actividad productiva se rastrea mediante movimientos de inventario (`m_inout`) como fuente primaria, y `m_production` como fuente secundaria (~32 registros BATCH SIROPE). Las recetas/BOM se consultan desde `pp_product_bom`.

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `m_inout` | `io` | Movimientos de inventario (262,794 documentos) |
| `m_inoutline` | `iol` | Lineas de movimiento (producto, cantidad) |
| `m_product` | `p` | Productos |
| `m_warehouse` | `w` | Almacenes |
| `m_storageonhand` | `s` | Stock actual en almacenes |
| `m_locator` | `l` | Ubicaciones de almacen |
| `m_production` | `mp` | Producciones simplificadas (~32 BATCH SIROPE) |
| `m_productionline` | `mpl` | Lineas de produccion (terminado/insumos) |
| `pp_product_bom` | `bom` | Listas de materiales / recetas |
| `pp_product_bomline` | `bl` | Componentes de BOM |
| `m_movement` | `mv` | Movimientos internos entre almacenes |
| `m_movementline` | `mvl` | Lineas de movimiento interno |
| `c_uom` | `u` | Unidades de medida |
| `c_bpartner` | `bp` | Socio de negocio del movimiento |
| `ad_org` | `org` | Organizaciones |

#### Relaciones (JOINs)

```
m_inout (io)
  ├── JOIN m_inoutline (iol) ON io.m_inout_id = iol.m_inout_id
  │     └── JOIN m_product (p) ON iol.m_product_id = p.m_product_id
  ├── JOIN ad_org (org) ON io.ad_org_id = org.ad_org_id
  └── LEFT JOIN c_bpartner (bp) ON io.c_bpartner_id = bp.c_bpartner_id

m_storageonhand (s)
  ├── JOIN m_locator (l) ON s.m_locator_id = l.m_locator_id
  │     └── JOIN m_warehouse (w) ON l.m_warehouse_id = w.m_warehouse_id
  │           └── JOIN ad_org (o) ON w.ad_org_id = o.ad_org_id
  └── JOIN m_product (p) ON s.m_product_id = p.m_product_id
```

#### Columnas de `m_inout`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `m_inout_id` | integer (PK) | ID del movimiento |
| `ad_org_id` | integer (FK) | Organizacion |
| `c_bpartner_id` | integer (FK) | Socio de negocio |
| `documentno` | varchar | Numero de documento |
| `movementdate` | date | Fecha del movimiento |
| `movementtype` | char(2) | Tipo de movimiento |
| `docstatus` | char(2) | Estado del documento |
| `isactive` | char(1) | Activo: Y/N |

#### Tipos de movimiento (`movementtype`)

| Codigo | Significado | Descripcion operativa |
|--------|-------------|----------------------|
| `V+` | Vendor Receipt | Recepcion de materia prima (arroz paddy, maiz, insumos) |
| `C-` | Customer Shipment | Despacho de producto terminado (arroz, harina) |
| `M+` | Movement To | Movimiento interno - entrada |
| `M-` | Movement From | Movimiento interno - salida |
| `P+` | Production Plus | Recepcion de produccion (poco usado) |
| `P-` | Production Minus | Consumo de produccion (poco usado) |

#### Columnas de `m_storageonhand`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `m_product_id` | integer (FK) | Producto |
| `qtyonhand` | numeric | Cantidad disponible |
| `m_locator_id` | integer (FK) | Ubicacion en almacen |
| `m_attributesetinstance_id` | integer (FK) | Lote/batch (genera multiples filas por producto) |
| `isactive` | char(1) | Activo: Y/N |

**NOTA:** `m_storageonhand` tiene multiples filas por producto (una por lote). Las queries agregan con `SUM(s.qtyonhand)` agrupando por producto.

#### Funcion `build_production_runs` (Producciones Directas)

Consulta la tabla `m_production` (produccion simplificada, no manufactura `pp_order`).

```
m_production (mp)
  └── JOIN m_productionline (mpl) ON mp.m_production_id = mpl.m_production_id
        └── JOIN m_product (p) ON mpl.m_product_id = p.m_product_id
```

| Columna de `m_productionline` | Descripcion |
|-------------------------------|-------------|
| `isendproduct` | 'Y'=Producto terminado, 'N'=Insumo consumido |
| `movementqty` | Cantidad (positivo=producido, negativo=consumido) |

**Nota:** Siempre usa `IdempiereSession()` directo — la DB local solo tiene ~32 registros vs 5,919+ en iDempiere.

#### Funcion `build_bom_info` (Recetas / Listas de Materiales)

```
pp_product_bom (bom)
  ├── JOIN m_product (p) ON bom.m_product_id = p.m_product_id
  ├── LEFT JOIN ad_org (o) ON bom.ad_org_id = o.ad_org_id
  └── JOIN pp_product_bomline (bl) ON bom.pp_product_bom_id = bl.pp_product_bom_id
        ├── JOIN m_product (cp) ON bl.m_product_id = cp.m_product_id
        └── LEFT JOIN c_uom (u) ON bl.c_uom_id = u.c_uom_id
```

**Retorna:** Lista de BOMs con componentes (componente, cantidad, unidad, tipo).
**Nota:** Siempre usa `IdempiereSession()` (datos de referencia, no temporales).

#### Funcion `build_warehouse_movements` (Movimientos Internos)

```
m_movement (mv)
  ├── JOIN m_movementline (mvl) ON mv.m_movement_id = mvl.m_movement_id
  │     ├── JOIN m_product (p) ON mvl.m_product_id = p.m_product_id
  │     ├── JOIN m_locator (lf) ON mvl.m_locator_id = lf.m_locator_id [origen]
  │     │     └── JOIN m_warehouse (wf) ON lf.m_warehouse_id = wf.m_warehouse_id
  │     └── JOIN m_locator (lt) ON mvl.m_locatorto_id = lt.m_locator_id [destino]
  │           └── JOIN m_warehouse (wt) ON lt.m_warehouse_id = wt.m_warehouse_id
  └── LEFT JOIN ad_org (o) ON mv.ad_org_id = o.ad_org_id
```

**Retorna:** total_movimientos, por_producto (top 20), flujo_almacenes (origen→destino top 15), documentos_recientes.
**Nota:** Siempre usa `IdempiereSession()` (6,014+ movimientos; DB local incompleta).

---

### 4.6 COMPRAS INSUMOS (Supply Purchases Agent)

**Archivo:** `backend/app/agents/compras_insumos.py`
**Queries:** `idempiere_queries.py` -- `build_supply_purchases`, `build_product_purchase_history`, `build_inventory_stock`, `build_pending_purchase_orders`, `build_supplier_price_comparison`, `build_purchase_payment_status`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `c_invoice` | `i` | Facturas de compra (issotrx='N') |
| `c_invoiceline` | `il` | Lineas de factura (producto, cantidad, precio) |
| `c_bpartner` | `bp` | Proveedores |
| `m_product` | `p` | Productos/insumos |
| `m_product_category` | `pc` | Categorias de productos |
| `m_storageonhand` | `s` | Stock actual |
| `m_locator` | `l` | Ubicaciones de almacen |
| `m_warehouse` | `w` | Almacenes |
| `c_order` | `o` | Ordenes de compra (issotrx='N', para pendientes) |
| `c_orderline` | `ol` | Lineas de orden de compra |
| `c_paymentterm` | `pt` | Terminos de pago (para vencimiento) |
| `c_uom` | `u` | Unidades de medida |
| `ad_org` | `o` | Organizaciones |

#### Relaciones (JOINs)

```
c_invoice (i) [issotrx='N']
  ├── JOIN c_invoiceline (il) ON i.c_invoice_id = il.c_invoice_id
  │     └── JOIN m_product (p) ON il.m_product_id = p.m_product_id
  ├── JOIN c_bpartner (bp) ON i.c_bpartner_id = bp.c_bpartner_id
  └── LEFT JOIN c_paymentterm (pt) ON i.c_paymentterm_id = pt.c_paymentterm_id

c_order (o) [issotrx='N', para ordenes pendientes]
  ├── JOIN c_orderline (ol) ON o.c_order_id = ol.c_order_id
  ├── JOIN c_bpartner (bp) ON o.c_bpartner_id = bp.c_bpartner_id
  └── LEFT JOIN ad_org (org) ON o.ad_org_id = org.ad_org_id

m_storageonhand (s)
  ├── JOIN m_locator (l) ON s.m_locator_id = l.m_locator_id
  │     └── JOIN m_warehouse (w) ON l.m_warehouse_id = w.m_warehouse_id
  │           └── JOIN ad_org (o) ON w.ad_org_id = o.ad_org_id
  ├── JOIN m_product (p) ON s.m_product_id = p.m_product_id
  │     └── LEFT JOIN m_product_category (pc) ON p.m_product_category_id = pc.m_product_category_id
  └── LEFT JOIN c_uom (u) ON p.c_uom_id = u.c_uom_id
```

#### Columnas de `c_invoiceline`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_invoiceline_id` | integer (PK) | ID de linea |
| `c_invoice_id` | integer (FK) | Factura |
| `m_product_id` | integer (FK) | Producto |
| `qtyinvoiced` | numeric | Cantidad facturada |
| `linenetamt` | numeric | Monto neto de la linea |
| `priceactual` | numeric | Precio unitario |

#### Funcion `build_pending_purchase_orders` (Ordenes Pendientes)

Consulta ordenes de compra con `docstatus IN ('DR','IP')` solamente (excluye CO=completadas).

```sql
-- DR = Borrador (Draft), IP = En Proceso (In Progress)
-- CO = Completada (EXCLUIDA — no es pendiente)
WHERE o.docstatus IN ('DR', 'IP') AND o.issotrx = 'N'
```

**Retorna:** total_ordenes, total_monto_mixto, por_moneda, por_estado, por_proveedor (top 20), detalle_ordenes (ultimas 30).

#### Funcion `build_supplier_price_comparison` (Comparacion de Precios)

Compara precios de un producto entre proveedores basado en facturas reales.

```sql
SELECT bp.name AS proveedor, p.name AS producto,
  _currency_label('i') AS moneda,
  COUNT(*) AS compras,
  MIN(il.priceactual), AVG(il.priceactual), MAX(il.priceactual),
  MAX(i.dateinvoiced) AS ultima_compra,
  SUM(il.qtyinvoiced) AS cantidad_total
FROM c_invoice i JOIN c_invoiceline il ...
WHERE i.issotrx = 'N' AND product_search_filter
GROUP BY proveedor, producto, moneda
```

**Retorna:** Lista de proveedores con precio_minimo, precio_promedio, precio_maximo, ultima_compra (limit 30).

#### Funcion `build_purchase_payment_status` (Estado de Pago)

Clasifica facturas de compra en Pagadas vs Pendientes, con detalle de vencidas.

**Retorna:** resumen_pago (estado_pago, moneda, facturas, total), facturas_vencidas (top 20 mas antiguas).

---

### 4.7 COMPRAS PRODUCTORES (Producer Purchases Agent)

**Archivo:** `backend/app/agents/compras_productores.py`
**Queries:** `idempiere_queries.py` -- `build_producer_purchases`, `build_registered_producers`, `build_producer_pending_payments`, `build_producer_price_analysis`

#### Tablas utilizadas

| Tabla | Alias | Rol en las queries |
|-------|-------|--------------------|
| `c_order` | `o` | Ordenes de compra a productores (277,538 ordenes) |
| `c_orderline` | `ol` | Lineas de orden (producto, cantidad, precio) |
| `c_bpartner` | `bp` | Productores (isagricultor='Y') |
| `c_bpartner_location` | `bpl` | Ubicacion del productor |
| `c_location` | `loc` | Coordenadas/direccion |
| `c_city` | `ci` | Ciudad/municipio |
| `c_region` | `r` | Estado/region |
| `m_product` | `p` | Productos agricolas (arroz paddy, maiz) |
| `c_invoice` | `i` | Facturas impagas (para pagos pendientes) |
| `c_invoiceline` | `il` | Lineas de factura (filtro por producto en pendientes) |
| `ad_org` | `o` | Organizaciones |

#### Relaciones (JOINs)

```
c_order (o) [issotrx='N']
  ├── JOIN c_orderline (ol) ON o.c_order_id = ol.c_order_id
  │     └── JOIN m_product (p) ON ol.m_product_id = p.m_product_id
  └── JOIN c_bpartner (bp) ON o.c_bpartner_id = bp.c_bpartner_id
        └── LEFT JOIN c_bpartner_location (bpl) ON bp.c_bpartner_id = bpl.c_bpartner_id

-- Pagos pendientes usa c_invoice en lugar de c_order
c_invoice (i) [issotrx='N', ispaid='N']
  └── JOIN c_bpartner (bp) ON i.c_bpartner_id = bp.c_bpartner_id
```

#### Columnas de `c_order`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_order_id` | integer (PK) | ID de orden |
| `ad_org_id` | integer (FK) | Organizacion |
| `c_bpartner_id` | integer (FK) | Productor |
| `dateordered` | date | Fecha de la orden |
| `grandtotal` | numeric | Total de la orden |
| `docstatus` | char(2) | Estado: CO=Completado |
| `issotrx` | char(1) | N=Compra |
| `isactive` | char(1) | Activo: Y/N |

#### Campos especificos de guias agricolas en `c_order` (personalizados)

| Columna | Tipo | Descripcion | Estado |
|---------|------|-------------|--------|
| `driver` | varchar | Nombre del chofer | Disponible |
| `plateno` | varchar | Placa del vehiculo | Disponible |
| `grossweight` | numeric | Peso bruto | Disponible (sin uso activo) |
| `tareweight` | numeric | Peso tara | Disponible (sin uso activo) |
| `netweight` | numeric | Peso neto | Disponible (sin uso activo) |
| `classification` | varchar | Clasificacion del grano | Disponible (sin uso activo) |
| `tipofrijol` | varchar | Tipo de frijol | Disponible (sin uso activo) |
| `guidemac` | varchar | Guia MAC | Disponible (sin uso activo) |
| `guideproducer` | varchar | Guia del productor | Disponible (sin uso activo) |
| `guidesada` | varchar | Guia SADA | Disponible (sin uso activo) |

> **Nota:** Los campos de peso, clasificacion y guias existen en la tabla pero actualmente reportan valores en 0.0 o vacios. No se consultan activamente.

#### Columnas de `c_orderline`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `c_orderline_id` | integer (PK) | ID de linea |
| `c_order_id` | integer (FK) | Orden |
| `m_product_id` | integer (FK) | Producto |
| `qtyordered` | numeric | Cantidad ordenada (kg) |
| `priceactual` | numeric | Precio unitario (Bs./kg) |
| `linenetamt` | numeric | Monto neto de la linea |

---

## 5. Mapeo de Monedas (c_currency_id)

Santoni utiliza **multiples entradas de moneda** para USD, una por organizacion. Esto es una particularidad de su configuracion de iDempiere.

### Bolivares (VES)

| c_currency_id | iso_code | Organizacion | Descripcion |
|---------------|----------|-------------|-------------|
| 205 | VES | Todas | Bolivar Soberano |

### Dolares (USD)

| c_currency_id | iso_code | Organizacion | Descripcion |
|---------------|----------|-------------|-------------|
| 1000000 | DOL | INPROA SANTONI | Dolar |
| 1000003 | USA | AGROINPROA | Dolar |
| 1000006 | Dol | INVERSIONES AGA | Dolar |
| 1000008 | dol | AGROPECUARIA R.R. | Dolar |
| 1000011 | DoL | InproMaiz | Dolar |
| 1000013 | Dla | AGA AGRICOLA | Dolar |
| 1000017 | DLA | Santoni Service | Dolar |

### Otros IDs USD detectados en queries

| c_currency_id | Contexto |
|---------------|----------|
| 100 | Mencionado en system prompts de Finanzas y Contabilidad (posiblemente legacy) |
| 1000009 | Incluido en `_currency_label()` pero sin organizacion documentada |

### Expresion SQL para etiqueta de moneda

```sql
CASE
  WHEN i.c_currency_id = 205 THEN 'Bs.'
  WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
  ELSE 'Otro'
END
```

### Filtrado por moneda

```sql
-- Filtrar por VES
WHERE i.c_currency_id IN (205)

-- Filtrar por USD (todas las variantes)
WHERE i.c_currency_id IN (1000000, 1000003, 1000006, 1000008, 1000011, 1000013, 1000017)
```

---

## 6. Patrones de Consulta (Query Patterns)

### 6.1 Filtro por organizacion

Dos mecanismos, usados segun el contexto:

```sql
-- Mecanismo 1: Por lista de IDs (viene del RBAC del usuario)
_add_org_filter(conditions, params, org_ids, "i")
-- Genera: i.ad_org_id IN (:org_0, :org_1, ...)

-- Mecanismo 2: Por nombre (usuario menciona "inpromaiz" en el chat)
_add_org_name_filter(conditions, params, org_name, "i")
-- Genera: i.ad_org_id IN (SELECT o.ad_org_id FROM adempiere.ad_org o WHERE o.name ILIKE '%inpromaiz%')
```

### 6.2 Filtro por fecha

Se admiten dos formatos, con prioridad al rango explicito:

```sql
-- Rango de fechas (prioridad)
WHERE i.dateinvoiced >= :date_from AND i.dateinvoiced <= :date_to

-- Mes y/o ano
WHERE EXTRACT(YEAR FROM i.dateinvoiced) = :anio
  AND EXTRACT(MONTH FROM i.dateinvoiced) = :mes
```

Formatos soportados desde el chat:
- `01/01/2026 al 31/01/2026` (rango con separadores)
- `01012026 al 31012026` (rango compacto)
- `enero 2026` (mes y ano)
- `2026` (solo ano)

### 6.3 Filtro por moneda

```sql
-- Soporta multiples IDs para USD
WHERE i.c_currency_id IN (:cur_0, :cur_1, ...)
```

### 6.4 Filtro por distribuidor (Ventas)

```sql
-- salesrep_id apunta a c_bpartner (distribuidor, NO vendedor interno)
WHERE sr.name ILIKE :vendedor

-- Para cobros, filtro indirecto via c_allocationline
WHERE EXISTS (
  SELECT 1 FROM adempiere.c_allocationline al
  JOIN adempiere.c_invoice inv ON al.c_invoice_id = inv.c_invoice_id
  WHERE al.c_payment_id = p.c_payment_id AND inv.salesrep_id = :salesrep_id
)
```

### 6.5 Busqueda de productos (Compras Insumos)

```sql
-- Por codigo de producto (ej: REP-LAMI-0037)
WHERE (p.name ILIKE '%REP-LAMI-0037%' OR p.value ILIKE '%REP-LAMI-0037%')

-- Por texto libre (con de-pluralizacion basica en español)
-- "cajas de laminas" → busca "%caja%" AND "%lamina%"
WHERE (p.name ILIKE '%caja%' OR p.value ILIKE '%caja%')
  AND (p.name ILIKE '%lamina%' OR p.value ILIKE '%lamina%')
```

### 6.6 Busqueda por cargo (RRHH)

```sql
-- "obreros integrales" → busca stems en hr_job.name
WHERE j.name ILIKE '%obrero%' AND j.name ILIKE '%integral%'
```

### 6.7 Herencia de contexto temporal (Follow-ups)

Todos los agentes implementan el patron de herencia temporal: si el mensaje actual no contiene periodo, se busca en el historial reciente:

```python
if not date_from and not date_to and not mes and history:
    for role, content in reversed(history):
        if role != "user": continue
        df, dt = extract_date_range(content)
        if df and dt:
            date_from, date_to = df, dt
            break
        m, a = extract_month_year(content)
        if m:
            mes, anio = m, a
            break
```

---

## 7. Problemas de Calidad de Datos Conocidos

| Problema | Tabla | Impacto | Workaround |
|----------|-------|---------|------------|
| Multiples registros por empleado | `hr_employee` | Conteos inflados | `COUNT(DISTINCT e.c_bpartner_id)`, `DISTINCT ON` |
| Multiples direcciones por cliente | `c_bpartner_location` | JOIN multiplication | CTE `client_zone` con `DISTINCT ON` |
| Multiples IDs de moneda para USD | `c_currency` | Montos mezclados | `c_currency_id IN (lista completa)` |
| `hr_movement.qty` siempre 0 para ausencias | `hr_movement` | Sin datos de horas | Usar `COUNT(*)` para ocurrencias, `amount` para monto |
| Peso bruto/neto/tara en 0 | `c_order` (campos personalizados) | Sin datos de peso de guias | No se consultan actualmente |
| Humedad e impureza en 0 | `c_order` (campos personalizados) | Sin datos de calidad de grano | No se consultan actualmente |
| `ad_org_id` de `c_bpartner` apunta a org wildcard '*' | `c_bpartner` | Org incorrecta para empleados | Usar `hr_employee.ad_org_id` en su lugar |
| Ubicacion de productores incompleta | `c_bpartner_location` (c_city_id, c_region_id) | Sin estado/municipio | Se retorna string vacio |
| Saldos residuales en facturas antiguas | `c_invoice` (ispaid='N') | CxC/CxP infladas | Filtro `dateinvoiced >= CURRENT_DATE - INTERVAL '3 years'` y `grandtotal > 100` |

---

## 8. Tablas NO Utilizadas (Disponibles para Futuras Consultas)

Las siguientes tablas existen en iDempiere pero **no son consultadas actualmente** por ningun agente:

| Tabla | Descripcion | Potencial uso futuro |
|-------|-------------|---------------------|
| `pp_order` | Ordenes de produccion (manufactura) | **Vacio en Santoni** - modulo no activado |
| `pp_order_bomline` | Lineas de ordenes de manufactura | Vacio (depende de pp_order) |
| `c_order` (issotrx='Y') | Pedidos de venta (antes de facturar) | Ventas: cotizaciones y pedidos en proceso |
| `m_inventory` | Inventario fisico / conteo | Produccion: ajustes de inventario |
| `c_projectline` | Lineas de proyecto | Produccion: seguimiento de proyectos |
| `c_tax` | Impuestos (IVA, retenciones) | Contabilidad: reportes fiscales |
| `c_taxcategory` | Categorias de impuestos | Contabilidad: analisis fiscal |
| `c_conversionrate` | Tasas de cambio | Finanzas: conversion VES/USD |
| `c_bankstatement` | Conciliaciones bancarias | Finanzas: conciliacion automatizada |
| `c_bankstatementline` | Lineas de conciliacion | Finanzas: detalle de conciliacion |
| `c_dunning` | Gestion de cobranza | Ventas: cartas de cobro automaticas |
| `c_campaign` | Campanas comerciales | Ventas: analisis por campana |
| `hr_attendance` | Asistencia de empleados | RRHH: control de horarios (si se activa) |
| `hr_leave` | Solicitudes de vacaciones | RRHH: gestion de ausencias |
| `ad_changelog` | Log de cambios | Admin: trazabilidad de modificaciones |
| `c_subscription` | Suscripciones | Ventas: clientes recurrentes |
| `a_asset` | Activos fijos | Contabilidad: gestion de activos |
| `gl_journal` | Asientos manuales | Contabilidad: ajustes contables |
| `gl_journalline` | Lineas de asientos manuales | Contabilidad: detalle de ajustes |

> **Tablas movidas a "en uso" desde la ultima revision:** `m_production`, `m_movement`, `pp_product_bom`, `pp_product_bomline`, `ad_user` (para cumpleanos en RRHH)

---

## 9. Volumetria de Referencia

Datos aproximados del ambiente de produccion (Marzo 2026):

| Tabla | Registros | Notas |
|-------|-----------|-------|
| `c_invoice` (ventas) | ~447,386 | issotrx='Y' |
| `c_payment` | ~798,150 | isreceipt='Y' |
| `c_bpartner` | ~26,070 | Todos los tipos |
| `m_product` | ~40,766 | Todos los productos |
| `m_inout` | ~262,794 | Documentos de movimiento |
| `c_order` (compras productores) | ~277,538 | issotrx='N' |
| `fact_acct` | ~7,700,000 | Asientos contables |
| `c_elementvalue` | ~3,556 | Plan de cuentas |
| `hr_employee` | Variable | Multiples filas por persona |
| `m_production` | ~5,919 | Producciones simplificadas (en iDempiere) |
| `m_movement` | ~6,014 | Movimientos internos entre almacenes |
| `pp_product_bom` | ~15+ | Recetas / listas de materiales |

---

## 10. Archivo de Referencia de Codigo

| Archivo | Contenido |
|---------|-----------|
| `backend/app/services/idempiere_queries.py` | Todas las queries SQL contra iDempiere |
| `backend/app/services/query_service.py` | Router demo/produccion + funciones wrapper |
| `backend/app/agents/ventas.py` | Agente de Ventas |
| `backend/app/agents/finanzas.py` | Agente de Finanzas |
| `backend/app/agents/contabilidad.py` | Agente de Contabilidad |
| `backend/app/agents/rrhh.py` | Agente de RRHH |
| `backend/app/agents/produccion.py` | Agente de Produccion |
| `backend/app/agents/compras_insumos.py` | Agente de Compras Insumos |
| `backend/app/agents/compras_productores.py` | Agente de Compras Productores |
| `backend/app/agents/base_agent.py` | Clase base de agentes |
| `backend/app/agents/date_utils.py` | Parsing de fechas en espanol |
| `backend/app/database.py` | Conexion dual (interna + iDempiere) |
