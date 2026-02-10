# SantoniBot - Manual de Usuario

## ¿Qué es SantoniBot?

SantoniBot es un asistente inteligente que le permite consultar información de su empresa usando lenguaje natural. En vez de abrir reportes en el sistema, simplemente escriba su pregunta y SantoniBot le dará la respuesta.

---

## Cómo Ingresar

1. Abra su navegador web (Chrome, Firefox, Edge)
2. Vaya a la dirección que le proporcionó su supervisor
3. Ingrese su **usuario** y **contraseña**
4. Haga clic en **"Ingresar"**

> Si olvidó su contraseña, contacte al administrador del sistema.

---

## Pantalla Principal - Chat

Al ingresar verá la pantalla de chat con tres áreas:

- **Barra lateral izquierda:** Sus conversaciones anteriores
- **Área central:** El chat donde escribe y lee respuestas
- **Sugerencias:** Preguntas sugeridas para su departamento

### Escribir una consulta

1. Escriba su pregunta en el campo de texto inferior
2. Presione **Enter** para enviar (o haga clic en el botón de enviar)
3. Espere la respuesta (verá puntos animados mientras procesa)

> **Tip:** Use **Shift + Enter** para agregar una nueva línea sin enviar el mensaje.

---

## Ejemplos de Consultas por Departamento

### Ventas
- "¿Cuáles son los top 10 clientes por facturación este año?"
- "¿Cuánto hemos cobrado este mes?"
- "¿Cuáles son las facturas vencidas?"
- "Dame un ranking de vendedores del último trimestre"
- "¿Cuánto vendió Carlos Matias en enero?"

### Finanzas
- "¿Cuál es el flujo de caja actual?"
- "¿Cuánto tenemos en cuentas por pagar?"
- "Muéstrame el saldo de las cuentas bancarias"
- "¿Cuáles son las cuentas por cobrar vencidas?"

### Contabilidad
- "Dame el balance general del primer trimestre"
- "¿Cuáles son los asientos contables de enero?"
- "Resumen del estado de resultados este año"

### Recursos Humanos
- "¿Cuántos empleados activos tenemos?"
- "Dame el resumen de nómina de enero"
- "¿Quiénes han faltado esta semana?"

### Producción
- "¿Cuál es la producción de hoy?"
- "Dame el resumen de eficiencia de esta semana"
- "¿Cuánto desperdicio tuvimos este mes?"

### Compras de Insumos
- "¿Cuáles son las órdenes de compra pendientes?"
- "¿Quiénes son nuestros proveedores de empaques?"

### Compras de Productores
- "¿Cuánto arroz hemos comprado este mes?"
- "¿Cuántos productores activos de maíz tenemos?"
- "¿Cuáles son los pagos pendientes a productores?"

---

## Funciones del Chat

### Copiar respuesta
Pase el cursor sobre cualquier respuesta del bot y verá un botón de **copiar** en la esquina. Haga clic para copiar el texto al portapapeles.

### Exportar datos
Cuando el bot responde con una tabla de datos, aparecerán tres botones:

| Botón | Formato | Para qué sirve |
|-------|---------|-----------------|
| **CSV** | Texto separado por comas | Abrir en Excel o Google Sheets |
| **Excel** | Archivo .xlsx | Archivo de Excel listo para usar |
| **PDF** | Documento PDF | Para imprimir o compartir |

Simplemente haga clic en el botón del formato que desee y se descargará automáticamente.

### Conversaciones

- **Nueva conversación:** Haga clic en "Nueva conversación" en la barra lateral
- **Ver conversación anterior:** Haga clic sobre ella en la barra lateral
- **Buscar conversación:** Use el campo de búsqueda en la barra lateral
- **Eliminar conversación:** Haga clic en el ícono de basura junto a la conversación

> Cada conversación mantiene contexto. Si pregunta "¿y en febrero?" después de preguntar por ventas de enero, el bot entenderá que se refiere a ventas.

---

## Permisos

Cada usuario tiene acceso **solo a los datos de su departamento**. Por ejemplo:
- Un usuario de Ventas no puede consultar datos de RRHH
- Un usuario de Finanzas no puede ver datos de Producción

Si intenta consultar datos fuera de su departamento, el bot le informará que no tiene acceso.

Los **supervisores** pueden tener acceso a departamentos adicionales según lo configure el administrador.

---

## Panel de Administración

Solo disponible para usuarios con rol **Administrador**.

### Acceso
Haga clic en "Administración" en la barra lateral.

### Pestañas disponibles

1. **Estadísticas**
   - Cantidad de usuarios activos
   - Total de conversaciones y mensajes
   - Uso por agente (gráfico)

2. **Usuarios**
   - Crear nuevos usuarios
   - Editar rol y departamento
   - Activar/desactivar usuarios
   - Eliminar usuarios

3. **Auditoría**
   - Registro de todas las acciones del sistema
   - Quién consultó qué y cuándo

### Crear un nuevo usuario
1. Ir a Administración → Usuarios
2. Clic en "Nuevo Usuario"
3. Llenar: nombre de usuario, nombre completo, email, contraseña
4. Seleccionar **rol** (Usuario, Supervisor, Administrador)
5. Seleccionar **departamento**
6. Clic en "Crear"

---

## Preguntas Frecuentes

**¿El bot puede modificar datos en el sistema?**
No. SantoniBot solo **lee** información. No puede crear facturas, modificar clientes ni realizar ningún cambio en los datos.

**¿Las consultas quedan registradas?**
Sí. Todas las consultas quedan en el registro de auditoría para fines de seguridad.

**¿Puedo consultar datos de años anteriores?**
Sí. Especifique el año en su pregunta: "ventas del 2024" o "producción de marzo 2023".

**¿Qué tan precisa es la información?**
Los datos vienen directamente del sistema iDempiere. El bot consulta la base de datos en tiempo real, así que la información está tan actualizada como lo está el sistema.

**¿Puedo hacer la misma pregunta de diferentes formas?**
Sí. El bot entiende lenguaje natural. Estas preguntas dan el mismo resultado:
- "¿Cuánto vendimos en enero?"
- "Total de ventas del mes de enero"
- "Facturación de enero"
- "Dame las ventas de enero"

**¿El bot entiende inglés?**
El sistema está configurado para responder en español. Puede entender preguntas en inglés, pero siempre responderá en español.

**La respuesta es muy larga y no se ve bien:**
Use los botones de exportación (CSV, Excel, PDF) para ver los datos en un formato más cómodo.

---

## Soporte

Si tiene algún problema:
1. Verifique su conexión a internet
2. Intente cerrar sesión e ingresar nuevamente
3. Si el problema persiste, contacte al administrador del sistema

---

*SantoniBot - Desarrollado por OVA Agency para Alimentos Santoni, C.A.*
