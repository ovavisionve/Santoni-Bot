# Resultados Verificación Ventas - 14/Mar/2026

Script: `verificacion_ventas_2025.sql`
Ejecutado contra: iDempiere producción (192.168.1.73)

---

## Resumen Ejecutivo

| Métrica | 2024 | 2025 |
|---------|------|------|
| Facturas (ARI) | 38,674 | 42,869 |
| Total facturado | Bs. 1,994M | Bs. 10,404M |
| Notas crédito (ARC) | 21,270 | 15,150 |
| Monto NC | Bs. 88.9M | Bs. 1,370M |
| **Venta neta** | **Bs. 1,905M** | **Bs. 9,033M** |
| Recibos cobranza | 39,160 | 52,913 |
| Total cobrado | Bs. 7,930M | Bs. 34,928M |

---

## A) Facturación

### Por mes 2025

| Mes | Facturas | NC | Venta neta |
|-----|----------|-----|------------|
| Ene | 2,785 | 2,009 | 215.6M |
| Feb | 2,929 | 1,679 | 244.8M |
| Mar | 2,928 | 1,697 | 231.5M |
| Abr | 3,607 | 1,517 | 373.3M |
| May | 3,723 | 2,675 | 437.8M |
| Jun | 3,402 | 925 | 479.9M |
| Jul | 3,556 | 828 | 389.3M |
| Ago | 3,640 | 574 | 828.8M |
| Sep | 4,124 | 894 | 918.5M |
| Oct | 5,052 | 882 | 1,558M |
| Nov | 3,728 | 722 | 1,350M |
| Dic | 3,395 | 748 | 2,005M |

### Por moneda 2025

| Moneda | Facturas | NC | Total facturado | Venta neta |
|--------|----------|-----|-----------------|------------|
| Bs. | 20,037 | 5,617 | 10,325M | 8,960M |
| USD | 22,832 | 9,533 | 78.8M | 73.2M |

### Por organización 2025

| Organización | Facturas | Venta neta |
|---|---|---|
| INPROA SANTONI C.A. | 27,313 | 5,476M |
| InproMaiz C.A | 10,056 | 2,930M |
| AGROINPROA C.A | 2,695 | 401M |
| AGROPECUARIA R.R. C.A. | 1,551 | 132M |
| INVERSIONES AGA C.A | 1,222 | 52.6M |
| AGA AGRICOLA C.A | 2 | 32.8M |
| Santoni Service C.A | 25 | 7.4M |
| Ocean Equipment Industries LLC | 5 | 0.28M |

---

## B) Top Clientes 2025 (Top 20, Bs.)

Datos verificados — ver output completo del script SQL.

---

## C) Cobranza

### BUG ENCONTRADO: Métodos de pago

El bot solo mapeaba 5 tipos de pago (X, C, K, D, T) pero existen **19 tipos** en producción.
El más usado, "W" (Transferencia), representaba el 81% de los recibos y aparecía como código crudo.

**Fix aplicado** en `idempiere_queries.py`. Nombres verificados contra `ad_ref_list` (14/Mar/2026):

| Código | Nombre (verificado) | Recibos 2025 | Total |
|--------|---------------------|-------------|-------|
| W | Transferencia | 42,770 | 11,117M |
| Z | Dólar Transferencia | 434 | 9,557M |
| D | Débito Directo | 73 | 6,811M |
| S | Transferencia Empresas | 2,275 | 5,161M |
| X | Efectivo | 5,195 | 1,144M |
| T | Cuenta | 1,101 | 742M |
| Y | Dólar Efectivo | 1,057 | 296M |
| U | Euro Transferencia | 1 | 96M |
| K | Cheque | 3 | 209K |
| R | Dólar IGTF | 1 | 88K |
| B | Tarjeta de Débito | 2 | 6K |
| E | Euro Efectivo | 1 | 2K |

### Top 20 clientes por cobranza 2025

| Cliente | Recibos | Total |
|---------|---------|-------|
| INPROA SANTONI, C.A | 2,955 | 12,190M |
| INPROMAIZ, C.A. | 1,467 | 10,475M |
| AGROINPROA, C.A. | 190 | 1,726M |
| (y 17 más...) | | |

> **NOTA:** Cobranza (34,928M) >> Facturación (10,404M) porque incluye
> transferencias inter-empresa entre organizaciones del grupo.

---

## D) Cuentas por cobrar vencidas

- Las más antiguas tienen **+1,000 días de atraso** (desde 2023)
- Incluye facturas de ALIMENTOS POLAR con montos de 54M y 18M
- Query funciona correctamente con filtro `ispaid='N'` + `grandtotal > 100`

---

## E) Verificación de estructura

### Docstatus facturas 2025
- CO (Completado): 58,019
- RE (Reversado): 1,913
- VO (Anulado): 293
- DR (Borrador): 6
- **No hay CL (Cerrado)** — el filtro `IN ('CO','CL')` es correcto pero CL no se usa

### Docstatus pagos 2025
- CO: 52,913
- RE: 1,794
- VO: 70
- IP: 28
- DR: 9
- IN: 4

### Monedas verificadas
| iso_code | c_currency_id | Facturas 2025 |
|----------|---------------|---------------|
| VES | 205 | 25,654 |
| DOL | 1000000 | 19,751 |
| DoL | 1000011 | 7,189 |
| USA | 1000003 | 2,796 |
| dol | 1000008 | 1,550 |
| Dol | 1000006 | 1,074 |
| USD | 100 | 5 |

IDs 1000009, 1000013, 1000017 del código no aparecen en 2025 (posiblemente en data más vieja).

### Zonas de venta
- **"Sin Zona"** agrupa el 55% de las facturas
- Zonas más activas: BARQUISIMETO, MARACAIBO, MERIDA, GUANARE, FALCON
- Existen zonas duplicadas con IDs diferentes (ej: "ZONA BARQUISIMETO" x2)

### Tipologías de clientes
- Clientes: 3,635
- ClientesInproa: 3,432
- ClientesInproaPLANTA: 384
- Clientes al Mayor: 236
- (+ proveedores, empleados, productores)

---

## Acciones tomadas

1. **Fix tendertype** (`idempiere_queries.py`): Agregados 8 nuevos tipos de pago al CASE
2. **Docs actualizados** (`MAPEO_TABLAS_IDEMPIERE.md`): Tabla de tendertype con volumen real
3. **System prompts** (`ventas.py`, `finanzas.py`): Actualizados códigos de tendertype

## Pendientes

1. ~~Confirmar nombres exactos de W, Z, S, Y contra `ad_ref_list` en iDempiere~~ **HECHO 14/Mar/2026** - 19 tipos verificados
2. Evaluar si las zonas duplicadas (mismo nombre, diferente ID) causan problemas
3. Considerar excluir pagos inter-empresa del resumen de cobranza (INPROA, INPROMAIZ) — **DECIDIDO: NO filtrar** (usuario quiere verlos)
4. **CRÍTICO:** El agente de ventas hallucina datos en consultas de "Ventas en Bs." — facturas, montos y desglose regional inventados. Investigar por qué USD funciona bien pero Bs. no. Ver tabla de discrepancias en `DATOS_VERIFICACION_IDEMPIERE.md`
