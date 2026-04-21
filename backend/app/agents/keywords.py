"""
Módulo centralizado de keywords para todos los agentes de SantoniBot.

Organizado por categorías semánticas. Cada agente importa las categorías
que necesita para detectar tipos de consulta, entidades, temporalidad, etc.

Convenciones:
- Todo en minúsculas (la comparación se hace con msg.lower())
- Incluye variantes con/sin acento
- Incluye singular y plural
- Incluye formas informales venezolanas
- Cada set contiene frozenset para búsqueda O(1)
"""

# ═══════════════════════════════════════════════════════════════════
# 1. VERBOS DE CONSULTA (formas en las que el usuario pide datos)
# ═══════════════════════════════════════════════════════════════════

# Verbos de solicitud/petición
VERBOS_SOLICITUD = frozenset({
    # Imperativos directos
    "dame", "dime", "muéstrame", "muestrame", "muestra", "indica",
    "indícame", "indicame", "enseña", "enseñame", "enséñame",
    "presenta", "preséntame", "presentame",
    "pásame", "pasame", "envíame", "enviame",
    # Condicionales
    "podrías", "podrias", "pudieras", "pudiera", "puedes",
    "sería posible", "seria posible", "es posible",
    "me pudieras", "me podrías", "me podrias",
    # Querer/Necesitar
    "quiero", "quisiera", "necesito", "requiero",
    "me gustaría", "me gustaria",
    # Buscar/Encontrar
    "busca", "encuentra", "localiza", "ubica", "rastrea",
    "búscame", "buscame", "encuéntrame", "encuentrame",
    # Ver/Consultar
    "ver", "consulta", "consultar", "revisa", "revisar",
    "chequea", "chequear", "verifica", "verificar",
    "comprueba", "comprobar",
    # Listar/Enumerar
    "lista", "listar", "enumera", "enumerar", "detalla", "detallar",
    "desglosa", "desglosar",
    # Reportar/Informar
    "reporta", "reportar", "informa", "informar", "resume", "resumir",
    "genera", "generar", "elabora", "elaborar",
    # Calcular/Analizar
    "calcula", "calcular", "analiza", "analizar",
    "compara", "comparar", "evalúa", "evalua", "evaluar",
    # Saber
    "cuál es", "cual es", "cuáles son", "cuales son",
    "cuánto", "cuanto", "cuántos", "cuantos", "cuántas", "cuantas",
    "cómo está", "como esta", "cómo van", "como van",
    "qué hay", "que hay", "qué tiene", "que tiene",
    "hay algún", "hay algun", "hay alguna",
    "existe", "existen",
    # Venezolanismos
    "échale un ojo", "echale un ojo",
    "tráeme", "traeme", "sácame", "sacame",
    "hazme", "pásame", "pasame",
})

# Verbos de compra/adquisición
VERBOS_COMPRA = frozenset({
    "compró", "compro", "compramos", "compraron", "comprado",
    "adquirió", "adquirio", "adquirimos", "adquirieron", "adquirido",
    "se compró", "se compro", "se ha comprado", "se han comprado",
    "se adquirió", "se adquirio",
    "gastó", "gasto", "gastamos", "gastaron", "gastado",
    "invirtió", "invirtio", "invertimos", "invertido",
    "facturó", "facturo", "facturamos", "facturaron", "facturado",
})

# Verbos de venta
VERBOS_VENTA = frozenset({
    "vendió", "vendio", "vendimos", "vendieron", "vendido",
    "facturó", "facturo", "facturamos", "facturaron", "facturado",
    "despachó", "despacho", "despachamos", "despacharon", "despachado",
    "cobró", "cobro", "cobramos", "cobraron", "cobrado",
    "recaudó", "recaudo", "recaudamos", "recaudaron", "recaudado",
})

# Verbos de producción
VERBOS_PRODUCCION = frozenset({
    "produjo", "producimos", "produjeron", "producido",
    "fabricó", "fabrico", "fabricamos", "fabricaron", "fabricado",
    "manufacturó", "manufacturo", "manufacturado",
    "procesó", "proceso", "procesamos", "procesaron", "procesado",
    "elaboró", "elaboro", "elaboramos", "elaboraron", "elaborado",
    "empacó", "empaco", "empacamos", "empacaron", "empacado",
    "envasó", "envaso", "envasamos", "envasaron", "envasado",
    "molió", "molio", "molimos", "molieron", "molido",
    "trituró", "trituro", "trituramos", "trituraron", "triturado",
    "mezcló", "mezclo", "mezclamos", "mezclaron", "mezclado",
})

# Verbos de RRHH
VERBOS_RRHH = frozenset({
    "trabaja", "trabajan", "trabajando",
    "ingresó", "ingreso", "ingresaron", "ingresado",
    "renunció", "renuncio", "renunciaron", "renunciado",
    "despidió", "despidio", "despidieron", "despedido",
    "contrató", "contrato", "contratamos", "contrataron", "contratado",
    "cumple años", "cumpleaños", "cumple",
    "faltó", "falto", "faltaron", "faltado",
    "ausentó", "ausento", "ausentaron", "ausentado",
    "vacacionó", "vacaciones",
})

# Verbos financieros
VERBOS_FINANCIEROS = frozenset({
    "pagó", "pago", "pagamos", "pagaron", "pagado",
    "debemos", "debe", "deben", "adeuda", "adeudamos",
    "depositó", "deposito", "depositamos", "depositaron",
    "transfirió", "transfirio", "transferimos", "transfirieron",
    "financió", "financio", "financiamos", "financiaron",
    "prestó", "presto", "prestamos", "prestaron",
})


# ═══════════════════════════════════════════════════════════════════
# 2. TIPOS DE CONSULTA POR AGENTE
# ═══════════════════════════════════════════════════════════════════

# ── COMPRAS INSUMOS ──────────────────────────────────────────────

COMPRAS_INVENTARIO = frozenset({
    # Stock/Inventario
    "inventario", "stock", "existencia", "existencias",
    "almacén", "almacen", "almacenes", "bodega", "bodegas",
    "depósito", "deposito", "depósitos", "depositos",
    "silo", "silos",
    # Disponibilidad
    "disponible", "disponibles", "disponibilidad",
    "en existencia", "en stock", "en almacén", "en almacen",
    "en bodega", "hay en", "quedan en",
    # Cuánto hay
    "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
    "cuánto tenemos", "cuanto tenemos", "cuántas quedan", "cuantas quedan",
    "cuántos quedan", "cuantos quedan", "cuánto nos queda", "cuanto nos queda",
    "cuántas hay", "cuantas hay", "cuántos hay", "cuantos hay",
    "qué hay en", "que hay en", "qué queda", "que queda",
    # Quedar (sin frase completa, para matchear "cuantas X quedan")
    "quedan", "queda",
    # Agotado/Escaso
    "agotado", "agotados", "agotada", "agotadas",
    "escaso", "escasos", "escasa", "escasas", "escasez",
    "por agotarse", "punto de agotarse", "sin stock", "sin existencia",
    "faltante", "faltantes",
    # Reponer/Reabastecer
    "reponer", "reabastecer", "reposición", "reposicion",
    "reabastecimiento", "reordenar", "punto de reorden",
    # Categoría
    "categoría de producto", "categoria de producto",
    "tipo de producto", "familia de producto",
    "grupo de producto",
})

COMPRAS_ORDENES = frozenset({
    # Órdenes de compra
    "orden de compra", "órdenes de compra", "ordenes de compra",
    "oc ", "o.c.", "oc-",
    # Pendientes de entrega
    "orden pendiente", "órdenes pendientes", "ordenes pendientes",
    "pedido pendiente", "pedidos pendientes",
    "por recibir", "sin recibir", "no recibido", "no recibidos",
    "por recepcionar", "sin recepcionar",
    "por recepción", "por recepcion",
    "por entregar", "sin entregar", "no entregado", "no entregados",
    # Estado de órdenes
    "estado de orden", "estado de la orden", "estado del pedido",
    "estado de pedido", "seguimiento de orden", "tracking de orden",
    "borrador", "borradores", "en proceso", "en progreso",
    # Solicitudes
    "solicitado", "solicitados", "solicitada", "solicitadas",
    "requisición", "requisicion", "requisiciones",
    "solicitud de compra", "solicitudes de compra",
    # Aprobación
    "por aprobar", "sin aprobar", "aprobado", "aprobada",
    "aprobados", "aprobadas",
})

COMPRAS_PRECIOS = frozenset({
    # Comparación de precios
    "comparar precio", "comparar precios",
    "comparación de precio", "comparacion de precio",
    "comparación de precios", "comparacion de precios",
    "comparativo de precio", "comparativo de precios",
    "entre proveedores", "de proveedores",
    # Mejor/Peor precio
    "mejor precio", "mejores precios", "peor precio",
    "precio más bajo", "precio mas bajo",
    "precio más alto", "precio mas alto",
    "precio más barato", "precio mas barato",
    "precio más caro", "precio mas caro",
    "más barato", "mas barato", "más caro", "mas caro",
    "más económico", "mas economico",
    # Quién vende
    "quién vende", "quien vende",
    "quién ofrece", "quien ofrece",
    "quién tiene", "quien tiene",
    "quién distribuye", "quien distribuye",
    "quién vende más barato", "quien vende mas barato",
    "proveedores que venden", "proveedores de",
    "alternativas de proveedor", "alternativa de proveedor",
    "opciones de proveedor", "opción de proveedor",
    # Cotización
    "cotización", "cotizacion", "cotizaciones",
    "cotizar", "recotizar",
    # Precio unitario
    "precio unitario", "precio por unidad", "precio/unidad",
    "costo unitario", "costo por unidad",
    "valor unitario", "valor por unidad",
    # Tendencia de precios
    "tendencia de precio", "tendencia de precios",
    "evolución de precio", "evolucion de precio",
    "variación de precio", "variacion de precio",
    "histórico de precio", "historico de precio",
    "historial de precio", "historial de precios",
    "precio promedio", "precio medio",
})

COMPRAS_PAGOS = frozenset({
    # Estado de pago
    "estado de pago", "estatus de pago", "status de pago",
    "estado del pago", "estatus del pago",
    # Facturas pagadas/pendientes
    "factura pagada", "facturas pagadas",
    "factura pendiente", "facturas pendientes",
    "factura sin pagar", "facturas sin pagar",
    "factura por pagar", "facturas por pagar",
    "pagada", "pagadas", "pagado", "pagados",
    "pendiente de pago", "pendientes de pago",
    "sin pagar", "no pagado", "no pagada", "no pagados", "no pagadas",
    "impago", "impaga", "impagos", "impagas",
    # Vencimiento
    "factura vencida", "facturas vencidas",
    "vencida", "vencidas", "vencido", "vencidos",
    "por vencer", "próxima a vencer", "proxima a vencer",
    "próximas a vencer", "proximas a vencer",
    "vencimiento", "vencimientos", "fecha de vencimiento",
    "días de atraso", "dias de atraso",
    "plazo vencido", "fuera de plazo",
    # Morosidad
    "morosidad", "moroso", "morosa", "morosos", "morosas",
    "atrasada", "atrasadas", "atrasado", "atrasados",
    "atraso", "atrasos", "en mora",
    # Cuentas por pagar
    "cuentas por pagar", "cuenta por pagar",
    "deuda", "deudas", "adeudado", "adeudada",
    "compromisos de pago", "compromiso de pago",
    "saldo pendiente", "saldos pendientes",
    "saldo por pagar", "saldos por pagar",
    "debe", "debemos", "deben",
    # Cobro a proveedores
    "anticipo", "anticipos", "abono", "abonos",
    "pago parcial", "pagos parciales",
    "saldo a favor", "crédito con proveedor",
    "nota de crédito", "nota de credito",
    "nota de débito", "nota de debito",
})

COMPRAS_GENERAL = frozenset({
    # Resumen general
    "resumen", "resumen de compras", "resumen general",
    "total de compras", "total comprado", "total compras",
    "cuánto se compró", "cuanto se compro",
    "cuánto compramos", "cuanto compramos",
    "cuánto se ha comprado", "cuanto se ha comprado",
    "cuánto gastamos", "cuanto gastamos",
    "cuánto se gastó", "cuanto se gasto",
    "monto total de compras", "valor total de compras",
    # Proveedores genérico
    "proveedor", "proveedores", "principales proveedores",
    "top proveedores", "ranking de proveedores",
    "mejores proveedores", "mayores proveedores",
    # Productos genérico
    "principales productos", "productos más comprados",
    "productos mas comprados", "top productos",
    "ranking de productos", "qué se compra más", "que se compra mas",
    "insumo más comprado", "insumos más comprados",
    # Tendencia/Análisis
    "tendencia de compras", "tendencia mensual",
    "evolución de compras", "evolucion de compras",
    "análisis de compras", "analisis de compras",
    "comportamiento de compras",
    "mensual", "mensualmente", "por mes", "mes a mes",
    # Gastos operativos
    "gasto operativo", "gastos operativos",
    "gasto de insumos", "gastos de insumos",
    "costo de insumos", "costos de insumos",
    "gasto en materiales", "gastos en materiales",
})

COMPRAS_HISTORIAL = frozenset({
    # Historial de compras
    "historial", "historial de compras", "historial de compra",
    "histórico", "historico", "histórico de compras", "historico de compras",
    "registro de compras", "registros de compras",
    "últimas compras", "ultimas compras",
    "compras recientes", "compras anteriores",
    "cuándo fue la última", "cuando fue la ultima",
    "última vez que se compró", "ultima vez que se compro",
    "cuándo compramos", "cuando compramos",
    "frecuencia de compra", "cada cuánto compramos",
    # Detalle de factura
    "detalle de factura", "detalles de factura",
    "factura de compra", "facturas de compra",
    "líneas de factura", "lineas de factura",
})

# ── VENTAS ───────────────────────────────────────────────────────

VENTAS_CLIENTES = frozenset({
    # Top/Ranking (incluye stems cortos para detección intra-agente)
    "top", "mejor", "ranking", "principales",
    "top clientes", "top cliente", "top 10 clientes", "top 20 clientes",
    "ranking de clientes", "ranking clientes",
    "principales clientes", "mejores clientes",
    "mayores clientes", "clientes más grandes", "clientes mas grandes",
    "pareto", "pareto de clientes", "abc de clientes",
    "clientes clave", "clientes estratégicos", "clientes estrategicos",
    # Análisis de clientes
    "clientes activos", "clientes inactivos",
    "clientes nuevos", "nuevos clientes",
    "cartera de clientes", "base de clientes",
    "cuántos clientes", "cuantos clientes",
    "segmentación de clientes", "segmentacion de clientes",
    "clasificación de clientes", "clasificacion de clientes",
    "tipología de clientes", "tipologia de clientes",
    # Distribuidores
    "distribuidor", "distribuidores",
    "distribuidor mayorista", "distribuidores mayoristas",
    "canal de venta", "canales de venta",
    "intermediario", "intermediarios",
    "agente comercial", "agentes comerciales",
})

VENTAS_FACTURACION = frozenset({
    # Facturación
    "facturación", "facturacion", "facturado",
    "cuánto se facturó", "cuanto se facturo",
    "cuánto facturamos", "cuanto facturamos",
    "total facturado", "monto facturado",
    "venta neta", "ventas netas",
    "volumen de venta", "volumen de ventas", "volumen",
    "ingreso", "ingresos",
    # Ventas general
    "venta", "ventas", "vendido", "vendidos",
    "cuánto se vendió", "cuanto se vendio",
    "cuánto vendimos", "cuanto vendimos",
    "resumen de ventas", "total de ventas",
    "reporte de ventas", "informe de ventas",
    # Notas de crédito
    "nota de crédito", "nota de credito",
    "notas de crédito", "notas de credito",
    "devolución", "devolucion", "devoluciones",
    # Proforma
    "proforma", "proformas", "prefactura", "prefacturas",
})

VENTAS_COBRANZA = frozenset({
    # Cobros (incluye formas verbales para detección)
    "cobranza", "cobranzas", "cobro", "cobros",
    "cobrado", "cobrada", "cobrados", "pago", "pagos",
    "recaudación", "recaudacion", "recaudado",
    "cuánto se cobró", "cuanto se cobro",
    "cuánto cobramos", "cuanto cobramos",
    "total cobrado", "monto cobrado",
    "cobros del día", "cobros del dia",
    "cobros de hoy", "cobranza diaria",
    "cobro diario", "recibo", "recibos",
    # Pendientes de cobro
    "pendiente de cobro", "pendientes de cobro",
    "por cobrar", "sin cobrar",
    "cartera vencida", "cartera morosa",
    # Métodos de pago
    "transferencia", "efectivo", "cheque",
    "depósito", "deposito", "tarjeta",
    "método de pago", "metodo de pago",
    "forma de pago", "formas de pago",
    "débito", "debito", "crédito", "credito",
})

VENTAS_ZONAS = frozenset({
    # Zonas geográficas
    "zona", "zonas", "región", "region", "regiones",
    "por zona", "por región", "por region",
    "ventas por zona", "ventas por región", "ventas por region",
    "ranking por zona", "top por zona",
    # Ciudades/Estados de Venezuela
    "portuguesa", "barinas", "lara", "carabobo", "aragua",
    "zulia", "maracaibo", "falcón", "falcon", "margarita",
    "trujillo", "mérida", "merida", "táchira", "tachira",
    "guanare", "cabimas", "valencia", "caracas", "oriente",
    "santa bárbara", "santa barbara", "barquisimeto",
    "san cristóbal", "san cristobal", "san félix", "san felix",
    "ciudad guayana", "ciudad bolívar", "ciudad bolivar",
    "maturín", "maturin", "el vigía", "el vigia",
    "yaracuy", "anzoátegui", "anzoategui", "cumaná", "cumana",
    "barcelona", "acarigua",
    # Zona desatendida
    "desatendida", "desatendidas", "sin atender", "sin cobertura",
})

VENTAS_VENDEDORES = frozenset({
    # Vendedores
    "vendedor", "vendedores", "vendedora", "vendedoras",
    "asesor comercial", "asesores comerciales",
    "representante de ventas", "representantes de ventas",
    "fuerza de ventas", "equipo de ventas",
    "ranking de vendedores", "top vendedores",
    "mejor vendedor", "peor vendedor",
    "meta", "metas", "cuota", "cuotas",
    "cumplimiento", "cumplimiento de meta",
})

VENTAS_CXC = frozenset({
    # Cuentas por cobrar
    "cuentas por cobrar", "cuenta por cobrar",
    "cartera por cobrar", "saldos por cobrar",
    "facturas por cobrar", "factura por cobrar",
    # Stems cortos para detección intra-agente
    "pendiente", "pendientes", "deben", "deudor", "deudores",
    "vencido", "vencida", "vencidos", "vencidas", "vencimiento",
    "atrasado", "atrasada", "atrasados", "atraso", "atrasos",
    # Vencidas/Morosas
    "cuentas vencidas", "facturas vencidas",
    "clientes morosos", "cliente moroso",
    "moroso", "morosos", "morosa", "morosas",
    "morosidad", "mora",
    "atraso en pago", "atrasos en pago",
    "deuda de cliente", "deudas de clientes",
    "antigüedad de saldos", "antiguedad de saldos",
    "aging", "envejecimiento",
    # Top morosos
    "top morosos", "principales morosos",
    "clientes con mayor deuda", "clientes que más deben",
    "quién debe más", "quien debe mas",
})

# ── FINANZAS ─────────────────────────────────────────────────────

FINANZAS_BANCOS = frozenset({
    # Saldos bancarios
    "saldo bancario", "saldos bancarios",
    "cuenta bancaria", "cuentas bancarias",
    "banco", "bancos", "balance bancario",
    "disponibilidad bancaria", "liquidez",
    "dinero en banco", "fondos disponibles",
    "cuánto tenemos en banco", "cuanto tenemos en banco",
    "mayor disponibilidad", "mejor saldo",
    "cuenta corriente", "cuentas corrientes",
    "cuenta de ahorro", "cuentas de ahorro",
    "cuenta inversión", "cuenta inversion",
    "fideicomiso", "fideicomisos",
})

FINANZAS_CXP = frozenset({
    # Cuentas por pagar
    "cuentas por pagar", "cuenta por pagar",
    "saldo por pagar", "saldos por pagar",
    "cuánto debemos", "cuanto debemos",
    "cuánto se debe", "cuanto se debe",
    "compromisos de pago", "compromiso de pago",
    "obligaciones", "pasivos corrientes",
    "deuda total", "total de deudas",
})

FINANZAS_CXC = frozenset({
    # Cuentas por cobrar
    "cuentas por cobrar", "cuenta por cobrar",
    "nos deben", "nos adeudan",
    "cuánto nos deben", "cuanto nos deben",
    "cartera de cobro", "cartera de clientes",
    # Stems para detección intra-agente finanzas
    "cobrar", "morosidad", "vencido", "vencida",
    "atrasado", "atrasada", "atraso",
})

FINANZAS_FLUJO = frozenset({
    # Flujo de caja
    "flujo de caja", "flujo de efectivo", "cash flow",
    "flujo neto", "flujo operativo",
    "entradas y salidas", "ingresos y egresos",
    "movimientos bancarios", "movimientos de caja",
    "arqueo", "arqueo de caja",
    "conciliación bancaria", "conciliacion bancaria",
})

FINANZAS_PRESTAMOS = frozenset({
    # Préstamos
    "préstamo", "prestamo", "préstamos", "prestamos",
    "crédito", "credito", "créditos", "creditos",
    "línea de crédito", "linea de credito",
    "financiamiento", "financiamientos",
    "cuota", "cuotas", "cuota de préstamo", "cuota de prestamo",
    "amortización", "amortizacion",
    "interés", "interes", "intereses",
    "capital", "capital pendiente",
    "refinanciamiento", "reestructuración", "reestructuracion",
})

# ── CONTABILIDAD ─────────────────────────────────────────────────

CONTABILIDAD_BALANCE = frozenset({
    # Balance general
    "balance", "balance general", "balance de situación",
    "balance de situacion", "estado de situación",
    "estado de situacion", "situación financiera",
    "situacion financiera", "estado patrimonial",
    "situación patrimonial", "situacion patrimonial",
    "activo", "activos", "pasivo", "pasivos",
    "patrimonio", "capital contable",
    "estructura financiera",
})

CONTABILIDAD_RESULTADOS = frozenset({
    # Estado de resultados
    "estado de resultados", "cuenta de resultados",
    "pérdidas y ganancias", "perdidas y ganancias",
    "p&l", "pyg", "pyd",
    "utilidad", "utilidades", "utilidad neta",
    "ganancia", "ganancias", "ganancia neta",
    "pérdida", "perdida", "pérdidas", "perdidas",
    "rentabilidad", "margen", "márgenes", "margenes",
    "ebitda", "ebit",
    "ingresos operacionales", "gastos operacionales",
    "costos de venta", "costo de ventas",
})

CONTABILIDAD_LIBROS = frozenset({
    # Libros contables
    "libro diario", "diario contable", "asiento", "asientos",
    "libro mayor", "mayor contable", "mayor general",
    "comprobante", "comprobantes",
    "póliza", "poliza", "pólizas", "polizas",
    "movimientos contables", "registros contables",
    "partida", "partidas", "partida doble",
    "débito", "debito", "crédito", "credito",
    "debe", "haber",
})

CONTABILIDAD_CUENTAS = frozenset({
    # Cuentas contables
    "cuenta contable", "cuentas contables",
    "plan de cuentas", "catálogo de cuentas", "catalogo de cuentas",
    "código de cuenta", "codigo de cuenta",
    "saldo de cuenta", "saldo contable",
    "movimiento de cuenta", "movimientos de cuenta",
    "cuenta auxiliar", "subcuenta",
    "cuentas de gasto", "cuentas de ingreso",
    "cuentas de activo", "cuentas de pasivo",
    "cuentas de patrimonio", "cuentas de capital",
})

CONTABILIDAD_COSTOS = frozenset({
    # Costos y gastos
    "costo", "costos", "gasto", "gastos",
    "costo de producción", "costo de produccion",
    "costo de producto", "costos de productos",
    "gasto administrativo", "gastos administrativos",
    "gasto de venta", "gastos de venta",
    "gasto operativo", "gastos operativos",
    "gasto financiero", "gastos financieros",
    "presupuesto", "presupuestos",
    "desviación presupuestaria", "desviacion presupuestaria",
})

# ── RRHH ─────────────────────────────────────────────────────────

RRHH_EMPLEADOS = frozenset({
    # Empleados general
    "empleado", "empleados", "empleada", "empleadas",
    "trabajador", "trabajadores", "trabajadora", "trabajadoras",
    "personal", "plantilla", "nómina activa", "nomina activa",
    "lista", "listado",
    # Ingresos/contrataciones
    "ingresaron", "ingresó", "ingreso",
    "contratación", "contratacion", "contrataciones", "contrataron",
    "nuevo ingreso", "nuevos ingresos",
    "recurso humano", "recursos humanos", "talento humano",
    "cuántos empleados", "cuantos empleados",
    "cuántos trabajadores", "cuantos trabajadores",
    "cuántas personas", "cuantas personas",
    "total de empleados", "total empleados",
    "headcount", "dotación", "dotacion",
    # Estado
    "activo", "activos", "activa", "activas",
    "inactivo", "inactivos", "inactiva", "inactivas",
    "jubilado", "jubilados", "jubilada", "jubiladas",
    "suspendido", "suspendidos", "suspendida", "suspendidas",
    # Por departamento
    "por departamento", "por área", "por area",
    "por gerencia", "por unidad",
    "departamento de", "área de", "area de",
})

RRHH_CARGOS = frozenset({
    # Cargos/Posiciones
    "cargo", "cargos", "puesto", "puestos",
    "posición", "posicion", "posiciones",
    "función", "funcion", "funciones",
    # Tipos de cargo (extensivo)
    "obrero", "obreros", "obrera", "obreras",
    "obrero integral", "obreros integrales",
    "gerente", "gerentes", "gerenta", "gerentas",
    "gerente general", "gerente de planta",
    "analista", "analistas",
    "supervisor", "supervisores", "supervisora", "supervisoras",
    "coordinador", "coordinadores", "coordinadora", "coordinadoras",
    "jefe", "jefes", "jefa", "jefas",
    "director", "directores", "directora", "directoras",
    "operario", "operarios", "operaria", "operarias",
    "operador", "operadores", "operadora", "operadoras",
    "asistente", "asistentes",
    "auxiliar", "auxiliares",
    "secretaria", "secretario", "secretarias", "secretarios",
    "técnico", "tecnicos", "técnicos", "tecnico",
    "ingeniero", "ingenieros", "ingeniera", "ingenieras",
    "chofer", "choferes", "conductor", "conductores",
    "vigilante", "vigilantes", "seguridad",
    "electricista", "electricistas",
    "mecánico", "mecanico", "mecánicos", "mecanicos",
    "soldador", "soldadores",
    "almacenista", "almacenistas",
    "recepcionista", "recepcionistas",
    "cajero", "cajera", "cajeros", "cajeras",
    "contador", "contadora", "contadores", "contadoras",
    "administrador", "administradora", "administradores",
    "mensajero", "mensajeros", "mensajera",
    "abogado", "abogada", "abogados",
    "médico", "medico", "médicos", "medicos",
    "enfermero", "enfermera", "enfermeros", "enfermeras",
    "cocinero", "cocinera", "cocineros",
    "jardinero", "jardinera", "jardineros",
    "limpieza", "mantenimiento",
    "pasante", "pasantes", "practicante", "practicantes",
    "aprendiz", "aprendices",
    "contratista", "contratistas",
    # Control de calidad
    "control de calidad", "calidad",
    "analista de calidad", "inspector", "inspectores",
    # IT
    "programador", "desarrollador", "sistemas",
    "informática", "informatica", "soporte técnico",
})

RRHH_NOMINA = frozenset({
    # Nómina
    "nómina", "nomina", "nóminas", "nominas",
    "pago de nómina", "pago de nomina",
    "recibo de pago", "recibos de pago",
    # Devengado/Deducciones
    "devengado", "devengados", "salario", "salarios",
    "sueldo", "sueldos", "remuneración", "remuneracion",
    "compensación", "compensacion",
    "deducción", "deduccion", "deducciones",
    "retención", "retencion", "retenciones",
    "aporte", "aportes",
    "bono", "bonos", "bonificación", "bonificacion",
    "prima", "primas",
    "aguinaldo", "utilidades",
    "prestaciones", "liquidación", "liquidacion",
    "neto a pagar", "neto", "total neto",
    # Seguro social
    "seguro social", "ivss", "faov", "lph", "banavih",
    "ince", "lopcymat", "inces",
    "aporte patronal", "aportes patronales",
    "cuota obrera", "cuota patronal",
    # Nómina especial
    "nómina especial", "nomina especial",
    "nómina quincenal", "nomina quincenal",
    "nómina semanal", "nomina semanal",
    "nómina mensual", "nomina mensual",
})

RRHH_AUSENTISMO = frozenset({
    # Ausentismo
    "ausentismo", "ausentismos", "ausentimos", "ausencia", "ausencias", "asistencia",
    "inasistencia", "inasistencias",
    "falta", "faltas", "faltó", "falto",
    "no asistió", "no asistio", "no asistieron",
    "índice de ausentismo", "indice de ausentismo",
    "tasa de ausentismo", "porcentaje de ausencia",
    # Permisos
    "permiso", "permisos",
    "permiso remunerado", "permisos remunerados",
    "permiso no remunerado", "permisos no remunerados",
    "permiso personal", "permisos personales",
    "permiso médico", "permiso medico",
    "día libre", "dia libre", "días libres", "dias libres",
    # Reposo
    "reposo", "reposos", "reposo médico", "reposo medico",
    "reposo pagado", "reposos pagados",
    "incapacidad", "incapacidades",
    "licencia", "licencias", "licencia médica", "licencia medica",
})

RRHH_CUMPLEANOS = frozenset({
    # Cumpleaños
    "cumpleaños", "cumpleanos", "cumpleañero", "cumpleañeros",
    "cumpleañera", "cumpleañeras",
    "nacimiento", "nacimientos", "fecha de nacimiento",
    "nació", "nacio", "nacieron",
    "quién cumple", "quien cumple",
    "quiénes cumplen", "quienes cumplen",
    "cumple años", "cumplen años", "cumplir años",
    "aniversario", "aniversarios",
    "felicitar", "felicitaciones",
    "birthday", "birthdays",
})

RRHH_VACACIONES = frozenset({
    # Vacaciones
    "vacación", "vacacion", "vacaciones",
    "período vacacional", "periodo vacacional",
    "días de vacaciones", "dias de vacaciones",
    "bono vacacional", "bono de vacaciones",
    "disfrute de vacaciones", "salió de vacaciones",
    "salio de vacaciones", "está de vacaciones",
    "esta de vacaciones", "están de vacaciones",
    "estan de vacaciones",
    "cuántos días de vacaciones", "cuantos dias de vacaciones",
    "acumulado de vacaciones", "pendiente de vacaciones",
    "vencimiento de vacaciones",
})

RRHH_ROTACION = frozenset({
    # Rotación
    "rotación", "rotacion", "turnover",
    "renunció", "renuncio", "renuncias", "renuncia",
    "despido", "despidos", "despedido", "despedidos",
    "egreso", "egresos", "egresado", "egresados",
    "ingreso de personal", "ingresos de personal",
    "nuevo ingreso", "nuevos ingresos",
    "cuántos renunciaron", "cuantos renunciaron",
    "cuántos ingresaron", "cuantos ingresaron",
    "se fueron", "se han ido", "se fue", "dejaron la empresa",
    "cuántos salieron", "cuantos salieron",
    "cuántos salieron", "cuantos salieron",
    "índice de rotación", "indice de rotacion",
    "tasa de rotación", "tasa de rotacion",
    "antigüedad", "antiguedad",
    "tiempo de servicio", "años de servicio",
    # Stems para detección intra-agente
    "baja", "bajas", "salida", "salidas",
})

# ── PRODUCCIÓN ───────────────────────────────────────────────────

PRODUCCION_GENERAL = frozenset({
    # Producción general (incluye formas verbales)
    "producción", "produccion", "producciones",
    "produjo", "producido", "producimos", "produjeron",
    "fabricó", "fabrico", "fabricado", "fabricar", "fabricamos",
    "cuánto se produjo", "cuanto se produjo",
    "cuánto producimos", "cuanto producimos",
    "total producido", "volumen de producción",
    "volumen de produccion", "capacidad de producción",
    "capacidad de produccion",
    "manufactura", "fabricación", "fabricacion",
    "procesamiento",
    # Órdenes de producción
    "orden de producción", "orden de produccion",
    "órdenes de producción", "ordenes de produccion",
    # Producto terminado
    "producto terminado", "productos terminados",
    "pt", "p.t.",
    "unidades producidas", "unidades fabricadas",
    "producción diaria", "produccion diaria",
    "producción semanal", "produccion semanal",
    "producción mensual", "produccion mensual",
    # Eficiencia
    "eficiencia", "rendimiento", "productividad",
    "oee", "utilización", "utilizacion",
    "velocidad de línea", "velocidad de linea",
    "throughput", "ritmo de producción", "ritmo de produccion",
})

PRODUCCION_DOCUMENTOS = frozenset({
    # Documentos de movimiento de inventario
    "documento", "documentos", "detalle", "detalles",
    "reciente", "recientes", "último", "ultimos", "últimos",
    "recepción", "recepcion", "recepciones",
    "despacho", "despachos",
    "exacto", "exactos", "exactas",
    "cuáles", "cuales", "cuál", "cual",
})

PRODUCCION_MATERIA_PRIMA = frozenset({
    # Materia prima
    "materia prima", "materias primas", "mp",
    "insumo", "insumos", "material", "materiales",
    "consumo", "consumido", "consumidos",
    "consumieron", "gastó", "gastaron", "usaron",
    "cuánto se consumió", "cuanto se consumio",
    "cuánto se usó", "cuanto se uso",
    "cuánto se gastó", "cuanto se gasto",
    # Recepción
    "recepción", "recepcion", "recepciones",
    "recibido", "recibidos", "recibida", "recibidas",
    "cuánto se recibió", "cuanto se recibio",
    "ingreso de materia prima", "entrada de materia",
    # Despacho
    "despacho", "despachos",
    "despachado", "despachados", "despachada", "despachadas",
    "salida de producto", "salidas de producto",
    "cuánto se despachó", "cuanto se despacho",
    "envío", "envio", "envíos", "envios",
})

PRODUCCION_DESPERDICIO = frozenset({
    # Desperdicios
    "desperdicio", "desperdicios",
    "merma", "mermas", "pérdida", "perdida", "pérdidas", "perdidas",
    "scrap", "rechazo", "rechazos", "rechazado", "rechazados",
    "defecto", "defectos", "defectuoso", "defectuosos",
    "descarte", "descartes", "descartado", "descartados",
    "subproducto", "subproductos",
    "cascarilla", "afrecho", "germen",
    "porcentaje de desperdicio", "tasa de desperdicio",
    "índice de merma", "indice de merma",
})

PRODUCCION_RECETAS = frozenset({
    # Recetas / BOM
    "receta", "recetas", "fórmula", "formula", "fórmulas", "formulas",
    "bom", "bill of material", "lista de materiales",
    "ingrediente", "ingredientes",
    "componente", "componentes",
    "composición", "composicion",
    "qué lleva", "que lleva", "qué tiene", "que tiene",
    "cómo se hace", "como se hace",
    "de qué está hecho", "de que esta hecho",
    "cuánto lleva", "cuanto lleva",
    "proporción", "proporcion", "proporciones",
    "mezcla", "mezclas", "batch", "lote",
})

PRODUCCION_ALMACENES = frozenset({
    # Almacenes/Movimientos
    "traslado", "traslados", "transferencia", "transferencias",
    "movimiento interno", "movimientos internos",
    "movimiento entre almacen", "movimiento entre almacén",
    "movimiento entre almacenes",
    "entre silo", "entre silos",
    "mover", "movió", "movio", "trasladó", "traslado",
    "trasladaron", "trasladados",
    "almacén", "almacen", "almacenes",
    "silo", "silos", "bodega", "bodegas",
    "depósito", "deposito",
    "planta", "sucursal", "sucursales",
    "locación", "locacion", "ubicación", "ubicacion",
})

# ── COMPRAS PRODUCTORES ──────────────────────────────────────────

PRODUCTORES_GENERAL = frozenset({
    # Productores
    "productor", "productores", "productora", "productoras",
    "agricultor", "agricultores", "agricultora", "agricultoras",
    "campesino", "campesinos",
    "sembrador", "sembradores",
    "cosechador", "cosechadores",
    "cooperativa", "cooperativas",
    "finca", "fincas", "hacienda", "haciendas",
    "parcela", "parcelas",
    # Registro
    "registrado", "registrados", "registrada", "registradas",
    "cuántos productores", "cuantos productores",
    "productores de arroz", "productores de maíz",
    "productores de maiz",
    "productores activos",
})

PRODUCTORES_COMPRAS = frozenset({
    # Compras agrícolas
    "arroz paddy", "arroz acondicionado",
    "maíz blanco", "maiz blanco", "maíz", "maiz",
    "materia prima agrícola", "materia prima agricola",
    "compra de arroz", "compras de arroz",
    "compra de maíz", "compra de maiz", "compras de maíz", "compras de maiz",
    "guía", "guia", "guías", "guias",
    "guía de despacho", "guia de despacho",
    "tonelada", "toneladas", "ton",
    "kilo", "kilos", "kilogramo", "kilogramos", "kg",
    "quintal", "quintales", "qq",
    "saco", "sacos",
    # Calidad
    "humedad", "impureza", "impurezas",
    "calidad del grano", "análisis de calidad",
    "analisis de calidad",
    "rendimiento del grano", "rendimiento de arroz",
    "grado de humedad",
    # Precio agrícola
    "precio del arroz", "precio del maíz", "precio del maiz",
    "precio del kilo", "precio por kilo",
    "precio del quintal", "precio por quintal",
    "precio del saco", "precio por saco",
    "precio promedio", "precio base",
    "precio de compra", "precios de compra",
    "liquidación al productor", "liquidacion al productor",
})

PRODUCTORES_PAGOS = frozenset({
    # Pagos a productores
    "pago a productor", "pagos a productores",
    "pago pendiente", "pagos pendientes",
    "deuda con productor", "deudas con productores",
    "cuánto se le debe", "cuanto se le debe",
    "cuánto le debemos", "cuanto le debemos",
    "liquidación pendiente", "liquidacion pendiente",
    "anticipo a productor", "anticipos a productores",
    "abono a productor", "abonos a productores",
    "saldo a favor del productor",
})


# ═══════════════════════════════════════════════════════════════════
# 3. TEMPORALIDAD (expresiones de tiempo)
# ═══════════════════════════════════════════════════════════════════

TEMPORALIDAD_HOY = frozenset({
    "hoy", "de hoy", "del día", "del dia",
    "del día de hoy", "del dia de hoy",
    "esta jornada", "hoy día", "hoy dia",
    "en el día", "en el dia", "al día de hoy", "al dia de hoy",
    "a la fecha", "fecha actual",
})

TEMPORALIDAD_AYER = frozenset({
    "ayer", "de ayer", "del día anterior", "del dia anterior",
    "día anterior", "dia anterior", "el día de ayer", "el dia de ayer",
})

TEMPORALIDAD_SEMANA = frozenset({
    "esta semana", "semana actual", "semana en curso",
    "semana pasada", "la semana pasada", "semana anterior",
    "última semana", "ultima semana",
    "últimos 7 días", "ultimos 7 dias",
    "últimos siete días", "ultimos siete dias",
    "semanal", "semanalmente", "por semana",
})

TEMPORALIDAD_MES = frozenset({
    "este mes", "mes actual", "mes en curso",
    "mes pasado", "el mes pasado", "mes anterior",
    "último mes", "ultimo mes",
    "mensual", "mensualmente", "por mes",
    "del mes", "en el mes",
    # Meses en español
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    # Abreviaciones
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
})

TEMPORALIDAD_TRIMESTRE = frozenset({
    "trimestre", "trimestral", "trimestralmente",
    "primer trimestre", "segundo trimestre",
    "tercer trimestre", "cuarto trimestre",
    "q1", "q2", "q3", "q4",
    "1er trimestre", "2do trimestre", "3er trimestre", "4to trimestre",
    "últimos 3 meses", "ultimos 3 meses",
    "últimos tres meses", "ultimos tres meses",
})

TEMPORALIDAD_ANO = frozenset({
    "este año", "año actual", "año en curso",
    "año pasado", "el año pasado", "año anterior",
    "último año", "ultimo año", "ultimo ano",
    "anual", "anualmente", "por año", "por ano",
    "del año", "del ano", "en el año", "en el ano",
    "acumulado anual", "acumulado del año", "acumulado del ano",
    "ytd", "year to date",
    "2024", "2025", "2026",
})

TEMPORALIDAD_RANGO = frozenset({
    "desde", "hasta", "entre", "al",
    "del", "desde el", "hasta el",
    "desde enero", "hasta marzo",
    "de enero a marzo", "de enero a diciembre",
    "primer semestre", "segundo semestre",
    "semestre", "semestral",
    "últimos 6 meses", "ultimos 6 meses",
    "últimos 12 meses", "ultimos 12 meses",
})


# ═══════════════════════════════════════════════════════════════════
# 4. MONEDAS
# ═══════════════════════════════════════════════════════════════════

MONEDA_USD = frozenset({
    # Dólares
    "dólar", "dolar", "dólares", "dolares",
    "usd", "us$", "us $", "$",
    "dol", "en dólares", "en dolares",
    "en dólar", "en dolar", "en usd",
    "en dol", "moneda dol", "moneda usd",
    "moneda dólar", "moneda dolares",
    "divisa", "divisas",
    "billete verde", "greenback",
    # Contexto venezolano
    "dolarizado", "en verde", "precio en dólar",
    "precio en dolar", "monto en dólares", "monto en dolares",
})

MONEDA_VES = frozenset({
    # Bolívares
    "bolívar", "bolivar", "bolívares", "bolivares",
    "ves", "bs", "bs.", "bsf", "bss",
    "en bolívares", "en bolivares",
    "en ves", "en bs", "en bs.",
    "moneda ves", "moneda bolivar", "moneda bolívares",
    "moneda nacional", "moneda local",
    "en moneda nacional", "en moneda local",
    "precio en bolívares", "precio en bolivares",
    "monto en bolívares", "monto en bolivares",
})


# ═══════════════════════════════════════════════════════════════════
# 5. ORGANIZACIONES (Grupo Santoni)
# ═══════════════════════════════════════════════════════════════════

ORGANIZACIONES = frozenset({
    # Nombres completos
    "inproa santoni", "inproa santoni c.a.", "inproa santoni c.a",
    "inproa", "santoni",
    "inpromaiz", "inpro maiz", "inpromaíz", "inpromaiz c.a",
    "inpromaiz c.a.", "inpromaíz c.a",
    "santoni service", "santoni service c.a", "santoni service c.a.",
    "agropecuaria r.r.", "agropecuaria", "agropecuaria rr",
    "aga agrícola", "aga agricola", "aga agrícola c.a", "aga agricola c.a",
    "agroinproa", "agroinproa c.a", "agroinproa c.a.",
    "inversiones aga", "inversiones aga c.a", "inversiones aga c.a.",
    "agro import",
    # Informales
    "la empresa", "la compañía", "la compania",
    "el grupo", "grupo santoni", "grupo empresarial",
    "todas las empresas", "todas las organizaciones",
    "todo el grupo", "consolidado",
    "por empresa", "por organización", "por organizacion",
    "por compañía", "por compania",
    # Planta/Sede
    "planta inproa", "planta inpromaiz", "planta de arroz",
    "planta de maíz", "planta de maiz",
    "sede principal", "sede central",
    "oficina central", "corporativo",
})


# ═══════════════════════════════════════════════════════════════════
# 6. PRODUCTOS COMUNES (categorías genéricas para detección)
# ═══════════════════════════════════════════════════════════════════

PRODUCTOS_ARROZ = frozenset({
    "arroz", "arroz paddy", "arroz acondicionado",
    "arroz blanco", "arroz integral", "arroz premium", "arroz premiun",
    "arroz santoni", "arroz zafiro", "arroz excelente",
    "arroz doña blanca", "arroz dona blanca",
    "arroz saborizado", "arroz con ajo",
    "arroz de segunda", "arroz segunda", "arroz tercerilla",
    "grano entero", "grano a granel",
    "cascarilla de arroz", "cascarilla",
})

PRODUCTOS_MAIZ = frozenset({
    "maíz", "maiz", "maíz blanco", "maiz blanco",
    "harina de maíz", "harina de maiz",
    "harina precocida", "harina masantoni", "masantoni",
    "afrecho de maíz", "afrecho de maiz", "afrecho",
    "germen de maíz", "germen de maiz", "germen",
})

PRODUCTOS_SNACKS = frozenset({
    "choco toni", "chocotoni",
    "chicha toni", "chichatoni",
    "nutri toni", "nutritoni",
    "planet fruit", "planet cronch",
    "space pop", "rocket planet",
    "crema de arroz",
})

PRODUCTOS_EMPAQUES = frozenset({
    "laminado", "laminados", "lamina", "lámina", "láminas", "laminas",
    "empaque", "empaques", "envase", "envases",
    "bolsa", "bolsas", "funda", "fundas",
    "caja", "cajas", "cartón", "carton", "caja de cartón", "caja de carton",
    "fardo", "fardos", "saco", "sacos",
    "cinta adhesiva", "cinta", "cintas",
    "etiqueta", "etiquetas",
    "polietileno", "polipropileno",
    "plástico", "plastico", "plásticos", "plasticos",
})

PRODUCTOS_INSUMOS = frozenset({
    # Químicos/Aditivos
    "azúcar", "azucar", "azúcar refinada", "azucar refinada",
    "sal", "sal marina", "sal fina",
    "cacao", "cacao en polvo", "cacao alcalinizado",
    "vainilla", "sabor vainilla", "esencia",
    "chocolate", "sabor chocolate",
    "caramelo", "sabor caramelo",
    "leche condensada", "sabor leche condensada",
    "malta", "sabor malta",
    "vitamina", "vitaminas", "minerales", "premix", "pmx",
    "carboximetil", "celulosa", "cmc",
    # Agrícolas
    "fertilizante", "fertilizantes", "abono", "abonos",
    "semilla", "semillas", "herbicida", "herbicidas",
    "insecticida", "insecticidas", "fungicida", "fungicidas",
    "pesticida", "pesticidas", "agroquímico", "agroquimico",
    "agroquímicos", "agroquimicos",
    # Combustibles/Servicios
    "gasoil", "diesel", "diésel", "combustible", "combustibles",
    "gas", "gasolina",
    # Repuestos
    "repuesto", "repuestos", "pieza", "piezas",
    "herramienta", "herramientas",
    "cangilón", "cangilon", "cangilones",
    "correa", "correas", "rodamiento", "rodamientos",
    "tornillo", "tornillos", "tuerca", "tuercas",
    "tubería", "tuberia", "tuberías", "tuberias",
    "manguera", "mangueras", "válvula", "valvula",
    "válvulas", "valvulas",
    "motor", "motores", "bomba", "bombas",
    "filtro", "filtros", "aceite", "aceites",
    "lubricante", "lubricantes", "grasa", "grasas",
})


# ═══════════════════════════════════════════════════════════════════
# 7. MODIFICADORES Y CONECTORES
# ═══════════════════════════════════════════════════════════════════

MODIFICADORES_COMPARACION = frozenset({
    "más que", "mas que", "menos que", "mayor que", "menor que",
    "comparado con", "versus", "vs", "contra",
    "diferencia", "variación", "variacion",
    "incremento", "aumento", "crecimiento",
    "disminución", "disminucion", "reducción", "reduccion", "caída", "caida",
    "porcentaje de cambio", "cambio porcentual",
    "año anterior", "ano anterior", "mes anterior",
    "período anterior", "periodo anterior",
    "respecto a", "con respecto a", "en comparación con",
    "en comparacion con",
})

MODIFICADORES_RANKING = frozenset({
    "top", "top 5", "top 10", "top 20", "top 50",
    "ranking", "rank", "posición", "posicion",
    "primero", "primeros", "primera", "primeras",
    "mejor", "mejores", "peor", "peores",
    "mayor", "mayores", "menor", "menores",
    "más alto", "mas alto", "más bajo", "mas bajo",
    "principal", "principales",
    "líder", "lider", "líderes", "lideres",
    "número uno", "numero uno", "#1",
    "los que más", "los que mas", "las que más", "las que mas",
    "quién tiene más", "quien tiene mas",
})

MODIFICADORES_DETALLE = frozenset({
    "detalle", "detalles", "detallado", "detallada",
    "desglose", "desglosado", "desglosada",
    "pormenorizado", "específico", "especifico",
    "completo", "completa", "todo", "todos", "todas",
    "a fondo", "en profundidad", "exhaustivo",
    "línea por línea", "linea por linea",
    "uno por uno", "cada uno", "cada una",
    "incluir", "incluyendo", "con detalle",
})

MODIFICADORES_EXPORTACION = frozenset({
    "exportar", "descargar", "bajar",
    "excel", "csv", "pdf",
    "hoja de cálculo", "hoja de calculo",
    "archivo", "documento", "reporte",
    "imprimir", "impresión", "impresion",
    "enviar por correo", "enviar por email",
    "mandar por correo",
})


# ═══════════════════════════════════════════════════════════════════
# 8. FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════

def matches_any(text: str, keyword_set: frozenset) -> bool:
    """Check if any keyword from the set appears in the text (lowercase)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keyword_set)


def matches_count(text: str, keyword_set: frozenset) -> int:
    """Count how many keywords from the set appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in keyword_set if kw in text_lower)


def best_match(text: str, *keyword_sets: tuple[str, frozenset]) -> str | None:
    """Return the name of the keyword set with the most matches.

    Args:
        text: The user message.
        *keyword_sets: Pairs of (name, frozenset) to check.

    Returns:
        Name of the best matching set, or None if no matches.
    """
    text_lower = text.lower()
    best_name = None
    best_count = 0
    for name, kws in keyword_sets:
        count = sum(1 for kw in kws if kw in text_lower)
        if count > best_count:
            best_count = count
            best_name = name
    return best_name
