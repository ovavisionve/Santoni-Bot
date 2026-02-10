"""
Demo data models - simulates iDempiere tables locally.
These tables are used when the real iDempiere connection is not available.
Once iDempiere is connected, queries will target the real database.
"""

import enum
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    String,
    Text,
    Integer,
    Numeric,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ============================================================
# VENTAS (Sales) - Priority department
# ============================================================


class DemoCliente(Base):
    """Simulates C_BPartner (customers)."""

    __tablename__ = "demo_clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(255))
    rif: Mapped[str] = mapped_column(String(20))
    zona: Mapped[str] = mapped_column(String(100))
    vendedor: Mapped[str] = mapped_column(String(100))
    tipologia: Mapped[str] = mapped_column(String(50))  # mayorista, detallista, etc.
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(50))
    ciudad: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_registro: Mapped[date] = mapped_column(Date)
    ultima_compra: Mapped[date | None] = mapped_column(Date, nullable=True)
    limite_credito: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)


class DemoFacturaVenta(Base):
    """Simulates C_Invoice for sales."""

    __tablename__ = "demo_facturas_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_factura: Mapped[str] = mapped_column(String(20), unique=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("demo_clientes.id"))
    vendedor: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(100))
    fecha: Mapped[date] = mapped_column(Date)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    monto_iva: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    monto_neto: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado: Mapped[str] = mapped_column(String(20))  # pagada, pendiente, anulada
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3), default="VES")


class DemoLineaFacturaVenta(Base):
    """Simulates C_InvoiceLine for sales."""

    __tablename__ = "demo_lineas_factura_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_facturas_venta.id")
    )
    producto: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[str] = mapped_column(String(100))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2))


class DemoCobranza(Base):
    """Simulates C_Payment for collections."""

    __tablename__ = "demo_cobranzas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_recibo: Mapped[str] = mapped_column(String(20), unique=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("demo_clientes.id"))
    factura_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_facturas_venta.id")
    )
    vendedor: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(100))
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    metodo_pago: Mapped[str] = mapped_column(String(50))  # efectivo, transferencia, etc.


class DemoMetaVenta(Base):
    """Sales targets by salesperson and period."""

    __tablename__ = "demo_metas_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendedor: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(100))
    mes: Mapped[int] = mapped_column(Integer)
    anio: Mapped[int] = mapped_column(Integer)
    meta_venta: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    meta_cobranza: Mapped[Decimal] = mapped_column(Numeric(15, 2))


# ============================================================
# FINANZAS (Finance)
# ============================================================


class DemoCuentaBancaria(Base):
    """Bank accounts."""

    __tablename__ = "demo_cuentas_bancarias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    banco: Mapped[str] = mapped_column(String(100))
    numero_cuenta: Mapped[str] = mapped_column(String(30))
    tipo: Mapped[str] = mapped_column(String(20))  # corriente, ahorro
    moneda: Mapped[str] = mapped_column(String(3))
    saldo: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    fecha_saldo: Mapped[date] = mapped_column(Date)


class DemoMovimientoBancario(Base):
    """Bank movements."""

    __tablename__ = "demo_movimientos_bancarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cuenta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_cuentas_bancarias.id")
    )
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str] = mapped_column(String(255))
    referencia: Mapped[str] = mapped_column(String(50))
    tipo: Mapped[str] = mapped_column(String(10))  # debito, credito
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(15, 2))


class DemoCuentaPorPagar(Base):
    """Accounts payable."""

    __tablename__ = "demo_cuentas_por_pagar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    proveedor: Mapped[str] = mapped_column(String(255))
    numero_factura: Mapped[str] = mapped_column(String(30))
    fecha_factura: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    monto_original: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    monto_pendiente: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="VES")
    estado: Mapped[str] = mapped_column(String(20))


# ============================================================
# CONTABILIDAD (Accounting)
# ============================================================


class DemoAsientoContable(Base):
    """General ledger entries."""

    __tablename__ = "demo_asientos_contables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_asiento: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[date] = mapped_column(Date)
    cuenta_contable: Mapped[str] = mapped_column(String(20))
    nombre_cuenta: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(String(255))
    debe: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    haber: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    periodo: Mapped[str] = mapped_column(String(7))  # 2025-01


class DemoBalanceGeneral(Base):
    """Balance sheet summary by period."""

    __tablename__ = "demo_balance_general"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    periodo: Mapped[str] = mapped_column(String(7))
    tipo_cuenta: Mapped[str] = mapped_column(String(50))  # activo, pasivo, patrimonio
    grupo: Mapped[str] = mapped_column(String(100))
    cuenta: Mapped[str] = mapped_column(String(200))
    saldo: Mapped[Decimal] = mapped_column(Numeric(15, 2))


# ============================================================
# RRHH (Human Resources)
# ============================================================


class DemoEmpleado(Base):
    """Employees."""

    __tablename__ = "demo_empleados"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cedula: Mapped[str] = mapped_column(String(15), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[str] = mapped_column(String(100))
    departamento: Mapped[str] = mapped_column(String(100))
    ubicacion: Mapped[str] = mapped_column(String(100))  # Agua Blanca, Araure
    fecha_ingreso: Mapped[date] = mapped_column(Date)
    salario_basico: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    turno: Mapped[str] = mapped_column(String(20))  # diurno, rotativo
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)


class DemoNomina(Base):
    """Payroll entries."""

    __tablename__ = "demo_nominas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empleado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_empleados.id")
    )
    periodo: Mapped[str] = mapped_column(String(7))  # 2025-01
    tipo_nomina: Mapped[str] = mapped_column(String(30))  # quincenal, mensual
    salario_basico: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    asignaciones: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    deducciones: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    neto_pagar: Mapped[Decimal] = mapped_column(Numeric(15, 2))


class DemoAsistencia(Base):
    """Attendance records."""

    __tablename__ = "demo_asistencias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empleado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_empleados.id")
    )
    fecha: Mapped[date] = mapped_column(Date)
    hora_entrada: Mapped[str | None] = mapped_column(String(5), nullable=True)
    hora_salida: Mapped[str | None] = mapped_column(String(5), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))  # asistencia, falta, permiso, vacacion


# ============================================================
# PRODUCCION (Production)
# ============================================================


class DemoProduccionDiaria(Base):
    """Daily production records."""

    __tablename__ = "demo_produccion_diaria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date)
    planta: Mapped[str] = mapped_column(String(50))  # Planta 1, Planta 2
    linea: Mapped[str] = mapped_column(String(50))
    turno: Mapped[str] = mapped_column(String(20))
    producto: Mapped[str] = mapped_column(String(200))
    cantidad_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    desperdicio_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    horas_operacion: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    horas_parada: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    motivo_parada: Mapped[str | None] = mapped_column(String(200), nullable=True)


class DemoOrdenProduccion(Base):
    """Production orders."""

    __tablename__ = "demo_ordenes_produccion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_orden: Mapped[str] = mapped_column(String(20), unique=True)
    fecha: Mapped[date] = mapped_column(Date)
    producto: Mapped[str] = mapped_column(String(200))
    cantidad_planificada: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad_producida: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    estado: Mapped[str] = mapped_column(String(20))  # planificada, en_proceso, completada
    planta: Mapped[str] = mapped_column(String(50))


# ============================================================
# COMPRAS INSUMOS (Supplies Procurement)
# ============================================================


class DemoProveedorInsumo(Base):
    """Supply vendors."""

    __tablename__ = "demo_proveedores_insumos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(255))
    rif: Mapped[str] = mapped_column(String(20))
    contacto: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tipo_insumo: Mapped[str] = mapped_column(String(100))
    calificacion: Mapped[int] = mapped_column(Integer, default=3)  # 1-5


class DemoOrdenCompraInsumo(Base):
    """Purchase orders for supplies."""

    __tablename__ = "demo_ordenes_compra_insumos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_orden: Mapped[str] = mapped_column(String(20), unique=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_proveedores_insumos.id")
    )
    fecha: Mapped[date] = mapped_column(Date)
    fecha_entrega_estimada: Mapped[date] = mapped_column(Date)
    fecha_entrega_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    insumo: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unidad: Mapped[str] = mapped_column(String(20))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado: Mapped[str] = mapped_column(String(20))  # pendiente, recibida, parcial


# ============================================================
# COMPRAS PRODUCTORES (Producer Purchases)
# ============================================================


class DemoProductor(Base):
    """Agricultural producers."""

    __tablename__ = "demo_productores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(255))
    cedula: Mapped[str] = mapped_column(String(15))
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado: Mapped[str] = mapped_column(String(50))  # Portuguesa, Barinas, etc.
    municipio: Mapped[str] = mapped_column(String(100))
    tipo_producto: Mapped[str] = mapped_column(String(20))  # arroz, maiz
    hectareas: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class DemoCompraProductor(Base):
    """Purchases from producers."""

    __tablename__ = "demo_compras_productores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_guia: Mapped[str] = mapped_column(String(20), unique=True)
    productor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("demo_productores.id")
    )
    fecha: Mapped[date] = mapped_column(Date)
    producto: Mapped[str] = mapped_column(String(50))  # Arroz Paddy Húmedo, Maíz
    peso_bruto_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    peso_neto_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    humedad_porcentaje: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    impureza_porcentaje: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    precio_kg: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    monto_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado_pago: Mapped[str] = mapped_column(String(20))  # pagado, pendiente
    moneda: Mapped[str] = mapped_column(String(3), default="VES")
