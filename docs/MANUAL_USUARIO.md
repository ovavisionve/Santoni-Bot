# SantoniBot - Manual de Usuario

### Sistema Inteligente de Analisis de Datos Empresariales
### Alimentos Santoni, C.A.

---

> **Version:** 1.0
> **Fecha:** Febrero 2026
> **Desarrollado por:** OVA Agency

---

## Tabla de Contenido

1. [Que es SantoniBot](#1-que-es-santonibot)
2. [Como acceder al sistema](#2-como-acceder-al-sistema)
3. [Inicio de sesion paso a paso](#3-inicio-de-sesion-paso-a-paso)
4. [La pantalla de chat explicada](#4-la-pantalla-de-chat-explicada)
5. [Ejemplos de consultas por departamento](#5-ejemplos-de-consultas-por-departamento)
6. [Como exportar datos (CSV, Excel, PDF)](#6-como-exportar-datos-csv-excel-pdf)
7. [Boton de copiar respuesta](#7-boton-de-copiar-respuesta)
8. [Como funcionan las conversaciones](#8-como-funcionan-las-conversaciones)
9. [Que hacer si te sale "Acceso Denegado"](#9-que-hacer-si-te-sale-acceso-denegado)
10. [Que hacer si ocurre un error](#10-que-hacer-si-ocurre-un-error)
11. [Panel de Administracion (solo administradores)](#11-panel-de-administracion-solo-administradores)
12. [Consejos de seguridad](#12-consejos-de-seguridad)
13. [Preguntas frecuentes](#13-preguntas-frecuentes)
14. [Soporte tecnico](#14-soporte-tecnico)

---

## 1. Que es SantoniBot

SantoniBot es el asistente inteligente de Alimentos Santoni, C.A. Es una herramienta que te permite hacer preguntas sobre los datos de tu departamento usando lenguaje normal, como si estuvieras hablando con un companero de trabajo.

**En palabras sencillas:** en vez de abrir reportes complicados en el sistema, simplemente le escribes tu pregunta a SantoniBot y el te da la respuesta con los datos actualizados directamente desde el sistema iDempiere.

### Que puede hacer SantoniBot

- Responder preguntas sobre datos de tu departamento (ventas, finanzas, contabilidad, RRHH, produccion, compras)
- Mostrarte tablas con informacion organizada
- Permitirte descargar reportes en CSV, Excel o PDF
- Mantener un historial de tus conversaciones para que puedas consultarlas despues

### Que NO puede hacer SantoniBot

- No puede modificar, crear ni eliminar datos del sistema. SantoniBot solo **lee** informacion.
- No puede acceder a datos de departamentos que no te corresponden.
- No reemplaza al sistema iDempiere; es un complemento que te facilita la consulta de datos.

---

## 2. Como acceder al sistema

### Requisitos

Antes de comenzar, asegurate de tener lo siguiente:

- **Una computadora** con conexion a la red de la empresa (o VPN si estas fuera de la oficina)
- **Un navegador web actualizado.** Recomendamos usar alguno de estos:
  - Google Chrome (recomendado)
  - Mozilla Firefox
  - Microsoft Edge
- **Tu usuario y contrasena.** Estos te los proporciona el administrador del sistema o tu supervisor.

### Pasos para acceder

1. **Abre tu navegador web.** Haz doble clic en el icono de Chrome, Firefox o Edge en tu escritorio.

2. **Escribe la direccion del sistema.** En la barra de direcciones (la barra que esta arriba del navegador, donde normalmente escribes las paginas web), escribe la direccion que te proporciono tu supervisor. Generalmente tiene un formato como:

   ```
   https://santonibot.tuempresa.com
   ```

   > **Nota importante:** La direccion exacta te la dara tu supervisor o el equipo de sistemas. No intentes adivinarla.

3. **Presiona la tecla Enter.** Se cargara la pantalla de inicio de sesion de SantoniBot.

4. Veras una pantalla blanca con el logo de SantoniBot (una letra **"S"** en un cuadro verde) y dos campos para escribir tu usuario y contrasena.

---

## 3. Inicio de sesion paso a paso

Una vez que estes en la pantalla de inicio de sesion, sigue estos pasos:

### Paso 1: Escribe tu nombre de usuario

- Haz clic en el campo que dice **"Ingrese su usuario"**.
- Escribe tu nombre de usuario tal cual como te lo dieron. Por ejemplo: `jperez`, `mrodriguez`, etc.
- El nombre de usuario no distingue entre mayusculas y minusculas en la mayoria de los casos, pero es mejor escribirlo exactamente como te lo dieron.

### Paso 2: Escribe tu contrasena

- Haz clic en el campo que dice **"Ingrese su contrasena"**.
- Escribe tu contrasena. Veras que aparecen puntos negros en lugar de las letras (esto es normal, es para proteger tu contrasena).
- **Consejo:** Si quieres verificar que escribiste bien tu contrasena, haz clic en el icono del **ojito** que aparece a la derecha del campo de contrasena. Al hacer clic, podras ver temporalmente lo que escribiste. Haz clic de nuevo en el ojito para volver a ocultar la contrasena.

### Paso 3: Haz clic en "Iniciar Sesion"

- Haz clic en el boton verde que dice **"Iniciar Sesion"**.
- Veras que el boton cambia y muestra un circulito girando con el texto **"Ingresando..."**. Esto significa que el sistema esta verificando tus datos. Espera unos segundos.
- Si todo esta bien, seras llevado automaticamente a la pantalla del chat.

### Que hacer si la contrasena esta mal

Si escribiste mal tu usuario o contrasena, veras un mensaje en rojo que dice algo como: **"Error al iniciar sesion"** o **"Credenciales invalidas"**.

Que hacer:

1. **Verifica tu nombre de usuario.** Revisalo bien, asegurate de que no tenga espacios al inicio o al final.
2. **Verifica tu contrasena.** Usa el icono del ojito para ver lo que estas escribiendo y confirmar que esta bien.
3. **Revisa las mayusculas.** La contrasena SI distingue entre mayusculas y minusculas. Si tu contrasena es "Santoni2025", no funcionara si escribes "santoni2025".
4. **Revisa la tecla Bloq Mayus (Caps Lock).** Asegurate de que no la tengas activada sin querer.
5. **Si sigues sin poder entrar:** Contacta al administrador del sistema para que te restablezca la contrasena. No intentes adivinar la contrasena muchas veces seguidas.

### Que hacer si olvidaste tu contrasena

Contacta directamente a tu supervisor o al administrador del sistema. Ellos pueden restablecerte la contrasena desde el panel de administracion.

---

## 4. La pantalla de chat explicada

Cuando inicias sesion exitosamente, llegas a la **pantalla principal del chat**. Esta pantalla tiene varias secciones que vamos a explicar una por una.

### 4.1 Vista general de la pantalla

La pantalla esta dividida en dos partes principales:

```
+---------------------------+-----------------------------------------------+
|                           |                                               |
|   BARRA LATERAL           |          AREA PRINCIPAL DEL CHAT              |
|   (lado izquierdo)        |          (centro y derecha)                   |
|                           |                                               |
|   - Logo SantoniBot       |   - Encabezado con logo                      |
|   - Boton Nueva Conv.     |   - Area de mensajes                         |
|   - Buscador              |   - Sugerencias (si es nueva conversacion)   |
|   - Lista de conv.        |   - Campo para escribir tu pregunta          |
|   - Link Administracion   |                                               |
|   - Tu perfil             |                                               |
|   - Boton cerrar sesion   |                                               |
|                           |                                               |
+---------------------------+-----------------------------------------------+
```

### 4.2 La barra lateral izquierda (Sidebar)

La barra lateral esta a la izquierda de la pantalla, sobre un fondo oscuro (gris oscuro/negro). Aqui encuentras:

#### Logo y nombre
En la parte superior veras el logo de **SantoniBot** (una "S" en un cuadro verde) junto con el nombre "SantoniBot". A la derecha hay una flechita (`<`) que puedes presionar para **ocultar la barra lateral** y tener mas espacio para el chat.

> **En celular o pantalla pequena:** La barra lateral se oculta automaticamente. Puedes abrirla tocando el icono de tres lineas horizontales (menu hamburguesa) que aparece en la parte superior izquierda del chat.

#### Boton "Nueva conversacion"
Debajo del logo veras un boton con un icono de mensaje y el texto **"Nueva conversacion"**. Al hacer clic, se borra el chat actual y puedes comenzar una conversacion nueva desde cero.

> **Cuando usar este boton:** Usalo cuando quieras cambiar de tema por completo. Por ejemplo, si estabas preguntando sobre ventas y ahora quieres preguntar sobre nomina, es mejor iniciar una conversacion nueva.

#### Campo de busqueda
Debajo del boton de nueva conversacion hay un campo de texto con el texto **"Buscar conversaciones..."**. Aqui puedes escribir palabras para buscar entre tus conversaciones anteriores.

Por ejemplo, si escribes "ventas", te mostrara solo las conversaciones cuyo titulo contenga la palabra "ventas". Para limpiar la busqueda, haz clic en la **X** que aparece a la derecha del campo.

#### Lista de conversaciones anteriores
Debajo del buscador veras la lista de todas tus conversaciones previas. Cada conversacion muestra:

- **Un icono de mensaje** a la izquierda
- **El titulo de la conversacion** (se genera automaticamente basandose en tu primera pregunta)
- **Hace cuanto fue la ultima actividad** (ejemplo: "ahora", "5m", "2h", "ayer", "3d", o una fecha como "15 ene")
- **Una vista previa** del ultimo mensaje o la cantidad de mensajes

**Para abrir una conversacion anterior:** Simplemente haz clic sobre ella y se cargaran todos los mensajes de esa conversacion en el area principal.

**Para eliminar una conversacion:** Pasa el mouse sobre la conversacion y veras un icono de **basura** (papelera) a la derecha. Haz clic sobre el para eliminarla.

> **Atencion:** Eliminar una conversacion es permanente. No se puede recuperar.

#### Enlace de Administracion (solo para administradores)
Si tu usuario tiene el rol de **Administrador**, veras un enlace con el icono de engranaje y el texto **"Administracion"** en la parte inferior de la barra lateral, justo encima de tu perfil. Al hacer clic, te lleva al Panel de Administracion (ver seccion 11).

Si no eres administrador, este enlace no aparecera. Esto es completamente normal.

#### Tu informacion de perfil
En la parte inferior de la barra lateral veras:

- **Tu inicial** en un circulo verde (la primera letra de tu nombre)
- **Tu nombre completo**
- **Tu departamento** (por ejemplo: "Ventas", "Finanzas", "RRHH", etc.)

#### Boton de cerrar sesion
A la derecha de tu informacion de perfil hay un icono de **flecha de salida** (cerrar sesion). Al hacer clic se cierra tu sesion y te lleva de regreso a la pantalla de inicio de sesion.

### 4.3 El area principal del chat

El area principal del chat es donde sucede toda la magia. Aqui es donde escribes tus preguntas y lees las respuestas de SantoniBot.

#### Encabezado del chat
En la parte superior del area de chat veras una barra con:

- El logo de SantoniBot (la "S" verde)
- El nombre **"SantoniBot"**
- El texto **"Asistente inteligente de Alimentos Santoni"**

#### Pantalla de bienvenida (cuando no hay mensajes)
Cuando inicias una conversacion nueva, antes de enviar cualquier mensaje, veras una pantalla de bienvenida que dice:

> **"Bienvenido a SantoniBot"**
> "Haz una consulta sobre tu departamento. Estas son algunas sugerencias:"

Debajo del mensaje de bienvenida aparecen **4 botones con preguntas sugeridas** especificas para tu departamento. Estas sugerencias cambian segun tu departamento. Por ejemplo, si eres del departamento de Ventas, veras sugerencias como "Cuales son los top 20 clientes por ventas?" o "Ranking de vendedores del mes".

**Para usar una sugerencia:** Simplemente haz clic en la sugerencia que te interese. El texto se copiara automaticamente en el campo de escritura para que puedas enviarlo directamente o modificarlo antes de enviar.

#### Area de mensajes
Aqui aparecen todos los mensajes de la conversacion. Los mensajes se muestran de esta forma:

- **Tus mensajes** aparecen alineados a la **derecha**, en burbujas de color **verde** con texto blanco. Tu inicial aparece en un circulo gris oscuro.
- **Las respuestas de SantoniBot** aparecen alineadas a la **izquierda**, en burbujas **blancas** con texto oscuro. El avatar de SantoniBot (la "S" verde) aparece a la izquierda.

Cada mensaje muestra en la parte inferior la hora relativa en que fue enviado (por ejemplo: "ahora", "hace 5 min", "hace 2h").

#### Las insignias de agente (Agent Badges)

Cuando SantoniBot te responde, justo encima del texto de la respuesta puedes ver una **insignia de color verde** que indica cual agente especializado proceso tu consulta. Estas insignias son:

| Insignia | Significado |
|----------|-------------|
| **Agente de Finanzas** | Tu consulta fue procesada por el agente especializado en datos financieros (flujo de caja, cuentas por cobrar, cuentas por pagar, bancos) |
| **Agente de Contabilidad** | Tu consulta fue procesada por el agente de contabilidad (balance general, estado de resultados, libro mayor, asientos contables) |
| **Agente de Ventas** | Tu consulta fue procesada por el agente de ventas (clientes, facturacion, cobranzas, zonas, vendedores) |
| **Agente de RRHH** | Tu consulta fue procesada por el agente de recursos humanos (empleados, nomina, asistencia, vacaciones) |
| **Agente de Produccion** | Tu consulta fue procesada por el agente de produccion (produccion diaria, eficiencia, desperdicio) |
| **Agente de Compras Insumos** | Tu consulta fue procesada por el agente de compras de insumos (ordenes de compra, proveedores) |
| **Agente de Compras Productores** | Tu consulta fue procesada por el agente de compras a productores (arroz, maiz, productores) |
| **Asistente General** | Tu consulta fue procesada por el asistente general (preguntas generales que no corresponden a un departamento especifico) |
| **Sistema** | Mensaje del sistema (informacion tecnica o notificaciones) |

> **Para que sirve esto:** La insignia te ayuda a saber cual departamento del sistema proceso tu pregunta. Si ves que el agente no es el que esperabas, intenta reformular tu pregunta para que sea mas especifica.

### 4.4 Como escribir y enviar mensajes

#### Paso 1: Haz clic en el campo de texto
En la parte inferior de la pantalla veras un campo de texto que dice **"Escribe tu consulta..."**. Haz clic sobre el.

#### Paso 2: Escribe tu pregunta
Escribe tu pregunta en espanol, como si estuvieras hablando con alguien. No necesitas usar lenguaje tecnico ni formato especial. Simplemente pregunta lo que quieres saber.

Ejemplos:
- "Cuales son las ventas del mes?"
- "Dame el flujo de caja de enero"
- "Cuantos empleados activos hay?"

> **Limite de caracteres:** Cada mensaje puede tener hasta **2,000 caracteres**. Cuando te acerques al limite, veras un contador en la esquina inferior derecha del campo de texto. Si esta en color **amarillo**, te estas acercando al limite. Si esta en **rojo**, estas muy cerca. No podras escribir mas de 2,000 caracteres.

#### Paso 3: Envia tu mensaje

Tienes dos formas de enviar tu mensaje:

- **Opcion 1 (recomendada):** Presiona la tecla **Enter** en tu teclado.
- **Opcion 2:** Haz clic en el **boton verde con la flecha** que esta a la derecha del campo de texto.

> **Consejo: Nueva linea sin enviar.** Si quieres escribir un mensaje largo con varias lineas (sin que se envie cada vez que presionas Enter), usa la combinacion **Shift + Enter**. Esto agrega una linea nueva sin enviar el mensaje.

#### Paso 4: Espera la respuesta

Despues de enviar tu mensaje veras:

1. **Tu mensaje** aparece inmediatamente en una burbuja verde a la derecha.
2. **Un indicador de escritura** aparece a la izquierda: veras el avatar de SantoniBot con tres puntos verdes que rebotan y el texto **"Procesando consulta..."**. Esto significa que SantoniBot esta analizando tu pregunta y buscando los datos en el sistema.
3. **La respuesta** aparecera en una burbuja blanca a la izquierda una vez que SantoniBot termine de procesar.

> **Cuanto tarda?** Normalmente la respuesta llega en unos pocos segundos (entre 3 y 15 segundos, dependiendo de la complejidad de la consulta). Si la pregunta involucra muchos datos, puede tardar un poco mas. Ten paciencia.

> **Mientras SantoniBot procesa:** El campo de texto se desactiva temporalmente y el boton de enviar muestra un circulito girando. No puedes enviar otro mensaje hasta que SantoniBot termine de responder.

#### Atajos de teclado rapidos

En la parte inferior del campo de texto veras un recordatorio:

- **`Enter`** -- Enviar mensaje
- **`Shift+Enter`** -- Nueva linea (salto de linea sin enviar)

---

## 5. Ejemplos de consultas por departamento

SantoniBot tiene **7 agentes especializados**, uno para cada departamento. Aqui te mostramos ejemplos concretos de preguntas que puedes hacer. Recuerda que puedes hacer la pregunta con tus propias palabras; SantoniBot entiende lenguaje natural.

### 5.1 Finanzas

El agente de Finanzas maneja datos de flujo de caja, cuentas por cobrar, cuentas por pagar y saldos bancarios.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cual es el flujo de caja actual?" | Te muestra un resumen del flujo de caja con ingresos y egresos |
| "Muestrame las cuentas por cobrar vencidas" | Lista de facturas que ya pasaron su fecha de vencimiento y aun no se han cobrado |
| "Cual es el saldo de bancos hoy?" | Te muestra el saldo actualizado de las cuentas bancarias de la empresa |
| "Cuanto tenemos en cuentas por pagar?" | Resumen del total pendiente por pagar a proveedores |
| "Resumen de cuentas por pagar" | Detalle de las cuentas pendientes por pagar organizadas |
| "Cuentas por cobrar de este mes" | Todas las cuentas por cobrar generadas en el mes actual |
| "Cuanto hemos pagado a proveedores este mes?" | Total de pagos realizados a proveedores en el periodo |
| "Muestrame los movimientos bancarios de la semana" | Detalle de las transacciones bancarias recientes |

### 5.2 Contabilidad

El agente de Contabilidad maneja datos del balance general, estado de resultados, libro mayor y asientos contables.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Dame el balance general del primer trimestre 2025" | Balance general completo con activos, pasivos y patrimonio del periodo indicado |
| "Cual es el estado de resultados del mes?" | Estado de resultados (perdidas y ganancias) del mes en curso |
| "Muestrame el balance general actualizado" | Balance general con los datos mas recientes del sistema |
| "Resumen del libro mayor" | Resumen de las cuentas principales del libro mayor |
| "Balance de comprobacion actualizado" | Balance de comprobacion con debitos y creditos |
| "Cuales son los asientos contables de enero?" | Lista de asientos contables registrados en enero |
| "Resumen del estado de resultados este ano" | Estado de resultados acumulado del ano en curso |
| "Dame las cuentas con mayor movimiento este mes" | Las cuentas contables mas activas del periodo |

### 5.3 Ventas

El agente de Ventas maneja datos de facturacion, clientes, cobranzas, vendedores y zonas de venta.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cuales son los top 10 clientes?" | Ranking de los 10 clientes con mayor facturacion |
| "Cuales son los top 20 clientes por ventas?" | Ranking ampliado con los 20 mejores clientes |
| "Ranking de ventas por zona" | Comparativo de ventas agrupado por zonas geograficas |
| "Cuanto hemos cobrado este mes?" | Total de cobranzas realizadas en el mes actual |
| "Ranking de vendedores del mes" | Lista de vendedores ordenados por monto vendido |
| "Cuales son las facturas vencidas?" | Facturas que ya pasaron su fecha de pago y no han sido cobradas |
| "Cuanto vendio Carlos Matias en enero?" | Ventas de un vendedor especifico en un periodo |
| "Resumen de ventas del mes por zona" | Desglose de ventas organizadas por zona |
| "Cuanto vendimos en enero?" | Total de ventas del mes de enero |
| "Dame las ventas de esta semana" | Resumen de la facturacion de la semana en curso |

> **Consejo:** Puedes preguntar lo mismo de muchas formas. Todas estas dan el mismo resultado:
> - "Cuanto vendimos en enero?"
> - "Total de ventas del mes de enero"
> - "Facturacion de enero"
> - "Dame las ventas de enero"

### 5.4 Recursos Humanos (RRHH)

El agente de RRHH maneja datos de empleados, nomina, asistencia y vacaciones.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cuantos empleados activos hay?" | Numero total de empleados activos en la empresa |
| "Cual es la nomina?" | Resumen general de la nomina actual |
| "Cuantos empleados hay por departamento?" | Desglose de empleados agrupados por cada departamento |
| "Resumen de nomina del mes" | Detalle de la nomina del mes (montos, deducciones, netos) |
| "Quienes han faltado esta semana?" | Lista de empleados con faltas registradas en la semana |
| "Quienes tienen asistencia pendiente?" | Empleados que tienen registros de asistencia sin completar |
| "Reporte de vacaciones pendientes" | Lista de empleados con dias de vacaciones acumuladas |
| "Dame el resumen de nomina de enero" | Detalle de la nomina correspondiente al mes de enero |

### 5.5 Produccion

El agente de Produccion maneja datos de produccion diaria, eficiencia de lineas y desperdicio.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cual es la produccion diaria de esta semana?" | Detalle dia por dia de la produccion de la semana actual |
| "Cual es la produccion de hoy?" | Resumen de lo producido en el dia de hoy |
| "Muestrame la eficiencia de la linea" | Porcentajes de eficiencia de las lineas de produccion |
| "Dame el resumen de eficiencia de esta semana" | Eficiencia promedio y por dia de la semana en curso |
| "Cuanto desperdicio tuvimos este mes?" | Total de desperdicio (merma) registrado en el mes |
| "Cuanto desperdicio hubo esta semana?" | Desperdicio registrado durante la semana actual |
| "Resumen de produccion mensual" | Vista consolidada de toda la produccion del mes |
| "Cual es la produccion acumulada del ano?" | Total producido en lo que va del ano |

### 5.6 Compras de Insumos

El agente de Compras de Insumos maneja datos de ordenes de compra, proveedores de insumos y materiales.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cuales son las ordenes de compra pendientes?" | Lista de ordenes de compra que aun no se han completado |
| "Cuanto se compro de insumos este mes?" | Total de compras de insumos en el mes actual |
| "Quienes son nuestros proveedores de empaques?" | Lista de proveedores que suministran materiales de empaque |
| "Top proveedores por monto de compra" | Ranking de proveedores ordenados por volumen de compra |
| "Ordenes de compra pendientes" | Ordenes que estan en proceso y aun no se reciben |
| "Resumen de compras de la semana" | Total y detalle de las compras realizadas en la semana |
| "Cuanto hemos gastado en insumos este trimestre?" | Total acumulado de compras de insumos del trimestre |

### 5.7 Compras de Productores

El agente de Compras de Productores maneja datos de compras de materia prima agricola (arroz, maiz) a productores del campo.

**Ejemplos de preguntas:**

| Pregunta | Que te responde |
|----------|-----------------|
| "Cuanto arroz hemos comprado en 2025?" | Total de compras de arroz paddy en el ano 2025 |
| "Cuanto es la compra de arroz paddy este ano?" | Volumen y monto total de compras de arroz en el ano |
| "Cuantos productores activos de maiz tenemos?" | Numero de productores de maiz que estan activos actualmente |
| "Cuales son los pagos pendientes a productores?" | Lista de pagos que se deben a productores |
| "Compras de maiz del mes actual" | Total de compras de maiz del mes en curso |
| "Top productores por volumen" | Ranking de productores ordenados por cantidad entregada |
| "Resumen de compras a productores" | Vista general de todas las compras a productores |
| "Cuanto le hemos comprado al productor Lopez?" | Compras a un productor especifico |

---

## 6. Como exportar datos (CSV, Excel, PDF)

Una de las funciones mas utiles de SantoniBot es la capacidad de **descargar los datos** que te muestra en diferentes formatos. Esto es especialmente util cuando la respuesta contiene tablas con mucha informacion.

### Cuando aparecen los botones de exportacion

Los botones de exportacion aparecen **automaticamente** debajo de cualquier respuesta de SantoniBot que contenga una tabla de datos. Si la respuesta es solo texto (sin tabla), los botones no aparecen.

Los botones de exportacion se encuentran en la esquina inferior derecha de la burbuja de respuesta, junto a un pequeno icono de descarga.

### Los tres formatos disponibles

Veras **tres iconos pequenos** junto al icono de descarga:

#### 1. CSV (icono de tabla)
- **Que es:** Un archivo de texto donde los datos estan separados por comas. Es el formato mas sencillo.
- **Extension del archivo:** `.csv`
- **Para que sirve:** Para abrir en Excel, Google Sheets, o cualquier programa de hojas de calculo. Tambien sirve para importar datos a otros sistemas.
- **Cuando usarlo:** Cuando necesites procesar los datos en una hoja de calculo o hacer analisis adicionales.

**Como usarlo:**
1. Busca el icono de tabla (columnas) que esta a la derecha del icono de descarga.
2. Haz clic sobre el.
3. El archivo se descargara automaticamente a tu carpeta de Descargas con el nombre `santonibot_reporte.csv`.
4. Abre el archivo con Excel o Google Sheets.

#### 2. Excel (icono de hoja de calculo)
- **Que es:** Un archivo nativo de Microsoft Excel, listo para abrir.
- **Extension del archivo:** `.xlsx`
- **Para que sirve:** Para trabajar directamente en Excel con formato, columnas ajustadas y datos organizados.
- **Cuando usarlo:** Cuando quieras un archivo de Excel ya formateado, listo para presentar o compartir con companeros.

**Como usarlo:**
1. Busca el icono de hoja de calculo (con las lineas y la pestana verde) que esta al centro de los tres botones.
2. Haz clic sobre el.
3. El archivo se descargara automaticamente como `santonibot_reporte.xlsx`.
4. Haz doble clic en el archivo descargado para abrirlo en Excel.

#### 3. PDF (icono de documento)
- **Que es:** Un documento PDF (Portable Document Format), ideal para imprimir.
- **Extension del archivo:** `.pdf`
- **Para que sirve:** Para imprimir reportes, guardarlos como documentos formales, o enviarlos por correo electronico.
- **Cuando usarlo:** Cuando necesites un documento presentable para imprimir, adjuntar a un informe, o enviar a alguien por correo.

**Como usarlo:**
1. Busca el icono de documento (con las lineas de texto) que esta mas a la derecha.
2. Haz clic sobre el.
3. El archivo se descargara automaticamente como `santonibot_reporte.pdf`.
4. Abre el archivo con tu visor de PDF (Adobe Reader, el visor del navegador, etc.).

### Resumen rapido de formatos

| Formato | Icono | Extension | Mejor para |
|---------|-------|-----------|------------|
| **CSV** | Tabla con columnas | `.csv` | Abrir en Excel para analizar datos, importar a otros sistemas |
| **Excel** | Hoja con pestana verde | `.xlsx` | Archivo de Excel listo para presentar o compartir |
| **PDF** | Documento con texto | `.pdf` | Imprimir, adjuntar a correos, archivo formal |

> **Donde se guardan los archivos descargados?** Por defecto, todos los archivos se guardan en la carpeta **"Descargas"** de tu computadora. Si tu navegador te pregunta donde guardar, elige la ubicacion que prefieras.

---

## 7. Boton de copiar respuesta

Cada respuesta de SantoniBot tiene un **boton de copiar** que te permite copiar todo el texto de la respuesta al portapapeles de tu computadora.

### Como usar el boton de copiar

1. **Ubica la respuesta** de SantoniBot que quieras copiar.
2. **Pasa el mouse** sobre la burbuja de la respuesta (no necesitas hacer clic todavia).
3. Veras aparecer un **pequeno boton con un icono de copiar** (dos cuadrados superpuestos) en la **esquina superior derecha** de la burbuja.
4. **Haz clic** en el boton de copiar.
5. El icono cambiara temporalmente a una **marca de verificacion verde** (un checkmark), lo que significa que el texto se copio exitosamente.
6. Ahora puedes **pegar** el texto donde quieras usando **Ctrl + V** (o clic derecho y "Pegar").

### Para que sirve copiar

- **Pegar en un correo electronico:** Copia la respuesta y pegala en tu email para compartirla con un companero.
- **Pegar en un documento de Word:** Copia los datos para incluirlos en un informe.
- **Pegar en WhatsApp u otro chat:** Comparte informacion rapidamente.
- **Pegar en una hoja de calculo:** Si la respuesta contiene numeros o tablas, puedes pegarlos directamente.

> **Diferencia con exportar:** El boton de copiar copia el **texto tal cual** de la respuesta. Si necesitas un archivo formateado (con tablas bien organizadas), usa los botones de exportar a CSV, Excel o PDF.

---

## 8. Como funcionan las conversaciones

SantoniBot organiza tus consultas en **conversaciones**. Entender como funcionan te ayudara a sacarle el mejor provecho al sistema.

### Que es una conversacion

Una conversacion es un grupo de preguntas y respuestas que estan relacionadas entre si. Cada vez que abres una conversacion nueva, SantoniBot empieza "desde cero", sin recordar lo que hablaste en conversaciones anteriores.

### Titulo automatico

Cuando haces tu primera pregunta en una conversacion nueva, SantoniBot automaticamente le pone un titulo basado en tu primera pregunta. Por ejemplo, si tu primera pregunta es "Cuales son los top 10 clientes por ventas?", la conversacion se titulara algo como "Cuales son los top 10 clientes por...".

### El contexto dentro de una conversacion

Dentro de una **misma conversacion**, SantoniBot recuerda lo que ya hablaron. Esto significa que puedes hacer preguntas de seguimiento sin repetir todo el contexto.

**Ejemplo:**
- Tu: "Cuales son las ventas de enero?"
- SantoniBot: (te muestra las ventas de enero)
- Tu: "Y en febrero?"
- SantoniBot: (entiende que te refieres a las ventas de febrero y te las muestra)

Esto funciona porque la conversacion mantiene el **contexto**. SantoniBot "recuerda" que estaban hablando de ventas.

### Iniciar una nueva conversacion

Para iniciar una conversacion nueva:

1. Haz clic en el boton **"Nueva conversacion"** en la barra lateral izquierda.
2. El area de chat se limpiara y veras la pantalla de bienvenida con las sugerencias.
3. Escribe tu nueva pregunta.

**Cuando conviene iniciar una conversacion nueva:**
- Cuando cambias completamente de tema (de ventas a RRHH, por ejemplo).
- Cuando la conversacion se vuelve muy larga y quieres empezar de cero.
- Cuando quieres hacer una consulta independiente que no tiene relacion con lo anterior.

### Ver una conversacion anterior

1. En la barra lateral izquierda, busca la conversacion que quieres revisar.
2. Puedes usar el campo de busqueda si tienes muchas conversaciones. Escribe una palabra clave (por ejemplo, "nomina" o "ventas").
3. Haz clic sobre la conversacion.
4. Se cargaran todos los mensajes de esa conversacion en el area principal.

### Buscar conversaciones

1. En la barra lateral, haz clic en el campo que dice **"Buscar conversaciones..."**.
2. Escribe lo que buscas. La lista se filtra en tiempo real.
3. Si no se encuentra nada, veras el mensaje: **"No se encontraron conversaciones"**.
4. Para volver a ver todas tus conversaciones, haz clic en la **X** que aparece a la derecha del campo de busqueda, o borra lo que escribiste.

### Eliminar una conversacion

1. En la barra lateral, pasa el mouse sobre la conversacion que quieres eliminar.
2. Aparecera un icono de **basura (papelera)** a la derecha del titulo.
3. Haz clic en el icono de basura.
4. La conversacion se eliminara inmediatamente.

> **Advertencia:** La eliminacion es **permanente**. Una vez eliminada, no puedes recuperar la conversacion ni sus mensajes. Si la conversacion contiene informacion importante, exporta los datos primero antes de eliminarla.

---

## 9. Que hacer si te sale "Acceso Denegado"

### Por que aparece este mensaje

En SantoniBot, cada usuario tiene acceso **unicamente a los datos de su departamento**. Esto es una medida de seguridad para proteger la informacion confidencial de la empresa.

Por ejemplo:
- Si eres del departamento de **Ventas**, puedes consultar datos de ventas, clientes, cobranzas y vendedores.
- Si eres del departamento de **RRHH**, puedes consultar datos de empleados, nomina y asistencia.
- **Pero** un usuario de Ventas **no puede** consultar datos de RRHH, y viceversa.

Si intentas hacer una consulta sobre un departamento al que no tienes acceso, SantoniBot te informara que **no tienes permiso** para ver esa informacion.

### Que hacer

1. **Verifica que tu pregunta corresponde a tu departamento.** A veces la pregunta puede ser ambigua y SantoniBot la dirige a otro departamento. Intenta ser mas especifico.

2. **Si realmente necesitas esa informacion:** Contacta a tu supervisor y explicale que necesitas datos de otro departamento. El supervisor puede:
   - Pedirle al administrador que te otorgue acceso adicional a ese departamento.
   - Solicitar la informacion el mismo si tiene permisos de supervisor.

3. **Si crees que es un error** (por ejemplo, eres de Finanzas y no puedes ver datos de Finanzas), contacta al administrador del sistema. Es posible que tu usuario no este configurado correctamente.

### Los roles del sistema

| Rol | Acceso |
|-----|--------|
| **Usuario** | Solo puede consultar datos de su departamento asignado |
| **Supervisor** | Puede consultar datos de su departamento y departamentos adicionales que le configure el administrador |
| **Administrador** | Acceso completo a todos los departamentos, mas el Panel de Administracion |

---

## 10. Que hacer si ocurre un error

A veces pueden ocurrir errores. Aqui te explicamos los mas comunes y como resolverlos.

### Error al procesar la consulta

Si despues de enviar tu mensaje ves un mensaje como: **"Lo siento, ocurrio un error al procesar tu consulta"**, seguido de un detalle del error:

1. **Intenta reformular tu pregunta.** A veces el error se debe a que la pregunta es muy ambigua o tiene una estructura que el sistema no logro interpretar.
2. **Intenta de nuevo.** Puede ser un error temporal. Haz la misma pregunta una segunda vez.
3. **Inicia una conversacion nueva.** Haz clic en "Nueva conversacion" e intenta de nuevo.
4. **Si el error persiste:** Anota el mensaje de error y reportalo al administrador del sistema.

### La pagina no carga o se ve en blanco

1. **Verifica tu conexion a internet.** Asegurate de que estas conectado a la red de la empresa.
2. **Recarga la pagina.** Presiona **F5** o **Ctrl + R** en tu teclado.
3. **Limpia la cache del navegador.** Presiona **Ctrl + Shift + Supr** y selecciona "Datos en cache" o "Archivos temporales". Luego haz clic en "Borrar datos" y recarga la pagina.
4. **Intenta con otro navegador.** Si usas Chrome, intenta con Firefox o Edge.
5. **Si nada funciona:** Contacta al equipo de sistemas.

### SantoniBot tarda mucho en responder

Si el indicador de "Procesando consulta..." lleva mas de 30 segundos:

1. **Espera un poco mas.** Algunas consultas complejas con muchos datos pueden tardar hasta 30-60 segundos.
2. **Si ya paso mas de un minuto:** Recarga la pagina (F5), inicia sesion de nuevo e intenta otra vez.
3. **Si sigue fallando:** El servidor podria estar experimentando un problema. Contacta al administrador.

### Soy redirigido a la pantalla de login sin motivo

Esto puede pasar si tu sesion expiro. Las sesiones tienen un tiempo limite por seguridad.

1. Simplemente ingresa tu usuario y contrasena de nuevo.
2. Si te sigue sacando inmediatamente despues de ingresar, limpia la cache del navegador y vuelve a intentar.
3. Si el problema continua, contacta al administrador.

### Error al exportar datos

Si al hacer clic en un boton de exportar (CSV, Excel o PDF) ves un mensaje de error:

1. **Verifica que aun estas conectado.** Si tu sesion expiro, el export fallara. Inicia sesion de nuevo.
2. **Intenta el mismo export de nuevo.**
3. **Intenta con otro formato.** Si CSV falla, intenta Excel o PDF.
4. **Si ninguno funciona:** Usa el boton de copiar como alternativa temporal y pega los datos donde los necesites.

---

## 11. Panel de Administracion (solo administradores)

El Panel de Administracion es una seccion especial de SantoniBot disponible **unicamente** para usuarios con el rol de **Administrador**. Si tu rol es Usuario o Supervisor, no tendras acceso a esta seccion y no veras el enlace en la barra lateral.

### Como acceder al Panel de Administracion

1. Inicia sesion con tu usuario de administrador.
2. En la barra lateral izquierda, en la parte inferior (justo encima de tu informacion de perfil), veras un enlace con un icono de engranaje y el texto **"Administracion"**.
3. Haz clic sobre el.
4. Se abrira el Panel de Administracion en una nueva pantalla.

### Como volver al chat

En la parte superior izquierda del Panel de Administracion veras una flecha apuntando a la izquierda (`<-`). Haz clic sobre ella para volver a la pantalla de chat.

### Las tres pestanas del Panel de Administracion

El panel tiene tres pestanas en la parte superior. Haz clic sobre cualquiera para cambiar la vista:

---

#### Pestana 1: Estadisticas

Esta pestana te muestra un resumen general del uso del sistema. Veras **cuatro tarjetas** con la siguiente informacion:

| Tarjeta | Que muestra |
|---------|-------------|
| **Usuarios Activos** | Cantidad de usuarios activos del total de usuarios registrados (ejemplo: "15 / 20") |
| **Conversaciones** | Numero total de conversaciones creadas en el sistema |
| **Mensajes Totales** | Numero total de mensajes enviados (tanto de usuarios como de SantoniBot) |
| **Agentes Activos** | Cuantos de los 7 agentes han sido utilizados (ejemplo: "5 / 7") |

Debajo de las tarjetas veras un grafico de barras titulado **"Uso por Agente"** que muestra cuantas consultas ha procesado cada agente. Las barras estan ordenadas de mayor a menor, para que puedas ver rapidamente cuales son los departamentos que mas usan el sistema.

---

#### Pestana 2: Usuarios

Esta pestana te permite gestionar los usuarios del sistema. Veras:

- Un titulo que dice **"Usuarios"** con el total entre parentesis (ejemplo: "Usuarios (15)").
- Un boton **"Nuevo Usuario"** en la esquina superior derecha.
- Una tabla con todos los usuarios registrados.

**La tabla de usuarios muestra:**

| Columna | Descripcion |
|---------|-------------|
| **Nombre** | Nombre completo del usuario |
| **Usuario** | Nombre de usuario (username) para iniciar sesion |
| **Departamento** | Departamento asignado al usuario |
| **Rol** | Rol del usuario: Usuario (gris), Supervisor (azul) o Administrador (morado) |
| **Estado** | Un punto verde si el usuario esta activo, o gris si esta desactivado |
| **Acciones** | Icono de basura para eliminar el usuario |

##### Como crear un nuevo usuario

1. Haz clic en el boton **"Nuevo Usuario"** (boton verde con el icono "+").
2. Se abrira un formulario con los siguientes campos:
   - **Nombre completo:** El nombre real del empleado (ejemplo: "Maria Rodriguez")
   - **Username:** El nombre de usuario para iniciar sesion (ejemplo: "mrodriguez"). Debe ser unico.
   - **Email:** Correo electronico del empleado.
   - **Contrasena:** La contrasena inicial para el usuario.
   - **Rol:** Selecciona uno de la lista:
     - **Usuario:** Acceso basico, solo a su departamento.
     - **Supervisor:** Acceso a su departamento y posibles departamentos adicionales.
     - **Administrador:** Acceso completo a todo el sistema, incluyendo este panel.
   - **Departamento:** Selecciona el departamento principal del usuario (Finanzas, Contabilidad, Ventas, RRHH, Produccion, Compras Insumos o Compras Productores).
3. Haz clic en el boton **"Crear"** para registrar al usuario.
4. Si quieres cancelar, haz clic en **"Cancelar"**.

> **Consejo:** Despues de crear un usuario, comunica el nombre de usuario y la contrasena al empleado personalmente o de forma segura. Recomienda al usuario cambiar su contrasena en el primer inicio de sesion.

##### Como eliminar un usuario

1. En la tabla de usuarios, busca al usuario que deseas eliminar.
2. Haz clic en el icono de **basura** (papelera roja) a la derecha de la fila de ese usuario.
3. Aparecera una ventana de confirmacion que pregunta: **"Estas seguro de eliminar este usuario?"**
4. Haz clic en **"Aceptar"** para confirmar, o **"Cancelar"** para no hacer nada.

> **Advertencia:** Eliminar un usuario es permanente. Si solo quieres suspender temporalmente el acceso, es mejor desactivar al usuario en lugar de eliminarlo.

---

#### Pestana 3: Auditoria

Esta pestana muestra el **registro de auditoria**: un historial detallado de todas las acciones realizadas en el sistema. Esto es muy importante para la seguridad y el control.

**La tabla de auditoria muestra:**

| Columna | Descripcion |
|---------|-------------|
| **Fecha** | Fecha y hora exacta de la accion |
| **Usuario** | Nombre completo y username del usuario que realizo la accion |
| **Accion** | Tipo de accion realizada (ver tabla abajo) |
| **Detalle** | Descripcion breve de lo que se hizo (por ejemplo, la pregunta que se realizo) |
| **Agente** | Cual agente proceso la consulta (si aplica) |
| **IP** | Direccion IP desde donde se conecto el usuario |

**Tipos de acciones registradas:**

| Accion | Color | Significado |
|--------|-------|-------------|
| **Inicio sesion** | Verde | Un usuario inicio sesion correctamente |
| **Login fallido** | Rojo | Alguien intento iniciar sesion con credenciales incorrectas |
| **ACCESO DENEGADO** | Rojo | Un usuario intento acceder a datos de un departamento sin permiso |
| **Consulta** | Azul | Un usuario realizo una consulta al chat |

> **Las filas resaltadas en rojo** corresponden a intentos de acceso denegado o logins fallidos. Presta atencion a estos registros, ya que podrian indicar intentos de acceso no autorizado.

> **Para que sirve la auditoria:** Te permite saber quien consulto que, cuando, y desde donde. Es util para detectar problemas de seguridad, verificar el uso del sistema, y llevar un control de la actividad.

---

## 12. Consejos de seguridad

La seguridad de la informacion de la empresa depende de todos. Sigue estos consejos para mantener tu cuenta y los datos de la empresa seguros:

### Tu contrasena

- **No compartas tu contrasena con nadie.** Tu contrasena es personal e intransferible. Ni siquiera tu supervisor deberia pedirtela.
- **No escribas tu contrasena en papeles o notas adhesivas.** Especialmente no la pegues en tu monitor o debajo del teclado.
- **No uses contrasenas faciles de adivinar.** Evita contrasenas como "123456", "santoni", tu fecha de nacimiento o tu nombre.
- **Si sospechas que alguien conoce tu contrasena,** contacta al administrador inmediatamente para que te la cambie.
- **Usa una contrasena diferente** a las que usas en tus cuentas personales (correo personal, redes sociales, etc.).

### Tu sesion

- **Cierra sesion cuando termines de usar el sistema.** Haz clic en el icono de **cerrar sesion** (la flecha de salida) en la parte inferior de la barra lateral. Esto es especialmente importante si:
  - Compartes computadora con otros companeros.
  - Vas a dejar tu escritorio por un periodo largo (almuerzo, reunion, fin de jornada).
  - Usas una computadora publica o compartida.
- **Bloquea tu computadora** cuando te levantes de tu puesto, incluso si es por poco tiempo. En Windows: **Win + L**. En Mac: **Ctrl + Cmd + Q**.
- **No dejes la sesion abierta en navegadores publicos** (cibercafes, computadoras de amigos, etc.).

### Tus datos

- **No compartas las respuestas de SantoniBot con personas fuera de la empresa.** La informacion del sistema es confidencial.
- **Ten cuidado al exportar datos.** Los archivos CSV, Excel y PDF contienen datos de la empresa. No los envies a correos personales ni los subas a servicios de almacenamiento publicos (Google Drive personal, etc.).
- **Si envias un reporte exportado por correo,** asegurate de enviarlo solo a personas autorizadas dentro de la empresa.

### Comportamiento sospechoso

- **Si ves mensajes de "Acceso Denegado" que no generaste tu,** alguien podria estar usando tu cuenta. Cambia tu contrasena inmediatamente y notifica al administrador.
- **Si notas que aparecen conversaciones que no creaste,** contacta al administrador.
- **Si recibes un correo o mensaje pidiendote tu contrasena de SantoniBot,** no respondas. Es un intento de fraude. El administrador nunca te pedira tu contrasena por correo.

---

## 13. Preguntas frecuentes

### Sobre el sistema

**El bot puede modificar datos en el sistema iDempiere?**
No. SantoniBot solo **lee** informacion. No puede crear facturas, modificar clientes, registrar pagos ni realizar ningun cambio en los datos. Puedes usarlo con total tranquilidad.

**Las consultas quedan registradas?**
Si. Todas las consultas quedan en el registro de auditoria para fines de seguridad. El administrador puede ver que consultaste, cuando y desde que direccion IP.

**Puedo consultar datos de anos anteriores?**
Si. Simplemente especifica el ano en tu pregunta. Por ejemplo: "ventas del 2024", "produccion de marzo 2023", "nomina de diciembre 2024". SantoniBot buscara los datos del periodo que indiques.

**Que tan precisa es la informacion?**
Los datos vienen directamente del sistema iDempiere en tiempo real. La informacion esta tan actualizada como lo esten los datos en el sistema. Si un dato se acaba de registrar en iDempiere, SantoniBot lo podra consultar inmediatamente.

### Sobre las preguntas

**Puedo hacer la misma pregunta de diferentes formas?**
Si. SantoniBot entiende lenguaje natural. Todas estas preguntas dan el mismo resultado:
- "Cuanto vendimos en enero?"
- "Total de ventas del mes de enero"
- "Facturacion de enero"
- "Dame las ventas de enero"
- "Muestrame las ventas de enero"
- "Cuales fueron las ventas en enero?"

**El bot entiende ingles?**
El sistema esta configurado para responder en espanol. Puede entender preguntas en ingles, pero siempre respondera en espanol.

**Hay un limite en la longitud de las preguntas?**
Si. Cada mensaje puede tener un maximo de **2,000 caracteres**. Esto es mas que suficiente para cualquier pregunta normal. Si necesitas dar mucho contexto, intenta ser conciso.

**Puedo hacer varias preguntas en un solo mensaje?**
Es mejor hacer una pregunta a la vez para obtener respuestas mas precisas. Si haces varias preguntas en un solo mensaje, SantoniBot intentara responderlas todas, pero es posible que se pierda alguna.

### Sobre las respuestas

**La respuesta es muy larga y no se ve bien.**
Si la respuesta contiene una tabla grande, usa los botones de exportacion (CSV, Excel, PDF) para descargar los datos en un formato mas comodo para leer.

**La respuesta no es lo que esperaba.**
Intenta reformular tu pregunta de manera mas especifica. Por ejemplo, en vez de "dame datos", intenta "muestrame las ventas del mes de enero 2025 por zona".

**SantoniBot me dice que no tiene informacion.**
Puede ser que los datos no esten cargados en el sistema iDempiere para el periodo que consultaste, o que tu pregunta no se relacione con datos disponibles. Verifica con tu departamento que los datos esten registrados en el sistema.

### Sobre la seguridad

**Que pasa si alguien ve mi pantalla mientras uso SantoniBot?**
Los datos de la empresa son confidenciales. Si trabajas en un area abierta, ten cuidado con lo que consultas cuando haya personas no autorizadas cerca. Puedes cerrar la barra lateral para tener mas espacio y ocultar el historial de conversaciones.

**Puedo usar SantoniBot desde mi telefono?**
Si, SantoniBot funciona en navegadores de telefono. La interfaz se adapta automaticamente a pantallas pequenas. La barra lateral se oculta automaticamente y puedes abrirla con el boton de menu.

---

## 14. Soporte tecnico

Si tienes algun problema que no pudiste resolver con este manual:

### Pasos antes de pedir ayuda

1. **Verifica tu conexion a internet.** Intenta abrir otra pagina web para confirmar.
2. **Recarga la pagina.** Presiona F5 o Ctrl+R.
3. **Cierra sesion e ingresa nuevamente.** A veces esto resuelve problemas de sesion.
4. **Intenta con otro navegador.** Si usas Chrome, prueba con Firefox o Edge.
5. **Revisa este manual.** Es posible que la respuesta este en las secciones anteriores.

### Como contactar al soporte

Si despues de seguir los pasos anteriores el problema persiste:

1. **Contacta al administrador del sistema** de tu empresa.
2. Al reportar un problema, incluye la siguiente informacion:
   - **Tu nombre y usuario**
   - **Que estabas haciendo** cuando ocurrio el problema (por ejemplo: "estaba preguntando por las ventas de enero")
   - **Que mensaje de error viste** (si hubo alguno, copialo exactamente)
   - **Que navegador usas** (Chrome, Firefox, Edge) y en que computadora
   - **La hora aproximada** en que ocurrio el problema

Mientras mas detalles des, mas rapido podran resolver tu problema.

---

> **Nota importante:** SantoniBot es un asistente inteligente que puede cometer errores. Como dice el mensaje que aparece en la parte inferior del chat: **"SantoniBot puede cometer errores. Verifica la informacion."** Si un dato te parece incorrecto o inusual, verificalo directamente en el sistema iDempiere antes de tomar decisiones importantes basadas en el.

---

*SantoniBot -- Sistema Inteligente de Analisis de Datos Empresariales*
*Desarrollado por OVA Agency para Alimentos Santoni, C.A.*
*Febrero 2026*
