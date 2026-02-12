# SantoniBot - Documento de Presentacion Completa del Proyecto

**Sistema Inteligente de Analisis de Datos Empresariales**
**Cliente:** Alimentos Santoni, C.A.
**Desarrollado por:** OVA Agency
**Fecha:** Febrero 2026

> Este documento describe de forma completa y detallada todo lo que es SantoniBot: que hace, como funciona, que tecnologias usa, que medidas de seguridad tiene, y por que es una solucion empresarial de nivel profesional. Esta pensado para servir como base para la creacion de un guion de video de presentacion.

---

## 1. QUE ES SANTONIBOT

SantoniBot es un sistema de inteligencia artificial empresarial que permite a los empleados de Alimentos Santoni, C.A. consultar datos de la empresa usando lenguaje natural, como si estuvieran hablando con un companero de trabajo. En vez de abrir reportes complicados, navegar menus de sistemas ERP o pedir informes a otros departamentos, el usuario simplemente escribe su pregunta y recibe la respuesta con datos reales en segundos.

### El problema que resuelve

En una empresa como Alimentos Santoni, la informacion esta dispersa en el sistema ERP (iDempiere), y acceder a ella requiere conocimiento tecnico o depender de otras personas. Un gerente de ventas que quiere saber sus top 10 clientes necesita abrir el ERP, navegar menus, generar un reporte, y esperar. Con SantoniBot, simplemente escribe "Cuales son mis top 10 clientes?" y recibe la respuesta en segundos, con tabla, grafica y opcion de descargar en Excel o PDF.

### En resumen

SantoniBot es un chatbot inteligente, conectado directamente al sistema ERP de Santoni, que entiende preguntas en espanol, busca los datos reales en la base de datos, y responde de forma clara con tablas, graficas y reportes exportables. Todo esto con control de acceso por departamento: cada usuario solo ve los datos que le corresponden.

---

## 2. ARQUITECTURA MULTI-AGENTE: 7 CEREBROS ESPECIALIZADOS

SantoniBot no es un chatbot generico. Tiene una arquitectura de multiples agentes de inteligencia artificial, donde cada departamento tiene su propio agente especializado con conocimiento profundo de su area.

### 2.1 El Orquestador

El corazon del sistema es el Orquestador: un agente central de IA que recibe cada pregunta del usuario, analiza la intencion, y la enruta automaticamente al agente especializado correcto. Si un usuario de Ventas pregunta "Cuales son mis top 10 clientes?", el Orquestador entiende que es una consulta de ventas y la envia al Agente de Ventas. Si el mismo usuario intenta preguntar sobre nomina (que pertenece a RRHH), el Orquestador detecta que no tiene permiso y le informa de forma amigable.

### 2.2 Los 7 Agentes de Departamento

Cada agente es un experto en su area. Sabe que tablas consultar, como interpretar los datos, y como presentar la informacion de forma util para el usuario.

**1. Agente de Finanzas**
Especialidad: Flujo de caja, cuentas por cobrar y pagar, saldos bancarios, indicadores financieros. Cuando un gerente de finanzas pregunta "Cual es el flujo de caja de este mes?", este agente consulta directamente las cuentas bancarias, los movimientos, las cuentas por cobrar y las cuentas por pagar, y presenta un resumen financiero completo con alertas de morosidad.

**2. Agente de Contabilidad**
Especialidad: Balance general, estado de resultados, libro mayor, balanza de comprobacion, asientos contables. Usa terminologia contable venezolana estandar y puede comparar periodos contables. Cuando le preguntas "Dame el balance general del primer trimestre", te lo presenta con activos, pasivos y patrimonio desglosados.

**3. Agente de Ventas**
Especialidad: Rankings de clientes, ventas por zona, vendedores, cobranzas, analisis Pareto (80/20), metas de venta. Es el agente mas completo: puede filtrar por zona (Portuguesa, Barinas, Lara, Carabobo, Aragua, Zulia), por vendedor (nombre especifico), o por periodo. Responde preguntas como "Top 20 clientes por ventas", "Ranking de vendedores del mes", "Cuanto hemos cobrado esta semana?", o "Cuales son las facturas vencidas?".

**4. Agente de Recursos Humanos (RRHH)**
Especialidad: Nomina, asistencia, empleados, vacaciones. Maneja datos altamente sensibles con cuidado especial. Conoce el contexto de Santoni: 2 plantas en Agua Blanca, oficinas administrativas en Araure, turnos rotativos en planta y horario de oficina de 7:30am a 5:00pm. Responde preguntas como "Cuantos empleados activos hay?", "Resumen de nomina del mes", "Quienes han faltado esta semana?".

**5. Agente de Produccion**
Especialidad: Produccion diaria, ordenes de produccion, eficiencia (OEE), desperdicio, mantenimiento. Conoce los productos de Santoni (Arroz Santoni Premium, Harina de Maiz Santoni) y las 2 plantas de Agua Blanca. Usa unidades metricas (kg, toneladas) y porcentajes de eficiencia. Responde preguntas como "Produccion diaria de esta semana", "Eficiencia de la linea", "Cuanto desperdicio hubo este mes?".

**6. Agente de Compras de Insumos**
Especialidad: Ordenes de compra de materiales, proveedores, inventario, precios. Maneja todo lo relacionado con la compra de insumos y materiales para la operacion. Responde preguntas como "Ordenes de compra pendientes", "Top proveedores por monto", "Cuanto gastamos en insumos este trimestre?".

**7. Agente de Compras a Productores**
Especialidad: Compras de materia prima agricola, especificamente Arroz Paddy Humedo y Maiz. Conoce las zonas productoras (Portuguesa, Barinas, Apure, Lara, Cojedes) y la responsable del area (Marlenis Figueredo). Maneja volumenes en kg/toneladas y precios en Bs./kg. Responde preguntas como "Cuanto arroz hemos comprado este ano?", "Pagos pendientes a productores", "Top productores por volumen".

### 2.3 Como funciona el flujo de una consulta

1. El usuario escribe su pregunta en lenguaje natural
2. El Orquestador clasifica la intencion y verifica los permisos del usuario
3. Si tiene acceso, la pregunta se envia al agente especializado
4. El agente consulta la base de datos de Santoni y obtiene los datos reales
5. La IA interpreta los datos y genera una respuesta clara en espanol
6. La respuesta se muestra al usuario con tablas formateadas y graficas interactivas
7. El usuario puede exportar los datos en CSV, Excel o PDF, o descargar la grafica como imagen

Todo este proceso ocurre en 3 a 15 segundos.

---

## 3. FUNCIONALIDADES DE LA PLATAFORMA

### 3.1 Chat Inteligente con IA

La interfaz principal es un chat donde el usuario escribe preguntas y recibe respuestas. Funciona como un WhatsApp empresarial con inteligencia artificial.

**Caracteristicas del chat:**
- Respuestas en espanol con datos reales del sistema ERP
- Tablas formateadas con estilo profesional (colores Santoni, bordes, encabezados)
- Graficas interactivas automaticas (barras, lineas, circular, area) con los colores de la marca
- Indicador de escritura animado mientras la IA procesa ("Procesando consulta...")
- Sugerencias de preguntas personalizadas segun el departamento del usuario
- Contador de caracteres (maximo 2,000 por mensaje)
- Soporte para Shift+Enter (nueva linea sin enviar)
- Cada respuesta muestra una insignia de color indicando cual agente la proceso

### 3.2 Historial de Conversaciones

Cada consulta se guarda en una conversacion con titulo automatico. El sistema mantiene un historial completo que el usuario puede:

- Ver todas sus conversaciones anteriores en la barra lateral
- Buscar conversaciones por palabra clave
- Retomar conversaciones previas (el contexto se mantiene)
- Eliminar conversaciones que ya no necesite
- Ver la hora relativa de cada conversacion ("ahora", "hace 5 min", "ayer")
- Ver una vista previa del ultimo mensaje

### 3.3 Exportacion de Datos en 3 Formatos

Cada respuesta que contiene una tabla tiene botones de exportacion para descargar los datos:

**CSV** - Archivo de texto separado por comas, compatible con Excel y cualquier hoja de calculo. Ideal para analisis adicional o importar a otros sistemas.

**Excel (.xlsx)** - Archivo de Excel formateado profesionalmente con:
- Encabezados con estilo corporativo Santoni (color naranja #E06400)
- Ancho de columnas ajustado automaticamente
- Formato numerico con separadores de miles y decimales
- Bordes en todas las celdas
- Filas alternadas en colores suaves
- Metadatos (agente, fecha) en la parte superior

**PDF** - Documento formal listo para imprimir con:
- Tipografia profesional (titulo 18pt, subtitulos 12pt, contenido 10pt)
- Colores corporativos Santoni
- Tablas con encabezados naranja y texto blanco en negrita
- Filas alternadas (blanco y naranja suave)
- Metadatos del agente y fecha de generacion

### 3.4 Graficas Interactivas

Cuando los datos se prestan para una representacion visual, el sistema genera graficas interactivas automaticamente:

- **Graficas de barras**: Para rankings, top N, comparativas (ejemplo: top 10 clientes)
- **Graficas de lineas**: Para tendencias en el tiempo (ejemplo: ventas mensuales)
- **Graficas circulares (pie)**: Para distribucion y composicion (ejemplo: ventas por zona)
- **Graficas de area**: Para acumulados en el tiempo (ejemplo: produccion acumulada)

Las graficas son interactivas: al pasar el mouse se muestra un tooltip con los valores exactos. Ademas, cada grafica tiene un boton para descargarla como imagen PNG en alta resolucion, ideal para incluir en presentaciones o informes.

### 3.5 Boton de Copiar Respuesta

Cada respuesta del bot tiene un boton de copiar que permite copiar todo el texto al portapapeles con un solo clic. Al copiar, el icono cambia a un check verde confirmando la accion. El texto copiado se puede pegar en correos electronicos, documentos de Word, WhatsApp o cualquier otra aplicacion.

### 3.6 Panel de Administracion

Los administradores del sistema tienen acceso a un panel completo de gestion con tres secciones:

**Estadisticas:**
- Total de usuarios, usuarios activos, total de conversaciones y mensajes
- Uso por agente: cuantas consultas ha procesado cada uno de los 7 agentes
- Metricas de uso: mensajes y conversaciones por dia, top usuarios, actividad por departamento

**Gestion de Usuarios:**
- Crear nuevos usuarios con rol, departamento y contrasena
- Editar usuarios existentes (cambiar rol, departamento, activar/desactivar)
- Eliminar usuarios (proteccion: no se puede eliminar a si mismo)
- Asignar departamentos adicionales a supervisores

**Auditoria:**
- Registro completo de todas las acciones del sistema
- Cada entrada muestra: usuario, accion, detalle, agente usado, IP, fecha/hora
- Acciones codificadas por color: verde (login), azul (consulta), rojo (acceso denegado, login fallido)
- Las filas de acceso denegado e intentos fallidos se resaltan en rojo
- Filtrable por usuario y tipo de accion

---

## 4. CONEXION CON EL ERP: DATOS REALES EN TIEMPO REAL

### 4.1 Integracion con iDempiere

SantoniBot se conecta directamente a la base de datos PostgreSQL del sistema ERP iDempiere de Alimentos Santoni. Esto significa que los datos que muestra son **reales y actualizados**, no son datos estaticos ni importados manualmente. No hay Excel, no hay carga manual de datos, no hay procesos de sincronizacion. Es una conexion directa en tiempo real.

### 4.2 Conexion de Solo Lectura

La conexion a la base de datos del ERP es estrictamente de solo lectura (SELECT). SantoniBot **nunca** puede modificar, crear ni eliminar datos del ERP bajo ninguna circunstancia. El usuario de base de datos tiene permisos exclusivamente de consulta. Esto garantiza que el sistema ERP esta completamente protegido.

### 4.3 Datos de Demostracion

Para pruebas y desarrollo, el sistema incluye un conjunto completo de datos de demostracion que simulan el entorno real de Santoni:
- 50 clientes con diferentes zonas y vendedores
- 200+ facturas de venta con lineas de detalle
- Registros de cobranza y metas de venta
- 30 empleados con nomina, asistencia y vacaciones
- Produccion diaria con eficiencia y desperdicio
- 15 proveedores de insumos con ordenes de compra
- 20 productores agricolas con guias de compra
- Asientos contables y balance general por periodo
- Cuentas bancarias con movimientos

Estos datos permiten demostrar completamente todas las capacidades del sistema sin necesitar acceso al ERP real.

---

## 5. SEGURIDAD: PROTECCION EMPRESARIAL COMPLETA

### 5.1 Autenticacion y Contrasenas

**Proteccion de contrasenas:** Todas las contrasenas se almacenan cifradas con BCrypt, el estandar de la industria para hashing de contrasenas. Ni siquiera un administrador de base de datos puede ver las contrasenas reales.

**Tokens JWT:** Una vez autenticado, el usuario recibe un token JWT (JSON Web Token) firmado digitalmente con clave secreta de minimo 32 caracteres. Este token tiene una duracion configurable (por defecto 8 horas) y contiene la informacion del usuario de forma segura. Cada peticion al servidor se valida con este token.

**Contrasena del administrador:** La contrasena del primer administrador se genera automaticamente de forma segura y se muestra una sola vez en los logs del sistema durante el primer arranque. No hay contrasenas por defecto.

### 5.2 Control de Acceso por Roles (RBAC)

El sistema implementa un control de acceso basado en roles y departamentos con 3 niveles:

**Usuario:** Solo puede consultar datos de su departamento asignado. Un usuario de Ventas no puede ver datos de RRHH ni de Finanzas.

**Supervisor:** Puede consultar datos de su departamento principal mas departamentos adicionales que le asigne el administrador. Por ejemplo, un supervisor puede tener acceso a Ventas y Compras.

**Administrador:** Acceso completo a todos los departamentos, mas el panel de administracion con gestion de usuarios y auditoria.

Este control se aplica a nivel del Orquestador de IA: antes de enrutar una pregunta a un agente, verifica que el usuario tenga permiso para acceder a ese departamento. Si no lo tiene, registra el intento y le informa amablemente al usuario.

### 5.3 Proteccion contra Ataques

**Limitacion de peticiones (Rate Limiting):** El sistema protege contra ataques de fuerza bruta y denegacion de servicio con limites por endpoint:
- API general: 30 peticiones por minuto
- Login: 5 intentos por minuto (proteccion contra fuerza bruta)
- Exportacion: 10 peticiones por minuto

**Encabezados de seguridad HTTP:** Cada respuesta del servidor incluye encabezados de seguridad que protegen contra:
- Clickjacking (X-Frame-Options)
- Inyeccion de contenido (X-Content-Type-Options)
- Cross-Site Scripting (X-XSS-Protection)
- Fuga de referencia (Referrer-Policy)
- Acceso a camara, microfono y geolocalizacion (Permissions-Policy)
- Politica de seguridad de contenido (CSP)

**CORS restrictivo:** Solo se permiten peticiones desde los dominios configurados, con metodos y encabezados especificos.

**Validacion de entrada:** Todos los datos que envian los usuarios se validan con schemas estrictos (Pydantic) antes de procesarse. Los mensajes de chat estan limitados a 2,000 caracteres.

**API de documentacion oculta:** En produccion, las paginas de documentacion Swagger/Redoc del API estan deshabilitadas para no exponer la estructura interna del sistema.

### 5.4 Auditoria Completa

Cada accion relevante del sistema se registra en un log de auditoria con la siguiente informacion:

- **Quien:** El usuario que realizo la accion (o "usuario desconocido" si fallo el login)
- **Que:** El tipo de accion (login, consulta, acceso denegado, login fallido)
- **Cuando:** Fecha y hora exacta con zona horaria
- **Donde:** La direccion IP desde donde se realizo la accion
- **Detalle:** Los primeros 200 caracteres de la consulta o el detalle del evento
- **Agente:** Cual agente de IA proceso la consulta

Los intentos de acceso denegado y los logins fallidos se registran especialmente y se resaltan en rojo en el panel de administracion, permitiendo detectar intentos de acceso no autorizado.

### 5.5 Proteccion de Datos Sensibles

Los datos de RRHH (nomina, salarios, asistencia) estan marcados como "altamente sensibles" dentro del sistema. Solo los usuarios con acceso al departamento de RRHH pueden consultar esta informacion. Ademas, los queries que se registran en el log de auditoria se truncan a 200 caracteres para no almacenar informacion sensible completa en los logs.

---

## 6. TECNOLOGIAS UTILIZADAS

### 6.1 Inteligencia Artificial

**Groq (Llama 3.3 70B)** - Motor principal de IA. Groq proporciona inferencia ultra-rapida usando chips LPU (Language Processing Units) especializados. El modelo Llama 3.3 de 70 mil millones de parametros de Meta es uno de los mas capaces del mundo en codigo abierto. Esto permite respuestas rapidas (3-15 segundos) con alta calidad de analisis.

**Claude API (Anthropic)** - Motor secundario preparado para integracion futura. El sistema tiene un factory de LLM que permite cambiar de Groq a Claude con solo modificar una variable de entorno, sin tocar codigo. Claude es especialmente fuerte en analisis de documentos, lo cual habilitara la funcion de adjuntar archivos para analisis.

**LangChain** - Framework de orquestacion de IA que gestiona la comunicacion con los modelos de lenguaje, el manejo de historial de conversaciones, y la integracion con la base de datos vectorial.

**ChromaDB** - Base de datos vectorial para el sistema RAG (Retrieval-Augmented Generation). Permite subir documentos de empresa (politicas, procedimientos, manuales) que enriquecen las respuestas de los agentes con contexto adicional. Cada departamento tiene su propia coleccion de documentos.

### 6.2 Backend

**Python 3.12 + FastAPI** - El backend esta construido con FastAPI, uno de los frameworks web mas modernos y rapidos de Python. Soporta operaciones asincronas, validacion automatica de datos, y documentacion auto-generada del API.

**PostgreSQL 16** - Base de datos interna del sistema (usuarios, conversaciones, mensajes, auditoria). PostgreSQL es la base de datos relacional de codigo abierto mas avanzada del mundo.

**SQLAlchemy** - ORM (Object-Relational Mapping) para interactuar con la base de datos de forma segura y eficiente, con modelos tipados y relaciones definidas.

**Alembic** - Sistema de migraciones de base de datos que permite evolucionar el esquema de forma controlada y versionada.

### 6.3 Frontend

**Next.js 14 + React 18** - El frontend esta construido con Next.js 14, el framework de React mas popular para aplicaciones web de produccion. Proporciona renderizado del lado del servidor, rutas automaticas, y optimizacion de rendimiento.

**TypeScript** - Todo el codigo frontend esta escrito en TypeScript, lo que proporciona seguridad de tipos y previene errores en tiempo de desarrollo.

**Tailwind CSS** - Framework de estilos con una paleta personalizada de colores corporativos de Santoni (naranja como color principal).

**Recharts** - Libreria de graficas interactivas basada en D3.js, la mas popular del ecosistema React. Genera graficas de barras, lineas, circulares y de area con animaciones suaves y tooltips interactivos.

**ReactMarkdown + remark-gfm** - Renderizado de markdown con soporte para tablas de GitHub Flavored Markdown, lo que permite que las respuestas de la IA se muestren con tablas formateadas profesionalmente.

### 6.4 Infraestructura

**Docker + Docker Compose** - Toda la aplicacion esta containerizada en 5 servicios:
1. Base de datos PostgreSQL 16
2. ChromaDB (base de datos vectorial)
3. Backend FastAPI (Python)
4. Frontend Next.js (Node.js)
5. Nginx (proxy reverso, seguridad, rate limiting)

Esto permite desplegar todo el sistema con un solo comando (`docker compose up -d`) y garantiza que funcione identicamente en cualquier servidor.

**Nginx** - Proxy reverso que maneja la seguridad a nivel de red: rate limiting, encabezados de seguridad, SSL/TLS, y enrutamiento de peticiones al backend y frontend.

**GitHub Actions** - Pipeline de CI/CD que automaticamente ejecuta pruebas y validaciones cada vez que se sube codigo nuevo:
- Backend: instala dependencias, ejecuta 150+ tests automatizados
- Frontend: instala dependencias, ejecuta lint, tests y build

### 6.5 Despliegue en Produccion

El sistema esta disenado para desplegarse en la VM de Santoni (192.168.1.26):
- Ubuntu 25.10 con 16GB RAM, 8 vCPU, 512GB SSD
- Scripts automatizados: setup-vm.sh (configuracion inicial), deploy.sh (despliegue), backup.sh (respaldo)
- Configuracion separada para desarrollo y produccion (docker-compose.prod.yml)
- En produccion: 4 workers del backend, sin hot-reload, debug desactivado, limites de recursos configurados

---

## 7. BASE DE CONOCIMIENTO (RAG)

### 7.1 Que es el sistema RAG

RAG significa "Retrieval-Augmented Generation" (Generacion Aumentada por Recuperacion). Es una tecnica que permite enriquecer las respuestas de la IA con informacion adicional de documentos de la empresa.

### 7.2 Como funciona

1. Un administrador sube documentos al sistema (politicas, procedimientos, manuales, reglas de negocio)
2. El sistema divide el documento en fragmentos y los almacena en ChromaDB con embeddings vectoriales
3. Cuando un usuario hace una pregunta, el sistema busca fragmentos relevantes en la base de conocimiento
4. Esos fragmentos se incluyen como contexto adicional para el agente de IA
5. El agente usa esa informacion adicional para dar respuestas mas completas y contextualizadas

### 7.3 Organizacion por departamento

Cada departamento tiene su propia coleccion de documentos, mas una coleccion "general" para politicas que aplican a toda la empresa. Cuando un agente procesa una consulta, busca en la coleccion de su departamento y tambien en la coleccion general.

### 7.4 Administracion de la base de conocimiento

Los administradores pueden:
- Subir documentos con texto, titulo y fuente
- Ver todas las colecciones y cuantos documentos tiene cada una
- Limpiar colecciones completas
- Probar consultas contra la base de conocimiento

### 7.5 Tolerancia a fallos

El sistema RAG es completamente opcional. Si ChromaDB no esta disponible o hay un error al buscar documentos, los agentes siguen funcionando normalmente con los datos de la base de datos. Nunca se bloquea una respuesta por un fallo del RAG.

---

## 8. MODELO DE DATOS

### 8.1 Base de datos interna (SantoniBot)

La base de datos interna de PostgreSQL almacena:

**Usuarios:** ID, email, nombre de usuario, nombre completo, contrasena cifrada, rol (usuario/supervisor/administrador), departamento principal, departamentos adicionales, estado activo, fechas de creacion y actualizacion.

**Conversaciones:** ID, usuario propietario, titulo automatico, fechas de creacion y actualizacion. Se eliminan en cascada si se elimina el usuario.

**Mensajes:** ID, conversacion a la que pertenece, rol (usuario/asistente/sistema), contenido del mensaje, agente que respondio, metadatos en JSON, fecha de creacion. Se eliminan en cascada si se elimina la conversacion.

**Logs de auditoria:** ID, usuario (puede ser nulo para logins fallidos), accion, recurso, detalle, agente usado, direccion IP, fecha de creacion.

### 8.2 Base de datos ERP (iDempiere)

Conexion de solo lectura a la base de datos PostgreSQL 13 de iDempiere en el servidor 192.168.1.73. El schema principal es `adempiere` con las tablas del ERP. SantoniBot consulta las tablas relevantes para cada departamento y transforma los datos en respuestas comprensibles para el usuario.

### 8.3 Base de datos vectorial (ChromaDB)

Almacena los embeddings de documentos subidos al sistema de base de conocimiento. Organizado en 8 colecciones (7 departamentos + 1 general). Cada fragmento de documento se almacena con metadatos (departamento, titulo, fuente, autor).

---

## 9. PRUEBAS Y CALIDAD

### 9.1 Suite de tests automatizados

El proyecto cuenta con **150+ pruebas automatizadas** organizadas en:

**Backend (12 archivos de tests):**
- Tests de autenticacion (login, JWT, permisos)
- Tests de los 7 agentes de IA (clasificacion, respuestas)
- Tests de RBAC (control de acceso por rol y departamento, aislamiento de datos)
- Tests de endpoints API (chat, export, users, admin)
- Tests del endpoint de metricas
- Tests del orquestador (enrutamiento de consultas)
- Tests del anonimizador de datos

**Frontend (4 archivos de tests):**
- Tests de componentes (ChatMessage, Sidebar)
- Tests de hooks (useAuth)
- Tests del cliente API

### 9.2 Integracion continua (CI/CD)

Cada vez que se sube codigo nuevo al repositorio:
1. Se ejecutan automaticamente todos los tests del backend con PostgreSQL de prueba
2. Se ejecuta lint, tests y build del frontend
3. Si todo pasa, el codigo esta listo para desplegar
4. El despliegue a la VM puede ser automatico o manual segun configuracion

---

## 10. PREPARACION PARA EL FUTURO

### 10.1 Integracion con Claude (Anthropic)

El sistema esta preparado de forma pasiva para la integracion con la API de Claude de Anthropic. Un "LLM Factory" permite cambiar de Groq a Claude con solo modificar una variable de entorno (`AI_PROVIDER=anthropic`), sin cambiar una sola linea de codigo. Claude permitira:

- Respuestas aun mas inteligentes y contextualizadas
- Analisis de documentos adjuntos (PDF, Excel, imagenes)
- Mayor capacidad de razonamiento para consultas complejas

### 10.2 Endpoint de Documentos

Ya existe un endpoint preparado para la carga de documentos (`/api/documents/upload`) que acepta PDF, Excel, CSV, Word, TXT e imagenes. Cuando se active Claude, los usuarios podran adjuntar archivos para que la IA los analice directamente.

### 10.3 Integracion WhatsApp (Fase 2)

La arquitectura esta disenada para soportar una futura integracion con WhatsApp Business API, lo que permitiria a los usuarios hacer consultas al sistema directamente desde WhatsApp, sin necesidad de abrir el navegador.

---

## 11. DIFERENCIADORES CLAVE

### Por que SantoniBot es especial

1. **No es un chatbot generico.** Tiene 7 agentes especializados, cada uno experto en su area. No es una IA que responde "de todo un poco" -- cada agente conoce profundamente su departamento.

2. **Datos reales, no inventados.** Se conecta directamente al ERP de Santoni. Los numeros que muestra son los mismos que estan en el sistema, en tiempo real.

3. **Seguridad empresarial seria.** Control de acceso por departamento, contrasenas cifradas, tokens JWT, rate limiting, encabezados de seguridad, auditoria completa. No es un prototipo, es una solucion de nivel empresarial.

4. **Exportacion profesional.** No solo muestra datos en pantalla: los exporta en Excel formateado con colores corporativos, PDF listo para imprimir, y CSV para analisis. Las graficas se descargan como imagenes PNG.

5. **100% en espanol.** Toda la interfaz, todas las respuestas, todos los mensajes de error, toda la documentacion -- todo en espanol, pensado para los empleados de Santoni.

6. **Multiplataforma.** Funciona en cualquier navegador (Chrome, Firefox, Edge) y se adapta automaticamente a celulares y tablets.

7. **Desplegable con un comando.** Toda la infraestructura esta containerizada en Docker. Un solo `docker compose up -d` levanta los 5 servicios.

8. **Preparado para crecer.** La arquitectura modular permite agregar nuevos agentes, nuevas integraciones (WhatsApp, Claude, documentos), y escalar sin reescribir.

---

## 12. RESUMEN TECNICO RAPIDO

| Componente | Tecnologia |
|------------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI |
| Base de datos interna | PostgreSQL 16 |
| Base de datos ERP | PostgreSQL 13 (iDempiere, solo lectura) |
| Base de datos vectorial | ChromaDB |
| IA principal | Groq (Llama 3.3 70B) |
| IA secundaria (preparada) | Claude API (Anthropic) |
| Orquestacion IA | LangChain |
| Graficas | Recharts |
| Exportacion | CSV, Excel (openpyxl), PDF (ReportLab) |
| Proxy y seguridad | Nginx |
| Containerizacion | Docker + Docker Compose (5 servicios) |
| CI/CD | GitHub Actions |
| Tests | Pytest (backend, 150+), Jest (frontend) |

---

## 13. ESTADO ACTUAL DEL PROYECTO

| Area | Estado | Porcentaje |
|------|--------|-----------|
| Backend completo | Terminado | 100% |
| 7 agentes de IA | Terminado | 100% |
| Frontend completo | Terminado | 100% |
| Docker y despliegue | Terminado | 100% |
| Tests automatizados | Terminado | 88% (falta E2E) |
| CI/CD | Terminado | 100% |
| Documentacion | Terminado | 100% |
| Seguridad | Terminado | 100% |
| Conexion iDempiere real | Pendiente | 0% (requiere VPN) |
| WhatsApp | Fase 2 | 0% (post-lanzamiento) |

**Avance general: 83% (73 de 88 tareas completadas)**

El sistema esta **100% funcional** para pruebas y demostracion con datos de ejemplo. Las tareas pendientes son la conexion al iDempiere real (requiere acceso VPN a la red de Santoni) y la integracion con WhatsApp (planificada para despues del lanzamiento).

---

*SantoniBot -- Sistema Inteligente de Analisis de Datos Empresariales*
*Desarrollado por OVA Agency para Alimentos Santoni, C.A.*
*Febrero 2026*
