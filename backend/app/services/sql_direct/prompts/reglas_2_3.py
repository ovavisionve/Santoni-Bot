"""REGLAs CRÍTICAs #2 y #3: separar facturas/NC, destacar anulatorias."""

REGLA_2_SEPARAR_NC = (
    "🎯 REGLA CRÍTICA #2 — SEPARAR FACTURAS DE NOTAS DE CRÉDITO:\n"
    "Cuando contés documentos en c_invoice, NO agrupes facturas (ARI) con notas "
    "de crédito (ARC) en un solo COUNT. En Santoni, una factura grande puede "
    "ser anulada con una NC del mismo monto (ejemplo real: marzo 2026 tiene una "
    "AR Invoice de USD 9.4M con su correspondiente AR Credit Memo de USD 9.4M "
    "que la anula). Si sumás todo el COUNT, el usuario no se da cuenta que son "
    "cosas distintas. Usá siempre dos contadores:\n"
    "  `COUNT(DISTINCT CASE WHEN dt.docbasetype='ARI' THEN i.c_invoice_id END) AS facturas`\n"
    "  `COUNT(DISTINCT CASE WHEN dt.docbasetype='ARC' THEN i.c_invoice_id END) AS notas_credito`\n"
    "En la respuesta final mostrá ambos por separado. Para montos, usá la "
    "expresión neta (ARI positivo − ARC negativo) en un SUM con CASE como "
    "mostré arriba.\n\n"
)

REGLA_3_ANULATORIAS = (
    "🎯 REGLA CRÍTICA #3 — DESTACAR TRANSACCIONES GRANDES ANULATORIAS:\n"
    "Si el SQL devuelve resultados donde una sola factura (ARI) representa "
    ">20% del total bruto del período Y hay una NC (ARC) del mismo monto "
    "aproximado en el mismo período, probable es una transacción anulada. "
    "No podés detectar esto en el SQL inicial, pero al formatear la respuesta "
    "para el usuario, si ves esa situación, mencionala explícitamente: 'hay "
    "una factura de USD X que parece haber sido anulada con una NC del mismo "
    "monto — el neto del mes sería Y sin considerar esa anulación'.\n\n"
)
