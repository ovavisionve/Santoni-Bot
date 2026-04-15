# Cuestionario de Levantamiento — SantoniBot (Transcripción Literal)

**Fuente:** `docs/CUESTIONARIO DE LEVANTAMIENTO Alimentos santoni.docx`
**Fecha de extracción:** 15/Abr/2026
**Propósito:** Transcripción textual del cuestionario de levantamiento completado
por Santoni al inicio del proyecto. Esta es la **fuente de verdad** sobre
expectativas, usuarios, alcance y preguntas que cada área necesita hacerle al bot.

---

## 1. INFORMACIÓN GENERAL DE LA EMPRESA

### 1.1 Datos generales

- **¿Cuántos empleados tiene actualmente la empresa?** (sin respuesta)
- **¿Cuántas áreas o departamentos existen?** (sin respuesta)
- **¿Cuáles son las ubicaciones físicas de la empresa? (plantas, oficinas, bodegas)**
  → Agua Blanca (2 plantas), Araure (Oficinas Administrativas)
- **¿Cómo funciona la estructura de turnos de trabajo?**
  → Oficina diurno - Planta Rotativo
- **¿Cuál es el horario general de operación?**
  → 7:30am a 5pm

### 1.2 Contactos clave del proyecto

**Sponsor / decisor:**
- Nombre: Graziella Russo
- Cargo: Vicepresidente
- Email: graziella74russo@gmail.com

**Coordinador del proyecto:**
- Nombre: Geovanna Quintero
- Cargo: Consultor iDempiere
- Email: idempiere.santoni@gmail.com

**Contactos técnicos IT:**
- Eduardo Hidalgo — Especialista en soporte — eduardohidalgoq5@gmail.com — 0412-2682934
- Darwin Mendoza — Analista en soporte — mdarwinruben@gmail.com — 0414-5728099

**Responsables por área:**

| Área | Responsables |
|------|--------------|
| Finanzas | Angela Russo / Orlando Artahona |
| Contabilidad | Johan Alvarez |
| Ventas | Carlos Matias / Lenny Silva / Yuleidys Gutierrez |
| RRHH | Emelin Salas / Leonardo Rivero / Daniela López |
| Producción | Mayra Bolivar / Eilen Perez / Elymar Davila |
| Compras de insumos | Onofrio Gueccia / Jorge Chahine |
| Compras a productores | Marlenis Figueredo |

---

## 2. EXPECTATIVAS DEL PROYECTO (MUY IMPORTANTE)

- **¿Cuál es el principal problema que desean resolver con SantoniBot?**
  → Reducción de carga de trabajo, inmediatez de respuesta.
- **¿Qué resultados esperan obtener del sistema?**
  → Que el Bot nos ayude a disminuir el tiempo de respuesta en soluciones
    estratégicas de la empresa.
- **¿Qué áreas consideran más críticas para comenzar la implementación?**
  → **Ventas**
- **¿Tienen preguntas o inquietudes sobre el proyecto?** → No

---

## 3. USUARIOS DEL SISTEMA

### 3.1 Cantidad estimada de usuarios

- Plataforma web: **~10 personas**
- WhatsApp: **~5 personas**

### 3.2 Roles y permisos

| Rol | Consulta | Acceso | Cantidad |
|-----|----------|--------|---------:|
| Finanzas | Todo lo referente a su departamento | Su departamento | 2 |
| Contabilidad | Todo lo referente a su departamento | Su departamento | 2 |
| Recursos Humanos | Todo lo referente a su departamento | Su departamento | 2 |
| Producción | Todo lo referente a su departamento | Su departamento | 2 |
| Compra de Insumos | Todo lo referente a su departamento | Su departamento | 2 |
| Compra Productores | Todo lo referente a su departamento | Su departamento | 2 |

### 3.3 Usuarios piloto (fase de pruebas)

- Johan Alvarez — Contabilidad
- Geovanna Quintero — Sistema
- Graziella Russo
- Lenny Silva — Ventas

---

## 4. CANAL WHATSAPP BUSINESS

- ¿La empresa tiene WhatsApp Business actualmente? **No**
- ¿Estarían dispuestos a crear una cuenta para el proyecto? (sin respuesta)

---

## 5. AGENTES DEL SISTEMA POR ÁREA

### 5.1 Finanzas

- **Responsables:** Angela Russo / Orlando Artahona
- **Sistemas que usan:** iDempiere

**Información a consultar:**
- Flujo de caja
- Cuentas por cobrar / pagar
- Bancos
- Presupuestos
- Indicadores financieros

### 5.2 Contabilidad

- **Responsable:** Johan Alvarez
- **Sistemas usados:** iDempiere

**Preguntas clave:**
1. Mostrar los costos de productos a una fecha determinada
2. Mostrar análisis de las partidas de gastos de fechas determinadas
3. Análisis de impuestos
4. Situación financiera de las empresas del grupo
5. Indicadores financieros

**Información necesaria:**
- Balance general
- Estado de resultados
- Libro diario / mayor
- Impuestos
- Activos fijos

### 5.3 Ventas

- **Responsable:** Lenny Silva
- **Sistemas usados:** iDempiere

**Preguntas clave:**
- Ranking de ventas por zonas, vendedores y tipología del cliente
- Zonas desatendidas
- Paretos de clientes
- Mejores 20 clientes por zona, por categoría, por vendedor y en general
- Activación de cliente
- Apertura de clientes
- Visitas a los clientes
- Ranking de cobranza por zona, vendedores y tipología de clientes
- Detectar cuentas por cobrar más atrasadas
- Cobranza diaria, semanal
- Comparativo de la cobranza vs metas

**Información necesaria:**
- Clientes
- Facturación
- Metas vs ventas
- Productos más vendidos
- Precios y descuentos

### 5.4 Recursos Humanos

- **Responsables:** Daniela López, Emelin Salas, Leonardo Rivero
- **Sistemas usados:** iDempiere + k-asistencia + SPI (solo consulta)

**Preguntas clave:**

**Ítem 1 — Rentabilidad y estructura organizacional**
- **Productividad laboral** (eficiencia con la que el capital humano genera ventas)
- **Factor de costo de compensación** (% del gasto operativo destinado a fuerza laboral)
- **Costo total de la rotación** (Costo de salida + reclutamiento + capacitación)

**Ítem 2 — Adquisición de talentos (reclutamiento)**
- Calidad de contratación
- Tasa de aceptación de ofertas
- Tiempo de cobertura

**Ítem 3 — Gestión y retención**
- Índice de rotación voluntaria (talento crítico)
- Tasa de ausentismo (ausencias, reposos, permisos, faltas y atrasos) con motivos

**Información necesaria:**
- Nómina
- Vacaciones
- Asistencia
- Datos de empleados
- Evaluaciones
- Garantía de prestaciones sociales
- Provisiones mensuales de pasivos laborales
- Liquidación de prestaciones sociales (finiquito)
- Asistencias de trabajadores
- Cumpleañeros
- Tiempos de servicio
- Evaluaciones de desempeño
- Gestión de beneficios laborales

**Información sensible de RRHH:**
> Toda la información salarial y laboral de los trabajadores es altamente
> confidencial, así como los datos de biométricos de asistencia, detalles
> de nómina, cuentas bancarias.

### 5.5 Producción

**Responsables:**
- Gerente General: Mayra Bolivar
- Coordinador de Molino: Jorge Galíndez
- Coordinador de Empaque Arroz Blanco: Jocsan Castro
- Coordinador de Extrusora de Cereales: Jhoan Paredes

**Sistemas usados:**
1. Registro de producción: **iDempiere**
2. Control de proceso: Software **GARTEN**

**Información necesaria:**

**1. Producción diaria — capacidad instalada de procesamiento de materia prima:**
- Molino 1: **4.000 TM/Mes en 2 turnos**
- Molino 2: **5.000 TM/Mes en 2 turnos**
- Total Procesamiento/día: **~400 TM**

**2. Órdenes de producción:**
- Se generan en base a la planificación mensual

**3. Eficiencia (OEE):**
- Sistema de control deficiente para medir la eficiencia de los equipos

**4. Desperdicios:**
- Extrusora de cereales: registros en Excel, no automatizado
- Empaque: desperdicios en material de empaque contabilizados manualmente

**5. Mantenimientos:**
- Se registra en iDempiere: preventivos, correctivos y predictivos

**Expectativa de reportes con IA (Mayra Bolivar):**
> Me gustaría generar reportes con información en cuanto a inventario
> inicial de mes tanto de materia prima como de producto en proceso y
> producto terminado, recepción y procesamiento del mes, producción,
> despacho del mes y pedidos en cola pendientes por despachar, existencia
> de producto disponible en almacén, rendimiento de materia prima. Entre
> otras.

### 5.6 Compras de insumos

- **Responsables:** Onofrio Gueccia / Jorge Chahine
- **Sistemas usados:** iDempiere

**Información necesaria:**

**Órdenes de compra y proveedores:**
- Filtrar cada insumo y reflejar los proveedores que distribuyen/fabrican cada uno
- Indicar métodos de pago que maneja cada proveedor

**Inventarios:**
- Inventario a la fecha de todos los insumos
- Máximo y mínimo que debe tener cada insumo
- **Alertar cuando un insumo esté en su límite mínimo**
- Insumos con mayor rotación en el último trimestre
- Según stock, para cuántos días de producción alcanza

**Precios históricos:**
- Precio de las últimas 6 compras de cada insumo

**Tiempos de entrega:**
- Análisis de cada proveedor con tiempo de entrega
- Si realiza despacho hasta almacenes de Santoni

**¿Qué consideran insumos?**
> Todo aquello que tenga contacto o esté involucrado de manera directa
> con el producto final:
>
> - Material de empaque primario y secundario
> - Azúcar
> - Harina de avena
> - Gritz de maíz
> - Leche entera en polvo
> - Almidón de maíz
> - Cacao alcalinizado
> - Sal
> - Premezclas
> - Glutamato
> - CMC
> - Grasa vegetal
> - Lecitina de soja
> - Glucosa
> - Extracto de malta
> - Aromas
> - Sabores
> - Colorantes
> - Cajas de cartón
> - Sacos

### 5.7 Compras a productores

- **Responsable:** Marleny Figueredo
- **Sistemas usados:** iDempiere

**Preguntas clave:**
- ¿Cuánto es la compra de arroz paddy húmedo en el año 2025?
- ¿Cuánto es la compra de maíz en el año 2025?

**Información necesaria:**
- **Productores registrados:**
  - Arroz: **1.679**
  - Maíz: **168**
- Compras por volumen
- Precios por kilo / tonelada
- Pagos pendientes
- **Ubicación productores:** Apure, Lara, Barinas, Portuguesa, Cojedes
- **Productos que se compran:** Arroz, Maíz

---

## 6. DISPONIBILIDAD DEL EQUIPO

(Sin respuestas completadas en el cuestionario original — horas semanales
por jefe de área y horario preferido para reuniones vacíos.)

---

## 7. DOMINIO WEB

- ¿Tienen dominio propio para el sistema? → No
- Tienen dominio público: **alimentossantoni.com**
- (Subdominio sugerido: sin respuesta)

---

## 8. SEGURIDAD Y RESTRICCIONES

**Políticas de seguridad informática:**
- Principio de Privilegio Mínimo
- Rotación de Credenciales
- Segmentación de Red (VLANs)
- Uso de VPN
- Filtrado de contenido
- Prohibición de instalación de software no autorizado
- Copias de Seguridad (Backup)

**Información confidencial marcada:**
- Datos financieros
- Salarios
- Costos de producción
- Precios de venta
- Proveedores/productores
- Procesos productivos
- **Otros: Todo**

---

## 9. DOCUMENTACIÓN EXISTENTE

(Casillas del cuestionario no marcadas — manuales de sistemas, diagramas
de red, esquemas de BD, documentación API, políticas IT, manuales de
procesos, organigrama.)

---

## 10. INFRAESTRUCTURA TECNOLÓGICA

**Sistemas actuales:** ERP iDempiere.

**Servidores propios:** Sí
- Sistema operativo: **VMware**
- Capacidad: **2 TB free**
- UPS / planta eléctrica: 2 UPS de 3.000 kVA cada uno
- Sala de servidores: Sí

**Conectividad:**
- Proveedor internet: **CANTV**
- Velocidad: **100 Mb dedicado**
- IP pública: **201.249.56.144/29**
- VPN corporativa: **Sí, FortiClient**
- Firewall: **Sí, Fortigate 100F**

---

## 11. BASES DE DATOS Y ACCESOS

**Base de datos existente:**
- Tipo: **PostgreSQL 13**
- Host: **192.168.1.73**
- Puerto: **5432**

**APIs disponibles:**
- Por ahora se está evaluando una API para la nueva aplicación de ventas.

**Archivos Excel/CSV:**
> No manejamos ningún Excel oficial, de hecho no nos gusta nada que sea
> en Excel, todo debe salir de un reporte por el iDempiere.

---

## Notas para el equipo SantoniBot

1. **Prioridad #1 declarada por el cliente:** VENTAS (sección 2).
2. **Canal inicial:** plataforma web (~10 usuarios). WhatsApp es Fase 2.
3. **Confidencialidad extrema:** RRHH (salarios, biométricos, nómina,
   cuentas bancarias) y "todo" marcado como confidencial.
4. **Fuente única de datos:** iDempiere PostgreSQL 13 — no hay Excel ni
   otras fuentes para el bot.
5. **Infraestructura ya existe:** VPN FortiClient, IP pública, VLANs.
   No hay que desplegar nada adicional a nivel de red.
6. **Expectativas de reportes (Mayra Bolivar — Producción)** son el
   backlog natural Fase 2 para el agente de Producción: inventario
   inicial, recepción, procesamiento, despachos, pedidos en cola.
7. **Datos de referencia confirmados:**
   - 1.679 productores de arroz / 168 productores de maíz
   - Capacidad Molino 1: 4.000 TM/mes, Molino 2: 5.000 TM/mes
   - ~400 TM/día procesamiento total
