# Manual de Usuario - SantoniBot

## Sistema Inteligente de Analisis de Datos Empresariales

**Alimentos Santoni, C.A.**

**Version:** 1.0
**Fecha:** Febrero 2026
**Desarrollado por:** OVA Agency
**Confidencial - Uso interno exclusivo**

---

## Tabla de Contenido

1. [Introduccion](#1-introduccion)
2. [Acceso al Sistema](#2-acceso-al-sistema)
3. [Interfaz del Chat](#3-interfaz-del-chat)
4. [Agentes Especializados](#4-agentes-especializados)
5. [Roles y Permisos](#5-roles-y-permisos)
6. [Panel de Administracion](#6-panel-de-administracion)
7. [Dashboard de KPIs](#7-dashboard-de-kpis)
8. [Alertas y Reportes](#8-alertas-y-reportes)
9. [Exportacion de Datos](#9-exportacion-de-datos)
10. [Seguridad](#10-seguridad)
11. [Preguntas Frecuentes (FAQ)](#11-preguntas-frecuentes-faq)
12. [Glosario](#12-glosario)
13. [Contacto y Soporte](#13-contacto-y-soporte)

---

# 1. Introduccion

## 1.1 Que es SantoniBot

SantoniBot es el **Sistema Inteligente de Analisis de Datos Empresariales** desarrollado exclusivamente para **Alimentos Santoni, C.A.** Se trata de un asistente conversacional impulsado por inteligencia artificial que permite a los usuarios de la empresa consultar informacion operativa, financiera y administrativa de forma rapida, segura y en lenguaje natural.

En lugar de generar reportes manuales, navegar por multiples pantallas del ERP o solicitar informacion a otros departamentos, los usuarios simplemente escriben una pregunta en el chat y SantoniBot responde con datos actualizados en tiempo real.

## 1.2 Para quien esta disenado

SantoniBot esta disenado para los siguientes perfiles dentro de Alimentos Santoni:

| Perfil | Uso Principal |
|--------|--------------|
| **Gerencia General** | Vision integral de la empresa, KPIs, indicadores clave |
| **Gerentes de Departamento** | Consultas especializadas de su area |
| **Supervisores** | Monitoreo de operaciones y seguimiento de metas |
| **Vendedores** | Consulta de sus propias ventas, cobranzas y clientes |
| **Equipo de TI** | Administracion del sistema, gestion de usuarios y seguridad |
| **Equipo Contable/Financiero** | Balances, estados de resultados, flujo de caja |
| **Produccion** | Eficiencia de planta, desperdicios, produccion diaria |
| **Compras** | Ordenes de compra, proveedores, compras a productores |

## 1.3 Fuente de datos

**Todos los datos que presenta SantoniBot provienen directamente del sistema ERP iDempiere** de Alimentos Santoni. No se utilizan hojas de calculo, archivos Excel ni fuentes externas. La informacion se consulta en tiempo real contra la base de datos PostgreSQL del ERP ubicada en la red interna de la empresa.

Esto garantiza que:
- Los datos estan siempre actualizados
- No hay duplicacion ni inconsistencia de informacion
- Se respetan los permisos y la segregacion por departamento
- Existe trazabilidad completa de las consultas

## 1.4 Arquitectura del sistema

SantoniBot utiliza una arquitectura de **multi-agentes especializados**. Cuenta con un **Orquestador** central que analiza cada consulta del usuario y la dirige automaticamente al agente especializado correspondiente. El sistema cuenta con **7 agentes departamentales**, cada uno experto en su area.

```
Usuario → Chat → Orquestador → Agente Especializado → Base de Datos iDempiere → Respuesta
```

El proceso es el siguiente:
1. El usuario escribe una pregunta en lenguaje natural
2. El Orquestador clasifica la consulta por palabras clave (clasificacion instantanea)
3. Se verifica que el usuario tenga permisos para ese departamento
4. El agente especializado genera una consulta SQL al ERP
5. Se obtienen los datos y se formatean en una respuesta clara
6. La respuesta se transmite al usuario en tiempo real (streaming)

## 1.5 Beneficios para la empresa

La implementacion de SantoniBot aporta los siguientes beneficios a Alimentos Santoni:

| Beneficio | Descripcion |
|-----------|-------------|
| **Ahorro de tiempo** | Consultas que antes requerían generar reportes manuales en iDempiere ahora se resuelven en segundos |
| **Democratizacion de la informacion** | Personal sin conocimientos tecnicos puede acceder a datos complejos con preguntas simples |
| **Toma de decisiones agil** | Informacion en tiempo real para decisiones oportunas |
| **Control y seguridad** | Registro de auditoria completo y acceso controlado por departamento |
| **Reduccion de errores** | Eliminacion de transcripcion manual y copias de datos entre sistemas |
| **Disponibilidad** | Acceso a la informacion desde cualquier dispositivo con navegador web |
| **Estandarizacion** | Respuestas consistentes y formateadas profesionalmente |

## 1.6 Caracteristicas principales

- **Consultas en lenguaje natural:** No requiere conocimientos tecnicos
- **Respuestas en tiempo real:** Datos directos del ERP, siempre actualizados
- **7 agentes especializados:** Un experto para cada area de la empresa
- **Streaming de respuestas:** Las respuestas aparecen progresivamente, sin esperas
- **Graficas automaticas:** Las tablas de datos se pueden visualizar como graficas
- **Exportacion multiple:** Descarga en CSV, Excel, PDF y Word
- **Adjuntar documentos:** Sube archivos para analisis con IA
- **Seguridad empresarial:** 2FA, bloqueo de cuentas, auditoria completa
- **Control de acceso por departamento:** Cada usuario ve solo la informacion de su area
- **Historial de conversaciones:** Todas las consultas se guardan para referencia

## 1.7 Que NO es SantoniBot

Es importante comprender las limitaciones del sistema:

- **No es un reemplazo del ERP:** SantoniBot consulta datos de iDempiere pero no modifica ni ingresa datos en el ERP
- **No realiza transacciones:** No puede crear facturas, ordenes de compra ni registros contables
- **No es infalible:** Como todo sistema basado en IA, puede ocasionalmente generar interpretaciones imprecisas. Siempre verifique datos criticos
- **No trabaja con datos externos:** Solo consulta la base de datos de iDempiere. No procesa datos de otros sistemas ni de internet
- **No es un sistema de mensajeria:** No permite comunicacion entre usuarios. Es un asistente de consulta individual

---

# 2. Acceso al Sistema

## 2.1 URL del sistema

SantoniBot se accede a traves del navegador web. La URL de acceso es proporcionada por el equipo de TI de Alimentos Santoni. El sistema es compatible con los siguientes navegadores:

| Navegador | Version Minima |
|-----------|---------------|
| Google Chrome | 90+ |
| Mozilla Firefox | 90+ |
| Microsoft Edge | 90+ |
| Safari | 15+ |

Se recomienda utilizar **Google Chrome** en su version mas reciente para la mejor experiencia.

## 2.2 Pantalla de inicio de sesion

Al acceder a la URL del sistema, se presenta la pantalla de inicio de sesion con los siguientes elementos:

- **Logo de SantoniBot** en la parte superior
- **Campo de usuario:** Ingrese su nombre de usuario asignado
- **Campo de contrasena:** Ingrese su contrasena
- **Boton "Iniciar Sesion":** Para acceder al sistema
- **Boton de visibilidad:** Icono de ojo para mostrar/ocultar la contrasena

### Pasos para iniciar sesion:

1. Abra su navegador web y navegue a la URL del sistema
2. En el campo **"Usuario"**, ingrese su nombre de usuario (por ejemplo: `jperez`)
3. En el campo **"Contrasena"**, ingrese su contrasena
4. Haga clic en el boton **"Iniciar Sesion"**
5. Si tiene 2FA activado, se le solicitara el codigo de 6 digitos de su aplicacion autenticadora

## 2.3 Verificacion en dos pasos (2FA)

Si su cuenta tiene habilitada la autenticacion de dos factores (2FA), despues de ingresar usuario y contrasena correctos, el sistema le mostrara una segunda pantalla solicitando:

- **Codigo de verificacion:** Un numero de 6 digitos generado por su aplicacion Google Authenticator (o compatible)

### Pasos con 2FA:

1. Ingrese usuario y contrasena normalmente
2. El sistema mostrara la pantalla de **"Verificacion en dos pasos"**
3. Abra la aplicacion **Google Authenticator** en su telefono
4. Busque la entrada **"SantoniBot"**
5. Ingrese los 6 digitos que aparecen en la aplicacion
6. Haga clic en **"Verificar"**

> **Nota:** El codigo cambia cada 30 segundos. Si el codigo expira mientras lo ingresa, espere a que se genere uno nuevo.

Si necesita volver a la pantalla de credenciales, haga clic en **"Volver al inicio de sesion"**.

## 2.4 Primer ingreso

Cuando un administrador crea su cuenta por primera vez, le proporcionara:

- Nombre de usuario
- Contrasena temporal
- Departamento asignado
- Rol asignado

**Se recomienda fuertemente** cambiar la contrasena temporal por una contrasena personal segura inmediatamente despues del primer ingreso. Consulte la seccion [10. Seguridad](#10-seguridad) para los requisitos de contrasena.

## 2.5 Mensajes de error comunes en el login

| Mensaje | Causa | Solucion |
|---------|-------|----------|
| "Credenciales incorrectas" | Usuario o contrasena mal escritos | Verifique los datos e intente de nuevo |
| "Cuenta bloqueada por demasiados intentos fallidos. Intente en X minutos..." | 5 intentos fallidos consecutivos | Espere el tiempo indicado o contacte al administrador para desbloqueo |
| "Codigo de verificacion incorrecto" | El codigo 2FA ingresado es invalido | Verifique el codigo en Google Authenticator y reintente |
| "No autorizado" | Token de sesion expirado | Vuelva a iniciar sesion |

## 2.6 Cierre de sesion

Para cerrar su sesion de forma segura:

1. Ubique la parte inferior de la barra lateral izquierda
2. Haga clic en el icono de **"Cerrar sesion"** (icono de flecha de salida)
3. Sera redirigido a la pantalla de inicio de sesion

### Cierre de sesion automatico por inactividad

Por seguridad, el sistema cierra automaticamente la sesion despues de **30 minutos de inactividad**. Cinco minutos antes del cierre automatico, aparecera un **banner amarillo** en la parte superior de la pantalla con el mensaje:

> "Tu sesion se cerrara en 5 minutos por inactividad."

Para evitar el cierre, haga clic en el boton **"Continuar sesion"** que aparece en el banner, o simplemente interactue con el sistema (mover el mouse, escribir, hacer clic).

---

# 3. Interfaz del Chat

## 3.1 Estructura general de la pantalla

La interfaz principal de SantoniBot se divide en dos secciones:

### Barra lateral izquierda (Sidebar)

La barra lateral contiene:

- **Logo y nombre** del sistema ("SantoniBot")
- **Boton "Nueva conversacion":** Inicia un nuevo chat
- **Barra de busqueda:** Para buscar entre sus conversaciones anteriores
- **Lista de conversaciones:** Historial de todas sus consultas previas, ordenadas por fecha
- **Enlace a Administracion:** Solo visible para usuarios con rol Administrador
- **Informacion del usuario:** Su nombre, departamento asignado y boton de cerrar sesion

Cada conversacion en la lista muestra:
- Titulo (generado automaticamente desde su primera pregunta)
- Hora relativa de la ultima actividad (ej: "hace 5m", "ayer", "3d")
- Vista previa del ultimo mensaje
- Boton para eliminar la conversacion (visible al pasar el mouse)

### Area principal de chat

El area de chat contiene:

- **Encabezado:** Logo de Santoni y nombre del sistema
- **Area de mensajes:** Donde aparecen sus consultas y las respuestas del sistema
- **Campo de entrada:** Donde escribe sus preguntas
- **Boton de adjuntar:** Para subir documentos
- **Boton de enviar:** Para enviar la consulta

## 3.2 Pantalla de bienvenida

Al iniciar una nueva conversacion, el sistema muestra una pantalla de bienvenida con:

- Logo de Alimentos Santoni
- Mensaje: **"Bienvenido a SantoniBot"**
- Texto: "Haz una consulta sobre tu departamento. Estas son algunas sugerencias:"
- **4 sugerencias rapidas** personalizadas segun su departamento

Las sugerencias son botones que, al hacer clic, colocan la consulta en el campo de texto para que pueda enviarla directamente.

## 3.3 Sugerencias por departamento

Las sugerencias que aparecen en la pantalla de bienvenida dependen del departamento asignado al usuario:

### Finanzas
- "Cual es el flujo de caja del mes?"
- "Muestrame las cuentas por cobrar vencidas"
- "Cual es el saldo de bancos hoy?"
- "Resumen de cuentas por pagar"

### Contabilidad
- "Muestrame el balance general actualizado"
- "Cual es el estado de resultados del mes?"
- "Resumen del libro mayor"
- "Balance de comprobacion actualizado"

### Ventas
- "Cuales son los top 20 clientes por ventas?"
- "Resumen de ventas del mes por zona"
- "Cuanto se ha cobrado esta semana?"
- "Ranking de vendedores del mes"

### RRHH
- "Cuantos empleados hay por departamento?"
- "Resumen de nomina del mes"
- "Quienes tienen asistencia pendiente?"
- "Reporte de vacaciones pendientes"

### Produccion
- "Cual es la produccion de hoy?"
- "Muestrame la eficiencia de la linea"
- "Cuanto desperdicio hubo esta semana?"
- "Resumen de produccion mensual"

### Compras de Insumos
- "Cuanto se compro de insumos este mes?"
- "Ordenes de compra pendientes"
- "Top proveedores por monto de compra"
- "Resumen de compras de la semana"

### Compras a Productores
- "Cuanto es la compra de arroz paddy este ano?"
- "Compras de maiz del mes actual"
- "Top productores por volumen"
- "Resumen de compras a productores"

### Sugerencias por defecto
Si el usuario no tiene un departamento con sugerencias especificas, se muestran las siguientes consultas generales:
- "Cuales son los top 20 clientes por ventas?"
- "Cuanto es la compra de arroz paddy este ano?"
- "Muestrame el flujo de caja del mes"
- "Cuantos empleados hay por departamento?"

## 3.4 Como enviar una consulta

### Envio basico

1. Escriba su consulta en el campo de texto en la parte inferior de la pantalla
2. Presione **Enter** para enviar, o haga clic en el boton de enviar (icono de flecha)
3. La respuesta aparecera progresivamente en el chat (streaming)

### Teclas de acceso rapido

| Tecla | Accion |
|-------|--------|
| `Enter` | Enviar el mensaje |
| `Shift + Enter` | Insertar una nueva linea (sin enviar) |

### Limite de caracteres

Cada mensaje puede contener hasta **2.000 caracteres**. Un contador aparece en la esquina inferior derecha del campo de texto cuando comienza a escribir:

- **Color gris:** Menos del 80% del limite
- **Color ambar:** Entre el 80% y 95% del limite
- **Color rojo:** Mas del 95% del limite

## 3.5 Indicador de procesamiento

Mientras el sistema procesa su consulta, aparece un indicador visual con:
- Tres puntos animados en secuencia
- Texto: "Procesando consulta..."

En el modo de streaming (consultas de texto sin archivos), la respuesta comienza a aparecer inmediatamente palabra por palabra, sin necesidad de esperar a que se complete toda la respuesta.

## 3.6 Adjuntar documentos

SantoniBot permite adjuntar archivos para analisis con inteligencia artificial. Para adjuntar un documento:

1. Haga clic en el **icono del clip** (a la izquierda del campo de texto)
2. Seleccione el archivo desde su computador
3. El nombre del archivo aparecera sobre el campo de texto con un boton para quitarlo
4. Escriba su consulta sobre el documento (ej: "Analiza este documento")
5. Presione Enter para enviar

### Formatos soportados

| Tipo | Extensiones |
|------|------------|
| Documentos | `.pdf`, `.doc`, `.docx`, `.txt` |
| Hojas de calculo | `.xlsx`, `.xls`, `.csv` |
| Imagenes | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |

### Restricciones

- **Tamano maximo:** 10 MB por archivo
- **Analisis de imagenes:** Requiere la API de Claude (Anthropic) activa. Si no esta disponible, se informara al usuario
- **Documentos de texto:** Se pueden analizar con el motor Groq como alternativa

### Ejemplo de uso

> **Usuario:** [adjunta factura.pdf] "Resume los montos de esta factura"
>
> **SantoniBot:** "He analizado la factura adjunta. Los montos principales son: [tabla con detalle]"

## 3.7 Formato de las respuestas

Las respuestas del sistema se presentan en formato enriquecido (Markdown), que incluye:

- **Texto con formato:** Negrita, cursiva, listas
- **Tablas de datos:** Con encabezados, filas y formato visual profesional
- **Indicador de agente:** Cada respuesta muestra que agente la genero (ej: "Agente de Ventas")
- **Marca de tiempo:** Hora relativa de la respuesta (ej: "hace 2 min", "ahora")

### Acciones sobre las respuestas

Cada respuesta del asistente incluye las siguientes acciones:

| Accion | Icono | Descripcion |
|--------|-------|-------------|
| **Copiar** | Icono de copiar | Copia todo el texto de la respuesta al portapapeles |
| **Ver como grafica** | Icono de grafico de barras | Genera una grafica automatica de los datos de la tabla |
| **Exportar CSV** | Icono de tabla | Descarga los datos en formato CSV |
| **Exportar Excel** | Icono de hoja de calculo | Descarga los datos en formato Excel (.xlsx) |
| **Exportar PDF** | Icono de documento | Descarga un reporte en formato PDF |
| **Exportar Word** | Icono de tipo de archivo | Descarga un reporte en formato Word (.docx) |

> **Nota:** Los botones de exportacion y grafica solo aparecen cuando la respuesta contiene una tabla de datos.

## 3.8 Graficas automaticas

Cuando la respuesta del sistema contiene una tabla de datos con al menos 3 filas y al menos una columna numerica, se habilita automaticamente la opcion de **ver como grafica**.

### Tipos de graficas

El sistema detecta automaticamente el tipo de grafica mas adecuado:

| Tipo | Cuando se usa | Ejemplo |
|------|--------------|---------|
| **Barras** | Comparaciones entre categorias | Top 10 clientes por ventas |
| **Lineas** | Series temporales | Ventas mensuales del ano |
| **Area** | Tendencias acumulativas | Flujo de caja semanal |
| **Torta** | Distribucion porcentual | Ventas por zona |

### Exportar graficas

Cada grafica incluye un boton **"PNG"** que permite descargar la grafica como imagen de alta resolucion para uso en presentaciones o informes.

### Formato de numeros

Las graficas respetan el formato venezolano de numeros:
- **Separador de miles:** punto (ej: 1.234.567)
- **Separador decimal:** coma (ej: 1.234,56)
- **Moneda:** Bs. (bolivares)

## 3.9 Historial de conversaciones

Todas las conversaciones se guardan automaticamente. Para acceder a una conversacion anterior:

1. Ubique la **barra lateral izquierda**
2. Desplacese por la lista de conversaciones o use la **barra de busqueda**
3. Haga clic en la conversacion que desea revisar
4. Los mensajes anteriores se cargaran en el area de chat

### Buscar conversaciones

1. Haga clic en la **barra de busqueda** en la parte superior de la lista
2. Escriba una palabra clave del tema que busca
3. La lista se filtrara mostrando solo las conversaciones que coinciden

### Eliminar conversaciones

1. Pase el mouse sobre la conversacion que desea eliminar
2. Aparecera un **icono de papelera** a la derecha
3. Haga clic en el icono
4. La conversacion sera eliminada permanentemente

### Nueva conversacion

Para iniciar una conversacion nueva sin contexto previo:
1. Haga clic en el boton **"Nueva conversacion"** en la parte superior de la barra lateral
2. El area de chat se limpiara y mostrara la pantalla de bienvenida con sugerencias

---

# 4. Agentes Especializados

SantoniBot cuenta con **7 agentes departamentales** especializados, cada uno con conocimiento profundo de su area. El sistema dirige automaticamente cada consulta al agente correspondiente basandose en las palabras clave de la pregunta.

## 4.1 Agente de Finanzas

**Identificador interno:** `finanzas`
**Especialidad:** Analisis financiero empresarial

### Capacidades

- Flujo de caja y posicion de tesoreria
- Cuentas por cobrar y cuentas por pagar
- Estado de cuentas bancarias
- Indicadores financieros (liquidez, rentabilidad)
- Alertas de morosidad y vencimientos
- Presupuestos y comparativos

### Palabras clave que activan este agente

`finanza`, `financiero`, `financiera`, `flujo de caja`, `banco`, `bancos`, `saldo bancario`, `saldos`, `cuenta por pagar`, `cuentas por pagar`, `presupuesto`, `rentabilidad`, `liquidez`, `estado de flujo`, `indicador financiero`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cual es el flujo de caja del mes?" | Tabla con ingresos, egresos y saldo neto del mes actual |
| "Muestrame las cuentas por cobrar vencidas" | Tabla con clientes morosos, monto adeudado y dias de atraso |
| "Cual es el saldo de bancos hoy?" | Detalle de saldos por cada cuenta bancaria |
| "Resumen de cuentas por pagar" | Listado de obligaciones pendientes con proveedores |
| "Cuales son los indicadores de liquidez?" | Ratios financieros calculados a partir de los estados contables |
| "Comparativo de flujo de caja enero vs febrero" | Tabla comparativa mes a mes |
| "Cuanto debemos a proveedores este mes?" | Resumen de cuentas por pagar con detalle |

### Formato de respuesta

Las respuestas del agente financiero utilizan:
- Formato de moneda con simbolo **Bs.** o **$** segun corresponda
- Separadores de miles (formato venezolano)
- Indicacion clara del periodo consultado
- Alertas resaltadas para cuentas vencidas o indicadores criticos

---

## 4.2 Agente de Contabilidad

**Identificador interno:** `contabilidad`
**Especialidad:** Informacion contable y tributaria

### Capacidades

- Balance general actualizado
- Estado de resultados (Ganancias y Perdidas)
- Balance de comprobacion
- Libro diario y libro mayor
- Impuestos (IVA, ISLR, retenciones)
- Activos fijos y depreciacion
- Asientos contables y plan de cuentas

### Palabras clave que activan este agente

`contab`, `balance general`, `balance de comprobacion`, `estado de resultado`, `libro diario`, `libro mayor`, `impuesto`, `iva`, `islr`, `retencion`, `retencion`, `activo fijo`, `activos fijos`, `depreciacion`, `depreciacion`, `asiento contable`, `plan de cuenta`, `partida`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Muestrame el balance general actualizado" | Tabla con activos, pasivos y patrimonio |
| "Cual es el estado de resultados del mes?" | Ingresos, costos, gastos y utilidad neta |
| "Resumen del libro mayor" | Movimientos por cuenta contable |
| "Balance de comprobacion actualizado" | Sumas y saldos por cuenta |
| "Cuanto hemos pagado de IVA este trimestre?" | Resumen de impuestos pagados |
| "Detalle de activos fijos y su depreciacion" | Tabla con activos, valor, depreciacion acumulada |
| "Asientos contables del dia de hoy" | Listado de registros contables del dia |

---

## 4.3 Agente de Ventas

**Identificador interno:** `ventas`
**Especialidad:** Analisis comercial y gestion de ventas

Este es el **agente mas utilizado** del sistema, diserado para cubrir toda la gestion comercial de la empresa.

### Capacidades

1. Ranking de ventas por zonas, vendedores y tipologia del cliente
2. Identificacion de zonas desatendidas
3. Paretos de clientes (analisis 80/20)
4. Top 20 mejores clientes por zona, categoria, vendedor y general
5. Activacion y apertura de clientes
6. Ranking de cobranza por zona, vendedores y tipologia
7. Deteccion de cuentas por cobrar mas atrasadas
8. Cobranza diaria/semanal y comparativo vs metas

### Palabras clave que activan este agente

`venta`, `ventas`, `vendedor`, `vendedores`, `cliente`, `clientes`, `factura`, `facturacion`, `cobranza`, `cobro`, `cobrar`, `recaudacion`, `zona`, `zonas`, `ranking`, `pareto`, `top clientes`, `top 10`, `top 20`, `top 5`, `mejores clientes`, `metas de venta`, `cotizacion`, `moroso`, `morosos`, `deuda`, `deudas`, `vencido`, `vencida`, `pendiente de cobro`, `cuentas por cobrar`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cuales son los top 20 clientes por ventas?" | Ranking con posicion, nombre del cliente y monto total |
| "Resumen de ventas del mes por zona" | Tabla con zona, monto de ventas y porcentaje |
| "Cuanto se ha cobrado esta semana?" | Resumen de recaudacion con detalle por dia |
| "Ranking de vendedores del mes" | Posicion, nombre del vendedor, ventas y meta |
| "Clientes morosos con mas de 30 dias de atraso" | Tabla con cliente, monto adeudado y dias de atraso |
| "Ventas del ano por mes" | Tabla mensual con grafica de lineas |
| "Pareto de clientes - 80/20" | Analisis de concentracion de ventas |
| "Comparativo de ventas enero vs diciembre" | Tabla comparativa con variacion |
| "Cuantos clientes nuevos se abrieron este mes?" | Conteo y listado de clientes nuevos |
| "Metas de venta vs real por vendedor" | Tabla con meta, real y cumplimiento (%) |

### Nota para vendedores

Los usuarios con rol **Vendedor** solo pueden ver informacion de sus propias ventas y clientes. El sistema filtra automaticamente los datos usando su identificador de vendedor en iDempiere.

---

## 4.4 Agente de RRHH (Recursos Humanos)

**Identificador interno:** `rrhh`
**Especialidad:** Gestion de personal y nomina

### Capacidades

- Informacion de empleados por departamento
- Resumen de nomina
- Control de asistencia e inasistencias
- Vacaciones pendientes y programadas
- Evaluaciones de desempeno
- Cumpleanos de empleados
- Contratos y liquidaciones
- Prestaciones sociales

### Palabras clave que activan este agente

`nomina`, `nomina`, `empleado`, `empleados`, `personal`, `vacacion`, `vacaciones`, `asistencia`, `inasistencia`, `evaluacion`, `evaluacion`, `cumpleano`, `cumpleanos`, `salario`, `sueldo`, `recurso humano`, `recursos humanos`, `rrhh`, `talento humano`, `contrato`, `liquidacion`, `liquidacion`, `prestacion`, `prestacion`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cuantos empleados hay por departamento?" | Tabla con departamento, cantidad de empleados y porcentaje |
| "Resumen de nomina del mes" | Detalle de nomina con conceptos, asignaciones y deducciones |
| "Quienes tienen asistencia pendiente?" | Listado de empleados con inasistencias sin justificar |
| "Reporte de vacaciones pendientes" | Tabla con empleado, dias acumulados y dias disfrutados |
| "Cumpleanos del mes" | Listado de empleados que cumplen anos este mes |
| "Cual es el costo total de nomina mensual?" | Resumen con total de asignaciones y deducciones |
| "Empleados contratados en los ultimos 3 meses" | Listado de nuevos ingresos |

---

## 4.5 Agente de Produccion

**Identificador interno:** `produccion`
**Especialidad:** Produccion industrial, eficiencia y control de calidad

### Capacidades

- Produccion diaria y mensual
- Eficiencia de lineas de produccion (OEE)
- Control de desperdicios y merma
- Ordenes de produccion
- Mantenimiento de equipos
- Turnos y lotes de produccion
- Producto terminado y envasado

### Palabras clave que activan este agente

`produccion`, `produccion`, `producir`, `planta`, `eficiencia`, `oee`, `desperdicio`, `merma`, `mantenimiento`, `turno`, `turnos`, `lote`, `lotes`, `orden de produccion`, `orden de produccion`, `producto terminado`, `empaque`, `envasado`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cual es la produccion de hoy?" | Detalle de produccion del dia con unidades por linea |
| "Muestrame la eficiencia de la linea" | Indicadores OEE con disponibilidad, rendimiento y calidad |
| "Cuanto desperdicio hubo esta semana?" | Tabla con tipo de desperdicio, cantidad y porcentaje |
| "Resumen de produccion mensual" | Tabla con produccion diaria acumulada del mes |
| "Ordenes de produccion pendientes" | Listado de ordenes con producto, cantidad y fecha programada |
| "Cual es el lote de produccion actual?" | Informacion del lote en proceso |
| "Comparativo de produccion este mes vs el anterior" | Tabla comparativa con variacion |

---

## 4.6 Agente de Compras de Insumos

**Identificador interno:** `compras_insumos`
**Especialidad:** Gestion de compras de materiales e insumos

### Capacidades

- Ordenes de compra a proveedores
- Inventario de materiales
- Ranking de proveedores
- Tiempos de entrega
- Resumen de compras por periodo
- Suministros y materias primas

### Palabras clave que activan este agente

`insumo`, `proveedor`, `proveedores`, `orden de compra`, `ordenes de compra`, `inventario de material`, `material`, `compra de insumo`, `compras insumo`, `suministro`, `tiempo de entrega`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cuanto se compro de insumos este mes?" | Resumen de compras con total y detalle por categoria |
| "Ordenes de compra pendientes" | Listado de ordenes pendientes con proveedor y monto |
| "Top proveedores por monto de compra" | Ranking de proveedores con monto total |
| "Resumen de compras de la semana" | Detalle de compras realizadas en la semana |
| "Cuales son los insumos mas comprados?" | Tabla con insumo, cantidad y monto |
| "Tiempo promedio de entrega por proveedor" | Tabla con proveedor y dias promedio de entrega |
| "Inventario critico de materiales" | Materiales con stock por debajo del minimo |

---

## 4.7 Agente de Compras a Productores

**Identificador interno:** `compras_productores`
**Especialidad:** Compras de materia prima a productores agricolas (arroz, maiz)

### Capacidades

- Compras de arroz paddy
- Compras de maiz blanco
- Arroz acondicionado
- Guias de compra
- Ranking de productores por volumen
- Precios de compra por tonelada/kilogramo

### Palabras clave que activan este agente

`productor`, `productores`, `arroz paddy`, `maiz blanco`, `arroz acondicionado`, `guia de compra`, `guias de compra`, `compra de arroz`, `compra de maiz`, `compras a productor`, `precio del arroz`, `precio del maiz`, `tonelada`, `kilogramo`

### Consultas de ejemplo

| Consulta | Tipo de respuesta esperada |
|----------|---------------------------|
| "Cuanto es la compra de arroz paddy este ano?" | Total en toneladas y bolivares con detalle mensual |
| "Compras de maiz del mes actual" | Detalle de compras de maiz con productor y volumen |
| "Top productores por volumen" | Ranking de productores con toneladas entregadas |
| "Resumen de compras a productores" | Vista general de compras por tipo de materia prima |
| "Precio promedio del arroz paddy este mes" | Precio por tonelada con comparativo al mes anterior |
| "Cuantas guias de compra se emitieron esta semana?" | Conteo y detalle de guias |
| "Compras de arroz acondicionado del trimestre" | Tabla con detalle mensual |

---

## 4.8 Mejores practicas para consultas

Para obtener los mejores resultados de SantoniBot, siga estas recomendaciones:

### Sea especifico con el periodo

| Consulta vaga | Consulta especifica |
|---------------|-------------------|
| "Cuanto se vendio?" | "Cuanto se vendio en enero 2026?" |
| "Dame las ventas" | "Resumen de ventas del mes actual por zona" |
| "Cuentas por cobrar" | "Cuentas por cobrar vencidas con mas de 30 dias de atraso" |

### Use terminos del departamento

El sistema identifica el agente apropiado por palabras clave. Incluya terminos que identifiquen claramente el area:

| Area | Terminos recomendados |
|------|----------------------|
| Finanzas | flujo de caja, bancos, saldos, cuentas por pagar |
| Contabilidad | balance general, libro mayor, IVA, estado de resultados |
| Ventas | clientes, vendedores, cobranza, ranking, facturacion |
| RRHH | empleados, nomina, vacaciones, asistencia |
| Produccion | produccion, eficiencia, desperdicio, planta, OEE |
| Compras Insumos | proveedores, insumos, ordenes de compra, materiales |
| Compras Productores | arroz paddy, maiz, productores, guias de compra |

### Pida comparativos

Los agentes pueden generar comparativos entre periodos:
- "Comparativo de ventas enero vs febrero"
- "Produccion de esta semana vs la semana pasada"
- "Flujo de caja este mes vs el mes anterior"

### Solicite formatos especificos

Puede solicitar que la informacion se presente de cierta manera:
- "Muestrame los top 20 clientes en una tabla con posicion, nombre y monto"
- "Dame un resumen ejecutivo de las finanzas del mes"
- "Lista los 5 vendedores con menor cumplimiento de meta"

### Consultas en cadena

Puede hacer consultas secuenciales que se complementen:
1. "Top 10 clientes por ventas del mes"
2. "De esos clientes, cuales tienen saldo vencido?"
3. "Dame el detalle de facturas pendientes del cliente A"

## 4.9 Asistente General

Cuando el sistema no puede clasificar la consulta en un departamento especifico, o cuando el usuario envia un saludo o pregunta general, responde el **Asistente General**.

### Comportamientos del asistente general

- **Saludos:** Responde amablemente y se presenta
- **Preguntas sobre el sistema:** Explica las capacidades de SantoniBot
- **Consultas ambiguas:** Solicita aclaracion al usuario

### Ejemplos

| Consulta | Respuesta |
|----------|-----------|
| "Hola" | "Hola! Soy SantoniBot, el asistente inteligente de Alimentos Santoni. Puedo ayudarte con consultas de Finanzas, Contabilidad, Ventas, RRHH, Produccion, Compras de Insumos y Compras a Productores." |
| "Que puedes hacer?" | Descripcion de las capacidades del sistema |
| "Gracias" | Respuesta cortes |

## 4.10 Tabla resumen de agentes

| # | Agente | Departamento | Palabras clave principales | Tipo de datos |
|---|--------|-------------|---------------------------|---------------|
| 1 | Finanzas | finanzas | flujo de caja, bancos, saldos, cuentas por pagar | Monetarios |
| 2 | Contabilidad | contabilidad | balance, libro mayor, IVA, ISLR, depreciacion | Contables |
| 3 | Ventas | ventas | clientes, vendedores, ranking, cobranza, zonas | Comerciales |
| 4 | RRHH | rrhh | empleados, nomina, vacaciones, asistencia | Personal |
| 5 | Produccion | produccion | planta, eficiencia, OEE, desperdicio, lotes | Industriales |
| 6 | Compras Insumos | compras_insumos | proveedores, insumos, ordenes de compra | Abastecimiento |
| 7 | Compras Productores | compras_productores | arroz paddy, maiz, productores, guias | Materia prima |
| - | General | general | hola, ayuda, que puedes hacer, gracias | Informativo |

## 4.11 Acceso denegado

Si un usuario intenta consultar informacion de un departamento al que no tiene acceso, el sistema respondera:

> "Lo siento, no tienes permisos para acceder a la informacion de ese departamento. Contacta a tu administrador si necesitas acceso adicional."

Estos intentos quedan registrados en el sistema de auditoria con la accion **"access_denied"** y son visibles para el administrador en el Panel de Auditoria.

### Comportamiento del control de acceso

El sistema verifica los permisos en dos niveles:

1. **Nivel de clasificacion:** Cuando el orquestador identifica el departamento destino, verifica si esta en la lista de departamentos permitidos del usuario
2. **Nivel de agente:** Antes de ejecutar la consulta, el agente verifica nuevamente que el departamento esta autorizado

Si un usuario necesita acceso a un departamento adicional:
1. Solicitar al administrador del sistema
2. El administrador puede agregar departamentos adicionales (si es Supervisor) o cambiar el rol

---

# 5. Roles y Permisos

SantoniBot implementa un sistema de **control de acceso basado en roles (RBAC)** que determina que informacion puede ver cada usuario y que acciones puede realizar.

## 5.1 Roles disponibles

El sistema cuenta con 4 roles:

| Rol | Nivel de Acceso | Departamentos | Panel Admin |
|-----|----------------|---------------|-------------|
| **Usuario** | Basico | Solo su departamento asignado | No |
| **Supervisor** | Intermedio | Su departamento + departamentos adicionales | No |
| **Administrador** | Total | Todos los departamentos | Si |
| **Vendedor** | Restringido | Solo Ventas (sus propios datos) | No |

## 5.2 Rol: Usuario

El rol **Usuario** es el nivel de acceso estandar para el personal de cada departamento.

### Permisos
- Acceso al chat para consultas de su departamento asignado
- Ver y gestionar sus propias conversaciones
- Adjuntar documentos para analisis
- Exportar datos de sus consultas (CSV, Excel, PDF, Word)
- Cambiar su propia contrasena
- Configurar 2FA para su cuenta

### Restricciones
- No puede ver informacion de otros departamentos
- No puede acceder al Panel de Administracion
- No puede crear ni gestionar otros usuarios

### Ejemplo
Un usuario asignado al departamento de **Produccion** puede consultar datos de produccion, eficiencia, desperdicios, etc., pero no puede preguntar por ventas, finanzas u otros departamentos.

## 5.3 Rol: Supervisor

El rol **Supervisor** tiene acceso extendido que puede incluir multiples departamentos.

### Permisos
- Todos los permisos del rol Usuario
- Acceso a su departamento principal
- Acceso a **departamentos adicionales** configurados por el administrador
- Vision mas amplia de la operacion

### Configuracion de departamentos adicionales
El administrador puede asignar departamentos adicionales al crear o editar un supervisor. Por ejemplo, un supervisor de Produccion podria tener acceso adicional a Compras de Insumos para monitorear la cadena de suministro.

### Ejemplo
Un supervisor con departamento principal **Ventas** y departamentos adicionales **Finanzas** y **Compras de Insumos** puede consultar:
- Ranking de ventas, clientes, cobranza (Ventas)
- Flujo de caja, cuentas por cobrar/pagar (Finanzas)
- Ordenes de compra, proveedores (Compras de Insumos)

## 5.4 Rol: Administrador

El rol **Administrador** tiene acceso completo al sistema.

### Permisos
- Acceso a **todos los departamentos** sin restriccion
- Acceso al **Panel de Administracion**
- Crear, editar y eliminar usuarios
- Ver estadisticas de uso del sistema
- Consultar registros de auditoria
- Gestionar seguridad (desbloquear cuentas, ver IPs sospechosas)
- Cambiar contrasenas y configurar 2FA

### Nota importante
El rol Administrador esta reservado para el equipo de TI y personal autorizado de Alimentos Santoni. Se recomienda mantener el numero de administradores al minimo necesario.

## 5.5 Rol: Vendedor

El rol **Vendedor** es un rol especializado diserado para los vendedores de campo de Alimentos Santoni.

### Permisos
- Acceso unicamente al departamento de **Ventas**
- **Solo puede ver SUS propias ventas y clientes**
- Consultar su cobranza personal
- Ver su ranking individual
- Exportar sus datos

### Vinculacion con iDempiere
Al crear un usuario con rol Vendedor, el administrador debe seleccionar el **vendedor correspondiente en iDempiere** (campo `idempiere_salesrep_id`). Esto permite que el sistema filtre automaticamente toda la informacion para que el vendedor solo vea sus propios datos.

### Restriccion clave
A diferencia de los demas roles que ven datos agregados del departamento, el vendedor ve exclusivamente la informacion asociada a su codigo de vendedor en el ERP.

## 5.6 Control de acceso por organizacion

Ademas del control por departamento, SantoniBot permite restringir el acceso por **organizacion de iDempiere**. Esto es util para empresas del grupo que comparten el mismo ERP.

### Configuracion

Al crear un usuario, el administrador puede seleccionar las organizaciones (empresas) a las que tiene acceso:

- **Sin seleccion = Acceso a todas las empresas**
- **Con seleccion = Solo las empresas seleccionadas**

Esta configuracion se aplica como filtro adicional sobre todas las consultas del usuario.

## 5.7 Matriz de permisos detallada

La siguiente tabla resume todos los permisos por rol:

| Funcionalidad | Usuario | Vendedor | Supervisor | Administrador |
|---------------|:-------:|:--------:|:----------:|:-------------:|
| Acceso al chat | Si | Si | Si | Si |
| Consultar su departamento | Si | Solo sus datos | Si | Si |
| Consultar departamentos adicionales | No | No | Si (configurado) | Si (todos) |
| Ver datos de otros vendedores | No | No | Si | Si |
| Adjuntar documentos | Si | Si | Si | Si |
| Exportar datos (CSV/Excel/PDF/Word) | Si | Si | Si | Si |
| Ver graficas automaticas | Si | Si | Si | Si |
| Historial de conversaciones | Propias | Propias | Propias | Propias |
| Buscar conversaciones | Si | Si | Si | Si |
| Cambiar su contrasena | Si | Si | Si | Si |
| Configurar 2FA propio | Si | Si | Si | Si |
| Panel de Administracion | No | No | No | Si |
| Crear usuarios | No | No | No | Si |
| Eliminar usuarios | No | No | No | Si |
| Ver estadisticas del sistema | No | No | No | Si |
| Ver auditoria | No | No | No | Si |
| Desbloquear cuentas | No | No | No | Si |
| Ver IPs sospechosas | No | No | No | Si |
| Ver metricas de seguridad | No | No | No | Si |

## 5.8 Recomendaciones para la asignacion de roles

| Perfil del empleado | Rol recomendado | Configuracion sugerida |
|--------------------|-----------------|----------------------|
| Personal operativo de un departamento | Usuario | Departamento correspondiente |
| Vendedor de campo | Vendedor | Vinculado a su salesrep de iDempiere |
| Gerente de departamento | Supervisor | Departamento principal + areas relacionadas |
| Gerente general | Supervisor | Departamento principal + todos los adicionales |
| Equipo de TI | Administrador | Acceso completo |
| Auditoria interna | Administrador | Acceso completo para revision |

---

# 6. Panel de Administracion

El Panel de Administracion es una herramienta exclusiva para usuarios con rol **Administrador**. Se accede desde el enlace "Administracion" en la barra lateral del chat.

## 6.1 Acceso al panel

1. Inicie sesion con una cuenta de rol Administrador
2. En la barra lateral izquierda, haga clic en **"Administracion"** (icono de engranaje)
3. Se abrira el Panel de Administracion en una nueva pagina
4. Para volver al chat, haga clic en la **flecha de regreso** en la esquina superior izquierda

## 6.2 Pestanas del panel

El Panel de Administracion tiene 4 pestanas principales:

| Pestana | Icono | Funcion |
|---------|-------|---------|
| **Estadisticas** | Grafico de barras | Metricas generales del sistema |
| **Usuarios** | Personas | Gestion de cuentas de usuario |
| **Auditoria** | Escudo | Registro de actividades del sistema |
| **Seguridad** | Escudo con check | 2FA, contrasenas, cuentas bloqueadas |

## 6.3 Pestana: Estadisticas

La pestana de Estadisticas muestra un resumen del uso del sistema con las siguientes tarjetas:

| Metrica | Descripcion |
|---------|-------------|
| **Usuarios Activos** | Cantidad de usuarios activos sobre el total registrado |
| **Conversaciones** | Numero total de conversaciones creadas |
| **Mensajes Totales** | Cantidad total de mensajes intercambiados |
| **Agentes Activos** | Cantidad de agentes departamentales con actividad |

### Uso por Agente

Debajo de las tarjetas, se muestra un grafico de barras horizontales con el **uso por agente**. Cada barra muestra:
- Nombre del agente (departamento)
- Cantidad de consultas procesadas
- Barra proporcional al agente mas utilizado

Esto permite al equipo de TI identificar cuales departamentos utilizan mas el sistema y cuales necesitan mas capacitacion o incentivo.

## 6.4 Pestana: Usuarios

La pestana de Usuarios permite la gestion completa de las cuentas del sistema.

### Lista de usuarios

Se muestra una tabla con todos los usuarios registrados:

| Columna | Descripcion |
|---------|-------------|
| **Nombre** | Nombre completo del usuario |
| **Usuario** | Nombre de usuario para el login |
| **Departamento** | Departamento principal (y adicionales si los tiene) |
| **Rol** | Rol asignado (con codigo de color) |
| **Empresas** | Organizaciones de iDempiere a las que tiene acceso |
| **Estado** | Indicador verde (activo) o gris (inactivo) |
| **Acciones** | Boton para eliminar usuario |

### Codigos de color por rol

| Rol | Color |
|-----|-------|
| Administrador | Purpura |
| Supervisor | Azul |
| Vendedor | Verde |
| Usuario | Gris |

### Crear un nuevo usuario

Para crear un usuario:

1. Haga clic en el boton **"Nuevo Usuario"** (esquina superior derecha)
2. Complete el formulario con los siguientes campos:

| Campo | Descripcion | Obligatorio |
|-------|-------------|:-----------:|
| **Nombre completo** | Nombre y apellido del usuario | Si |
| **Username** | Nombre de usuario para el login (sin espacios) | Si |
| **Email** | Correo electronico del usuario | Si |
| **Contrasena** | Contrasena inicial (debe cumplir politica de seguridad) | Si |
| **Rol** | Seleccionar: Usuario, Supervisor, Administrador o Vendedor | Si |
| **Departamento** | Departamento principal del usuario | Si |
| **Departamentos adicionales** | Solo para Supervisores: areas adicionales de acceso | No |
| **Empresas / Organizaciones** | Seleccionar organizaciones de iDempiere | No |
| **Vendedor en iDempiere** | Solo para rol Vendedor: vincular con vendedor del ERP | Condicional |

3. Haga clic en **"Crear"**

### Reglas especiales por rol

- **Vendedor:** El departamento se fija automaticamente en "Ventas". Se debe seleccionar el vendedor correspondiente en iDempiere
- **Administrador:** Tiene acceso automatico a "Todas las areas". No requiere seleccion de departamento especifico
- **Supervisor:** Se habilita la seccion de departamentos adicionales para seleccionar areas complementarias

### Eliminar un usuario

1. En la tabla de usuarios, ubique el usuario a eliminar
2. Haga clic en el **icono de papelera** (columna de acciones)
3. Confirme la eliminacion en el dialogo de confirmacion

> **Advertencia:** La eliminacion de un usuario es permanente. Se recomienda desactivar la cuenta en lugar de eliminarla si existe la posibilidad de reactivacion futura.

### Ejemplo paso a paso: Crear un vendedor

A continuacion se muestra un ejemplo completo de como crear un usuario con rol Vendedor:

1. Acceda al Panel de Administracion > Usuarios
2. Haga clic en **"Nuevo Usuario"**
3. Complete los campos:
   - **Nombre completo:** Juan Perez
   - **Username:** jperez
   - **Email:** jperez@santoni.com.ve
   - **Contrasena:** Santoni2026! (cumple con la politica de seguridad)
   - **Rol:** Vendedor (el departamento se fija automaticamente a "Ventas")
4. En la seccion **"Vendedor en iDempiere"**, seleccione "Juan Perez" de la lista desplegable
5. Si aplica, seleccione las organizaciones a las que tendra acceso
6. Haga clic en **"Crear"**
7. Comunique las credenciales al nuevo usuario de forma segura
8. Solicite al usuario que cambie su contrasena en el primer acceso

### Ejemplo paso a paso: Crear un supervisor multi-departamento

1. Acceda al Panel de Administracion > Usuarios
2. Haga clic en **"Nuevo Usuario"**
3. Complete los campos:
   - **Nombre completo:** Maria Garcia
   - **Username:** mgarcia
   - **Email:** mgarcia@santoni.com.ve
   - **Contrasena:** Garcia$2026
   - **Rol:** Supervisor
   - **Departamento:** Ventas (departamento principal)
4. En la seccion **"Departamentos adicionales"**, marque las casillas de:
   - Finanzas
   - Compras Insumos
5. Si aplica, seleccione las organizaciones
6. Haga clic en **"Crear"**

Con esta configuracion, Maria podra consultar datos de Ventas, Finanzas y Compras de Insumos.

## 6.5 Pestana: Auditoria

La pestana de Auditoria muestra un registro detallado de todas las acciones realizadas en el sistema. Esta informacion es fundamental para:

- Cumplimiento regulatorio
- Investigacion de incidentes de seguridad
- Monitoreo de uso del sistema
- Deteccion de comportamiento inusual

### Columnas del registro de auditoria

| Columna | Descripcion |
|---------|-------------|
| **Fecha** | Fecha y hora de la accion (formato venezolano) |
| **Usuario** | Nombre y username del usuario que realizo la accion |
| **Accion** | Tipo de accion realizada |
| **Detalle** | Descripcion del evento |
| **Agente** | Agente departamental utilizado (si aplica) |
| **IP** | Direccion IP desde donde se realizo la accion |

### Tipos de acciones registradas

| Accion | Color | Descripcion |
|--------|-------|-------------|
| **Inicio sesion** | Verde | Login exitoso |
| **Login fallido** | Rojo | Intento de login con credenciales incorrectas |
| **ACCESO DENEGADO** | Rojo | Intento de acceder a departamento sin permiso |
| **Consulta** | Azul | Consulta realizada al chat |
| **Otras** | Gris | Cambios de contrasena, configuracion de 2FA, etc. |

### Resaltado de alertas

Las filas correspondientes a eventos de seguridad (**login fallido** y **acceso denegado**) se resaltan con fondo rojo para facilitar su identificacion visual.

## 6.6 Pestana: Seguridad

La pestana de Seguridad es el **panel de control de TI** para gestionar la seguridad del sistema. Se divide en varias secciones:

### Panel de Seguridad (TI) - Vision general

Muestra 4 indicadores clave de seguridad:

| Indicador | Descripcion | Color |
|-----------|-------------|-------|
| **Logins fallidos (24h)** | Intentos de login fallidos en las ultimas 24 horas | Rojo |
| **Bloqueos (7 dias)** | Cuentas bloqueadas en los ultimos 7 dias | Naranja |
| **Cuentas bloqueadas** | Cuentas actualmente bloqueadas | Rojo/Verde |
| **Usuarios con 2FA** | Porcentaje de usuarios con 2FA habilitado | Azul |

### IPs sospechosas

Si existen direcciones IP con multiples intentos fallidos de login en los ultimos 7 dias, se muestran con:
- Direccion IP (formato monoespaciado)
- Cantidad de intentos fallidos
- Indicador visual de alerta

### Cuentas bloqueadas

Cuando hay cuentas bloqueadas por exceso de intentos fallidos, se muestra una seccion con:

| Dato | Descripcion |
|------|-------------|
| **Nombre** | Nombre completo del usuario bloqueado |
| **Usuario** | Username del usuario |
| **Intentos** | Cantidad de intentos fallidos |
| **Tiempo restante** | Minutos restantes del bloqueo |
| **Accion** | Boton "Desbloquear" |

Para desbloquear una cuenta:
1. Identifique la cuenta bloqueada en la lista
2. Haga clic en el boton **"Desbloquear"**
3. El usuario podra intentar iniciar sesion nuevamente

### Autenticacion de Dos Factores (2FA) - Cuenta propia

Esta seccion permite al administrador gestionar su propio 2FA:

**Para activar 2FA:**
1. Haga clic en **"Configurar 2FA"**
2. Escanee el codigo QR con Google Authenticator
3. O ingrese el codigo secreto manualmente en la aplicacion
4. Ingrese el codigo de 6 digitos generado
5. Haga clic en **"Activar 2FA"**

**Para desactivar 2FA:**
1. Ingrese el codigo actual de 6 digitos de su aplicacion
2. Haga clic en **"Desactivar 2FA"**

### Cambiar Contrasena - Cuenta propia

Permite al administrador cambiar su propia contrasena:

1. Ingrese su **contrasena actual**
2. Ingrese la **nueva contrasena** (debe cumplir con la politica de seguridad)
3. **Confirme** la nueva contrasena
4. Haga clic en **"Cambiar Contrasena"**

---

# 7. Dashboard de KPIs

## 7.1 Descripcion general

El Dashboard de KPIs es una funcionalidad planificada que proporcionara una vista consolidada de los indicadores clave de rendimiento (KPIs) de la empresa en una sola pantalla, accesible desde la ruta `/dashboard`.

## 7.2 Indicadores previstos

El dashboard esta disenado para mostrar indicadores de las siguientes areas:

### Finanzas
- Flujo de caja neto del mes
- Saldo total en bancos
- Cuentas por cobrar vencidas
- Cuentas por pagar proximas al vencimiento

### Ventas
- Ventas del mes actual vs meta
- Porcentaje de cumplimiento
- Top 5 clientes del mes
- Cobranza acumulada

### Produccion
- Produccion del dia/semana
- Eficiencia de linea (OEE)
- Porcentaje de desperdicio

### Compras
- Compras del mes (insumos)
- Compras de materia prima (arroz, maiz)
- Ordenes de compra pendientes

## 7.3 Actualizacion de datos

Los datos del dashboard se actualizaran en tiempo real desde la base de datos de iDempiere, al igual que las consultas del chat.

## 7.4 Acceso

El acceso al dashboard estara controlado por los mismos roles y permisos del sistema:
- Cada usuario vera solo los KPIs de su departamento
- Los administradores veran todos los KPIs
- Los supervisores veran los KPIs de sus departamentos asignados

> **Nota:** Esta funcionalidad se encuentra en desarrollo. Su disponibilidad sera comunicada por el equipo de TI.

## 7.5 Alternativa actual: Consultas por chat

Mientras el dashboard se encuentra en desarrollo, puede obtener la misma informacion a traves del chat de SantoniBot. Aqui tiene consultas equivalentes a los KPIs del dashboard:

| KPI del Dashboard | Consulta equivalente en el chat |
|-------------------|-------------------------------|
| Flujo de caja neto | "Cual es el flujo de caja del mes actual?" |
| Saldo en bancos | "Cual es el saldo de bancos hoy?" |
| Ventas vs meta | "Resumen de ventas del mes actual vs meta" |
| Produccion del dia | "Cual es la produccion de hoy?" |
| Eficiencia OEE | "Cual es la eficiencia de la linea?" |
| Compras del mes | "Cuanto se compro de insumos este mes?" |
| Cuentas por cobrar vencidas | "Muestrame las cuentas por cobrar vencidas" |
| Top 5 clientes | "Top 5 clientes por ventas del mes" |

---

# 8. Alertas y Reportes

## 8.1 Alertas automaticas en respuestas

Los agentes especializados de SantoniBot incluyen alertas contextuales en sus respuestas cuando detectan situaciones que requieren atencion:

### Tipos de alertas

| Area | Tipo de Alerta | Descripcion |
|------|---------------|-------------|
| **Finanzas** | Morosidad | Cuentas por cobrar con mas de X dias de atraso |
| **Finanzas** | Vencimientos | Cuentas por pagar proximas a vencer |
| **Finanzas** | Saldo critico | Saldos bancarios por debajo de un umbral |
| **Ventas** | Metas incumplidas | Vendedores por debajo de su meta mensual |
| **Ventas** | Caida de ventas | Zonas con disminucion significativa |
| **Ventas** | Clientes morosos | Clientes con saldo vencido significativo |
| **Produccion** | Desperdicio alto | Porcentaje de merma por encima de lo esperado |
| **Produccion** | Eficiencia baja | OEE por debajo del objetivo |
| **Compras** | Ordenes pendientes | Ordenes de compra sin recibir fuera de plazo |

### Como funcionan las alertas

Las alertas no son notificaciones push; se presentan como parte de las respuestas del agente. Cuando consulta informacion de su departamento, el agente resaltara automaticamente las situaciones criticas con texto destacado.

**Ejemplo:**

> **Consulta:** "Muestrame las cuentas por cobrar vencidas"
>
> **Respuesta del Agente de Finanzas:**
> "Aqui tienes las cuentas por cobrar vencidas al dia de hoy:
>
> | Cliente | Monto (Bs.) | Dias de Atraso |
> |---------|------------|----------------|
> | Cliente A | 150.000,00 | 45 |
> | Cliente B | 89.000,00 | 32 |
>
> **ALERTA:** El Cliente A tiene 45 dias de atraso. Se recomienda accion de cobranza inmediata."

## 8.2 Reportes bajo demanda

Los usuarios pueden generar reportes personalizados simplemente formulando la consulta adecuada:

### Ejemplos de reportes

| Reporte | Consulta sugerida |
|---------|-------------------|
| Ranking de ventas mensual | "Ranking de ventas por vendedor del mes actual" |
| Estado de cuentas por cobrar | "Reporte completo de cuentas por cobrar con dias de atraso" |
| Produccion semanal | "Resumen de produccion de la semana con comparativo" |
| Top proveedores | "Top 20 proveedores por monto de compra del ano" |
| Nomina mensual | "Resumen detallado de nomina del mes actual" |

### Exportar reportes

Todo reporte generado por SantoniBot puede exportarse en multiples formatos. Consulte la seccion [9. Exportacion de Datos](#9-exportacion-de-datos) para mas detalles.

## 8.3 Configuracion de alertas

Las alertas estan integradas en la logica de los agentes y se activan automaticamente cuando los datos superan ciertos umbrales predefinidos. No requieren configuracion por parte del usuario.

Si se requiere ajustar los umbrales o agregar nuevos tipos de alertas, contacte al equipo de desarrollo (OVA Agency).

---

# 9. Exportacion de Datos

## 9.1 Formatos disponibles

SantoniBot permite exportar las respuestas que contienen tablas de datos en 4 formatos:

| Formato | Extension | Descripcion | Uso recomendado |
|---------|-----------|-------------|-----------------|
| **CSV** | `.csv` | Valores separados por comas | Procesamiento en hojas de calculo, importacion a otros sistemas |
| **Excel** | `.xlsx` | Formato Microsoft Excel | Analisis de datos, filtros, formulas |
| **PDF** | `.pdf` | Documento portable | Impresion, archivo, presentaciones formales |
| **Word** | `.docx` | Documento Microsoft Word | Edicion, inclusion en informes |

## 9.2 Como exportar

Los botones de exportacion aparecen automaticamente en la parte inferior de cada respuesta que contiene una tabla de datos.

### Pasos:

1. Realice una consulta que genere una tabla (ej: "Top 20 clientes por ventas")
2. Espere a que la respuesta se muestre completamente
3. En la parte inferior derecha de la respuesta, ubique los iconos de exportacion
4. Haga clic en el icono correspondiente al formato deseado:
   - **Icono de tabla** = CSV
   - **Icono de hoja de calculo verde** = Excel
   - **Icono de documento rojo** = PDF
   - **Icono de documento azul** = Word
5. El archivo se descargara automaticamente con el nombre `santonibot_reporte.[extension]`

## 9.3 Exportar graficas

Las graficas generadas automaticamente tambien pueden exportarse:

1. Genere una grafica haciendo clic en el icono de grafico de barras
2. En la esquina superior derecha de la grafica, haga clic en el boton **"PNG"**
3. La grafica se descargara como imagen de alta resolucion (2x para pantallas retina)
4. El archivo se guardara como `santonibot_grafica_[timestamp].png`

## 9.4 Guia de seleccion de formato

| Necesidad | Formato recomendado | Razon |
|-----------|-------------------|-------|
| Abrir en Excel para filtrar y analizar | **Excel (.xlsx)** | Formato nativo, conserva formato de datos |
| Importar a otro sistema | **CSV** | Formato universal, ligero |
| Enviar por correo a gerencia | **PDF** | Profesional, no editable, listo para imprimir |
| Incluir en un informe que esta redactando | **Word (.docx)** | Editable, facil de copiar al documento final |
| Archivar como evidencia | **PDF** | Formato de archivo estandar |
| Compartir con alguien que no tiene Excel | **CSV o PDF** | CSV se abre en cualquier editor, PDF es universal |
| Presentar en reunion | **Grafica PNG** + **PDF** | Visual impactante + datos de soporte |

## 9.5 Ejemplo practico de exportacion

### Escenario: Preparar un informe de ventas para la reunion semanal

1. Abra SantoniBot e inicie una nueva conversacion
2. Escriba: "Top 20 clientes por ventas de la semana actual"
3. Espere la respuesta con la tabla de datos
4. Haga clic en el icono de **grafico de barras** para ver la grafica
5. Descargue la grafica como **PNG** (boton "PNG" en la esquina de la grafica)
6. Haga clic en el icono de **PDF** para descargar el reporte
7. Ambos archivos estan listos para incluir en su presentacion

### Escenario: Exportar datos para analisis en Excel

1. Escriba: "Resumen de ventas del mes por zona con detalle de vendedores"
2. Espere la respuesta completa
3. Haga clic en el icono de **Excel** (icono verde de hoja de calculo)
4. Abra el archivo descargado en Microsoft Excel
5. Aplique filtros, graficas dinamicas o formulas segun su necesidad

## 9.6 Consideraciones

- La exportacion requiere una sesion activa. Si su sesion expiro, debera iniciar sesion nuevamente
- Los archivos exportados contienen los datos tal como se presentaron en la respuesta
- El nombre del archivo siempre comienza con `santonibot_reporte` para facil identificacion
- El sistema aplica limitacion de velocidad (rate limiting) en las exportaciones para proteger el rendimiento del servidor
- Solo se puede exportar un mensaje a la vez. Si necesita exportar multiples respuestas, realice cada exportacion individualmente
- Los datos exportados corresponden al momento en que se realizo la consulta, no al momento de la exportacion

---

# 10. Seguridad

## 10.1 Politica de contrasenas

SantoniBot aplica una politica de contrasenas robusta que exige los siguientes requisitos minimos:

| Requisito | Detalle |
|-----------|---------|
| **Longitud minima** | 8 caracteres |
| **Mayusculas** | Al menos una letra mayuscula (A-Z) |
| **Minusculas** | Al menos una letra minuscula (a-z) |
| **Numeros** | Al menos un numero (0-9) |
| **Caracteres especiales** | Al menos un caracter especial (!@#$%^&*) |

### Ejemplos de contrasenas validas

- `Santoni2026!`
- `M1Clave#Segura`
- `Pr0ducc!on$`

### Ejemplos de contrasenas invalidas

- `santoni` (sin mayusculas, sin numeros, sin caracteres especiales, menos de 8 caracteres)
- `12345678` (sin letras ni caracteres especiales)
- `Password` (sin numeros ni caracteres especiales)

## 10.2 Autenticacion de Dos Factores (2FA/TOTP)

SantoniBot soporta autenticacion de dos factores usando el protocolo **TOTP (Time-based One-Time Password)**, compatible con las siguientes aplicaciones:

| Aplicacion | Plataforma |
|-----------|-----------|
| Google Authenticator | Android / iOS |
| Microsoft Authenticator | Android / iOS |
| Authy | Android / iOS / Desktop |
| 1Password | Multiplataforma |

### Activar 2FA

1. Acceda al **Panel de Administracion** > **Seguridad** (si es administrador)
2. En la seccion **"Autenticacion de Dos Factores (2FA)"**, haga clic en **"Configurar 2FA"**
3. Se generara un **codigo QR** y un **codigo secreto**
4. Abra Google Authenticator en su telefono
5. Toque **"+"** y seleccione **"Escanear codigo QR"**
6. Escanee el codigo QR que aparece en pantalla
7. Si no puede escanear, seleccione **"Ingresar clave manualmente"** e ingrese el codigo secreto mostrado
8. Ingrese el **codigo de 6 digitos** que genera la aplicacion
9. Haga clic en **"Activar 2FA"**
10. Un mensaje verde confirmara: **"2FA habilitado exitosamente"**

### Desactivar 2FA

1. En la seccion de 2FA, ingrese el **codigo de 6 digitos** actual de su aplicacion
2. Haga clic en **"Desactivar 2FA"**
3. Se le pedira confirmacion

> **Importante:** Se recomienda fuertemente mantener el 2FA activado, especialmente para cuentas de administradores.

### Que hacer si pierde acceso al 2FA

Si pierde su telefono o desinstala la aplicacion autenticadora:
1. Contacte al administrador del sistema
2. El administrador puede resetear su 2FA desde el panel de administracion
3. Una vez reseteado, configure el 2FA nuevamente

## 10.3 Bloqueo de cuentas

El sistema implementa un mecanismo de **bloqueo automatico** para proteger contra ataques de fuerza bruta:

| Parametro | Valor |
|-----------|-------|
| **Intentos permitidos** | 5 intentos fallidos consecutivos |
| **Tiempo de bloqueo** | 15 minutos |
| **Reinicio** | Automatico al expirar el tiempo, o manual por el administrador |

### Proceso de bloqueo

1. Un usuario ingresa credenciales incorrectas
2. Cada intento fallido incrementa el contador
3. Al llegar a **5 intentos fallidos**, la cuenta se bloquea por **15 minutos**
4. El sistema registra el evento en el log de auditoria
5. El usuario recibe el mensaje: "Cuenta bloqueada por demasiados intentos fallidos. Intente en X minutos o contacte al administrador."

### Desbloqueo manual

Un administrador puede desbloquear una cuenta antes de que expire el tiempo:
1. Acceder al **Panel de Administracion** > **Seguridad**
2. En la seccion **"Cuentas Bloqueadas"**, ubicar al usuario
3. Hacer clic en **"Desbloquear"**

## 10.4 Gestion de sesiones

### Tokens JWT

SantoniBot utiliza **JSON Web Tokens (JWT)** para la autenticacion:

| Parametro | Valor |
|-----------|-------|
| **Duracion del token** | 30 minutos |
| **Renovacion** | Automatica mientras haya actividad |
| **Almacenamiento** | localStorage del navegador |

### Cierre de sesion por inactividad

| Parametro | Valor |
|-----------|-------|
| **Tiempo de inactividad maximo** | 30 minutos |
| **Advertencia previa** | 5 minutos antes del cierre |
| **Verificacion de actividad** | Cada 30 segundos |

El sistema detecta la actividad del usuario a traves de:
- Movimiento del mouse
- Pulsaciones de teclado
- Clics
- Desplazamiento (scroll)
- Interaccion tactil

### Recomendaciones de seguridad

- **Cierre sesion manualmente** cuando termine de usar el sistema
- **No comparta sus credenciales** con otras personas
- **Active el 2FA** para mayor proteccion
- **Use contrasenas unicas** que no utilice en otros sistemas
- **No acceda al sistema** desde computadores publicos o no confiables
- **Reporte inmediatamente** cualquier actividad sospechosa al equipo de TI

## 10.5 Proteccion contra ataques

SantoniBot implementa multiples capas de seguridad:

| Mecanismo | Descripcion |
|-----------|-------------|
| **Rate limiting** | Limite de peticiones por IP (login, API, exportaciones) |
| **Bloqueo de cuentas** | Proteccion contra fuerza bruta |
| **2FA (TOTP)** | Segundo factor de autenticacion |
| **Cifrado de contrasenas** | Contrasenas almacenadas con hash seguro (bcrypt) |
| **JWT con expiracion** | Tokens de sesion con vida util limitada |
| **Auditoria completa** | Registro de todas las acciones del sistema |
| **RBAC** | Control de acceso basado en roles |
| **Nginx** | Proxy inverso con protecciones adicionales |
| **HTTPS** | Comunicacion cifrada en transito |
| **Monitoreo de IPs** | Deteccion de IPs con comportamiento sospechoso |

## 10.6 Guia rapida de seguridad para TI

Esta seccion resume las tareas de seguridad mas comunes para el equipo de TI de Alimentos Santoni.

### Verificacion diaria de seguridad (Checklist)

Realice las siguientes verificaciones al inicio de cada dia laboral:

- [ ] Acceder al Panel de Administracion > Seguridad
- [ ] Verificar el numero de **logins fallidos en las ultimas 24 horas**
- [ ] Revisar si hay **cuentas actualmente bloqueadas** y determinar si corresponde desbloquearlas
- [ ] Verificar las **IPs sospechosas** y tomar accion si se detectan patrones inusuales
- [ ] Revisar el **porcentaje de cobertura de 2FA** y promover su activacion entre los usuarios
- [ ] Consultar la pestana de **Auditoria** para detectar actividad inusual

### Acciones ante incidentes de seguridad

| Situacion | Accion recomendada |
|-----------|-------------------|
| IP desconocida con multiples intentos fallidos | Verificar si es un empleado o un intento de acceso no autorizado. Considerar bloqueo a nivel de firewall |
| Cuenta bloqueada de un empleado conocido | Contactar al empleado para verificar, luego desbloquear si corresponde |
| Acceso denegado frecuente de un usuario | Verificar si el usuario necesita acceso a departamentos adicionales |
| Login exitoso en horario inusual | Contactar al usuario para confirmar que fue el quien accedio |
| Multiples intentos desde la misma IP | Posible ataque de fuerza bruta. Bloquear IP en el firewall/Nginx |

### Politica de 2FA recomendada

Se recomienda que los siguientes perfiles tengan 2FA **obligatorio**:

| Perfil | Prioridad |
|--------|-----------|
| Administradores | Obligatorio |
| Gerentes | Altamente recomendado |
| Supervisores | Altamente recomendado |
| Usuarios regulares | Recomendado |
| Vendedores | Recomendado si acceden desde redes externas |

### Politica de contrasenas recomendada

| Practica | Recomendacion |
|----------|--------------|
| Cambio periodico | Cada 90 dias |
| Reutilizacion | No reutilizar las ultimas 5 contrasenas |
| Compartir credenciales | Estrictamente prohibido |
| Contrasenas temporales | Cambiar en el primer acceso |
| Almacenamiento | No guardar en texto plano ni en notas adhesivas |

## 10.7 Zonas de rate limiting

El servidor Nginx configura tres zonas de limitacion de velocidad:

| Zona | Recurso | Limite |
|------|---------|--------|
| **api** | Todas las APIs | Proteccion general |
| **login** | Endpoint de login | Mas restrictivo para prevenir ataques |
| **export** | Exportaciones | Evitar sobrecarga por exportaciones masivas |

---

# 11. Preguntas Frecuentes (FAQ)

## Acceso y Login

### P: Olvide mi contrasena. Como la recupero?
**R:** Contacte al administrador del sistema (equipo de TI). El administrador puede crear una nueva contrasena temporal para su cuenta. Una vez que inicie sesion con la contrasena temporal, cambiela inmediatamente por una contrasena personal en la seccion de Seguridad.

### P: Mi cuenta esta bloqueada. Que hago?
**R:** Su cuenta se bloquea automaticamente despues de 5 intentos fallidos de login. Tiene dos opciones:
1. Esperar 15 minutos para que el bloqueo expire automaticamente
2. Contactar al administrador para un desbloqueo inmediato

### P: Perdi mi telefono y no puedo generar el codigo 2FA. Como accedo?
**R:** Contacte al administrador del sistema. El puede resetear la configuracion de 2FA de su cuenta, permitiendole acceder sin el codigo y reconfigurarlo con un nuevo dispositivo.

### P: La sesion se cierra sola. Es normal?
**R:** Si, por seguridad el sistema cierra la sesion automaticamente despues de 30 minutos de inactividad. Aparecera un aviso 5 minutos antes del cierre. Puede evitarlo haciendo clic en "Continuar sesion" o simplemente interactuando con el sistema.

---

## Uso del Chat

### P: El sistema no entiende mi consulta. Que puedo hacer?
**R:** Intente las siguientes estrategias:
1. **Sea mas especifico:** En lugar de "dame datos", diga "muestrame las ventas del mes por zona"
2. **Use palabras clave del departamento:** Incluya terminos como "ventas", "produccion", "contabilidad", etc.
3. **Reformule la pregunta:** Intente expresar la misma consulta de otra manera
4. **Use las sugerencias:** Al iniciar una nueva conversacion, use las sugerencias predefinidas como punto de partida

### P: Me dice que no tengo permiso para ver cierta informacion. Por que?
**R:** Su cuenta tiene acceso solo a ciertos departamentos segun su rol y configuracion. Si necesita acceso a informacion de otro departamento, solicite al administrador que agregue ese departamento a su perfil.

### P: Los datos que muestra son en tiempo real?
**R:** Si, todas las consultas se realizan directamente contra la base de datos del ERP iDempiere. Los datos son tan actuales como los registros ingresados en el ERP.

### P: Puedo hacer varias preguntas en la misma conversacion?
**R:** Si, puede hacer multiples consultas en la misma conversacion. El sistema mantiene el contexto de la conversacion para respuestas mas coherentes.

### P: Cuantas conversaciones puedo tener?
**R:** No hay limite en el numero de conversaciones. Puede crear tantas como necesite y buscar entre ellas usando la barra de busqueda.

### P: Puedo eliminar una conversacion?
**R:** Si, pase el mouse sobre la conversacion en la barra lateral y haga clic en el icono de papelera. La eliminacion es permanente.

---

## Datos y Reportes

### P: Los montos se muestran en bolivares o en dolares?
**R:** Los montos se muestran en la moneda registrada en iDempiere. Generalmente se expresan en **Bs. (bolivares)**, pero pueden aparecer en dolares si asi estan registrados en el ERP. El agente indica la moneda en sus respuestas.

### P: Puedo exportar los datos a Excel?
**R:** Si, toda respuesta que contenga una tabla puede exportarse en CSV, Excel (.xlsx), PDF y Word (.docx). Los botones de exportacion aparecen en la parte inferior derecha de la respuesta.

### P: La grafica no se ve bien o no aparece. Que hago?
**R:** Las graficas automaticas se generan cuando la tabla tiene al menos 3 filas de datos y al menos una columna numerica. Si no aparece el boton de grafica, la tabla probablemente no cumple estos requisitos. Intente solicitar datos mas detallados.

### P: Puedo exportar la grafica?
**R:** Si, haga clic en el boton "PNG" en la esquina superior derecha de la grafica para descargarla como imagen.

### P: Los datos del reporte no coinciden con lo que veo en iDempiere.
**R:** Si encuentra discrepancias:
1. Verifique que esta consultando el mismo periodo
2. Confirme que esta viendo la misma organizacion/empresa
3. Considere que los filtros de SantoniBot pueden diferir de los que aplica en iDempiere
4. Si la discrepancia persiste, reporte el caso al equipo de TI

---

## Documentos

### P: Que tipos de archivos puedo adjuntar?
**R:** Puede adjuntar PDF, Excel, Word, CSV, texto plano e imagenes (PNG, JPG, GIF, WebP). El tamano maximo es de 10 MB.

### P: Por que no puede analizar mi imagen?
**R:** El analisis de imagenes requiere la API de Claude (Anthropic) activa. Si no esta disponible, el sistema le informara. Los documentos de texto se pueden analizar con el motor alternativo (Groq).

### P: Puedo adjuntar varios archivos a la vez?
**R:** No, actualmente solo se puede adjuntar un archivo por mensaje. Para analizar multiples documentos, envielos en mensajes separados.

---

## Administracion

### P: Como creo un usuario nuevo?
**R:** Acceda al Panel de Administracion > Usuarios > "Nuevo Usuario". Complete todos los campos obligatorios y haga clic en "Crear". Consulte la seccion [6.4 Pestana: Usuarios](#64-pestana-usuarios) para instrucciones detalladas.

### P: Como desbloqueo una cuenta?
**R:** Acceda al Panel de Administracion > Seguridad. En la seccion "Cuentas Bloqueadas", haga clic en "Desbloquear" junto al usuario bloqueado.

### P: Como veo quien ha usado el sistema?
**R:** Acceda al Panel de Administracion > Auditoria. Ahi vera un registro completo de todas las acciones: logins, consultas, exportaciones, cambios de contrasena, etc.

### P: Como se que IPs estan intentando acceder sin autorizacion?
**R:** En Panel de Administracion > Seguridad, la seccion "IPs sospechosas" muestra las direcciones IP con multiples intentos fallidos de login en los ultimos 7 dias.

---

## Rendimiento y Disponibilidad

### P: El sistema esta lento. Que puedo hacer?
**R:** Posibles causas y soluciones:
1. **Conexion a internet lenta:** Verifique su conexion de red
2. **Navegador con muchas pestanas:** Cierre pestanas innecesarias
3. **Cache del navegador:** Limpie la cache y cookies del navegador
4. **Consulta compleja:** Algunas consultas con grandes volumenes de datos pueden tardar mas
5. **Problema del servidor:** Contacte al equipo de TI si el problema persiste

### P: SantoniBot esta disponible 24/7?
**R:** El sistema esta disponible siempre que los servidores de Alimentos Santoni esten operativos. Las ventanas de mantenimiento seran comunicadas previamente por el equipo de TI.

### P: SantoniBot puede cometer errores?
**R:** Si, como cualquier sistema basado en inteligencia artificial, SantoniBot puede ocasionalmente generar respuestas imprecisas. El sistema muestra un aviso al respecto: **"SantoniBot puede cometer errores. Verifica la informacion."** Siempre verifique datos criticos consultando directamente el ERP si es necesario.

---

# 12. Glosario

| Termino | Definicion |
|---------|-----------|
| **2FA** | Autenticacion de Dos Factores. Mecanismo de seguridad que requiere un segundo codigo ademas de la contrasena para acceder al sistema |
| **Agente** | Modulo de inteligencia artificial especializado en un departamento especifico de la empresa |
| **API** | Interfaz de Programacion de Aplicaciones. Punto de conexion entre el frontend y el backend del sistema |
| **Auditoria** | Registro sistematico de todas las acciones realizadas en el sistema para control y trazabilidad |
| **Balance de comprobacion** | Estado contable que lista todas las cuentas con sus saldos deudores y acreedores |
| **Balance general** | Estado financiero que muestra activos, pasivos y patrimonio de la empresa |
| **Bloqueo de cuenta** | Suspension temporal del acceso a una cuenta despues de multiples intentos fallidos de login |
| **Bs.** | Bolivares. Moneda de curso legal en Venezuela |
| **Chat** | Interfaz conversacional donde el usuario escribe preguntas y recibe respuestas del sistema |
| **Conversacion** | Secuencia de mensajes entre el usuario y el sistema, agrupada bajo un titulo |
| **CSV** | Comma-Separated Values. Formato de archivo donde los datos se separan por comas |
| **Dashboard** | Panel visual que muestra indicadores clave de rendimiento (KPIs) de forma consolidada |
| **Departamento** | Area funcional de la empresa (Finanzas, Ventas, Produccion, etc.) |
| **ERP** | Enterprise Resource Planning. Sistema de planificacion de recursos empresariales |
| **Estado de resultados** | Estado financiero que muestra ingresos, costos, gastos y utilidad de un periodo |
| **Exportacion** | Proceso de descargar datos del sistema en un formato especifico (CSV, Excel, PDF, Word) |
| **Flujo de caja** | Movimiento de dinero (entradas y salidas) de la empresa en un periodo determinado |
| **Google Authenticator** | Aplicacion movil de Google para generar codigos TOTP de verificacion en dos pasos |
| **Groq** | Proveedor de infraestructura de IA utilizado como motor principal de procesamiento de lenguaje |
| **iDempiere** | Sistema ERP de codigo abierto utilizado por Alimentos Santoni para gestionar sus operaciones |
| **JWT** | JSON Web Token. Formato de token digital utilizado para autenticar usuarios en el sistema |
| **KPI** | Key Performance Indicator. Indicador clave de rendimiento para medir objetivos |
| **LLM** | Large Language Model. Modelo de lenguaje de gran escala que procesa y genera texto |
| **Login** | Proceso de inicio de sesion en el sistema |
| **Markdown** | Formato de texto enriquecido utilizado para las respuestas del sistema |
| **Morosidad** | Retraso en el pago de una obligacion financiera |
| **Nomina** | Registro de salarios, asignaciones y deducciones de los empleados |
| **OEE** | Overall Equipment Effectiveness. Eficiencia Global de los Equipos, indicador clave de produccion |
| **Organizacion** | Entidad empresarial dentro del ERP iDempiere. Puede representar diferentes empresas del grupo |
| **Orquestador** | Componente central de SantoniBot que analiza cada consulta y la dirige al agente apropiado |
| **Pareto** | Analisis 80/20. Principio que indica que el 80% de los resultados proviene del 20% de las causas |
| **PDF** | Portable Document Format. Formato de documento estandar para impresion y archivo |
| **PostgreSQL** | Sistema de gestion de bases de datos relacional utilizado por el sistema |
| **Rate limiting** | Limitacion de la cantidad de peticiones por tiempo para proteger el servidor |
| **RBAC** | Role-Based Access Control. Control de acceso basado en roles |
| **Rol** | Nivel de permisos asignado a un usuario (Usuario, Supervisor, Administrador, Vendedor) |
| **Salesrep** | Representante de ventas. Codigo de vendedor en el ERP iDempiere |
| **Sidebar** | Barra lateral izquierda de la interfaz que muestra conversaciones y opciones de navegacion |
| **SSE** | Server-Sent Events. Tecnologia de streaming para enviar respuestas token por token |
| **Streaming** | Modo de respuesta donde el texto aparece progresivamente, palabra por palabra |
| **Sugerencias** | Consultas predefinidas que se muestran al iniciar una nueva conversacion |
| **Token** | Unidad de autenticacion digital que permite acceder al sistema sin reingresar credenciales |
| **TOTP** | Time-based One-Time Password. Protocolo para generar codigos temporales de verificacion |
| **XLSX** | Formato de archivo de Microsoft Excel |

---

# 13. Contacto y Soporte

## 13.1 Soporte de primer nivel - Equipo de TI (Alimentos Santoni)

Para problemas operativos del dia a dia, contacte al equipo de TI de Alimentos Santoni:

### Problemas que puede resolver el equipo de TI:

- Creacion de nuevas cuentas de usuario
- Reseteo de contrasenas
- Desbloqueo de cuentas
- Asignacion de roles y departamentos
- Monitoreo de seguridad
- Revision de logs de auditoria
- Reinicio de servicios del sistema

### Como reportar un problema al equipo de TI:

Al reportar un problema, incluya la siguiente informacion:

1. **Nombre de usuario** afectado
2. **Descripcion del problema** (que intento hacer y que ocurrio)
3. **Mensaje de error** exacto (si aplica)
4. **Fecha y hora** del incidente
5. **Captura de pantalla** (si es posible)
6. **Navegador y version** que esta utilizando

## 13.2 Soporte de segundo nivel - OVA Agency

Para problemas tecnicos avanzados, errores del sistema, solicitudes de nuevas funcionalidades o mejoras, el equipo de TI debe escalar al equipo de desarrollo:

**OVA Agency**
Desarrollo de Software y Soluciones de IA

### Problemas que requieren escalamiento a OVA Agency:

- Errores de programacion (bugs) en el sistema
- Resultados incorrectos o inconsistentes de los agentes
- Solicitudes de nuevas funcionalidades
- Cambios en la logica de negocio de los agentes
- Problemas de rendimiento o escalabilidad
- Actualizaciones de la plataforma
- Integracion de nuevos modulos o departamentos
- Cambios en la infraestructura (Docker, servidores, bases de datos)

## 13.3 Informacion del sistema

| Componente | Detalle |
|-----------|---------|
| **Sistema** | SantoniBot v1.0 |
| **Frontend** | Next.js 14 + React + TypeScript |
| **Backend** | Python FastAPI |
| **Base de datos** | PostgreSQL 16 (interna) + PostgreSQL 13 (iDempiere) |
| **IA Principal** | Groq (Llama 3.1 70B) |
| **IA Secundaria** | Claude API (Anthropic) |
| **Despliegue** | Docker Compose + Coolify + Nginx |

---

## Historial de cambios del manual

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | Febrero 2026 | Version inicial del manual de usuario |

---

**Documento confidencial de Alimentos Santoni, C.A.**
**Desarrollado por OVA Agency**
**Febrero 2026**
