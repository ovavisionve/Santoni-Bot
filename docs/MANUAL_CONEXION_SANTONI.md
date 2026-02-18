# Manual de Conexion al Entorno de Produccion de Santoni

**Audiencia:** Luis / OVA Agency (desarrollador del sistema)
**Objetivo:** Conectar SantoniBot al entorno real de Alimentos Santoni, C.A. -- desde la VPN hasta el despliegue final en la VM de produccion.

> Este manual asume que ya tienes el proyecto funcionando localmente con datos demo (ver `MANUAL_PRUEBAS_LOCAL.md`). Ahora vamos a conectar todo al entorno real.

---

## Informacion del Entorno de Santoni

### Red Interna

| Recurso | IP / Host | Puerto | Notas |
|---------|-----------|--------|-------|
| VM SantoniBot | 192.168.1.26 | 22 (SSH) | Ubuntu 25.10, 16GB RAM, 8 vCPU, 512GB SSD |
| iDempiere DB | 192.168.1.73 | 5432 | PostgreSQL 13, DB: `idempiere_produccion` |
| SQL Server (asistencia) | Por confirmar | 1433 | SQL Server 11, sistema de asistencia |
| IP Publica | 201.249.55.198 | 80/443 | Acceso externo via port forwarding |

### Credenciales Actuales

#### VPN (FortiClient)

| Campo | Valor |
|-------|-------|
| Tipo | FortiClient VPN (SSL-VPN) |
| Servidor | `201.249.55.198` (o el gateway que indique IT de Santoni) |
| Puerto | `443` o `10443` (verificar con IT de Santoni) |
| Usuario | `OVA` |
| Contrasena | `Santoni2022$` |

#### VM (SSH)

| Campo | Valor |
|-------|-------|
| Host | `192.168.1.26` |
| Puerto | `22` |
| Usuario | `accinproa` |
| Contrasena | `pTTkL3gHLYmj5$BL1oFq` |

#### iDempiere Database (solo lectura)

| Campo | Valor |
|-------|-------|
| Host | `192.168.1.73` |
| Puerto | `5432` |
| Base de datos | `idempiere_produccion` |
| Schema principal | `adempiere` |
| Usuario | `ova` |
| Contrasena | `ova2026*` |
| Permisos | Solo lectura (SELECT). No se puede INSERT, UPDATE ni DELETE. |

### Contactos

| Rol | Persona | Para que contactarla |
|-----|---------|----------------------|
| IT Santoni | (preguntar nombre al contacto inicial) | VPN, firewall, acceso DB, permisos de red |
| Ventas | Marlenis Figueredo | Validar datos de ventas, confirmar logica de negocio |
| Compras Productores | Marlenis Figueredo | Validar datos de compras de arroz/maiz |
| Compras Insumos | Onofrio Gueccia, Jorge Chahine | Validar datos de insumos |
| Produccion | (preguntar) | Validar datos de produccion diaria |

---

## FASE 1: Preparar Acceso VPN

### 1.1 Que necesitas de Santoni

Antes de poder conectarte a la red interna de Santoni, necesitas que su equipo de IT te proporcione:

1. **Credenciales VPN**: usuario y contrasena para FortiClient (ya las tenemos: `OVA` / `Santoni2022$`)
2. **Tipo de VPN**: FortiClient SSL-VPN (ya confirmado)
3. **IP o hostname del gateway VPN**: `201.249.55.198` (ya confirmado)
4. **Puerto del gateway VPN**: `443` o `10443` (verificar cual funciona)
5. **Acceso SSH a la VM**: usuario y contrasena para `192.168.1.26` (ya los tenemos: `accinproa`)
6. **Acceso de solo lectura a iDempiere**: usuario PostgreSQL con SELECT sobre el schema `adempiere` (ya lo tenemos: `ova`)

### 1.2 Si necesitas solicitar acceso por primera vez

En caso de que las credenciales hayan cambiado o necesites solicitar acceso nuevo, enviar este mensaje al contacto de IT de Santoni:

```
Asunto: Solicitud de acceso VPN y base de datos para proyecto SantoniBot

Buenas tardes,

Soy Luis de OVA Agency. Estamos trabajando en el proyecto SantoniBot
(sistema de analisis de datos empresariales con IA) que se desplegara
en la VM 192.168.1.26.

Necesitamos los siguientes accesos para continuar con la implementacion:

1. ACCESO VPN
   - Tipo: FortiClient SSL-VPN
   - Necesitamos: usuario, contrasena y direccion del gateway
   - Sera usado desde nuestra oficina para desarrollo y soporte

2. ACCESO SSH A LA VM (192.168.1.26)
   - Necesitamos: usuario con permisos sudo para instalar Docker
     y administrar el servicio SantoniBot
   - Sistema operativo: Ubuntu 25.10

3. ACCESO A BASE DE DATOS iDempiere (192.168.1.73:5432)
   - Necesitamos: usuario PostgreSQL de SOLO LECTURA (SELECT)
   - Base de datos: idempiere_produccion
   - Schema: adempiere
   - SantoniBot solo consultara datos, nunca modificara nada

4. INFORMACION ADICIONAL (si es posible)
   - Diagrama de red o IPs relevantes
   - Horarios de mantenimiento donde la VPN o DB puedan no estar disponibles
   - Contacto directo de IT para resolver incidencias de conectividad

Quedo atento a su respuesta. Muchas gracias.

Luis - OVA Agency
```

### 1.3 Que informacion necesitas recibir de vuelta

Cuando IT de Santoni responda, asegurate de tener:

| Dato | Lo tienes? | Valor |
|------|-----------|-------|
| Tipo de VPN (FortiClient, OpenVPN, WireGuard) | Si | FortiClient SSL-VPN |
| IP o hostname del gateway VPN | Si | 201.249.55.198 |
| Puerto del gateway VPN | Verificar | 443 o 10443 |
| Usuario VPN | Si | OVA |
| Contrasena VPN | Si | Santoni2022$ |
| Archivo de configuracion VPN (si aplica) | No necesario para FortiClient | N/A |
| Certificado o fingerprint (para openfortivpn) | Obtener en primera conexion | Pendiente |
| Usuario SSH de la VM | Si | accinproa |
| Contrasena SSH de la VM | Si | pTTkL3gHLYmj5$BL1oFq |
| Usuario PostgreSQL para iDempiere | Si | ova |
| Contrasena PostgreSQL para iDempiere | Si | ova2026* |
| Nombre de la base de datos | Si | idempiere_produccion |
| Rangos de IP internos accesibles via VPN | Parcial | 192.168.1.x |

---

## FASE 2: Conectar VPN

### 2.1 Instalar el cliente VPN

Santoni usa **FortiClient VPN**. Tienes dos opciones: la aplicacion grafica (FortiClient) o la linea de comandos (openfortivpn, solo Linux).

#### Opcion A: FortiClient (interfaz grafica - Windows / macOS / Linux)

**Windows:**
1. Ir a https://www.fortinet.com/support/product-downloads
2. Buscar la seccion **"FortiClient VPN"** (NO FortiClient completo, solo la version VPN)
3. Descargar el instalador para Windows
4. Ejecutar el `.exe` descargado
5. En el instalador, seleccionar **"Yes, I have read and accept the..."**
6. Clic en **Install** y esperar a que termine
7. Clic en **Finish**
8. FortiClient se abre automaticamente. Si no, buscarlo en el menu Inicio: `FortiClient VPN`

**macOS:**
```bash
# Opcion 1: Homebrew (si lo tienes instalado)
brew install --cask forticlient-vpn

# Opcion 2: Descarga directa
# Ir a https://www.fortinet.com/support/product-downloads
# Descargar el .dmg para macOS
# Abrir el .dmg y arrastrar FortiClient a Applications
# Abrir desde Applications > FortiClient VPN
```

**Linux (Ubuntu/Debian):**
```bash
# Agregar repositorio de Fortinet
wget -O - https://repo.fortinet.com/repo/forticlient/7.4/ubuntu/DEB-GPG-KEY | sudo apt-key add -

# Agregar la fuente del repositorio
echo "deb https://repo.fortinet.com/repo/forticlient/7.4/ubuntu/ stable non-free" | sudo tee /etc/apt/sources.list.d/forticlient.list

# Instalar
sudo apt-get update
sudo apt-get install forticlient

# Verificar que se instalo
forticlient --version
```

#### Opcion B: openfortivpn (linea de comandos - solo Linux)

Si prefieres no instalar la aplicacion grafica en Linux:

```bash
# Instalar openfortivpn
sudo apt-get update
sudo apt-get install -y openfortivpn

# Verificar que se instalo
openfortivpn --version
# Debe mostrar algo como: openfortivpn 1.x.x
```

> **Nota:** openfortivpn es mas ligero pero requiere el fingerprint del certificado SSL del servidor VPN. Lo obtienes en la primera conexion.

### 2.2 Configurar la conexion VPN

#### Con FortiClient (interfaz grafica):

1. Abrir **FortiClient VPN**
2. Clic en el icono de **engranaje** o en **"Configure VPN"** / **"VPN Settings"**
3. Clic en **"New Connection"** o **"Add a new connection"**
4. Llenar los campos exactamente asi:

| Campo | Valor |
|-------|-------|
| Connection Name | `Santoni VPN` |
| Description | `VPN de Alimentos Santoni` (opcional) |
| Remote Gateway | `201.249.55.198` |
| Port | `443` (si no funciona, probar `10443`) |
| Username | `OVA` |
| Authentication | `Prompt on connect` (o guardar contrasena si lo permite) |

5. Clic en **"Save"** o **"Apply"**
6. La conexion `Santoni VPN` aparece en la lista

#### Con openfortivpn (Linux CLI):

Crear un archivo de configuracion para no tener que escribir todo cada vez:

```bash
# Crear el archivo de configuracion
sudo nano /etc/openfortivpn/santoni.conf
```

Pegar este contenido:
```
host = 201.249.55.198
port = 443
username = OVA
password = Santoni2022$
# trusted-cert = <PEGAR-FINGERPRINT-AQUI-DESPUES-DE-PRIMERA-CONEXION>
```

Guardar con Ctrl+S y salir con Ctrl+X.

> **Seguridad:** Este archivo tiene la contrasena en texto plano. Protegerlo:
> ```bash
> sudo chmod 600 /etc/openfortivpn/santoni.conf
> ```

### 2.3 Conectar la VPN

#### Con FortiClient (interfaz grafica):

1. Abrir **FortiClient VPN**
2. Seleccionar la conexion **"Santoni VPN"** del menu desplegable
3. El campo **Username** ya dice `OVA`
4. En el campo **Password**, escribir: `Santoni2022$`
5. Clic en **"Connect"**
6. Esperar 5-10 segundos
7. Si aparece una advertencia de certificado SSL, clic en **"Yes"** / **"Accept"** / **"Continue"**
8. El estado cambia a **"Connected"** con un icono verde
9. Ahora tienes acceso a la red interna de Santoni (192.168.1.x)

**Si dice "Connection failed" o "Unable to connect":**
- Verificar que tienes conexion a internet
- Probar cambiando el puerto de `443` a `10443` (o viceversa)
- Verificar que el servidor VPN esta activo (puede estar en mantenimiento)
- Contactar a IT de Santoni

#### Con openfortivpn (Linux CLI):

```bash
# Primera conexion (sin fingerprint, para obtenerlo)
sudo openfortivpn 201.249.55.198:443 \
  --username=OVA \
  --password='Santoni2022$'
```

En la primera conexion, openfortivpn mostrara un mensaje como:
```
ERROR: Server certificate validation failed.
Certificate:
  ...
  Fingerprint: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

Copiar el fingerprint y:
1. Agregarlo al archivo `/etc/openfortivpn/santoni.conf` en la linea `trusted-cert`
2. O usarlo directamente:

```bash
# Conexion con fingerprint ya conocido
sudo openfortivpn 201.249.55.198:443 \
  --username=OVA \
  --password='Santoni2022$' \
  --trusted-cert a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

O con el archivo de configuracion:
```bash
sudo openfortivpn -c /etc/openfortivpn/santoni.conf
```

> **Nota:** openfortivpn se queda corriendo en primer plano. Abre otra terminal para trabajar. Para desconectar: Ctrl+C.

### 2.4 Verificar que la VPN funciona

Abrir una terminal (diferente a la de openfortivpn si usas CLI) y ejecutar estos comandos uno por uno:

```bash
# Test 1: Ping a la VM de SantoniBot
ping -c 4 192.168.1.26
```
**Resultado esperado:** 4 paquetes enviados, 4 recibidos, 0% packet loss. Si ves `64 bytes from 192.168.1.26`, funciona.

```bash
# Test 2: Ping al servidor de iDempiere
ping -c 4 192.168.1.73
```
**Resultado esperado:** 4 paquetes enviados, 4 recibidos. Si ves `64 bytes from 192.168.1.73`, funciona.

```bash
# Test 3: Verificar que el puerto SSH de la VM esta abierto
nc -zv 192.168.1.26 22
# Resultado esperado: "Connection to 192.168.1.26 22 port [tcp/ssh] succeeded!"
```

```bash
# Test 4: Verificar que el puerto PostgreSQL de iDempiere esta abierto
nc -zv 192.168.1.73 5432
# Resultado esperado: "Connection to 192.168.1.73 5432 port [tcp/postgresql] succeeded!"
```

**Si los ping fallan:**

| Situacion | Posible causa | Solucion |
|-----------|---------------|----------|
| `Request timeout` en ambos IPs | VPN no esta conectada o no funciona | Verificar que FortiClient dice "Connected". Reconectar. |
| `Request timeout` solo en una IP | Firewall bloqueando esa IP | Contactar IT de Santoni para verificar reglas de firewall |
| `Network is unreachable` | La VPN no creo la ruta correcta | Verificar tabla de rutas: `ip route` (Linux) o `route print` (Windows). Contactar IT. |
| Ping funciona pero `nc` falla | Puerto cerrado por firewall | Contactar IT de Santoni para abrir el puerto |

### 2.5 Desconectar la VPN

**FortiClient (GUI):**
1. Abrir FortiClient VPN
2. Clic en **"Disconnect"**
3. El estado cambia a "Not Connected"

**openfortivpn (CLI):**
1. Ir a la terminal donde esta corriendo openfortivpn
2. Presionar **Ctrl+C**
3. El proceso se detiene y la VPN se desconecta

> **Importante:** Cuando no estes trabajando en el proyecto de Santoni, desconecta la VPN. No es necesario tenerla activa todo el tiempo y puede afectar tu conexion a internet normal.

---

## FASE 3: Verificar Acceso a iDempiere

### 3.1 Opcion A: Conectar por linea de comandos (psql)

psql es el cliente oficial de PostgreSQL. Es la forma mas rapida de verificar acceso.

**Instalar psql si no lo tienes:**

```bash
# macOS (Homebrew)
brew install postgresql

# Ubuntu/Debian
sudo apt-get install -y postgresql-client

# Windows: instalar PostgreSQL desde https://www.postgresql.org/download/windows/
# Durante la instalacion, marcar solo "Command Line Tools" si no necesitas el servidor completo.
```

**Verificar instalacion:**
```bash
psql --version
# Debe mostrar: psql (PostgreSQL) 16.x o similar
```

**Conectar a iDempiere (con la VPN activa):**

```bash
psql -h 192.168.1.73 -p 5432 -U ova -d idempiere_produccion
```

Te pedira la contrasena. Escribir: `ova2026*` y presionar Enter.

> **Nota:** La contrasena NO se muestra mientras la escribes (ni siquiera asteriscos). Esto es normal. Escribe y presiona Enter.

**Resultado esperado:** El prompt cambia a:
```
idempiere_produccion=>
```

Si ves ese prompt, estas conectado exitosamente. Puedes escribir queries SQL directamente.

**Si falla la conexion:**

| Error | Causa | Solucion |
|-------|-------|----------|
| `could not connect to server: Connection refused` | VPN no activa o puerto bloqueado | Verificar VPN, hacer ping a 192.168.1.73, verificar puerto 5432 con nc |
| `FATAL: password authentication failed for user "ova"` | Contrasena incorrecta | Verificar que usas `ova2026*` exactamente. Contactar IT si cambio. |
| `FATAL: database "idempiere_produccion" does not exist` | Nombre de BD incorrecto | Listar BDs: `psql -h 192.168.1.73 -U ova -l` para ver las disponibles |
| `could not translate host name` | Problema de DNS/red | Verificar VPN, usar IP directamente (no hostname) |
| `connection timed out` | Firewall, VPN no rutea bien | Verificar con `nc -zv 192.168.1.73 5432` |

**Para salir de psql:**
```sql
\q
```

### 3.2 Opcion B: Conectar con pgAdmin 4 (interfaz grafica)

pgAdmin 4 es la herramienta oficial grafica para administrar PostgreSQL. Util para explorar tablas visualmente.

**Instalar pgAdmin 4:**
- **Windows / macOS:** Descargar de https://www.pgadmin.org/download/
- **Linux:**
  ```bash
  # Ubuntu/Debian
  curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
  sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'
  sudo apt-get update
  sudo apt-get install pgadmin4-desktop
  ```

**Configurar la conexion en pgAdmin:**

1. Abrir pgAdmin 4
2. En el panel izquierdo, clic derecho en **"Servers"**
3. Seleccionar **"Register" > "Server..."**
4. En la pestana **"General"**:
   - **Name:** `Santoni iDempiere`
5. En la pestana **"Connection"**:
   - **Host name/address:** `192.168.1.73`
   - **Port:** `5432`
   - **Maintenance database:** `idempiere_produccion`
   - **Username:** `ova`
   - **Password:** `ova2026*`
   - Marcar **"Save password?"** (checkbox)
6. Clic en **"Save"**
7. El servidor aparece en el panel izquierdo. Si tiene un icono verde, la conexion funciona.
8. Expandir: **Santoni iDempiere > Databases > idempiere_produccion > Schemas > adempiere > Tables**
9. Ahi ves todas las tablas de iDempiere

### 3.3 Opcion C: Conectar con DBeaver (alternativa gratuita)

DBeaver es un cliente de bases de datos universal. Soporta PostgreSQL, MySQL, SQL Server, etc.

**Instalar DBeaver:**
- **Todas las plataformas:** Descargar de https://dbeaver.io/download/
- **macOS con Homebrew:** `brew install --cask dbeaver-community`
- **Linux Snap:** `sudo snap install dbeaver-ce`

**Configurar la conexion en DBeaver:**

1. Abrir DBeaver
2. Clic en **"New Database Connection"** (icono de enchufe con +, arriba a la izquierda)
3. Seleccionar **"PostgreSQL"** en la lista y clic en **"Next"**
4. Llenar los campos:
   - **Host:** `192.168.1.73`
   - **Port:** `5432`
   - **Database:** `idempiere_produccion`
   - **Username:** `ova`
   - **Password:** `ova2026*`
   - Marcar **"Save password locally"**
5. Clic en **"Test Connection..."**
   - Si pide descargar el driver de PostgreSQL, clic en **"Download"**
   - Debe decir **"Connected"** con un check verde
6. Clic en **"Finish"**
7. La conexion aparece en el panel izquierdo
8. Expandir: **idempiere_produccion > Schemas > adempiere > Tables**

### 3.4 Queries de verificacion

Una vez conectado a iDempiere (ya sea por psql, pgAdmin o DBeaver), ejecutar estas queries para verificar que todo funciona correctamente. Ejecutarlas **una por una** y verificar los resultados.

**Query 1: Verificar conexion basica**
```sql
SELECT current_database(), current_user, version();
```
**Resultado esperado:**
- `current_database`: `idempiere_produccion`
- `current_user`: `ova`
- `version()`: `PostgreSQL 13.x ...`

**Query 2: Verificar que el schema adempiere existe**
```sql
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'adempiere';
```
**Resultado esperado:** Una fila con `adempiere`. Si no aparece nada, el schema tiene otro nombre -- buscar con:
```sql
SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;
```

**Query 3: Contar tablas en el schema adempiere**
```sql
SELECT count(*)
FROM information_schema.tables
WHERE table_schema = 'adempiere';
```
**Resultado esperado:** Un numero mayor a 500 (iDempiere tipicamente tiene entre 800 y 1500 tablas).

**Query 4: Listar las primeras 30 tablas**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
ORDER BY table_name
LIMIT 30;
```
**Resultado esperado:** Lista de tablas que empieza con nombres como `a_asset`, `a_depreciation`, `ad_attachment`, `ad_client`, `ad_column`, etc.

**Query 5: Verificar que la tabla principal de metadatos existe**
```sql
SELECT count(*) FROM adempiere.ad_table;
```
**Resultado esperado:** Un numero (tipicamente 800+). Si da error `permission denied`, contactar a IT para verificar los permisos del usuario `ova`.

**Query 6: Verificar tablas clave para SantoniBot**
```sql
-- Socios de negocio (clientes, proveedores, empleados)
SELECT count(*) AS socios_negocio FROM adempiere.c_bpartner WHERE isactive = 'Y';

-- Facturas
SELECT count(*) AS facturas FROM adempiere.c_invoice WHERE isactive = 'Y';

-- Productos
SELECT count(*) AS productos FROM adempiere.m_product WHERE isactive = 'Y';

-- Ordenes
SELECT count(*) AS ordenes FROM adempiere.c_order WHERE isactive = 'Y';

-- Pagos/Cobranzas
SELECT count(*) AS pagos FROM adempiere.c_payment WHERE isactive = 'Y';

-- Empleados (registrados como socios de negocio con isemployee='Y')
SELECT count(*) AS empleados FROM adempiere.c_bpartner WHERE isemployee = 'Y';

-- Cuentas bancarias
SELECT count(*) AS cuentas_bancarias FROM adempiere.c_bankaccount WHERE isactive = 'Y';
```
**Resultado esperado:** Cada query devuelve un numero mayor a 0. Si alguna tabla no existe, verifica con `information_schema` que el nombre sea correcto (puede haber personalizaciones de Santoni).

**Query 7: Verificar que el usuario solo tiene permisos de lectura**
```sql
-- Esta query DEBE fallar (el usuario ova es de solo lectura)
-- NO LA EJECUTES SI NO QUIERES VER EL ERROR - es solo para verificar que no puedes modificar datos
-- INSERT INTO adempiere.c_bpartner (name) VALUES ('TEST');
-- Esperado: ERROR: permission denied for table c_bpartner
```

> **IMPORTANTE:** El usuario `ova` tiene acceso de **solo lectura (SELECT)**. No puedes hacer INSERT, UPDATE ni DELETE. Esto es intencional y correcto para la seguridad del ERP de produccion.

### 3.5 Como navegar el schema de iDempiere

iDempiere esta basado en ADempiere/Compiere y sigue una convencion de nombres especifica:

**Prefijos de tablas principales:**
| Prefijo | Modulo | Ejemplos |
|---------|--------|----------|
| `AD_` | Application Dictionary (sistema) | `ad_table`, `ad_column`, `ad_window` |
| `C_` | Core (ventas, compras, contabilidad) | `c_invoice`, `c_order`, `c_payment`, `c_bpartner` |
| `M_` | Material Management (inventario, produccion) | `m_product`, `m_inout`, `m_production` |
| `GL_` | General Ledger (libro mayor) | `gl_journal`, `gl_journalline` |
| `HR_` | Human Resources (RRHH) | `hr_employee`, `hr_payroll`, `hr_concept` |
| `Fact_` | Contabilidad (hechos contables) | `fact_acct` |
| `PP_` | Production Planning (planificacion) | `pp_order`, `pp_order_bomline` |
| `XX_` o personalizado | Tablas personalizadas de Santoni | Buscar con la query de abajo |

**Como explorar las columnas de una tabla especifica:**
```sql
SELECT column_name, data_type, is_nullable, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'c_invoice'
ORDER BY ordinal_position;
```
Esto te muestra todas las columnas de la tabla `c_invoice`, su tipo de dato, si acepta NULL, y la longitud maxima. Cambiar `'c_invoice'` por cualquier otra tabla para explorarla.

**Como buscar una tabla por nombre parcial:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND table_name LIKE '%invoice%'
ORDER BY table_name;
```

**Como buscar tablas personalizadas de Santoni:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND (table_name LIKE '%santoni%'
       OR table_name LIKE '%arroz%'
       OR table_name LIKE '%productor%'
       OR table_name LIKE '%xx_%'
       OR table_name LIKE '%custom%')
ORDER BY table_name;
```

---

## FASE 4: Mapear Tablas de iDempiere a los Agentes

Esta es la fase mas importante y la que requiere mas investigacion. Necesitas identificar exactamente que tablas y columnas usa Santoni en su iDempiere para cada departamento.

### 4.1 Mapeo general: Agente --> Tablas iDempiere

| Agente SantoniBot | Tablas iDempiere principales | Descripcion |
|-------------------|------------------------------|-------------|
| **Ventas** | `c_invoice`, `c_invoiceline`, `c_bpartner`, `c_order`, `c_orderline`, `c_payment`, `c_bpartner_location`, `c_salesregion`, `m_inout` | Facturas de venta, clientes, pedidos, cobranzas, despachos |
| **Finanzas** | `c_bankaccount`, `c_bankstatement`, `c_bankstatementline`, `c_payment`, `c_invoice`, `c_cashbook` | Saldos bancarios, estados de cuenta, flujo de caja |
| **Contabilidad** | `fact_acct`, `c_elementvalue`, `c_period`, `c_acctschema`, `gl_journal`, `gl_journalline`, `c_validcombination` | Balance, P&L, diario, asientos contables |
| **RRHH** | `c_bpartner` (con `isemployee='Y'`), `hr_employee`, `hr_payroll`, `hr_payrollrun`, `hr_movement`, `hr_concept`, `hr_attendance` (si existe) | Empleados, nomina, asistencia |
| **Produccion** | `m_production`, `m_productionline`, `m_product`, `pp_order`, `pp_order_bomline`, `pp_cost_collector` | Ordenes de produccion, lineas, productos, rendimiento |
| **Compras Insumos** | `c_order` (con `issotrx='N'`), `c_orderline`, `c_invoice` (compras), `m_product`, `c_bpartner` (proveedores), `m_inout` | Ordenes de compra, facturas de proveedor, recepciones |
| **Compras Productores** | Tablas personalizadas de Santoni (buscar con `xx_` o similares). Si no existen, posiblemente usan `c_order` con categorias especificas | Compras de arroz paddy, maiz, guias de productor |

### 4.2 Queries de exploracion por departamento

#### Ventas

```sql
-- Estructura de facturas de venta
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'c_invoice'
ORDER BY ordinal_position;

-- Facturas de venta recientes (issotrx='Y' = venta, 'N' = compra)
SELECT i.documentno, i.dateinvoiced, i.grandtotal, i.docstatus,
       bp.name AS cliente, bp.value AS codigo_cliente
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'Y' AND i.isactive = 'Y'
ORDER BY i.dateinvoiced DESC
LIMIT 20;

-- Vendedores activos
SELECT bp.value, bp.name, sr.name AS region_ventas
FROM adempiere.c_bpartner bp
LEFT JOIN adempiere.c_salesregion sr ON bp.c_salesregion_id = sr.c_salesregion_id
WHERE bp.issalesrep = 'Y' AND bp.isactive = 'Y'
ORDER BY bp.name;

-- Cobranzas recientes (pagos recibidos)
SELECT p.documentno, p.datetrx, p.payamt, p.docstatus,
       bp.name AS cliente
FROM adempiere.c_payment p
JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id
WHERE p.isreceipt = 'Y' AND p.isactive = 'Y'
ORDER BY p.datetrx DESC
LIMIT 20;

-- Despachos recientes
SELECT io.documentno, io.movementdate, io.docstatus,
       bp.name AS cliente
FROM adempiere.m_inout io
JOIN adempiere.c_bpartner bp ON io.c_bpartner_id = bp.c_bpartner_id
WHERE io.issotrx = 'Y' AND io.isactive = 'Y'
ORDER BY io.movementdate DESC
LIMIT 20;
```

#### Finanzas

```sql
-- Cuentas bancarias
SELECT ba.accountno, ba.name AS nombre_cuenta,
       b.name AS banco, ba.currentbalance
FROM adempiere.c_bankaccount ba
JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id
WHERE ba.isactive = 'Y'
ORDER BY b.name;

-- Estados de cuenta bancarios recientes
SELECT bs.name, bs.statementdate, bs.beginningbalance, bs.endingbalance
FROM adempiere.c_bankstatement bs
WHERE bs.isactive = 'Y'
ORDER BY bs.statementdate DESC
LIMIT 10;

-- Cuentas por cobrar (facturas de venta pendientes)
SELECT i.documentno, bp.name AS cliente, i.dateinvoiced,
       i.grandtotal, i.docstatus
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'Y' AND i.ispaid = 'N' AND i.docstatus = 'CO'
ORDER BY i.dateinvoiced DESC
LIMIT 20;

-- Cuentas por pagar (facturas de compra pendientes)
SELECT i.documentno, bp.name AS proveedor, i.dateinvoiced,
       i.grandtotal, i.docstatus
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'N' AND i.ispaid = 'N' AND i.docstatus = 'CO'
ORDER BY i.dateinvoiced DESC
LIMIT 20;
```

#### Contabilidad

```sql
-- Esquema contable activo
SELECT name, gaap, costingmethod
FROM adempiere.c_acctschema
WHERE isactive = 'Y';

-- Plan de cuentas (cuentas contables)
SELECT value, name, accounttype, issummary
FROM adempiere.c_elementvalue
WHERE isactive = 'Y'
ORDER BY value
LIMIT 50;

-- Asientos contables recientes (Fact_Acct = hechos contables)
SELECT fa.dateacct, fa.account_id, ev.value AS cuenta, ev.name AS nombre_cuenta,
       fa.amtsourcedr AS debe, fa.amtsourcecr AS haber, fa.description
FROM adempiere.fact_acct fa
JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
ORDER BY fa.dateacct DESC
LIMIT 30;

-- Periodos contables
SELECT p.name, p.startdate, p.enddate, p.periodno, p.isactive
FROM adempiere.c_period p
ORDER BY p.startdate DESC
LIMIT 24;

-- Diarios contables
SELECT j.documentno, j.datedoc, j.description, j.totaldrcr, j.docstatus
FROM adempiere.gl_journal j
WHERE j.isactive = 'Y'
ORDER BY j.datedoc DESC
LIMIT 20;
```

#### RRHH

```sql
-- Verificar si el modulo de RRHH esta instalado
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND table_name LIKE 'hr_%'
ORDER BY table_name;

-- Empleados (en c_bpartner con isemployee='Y')
SELECT bp.value AS codigo, bp.name, bp.isactive
FROM adempiere.c_bpartner bp
WHERE bp.isemployee = 'Y'
ORDER BY bp.name;

-- Si existe hr_employee
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'hr_employee'
ORDER BY ordinal_position;

-- Si existe hr_payroll (nomina)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'hr_payroll'
ORDER BY ordinal_position;

-- Si existe hr_attendance (asistencia) - poco comun en iDempiere
-- La asistencia puede estar en SQL Server (192.168.1.x:1433)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND (table_name LIKE '%attendance%' OR table_name LIKE '%asistencia%');
```

> **Nota sobre asistencia:** Santoni menciono un SQL Server separado para el sistema de asistencia. Es posible que esta data NO este en iDempiere. Confirmar con IT que servidor y base de datos tiene la asistencia.

#### Produccion

```sql
-- Verificar tablas de produccion disponibles
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND (table_name LIKE 'm_production%'
       OR table_name LIKE 'pp_%')
ORDER BY table_name;

-- Ordenes de produccion
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'm_production'
ORDER BY ordinal_position;

-- Producciones recientes
SELECT mp.documentno, mp.movementdate, mp.name, mp.description, mp.isactive
FROM adempiere.m_production mp
ORDER BY mp.movementdate DESC
LIMIT 20;

-- Lineas de produccion (detalle)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'm_productionline'
ORDER BY ordinal_position;

-- Si existe planificacion de produccion (PP_Order)
SELECT po.documentno, po.datedoc, po.datepromised, po.qtyordered,
       po.qtydelivered, po.docstatus, p.name AS producto
FROM adempiere.pp_order po
JOIN adempiere.m_product p ON po.m_product_id = p.m_product_id
WHERE po.isactive = 'Y'
ORDER BY po.datedoc DESC
LIMIT 20;
```

#### Compras (Insumos y Productores)

```sql
-- Ordenes de compra recientes (issotrx='N' = compra)
SELECT o.documentno, o.dateordered, o.grandtotal, o.docstatus,
       bp.name AS proveedor
FROM adempiere.c_order o
JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
WHERE o.issotrx = 'N' AND o.isactive = 'Y'
ORDER BY o.dateordered DESC
LIMIT 20;

-- Proveedores activos
SELECT bp.value AS codigo, bp.name, bp.isactive
FROM adempiere.c_bpartner bp
WHERE bp.isvendor = 'Y' AND bp.isactive = 'Y'
ORDER BY bp.name;

-- Recepciones de mercancia (compras recibidas)
SELECT io.documentno, io.movementdate, io.docstatus,
       bp.name AS proveedor
FROM adempiere.m_inout io
JOIN adempiere.c_bpartner bp ON io.c_bpartner_id = bp.c_bpartner_id
WHERE io.issotrx = 'N' AND io.isactive = 'Y'
ORDER BY io.movementdate DESC
LIMIT 20;

-- Buscar tablas personalizadas para productores (arroz, maiz)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND (table_name LIKE '%arroz%'
       OR table_name LIKE '%maiz%'
       OR table_name LIKE '%productor%'
       OR table_name LIKE '%guia%'
       OR table_name LIKE '%paddy%'
       OR table_name LIKE '%xx_%')
ORDER BY table_name;
```

### 4.3 Documentar el mapeo

Una vez que hayas ejecutado todas las queries de exploracion, documentar en una tabla como esta:

```
| Dato que necesita SantoniBot          | Tabla iDempiere real     | Columna(s) clave           | Notas                     |
|---------------------------------------|--------------------------|----------------------------|---------------------------|
| Nombre del cliente                    | adempiere.c_bpartner     | name, value                | Filtrar por iscustomer='Y'|
| Monto total de factura                | adempiere.c_invoice      | grandtotal                 | issotrx='Y' para ventas   |
| Fecha de factura                      | adempiere.c_invoice      | dateinvoiced               |                           |
| Vendedor                              | adempiere.c_bpartner     | name (con issalesrep='Y')  |                           |
| ...                                   | ...                      | ...                        | ...                       |
```

> **Guardar esta documentacion.** La necesitaras en la Fase 5 para actualizar `query_service.py`.

---

## FASE 5: Actualizar Configuracion del Proyecto

### 5.1 Actualizar .env con credenciales reales de iDempiere

Editar el archivo `.env` en la raiz del proyecto. Cambiar las variables de iDempiere:

```bash
# Abrir el archivo .env con tu editor preferido
nano .env
# o
code .env
```

Buscar esta seccion y verificar que tiene los valores correctos:

```env
# ---- iDempiere Database (read-only) ----
IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=ova2026*
```

> **Recordatorio:** Estos valores solo funcionan cuando la VPN esta activa. En desarrollo local sin VPN, los agentes usan las tablas demo internas y no necesitan conectarse a iDempiere.

### 5.2 El codigo ya esta preparado para dual-mode

**NO necesitas modificar archivos manualmente.** El sistema ya detecta automaticamente el entorno:

- `APP_ENV=development` → usa tablas demo (`demo_facturas_venta`, `demo_clientes`, etc.)
- `APP_ENV=production` → usa tablas iDempiere (`adempiere.c_invoice`, `adempiere.c_bpartner`, etc.)

Los archivos clave ya estan listos:

| Archivo | Estado |
|---------|--------|
| `backend/app/services/query_service.py` | Ya rutea automaticamente segun `APP_ENV` |
| `backend/app/services/idempiere_queries.py` | Ya tiene queries para los 7 agentes (basadas en schema estandar iDempiere) |
| `backend/app/config.py` | Ya tiene `idempiere_database_url` |
| `backend/app/database.py` | Ya tiene `IdempiereSession` con read-only enforced |
| `backend/app/agents/*.py` | No necesitan cambios (importan de query_service, que rutea solo) |

**Lo unico que necesitas hacer despues de la Fase 4 (mapeo):**

1. Si encuentras tablas personalizadas de Santoni (ej: tablas de productores con nombres distintos), actualizar las queries en `idempiere_queries.py`
2. Si alguna columna tiene un nombre diferente al estandar, ajustar en `idempiere_queries.py`
3. Las queries de `idempiere_queries.py` tienen comentarios `# TODO` marcando lo que necesita validacion

### 5.3 Probar cada agente con datos reales

Una vez actualizado el codigo, probar cada agente uno por uno:

1. Levantar el proyecto localmente con `docker compose up -d --build` (con VPN activa)
2. Entrar a http://localhost:3000 y hacer login
3. Hacer una pregunta de cada departamento y verificar que los datos son reales (no demo)
4. Comparar los resultados con lo que ves directamente en pgAdmin/DBeaver conectado a iDempiere

**Preguntas de prueba por agente:**

| Agente | Pregunta de prueba | Como verificar que son datos reales |
|--------|--------------------|-------------------------------------|
| Ventas | "Top 10 clientes por facturacion" | Los nombres de clientes deben ser reales, no "Distribuidora Caracas" (demo) |
| Finanzas | "Saldos bancarios actuales" | Los bancos y montos deben coincidir con lo que hay en iDempiere |
| Contabilidad | "Balance general del ultimo mes" | Las cuentas contables deben ser del plan de cuentas real de Santoni |
| RRHH | "Cantidad de empleados activos" | El numero debe coincidir con la realidad de Santoni |
| Produccion | "Produccion de esta semana" | Los productos deben ser arroz, harina de maiz, etc. reales |
| Compras Insumos | "Ordenes de compra pendientes" | Los proveedores deben ser reales |
| Compras Productores | "Compras de arroz del mes" | Los productores y cantidades deben ser reales |

---

## FASE 6: Despliegue en VM de Santoni

### 6.1 Conectar a la VM por SSH

**Prerequisito:** La VPN debe estar activa (Fase 2).

```bash
# Conectar por SSH
ssh accinproa@192.168.1.26
```

Te pedira la contrasena. Escribir: `pTTkL3gHLYmj5$BL1oFq` y presionar Enter.

> **Nota:** La contrasena tiene caracteres especiales (`$`, `!`). Escribirla exactamente como esta. NO se muestra mientras la escribes.

**Resultado esperado:** El prompt cambia a algo como:
```
accinproa@santoni-vm:~$
```

**Configurar acceso SSH con clave (recomendado, para no escribir la contrasena cada vez):**

Desde tu maquina local (NO desde la VM):
```bash
# Paso 1: Generar clave SSH si no tienes una
# (Si ya tienes ~/.ssh/id_ed25519, salta este paso)
ssh-keygen -t ed25519 -C "ova@santonibot"
# Presionar Enter para aceptar la ruta por defecto
# Opcionalmente poner una frase de seguridad (o Enter para ninguna)

# Paso 2: Copiar la clave publica al VM
ssh-copy-id accinproa@192.168.1.26
# Pedir la contrasena una ultima vez

# Paso 3: Verificar que funciona sin contrasena
ssh accinproa@192.168.1.26
# Debe conectar directamente sin pedir contrasena
```

**Configurar alias SSH (para conectar mas rapido):**

En tu maquina local, editar `~/.ssh/config`:
```bash
nano ~/.ssh/config
```

Agregar al final:
```
Host santoni
    HostName 192.168.1.26
    User accinproa
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

Ahora puedes conectar simplemente con:
```bash
ssh santoni
```

### 6.2 Setup inicial de la VM (primera vez)

Esto solo se hace **una vez**, la primera vez que configuras la VM.

```bash
# Paso 1: Conectar a la VM
ssh accinproa@192.168.1.26

# Paso 2: Verificar el sistema operativo
lsb_release -a
# Esperado: Ubuntu 25.10

# Paso 3: Verificar recursos del servidor
free -h          # RAM: debe mostrar ~16GB
nproc            # CPUs: debe mostrar 8
df -h /          # Disco: debe mostrar ~512GB
```

#### 6.2.1 Ejecutar el script de setup

```bash
# Paso 4: Clonar el repositorio en una ubicacion temporal
cd /tmp
git clone https://github.com/ovavisionve/Santoni-Bot.git santonibot-setup
cd santonibot-setup

# Paso 5: Ejecutar el script de setup
# Este script instala Docker, configura el firewall (UFW), instala fail2ban, etc.
bash scripts/setup-vm.sh
```

**Lo que hace `setup-vm.sh`:**
1. Actualiza los paquetes del sistema (`apt-get update && upgrade`)
2. Instala paquetes esenciales: `curl`, `wget`, `git`, `htop`, `ufw`, `fail2ban`, etc.
3. Instala Docker y Docker Compose
4. Configura el firewall UFW:
   - Permite SSH (puerto 22)
   - Permite HTTP (puerto 80)
   - Permite HTTPS (puerto 443)
   - Permite Backend API (puerto 8000) -- remover en produccion final
   - Permite Frontend dev (puerto 3000) -- remover en produccion final
5. Activa fail2ban para proteccion contra fuerza bruta SSH
6. Crea el directorio `/opt/santonibot` con permisos del usuario actual

**Si el script falla en algun paso:**
- Leer el mensaje de error
- Ejecutar los pasos manualmente uno por uno (el script esta documentado internamente)
- Si Docker no se instala: `curl -fsSL https://get.docker.com | sudo sh`

```bash
# Paso 6: Cerrar sesion y volver a conectar (necesario para que los permisos de Docker apliquen)
exit
ssh accinproa@192.168.1.26

# Paso 7: Verificar que Docker funciona
docker --version
# Esperado: Docker version 27.x.x

docker compose version
# Esperado: Docker Compose version v2.x.x

# Paso 8: Verificar que puedes ejecutar Docker sin sudo
docker ps
# Esperado: una tabla vacia (CONTAINER ID, IMAGE, etc.) sin errores
# Si da "permission denied": ejecutar `sudo usermod -aG docker $USER` y reconectar
```

#### 6.2.2 Clonar el proyecto en su ubicacion final

```bash
# Paso 9: Clonar el repositorio en la ubicacion de produccion
# (el directorio /opt/santonibot ya fue creado por setup-vm.sh)
git clone https://github.com/ovavisionve/Santoni-Bot.git /opt/santonibot

# Paso 10: Verificar que se clono correctamente
ls /opt/santonibot
# Debe mostrar: backend, frontend, docker-compose.yml, nginx, docs, scripts, etc.

# Paso 11: Entrar al directorio del proyecto
cd /opt/santonibot
```

### 6.3 Configurar .env de produccion

```bash
# Paso 12: Crear el archivo .env a partir del ejemplo
cp .env.example .env

# Paso 13: Generar claves seguras
# Primero, generar el SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Copiar el resultado (algo como: xK9mZ2pQ...)

# Segundo, generar el POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
# Copiar el resultado

# Paso 14: Editar el .env con los valores de produccion
nano .env
```

**Borrar todo el contenido del .env y pegar lo siguiente** (modificando los valores marcados con `<CAMBIAR>`):

```env
# ============================================
# SantoniBot - PRODUCCION (VM 192.168.1.26)
# ============================================

# ---- General ----
APP_NAME=SantoniBot
APP_ENV=production
DEBUG=false

# ---- Admin ----
# Contrasena del admin por defecto. Cambiar despues del primer login.
ADMIN_DEFAULT_PASSWORD=SantoniAdmin2026!

# ---- Backend ----
BACKEND_PORT=8000
SECRET_KEY=<CAMBIAR-PEGAR-EL-TOKEN-GENERADO-EN-PASO-13>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

# ---- Database SantoniBot (interna, PostgreSQL 16 en Docker) ----
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=santonibot
POSTGRES_USER=santonibot
POSTGRES_PASSWORD=<CAMBIAR-PEGAR-EL-PASSWORD-GENERADO-EN-PASO-13>

# ---- iDempiere Database (solo lectura, PostgreSQL 13 en 192.168.1.73) ----
IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=ova2026*

# ---- AI Provider ----
# Opciones: "groq" (gratis, por defecto) o "anthropic" (Claude, pago, mejor calidad)
AI_PROVIDER=groq

GROQ_API_KEY=<CAMBIAR-PEGAR-TU-GROQ-API-KEY>
GROQ_MODEL=llama-3.3-70b-versatile

# Claude API (activar cuando este listo - ver Fase 7)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_BASE_URL=

# ---- ChromaDB (Vector Database, en Docker) ----
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# ---- Frontend ----
NEXT_PUBLIC_API_URL=http://192.168.1.26:8000
NEXT_PUBLIC_APP_NAME=SantoniBot

# ---- Nginx / Domain ----
DOMAIN=192.168.1.26

# ---- Sentry (opcional, monitoreo de errores) ----
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
NEXT_PUBLIC_SENTRY_DSN=
```

Guardar con **Ctrl+O**, Enter, **Ctrl+X**.

**Verificar que el .env se guardo correctamente:**
```bash
# Ver el contenido (CUIDADO: no hacer esto si alguien esta mirando tu pantalla)
cat .env | head -20

# Verificar que no hay lineas vacias donde deberian tener valor
grep "=<CAMBIAR" .env
# Si aparece algo, falta cambiar ese valor
```

### 6.4 Desplegar con Docker Compose

```bash
# Paso 15: Ejecutar el script de despliegue
cd /opt/santonibot
bash scripts/deploy.sh
```

**Lo que hace `deploy.sh`:**
1. Verifica que Docker y Docker Compose estan instalados
2. Verifica que el archivo `.env` existe
3. Hace `git pull origin main` para traer los ultimos cambios
4. **Detecta automaticamente el entorno:** si `APP_ENV=production` en `.env`, usa `docker-compose.prod.yml` (sin bind mounts, 4 workers, limites de memoria)
5. Construye las imagenes Docker (`docker compose build --no-cache`)
6. Detiene los contenedores existentes (`docker compose down`)
7. Levanta los nuevos contenedores (`docker compose up -d`)
8. Espera 10 segundos y verifica la salud de la API

**Resultado esperado al final del deploy:**
```
==========================================
  Deployment Complete!
==========================================

Access points:
  Frontend:  http://192.168.1.26
  API:       http://192.168.1.26:8000

Default admin login:
  User: admin
  Pass: SantoniAdmin2026!
```

> **Nota:** En produccion (`DEBUG=false`), la documentacion interactiva de la API (`/api/docs`) esta deshabilitada por seguridad. Solo esta disponible en desarrollo.

**Verificar que todo esta corriendo:**
```bash
# Ver estado de todos los contenedores
docker compose ps
```

Debes ver 5 contenedores con estado `Up`:

| Nombre | Estado | Puerto |
|--------|--------|--------|
| santoni-bot-db-1 | Up (healthy) | 5433->5432 |
| santoni-bot-chromadb-1 | Up | 8001->8000 |
| santoni-bot-backend-1 | Up | 8000->8000 |
| santoni-bot-frontend-1 | Up | 3000->3000 |
| santoni-bot-nginx-1 | Up | 80->80, 443->443 |

**Si algun contenedor no esta Up:**
```bash
# Ver logs del contenedor con problemas
docker compose logs backend     # para el backend
docker compose logs frontend    # para el frontend
docker compose logs db          # para la base de datos
docker compose logs nginx       # para nginx
docker compose logs chromadb    # para ChromaDB

# Ver logs en tiempo real (Ctrl+C para salir)
docker compose logs -f backend
```

**Problemas comunes y soluciones:**

| Error en logs | Causa | Solucion |
|---------------|-------|----------|
| `password authentication failed` (db) | El password de PostgreSQL no coincide | Borrar volumenes y recrear: `docker compose down -v && bash scripts/deploy.sh` |
| `GROQ_API_KEY` vacio o invalido (backend) | No pusiste la API key de Groq | Editar `.env` y agregar la GROQ_API_KEY |
| `Cannot connect to iDempiere` (backend) | La VM no puede alcanzar 192.168.1.73 | Verificar conectividad: `ping 192.168.1.73` desde la VM. No necesita VPN porque ya esta en la red interna. |
| `port is already allocated` | Otro servicio usa ese puerto | `sudo lsof -i :80` para ver que esta usando el puerto. `sudo systemctl stop apache2` si hay Apache. |
| Frontend muestra pagina en blanco | Frontend aun esta compilando | Esperar 1-2 minutos. Ver logs: `docker compose logs frontend` |

### 6.5 Configurar Nginx con SSL (opcional, para HTTPS)

Si Santoni quiere acceso HTTPS (recomendado si se accede desde internet):

#### Opcion A: Certificado autofirmado (para red interna)

```bash
# Generar certificado autofirmado
sudo mkdir -p /opt/santonibot/nginx/certs

sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/santonibot/nginx/certs/selfsigned.key \
  -out /opt/santonibot/nginx/certs/selfsigned.crt \
  -subj "/C=VE/ST=Portuguesa/L=Acarigua/O=Alimentos Santoni/CN=192.168.1.26"
```

Luego editar `nginx/nginx.conf` y descomentar las lineas de SSL:
```bash
nano /opt/santonibot/nginx/nginx.conf
```

Cambiar:
```nginx
    server {
        listen 80;
        listen 443 ssl http2;
        server_name 192.168.1.26;

        ssl_certificate /etc/nginx/certs/selfsigned.crt;
        ssl_certificate_key /etc/nginx/certs/selfsigned.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5:!RC4;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
```

Agregar el volumen de certificados en `docker-compose.yml` o `docker-compose.prod.yml`:
```yaml
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
```

Reiniciar nginx:
```bash
docker compose restart nginx
```

#### Opcion B: Let's Encrypt (si tienen dominio publico)

Solo si Santoni configura un dominio apuntando a `201.249.55.198`:

```bash
# Instalar certbot en la VM
sudo apt-get install -y certbot

# Detener nginx temporalmente
docker compose stop nginx

# Obtener certificado
sudo certbot certonly --standalone -d santonibot.santoni.com.ve

# Los certificados se guardan en /etc/letsencrypt/live/santonibot.santoni.com.ve/
# Reiniciar nginx con la configuracion SSL apuntando a esos archivos
docker compose start nginx
```

### 6.6 Verificar que todo funciona

Desde cualquier computadora en la red de Santoni (o con VPN activa):

```bash
# Test 1: Health check del API
curl -s http://192.168.1.26:8000/api/health
# Esperado: {"status":"ok","app":"SantoniBot","version":"1.0.0"}

# Test 2: Abrir el frontend en el navegador
# Ir a http://192.168.1.26 en Chrome/Firefox
# Debe mostrar la pantalla de login de SantoniBot
```

**Hacer login:**
1. Usuario: `admin`
2. Contrasena: `SantoniAdmin2026!` (o la que hayas puesto en `ADMIN_DEFAULT_PASSWORD`)

**Probar una pregunta:**
1. Escribir: "Cuales son los top 10 clientes por facturacion?"
2. Esperar respuesta
3. Si los datos son de iDempiere (nombres reales de clientes), la integracion funciona
4. Si los datos son demo (Distribuidora Caracas, etc.), revisar la configuracion de `query_service.py`

### 6.7 Comandos utiles para mantenimiento de la VM

```bash
# ---- Estado y logs ----
docker compose ps                        # Ver estado de contenedores
docker compose logs -f                   # Ver todos los logs en tiempo real
docker compose logs -f backend           # Solo logs del backend
docker compose logs --tail=100 backend   # Ultimas 100 lineas del backend

# ---- Reiniciar servicios ----
docker compose restart                   # Reiniciar todo
docker compose restart backend           # Reiniciar solo el backend
docker compose restart nginx             # Reiniciar solo nginx

# ---- Detener y levantar ----
docker compose down                      # Detener todo
docker compose up -d                     # Levantar todo
docker compose up -d --build             # Reconstruir y levantar

# ---- Base de datos interna de SantoniBot ----
docker compose exec db psql -U santonibot    # Abrir shell SQL
docker compose exec db pg_dump -U santonibot santonibot > backup.sql  # Backup

# ---- Actualizar el codigo ----
cd /opt/santonibot
git pull origin main                     # Traer cambios del repositorio
bash scripts/deploy.sh                   # Redesplegar

# ---- Monitoreo del sistema ----
htop                                     # Ver CPU, RAM, procesos
df -h                                    # Ver espacio en disco
docker system df                         # Ver espacio usado por Docker

# ---- Limpiar Docker (si se llena el disco) ----
docker system prune -a --volumes         # CUIDADO: borra todo lo no usado
```

---

## FASE 7: Integracion con Claude API (cuando este listo)

SantoniBot soporta dos proveedores de IA:
- **Groq** (Llama 3.1 70B): Gratis, rapido, buen rendimiento. Es el proveedor por defecto.
- **Anthropic (Claude)**: Pago, mejor calidad de respuestas, soporta analisis de documentos e imagenes.

Cuando Santoni este listo para usar Claude (mejor calidad, analisis de documentos), seguir estos pasos:

### 7.1 Obtener API Key de Anthropic

1. Ir a https://console.anthropic.com/
2. Crear una cuenta o iniciar sesion
3. Ir a **"API Keys"** en el menu lateral
4. Clic en **"Create Key"**
5. Nombre: `SantoniBot Production`
6. Clic en **"Create Key"**
7. **Copiar la clave inmediatamente** (empieza con `sk-ant-...`). Solo se muestra una vez.
8. Guardarla en un lugar seguro

> **Costos:** Claude API cobra por tokens de entrada y salida. Consultar precios en https://www.anthropic.com/pricing
> Estimado para SantoniBot: depende del uso, pero para consultas empresariales tipicas puede ser entre $20-$100/mes.

### 7.2 Configurar la API Key en el .env

Conectar a la VM y editar el .env:

```bash
ssh accinproa@192.168.1.26
cd /opt/santonibot
nano .env
```

Cambiar estas dos lineas:
```env
# ANTES:
AI_PROVIDER=groq
ANTHROPIC_API_KEY=

# DESPUES:
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-PEGAR-TU-CLAVE-AQUI
```

El modelo ya esta configurado como `claude-sonnet-4-5-20250929`. No necesitas cambiarlo.

Guardar con Ctrl+O, Enter, Ctrl+X.

### 7.3 Reiniciar los contenedores

```bash
cd /opt/santonibot
docker compose restart backend
```

Esperar 10-15 segundos y verificar que el backend levanto correctamente:
```bash
# Verificar salud
curl -s http://localhost:8000/api/health

# Ver logs para confirmar que usa Anthropic
docker compose logs --tail=20 backend
# Buscar una linea que diga algo como "AI Provider: anthropic" o "Using Claude"
```

### 7.4 Probar la funcionalidad de documentos (si aplica)

Claude soporta analisis de documentos (PDF, imagenes). Si SantoniBot tiene esta funcionalidad implementada:

1. Entrar a http://192.168.1.26
2. Login como admin
3. Subir un documento (PDF de factura, imagen de inventario, etc.)
4. Hacer una pregunta sobre el documento
5. Claude debe ser capaz de leer y analizar el contenido

### 7.5 Comparar Groq vs Claude

Para evaluar cual proveedor es mejor para Santoni, probar la misma pregunta con ambos:

1. Configurar `AI_PROVIDER=groq` en `.env` y reiniciar
2. Hacer la pregunta: "Analiza las ventas del ultimo trimestre y dame recomendaciones"
3. Copiar la respuesta
4. Cambiar a `AI_PROVIDER=anthropic` en `.env` y reiniciar
5. Hacer la misma pregunta
6. Comparar:
   - Calidad del analisis
   - Profundidad de las recomendaciones
   - Tiempo de respuesta
   - Formato de la respuesta

**Criterios de comparacion:**
| Criterio | Groq (Llama 3.1) | Claude (Anthropic) |
|----------|-------------------|--------------------|
| Velocidad | Muy rapido (~2-5s) | Rapido (~3-8s) |
| Calidad de analisis | Buena | Excelente |
| Costo | Gratis | Pago (por token) |
| Analisis de documentos | No | Si |
| Razonamiento complejo | Bueno | Superior |
| Idioma espanol | Bueno | Excelente |

> **Recomendacion:** Empezar con Groq (gratis) y cambiar a Claude cuando Santoni confirme el presupuesto para la API.

---

## Template completo del .env de PRODUCCION

Para referencia rapida, aqui esta el `.env` completo con todos los valores de produccion. Copiar y adaptar:

```env
# ============================================
# SantoniBot - Configuracion de PRODUCCION
# VM: 192.168.1.26 (Ubuntu 25.10)
# ============================================
# NUNCA commitear este archivo al repositorio
# NUNCA compartir por canales no seguros

# ---- General ----
APP_NAME=SantoniBot
APP_ENV=production
DEBUG=false

# ---- Admin ----
ADMIN_DEFAULT_PASSWORD=SantoniAdmin2026!

# ---- Backend ----
BACKEND_PORT=8000
SECRET_KEY=<GENERAR: python3 -c "import secrets; print(secrets.token_urlsafe(48))">
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

# ---- Database SantoniBot (interna, Docker) ----
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=santonibot
POSTGRES_USER=santonibot
POSTGRES_PASSWORD=<GENERAR: python3 -c "import secrets; print(secrets.token_urlsafe(24))">

# ---- iDempiere Database (solo lectura) ----
IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=ova2026*

# ---- AI Provider ----
AI_PROVIDER=groq
GROQ_API_KEY=<TU-GROQ-API-KEY>
GROQ_MODEL=llama-3.3-70b-versatile

# ---- Claude API (activar cuando este listo) ----
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_BASE_URL=

# ---- ChromaDB ----
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# ---- Frontend ----
NEXT_PUBLIC_API_URL=http://192.168.1.26:8000
NEXT_PUBLIC_APP_NAME=SantoniBot

# ---- Nginx / Domain ----
DOMAIN=192.168.1.26

# ---- Sentry (opcional) ----
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
NEXT_PUBLIC_SENTRY_DSN=
```

---

## Checklist Completo de Conexion

Marca cada item cuando lo hayas completado:

### Fase 1: Acceso VPN
- [ ] Tienes las credenciales VPN (usuario: OVA, contrasena: Santoni2022$)
- [ ] Conoces la IP del gateway VPN (201.249.55.198)
- [ ] Conoces el puerto del gateway VPN (443 o 10443)

### Fase 2: Conectar VPN
- [ ] FortiClient (o openfortivpn) instalado
- [ ] Conexion VPN configurada
- [ ] VPN conectada exitosamente
- [ ] Ping a 192.168.1.26 (VM) funciona
- [ ] Ping a 192.168.1.73 (iDempiere) funciona
- [ ] Puerto 22 de la VM abierto (nc -zv)
- [ ] Puerto 5432 de iDempiere abierto (nc -zv)

### Fase 3: Acceso a iDempiere
- [ ] psql, pgAdmin o DBeaver instalado
- [ ] Conexion a idempiere_produccion exitosa
- [ ] Query `SELECT current_database()` funciona
- [ ] Query `SELECT count(*) FROM adempiere.ad_table` funciona
- [ ] Query de tablas clave (c_bpartner, c_invoice, m_product) funciona
- [ ] Verificado que el usuario ova es de solo lectura

### Fase 4: Mapeo de tablas
- [ ] Exploradas tablas de Ventas (c_invoice, c_bpartner, c_payment)
- [ ] Exploradas tablas de Finanzas (c_bankaccount, c_bankstatement)
- [ ] Exploradas tablas de Contabilidad (fact_acct, c_elementvalue, gl_journal)
- [ ] Exploradas tablas de RRHH (hr_employee, hr_payroll, o alternativas)
- [ ] Exploradas tablas de Produccion (m_production, pp_order)
- [ ] Exploradas tablas de Compras (c_order con issotrx='N')
- [ ] Buscadas tablas personalizadas de Santoni (xx_*, *arroz*, *productor*)
- [ ] Documentado el mapeo tabla por tabla

### Fase 5: Configuracion
- [ ] .env actualizado con credenciales de iDempiere
- [x] query_service.py con dual-mode (demo/iDempiere) - ya implementado
- [x] idempiere_queries.py con queries para los 7 agentes - ya implementado
- [ ] Queries de iDempiere validadas contra tablas reales (pueden necesitar ajustes)
- [ ] Cada agente probado con datos reales

### Fase 6: Despliegue
- [ ] SSH a la VM funciona (accinproa@192.168.1.26)
- [ ] setup-vm.sh ejecutado en la VM
- [ ] Docker y Docker Compose instalados en la VM
- [ ] Repositorio clonado en /opt/santonibot
- [ ] .env de produccion configurado
- [ ] deploy.sh ejecutado exitosamente
- [ ] 5 contenedores corriendo (docker compose ps)
- [ ] Health check OK (curl http://192.168.1.26:8000/api/health)
- [ ] Frontend accesible en http://192.168.1.26
- [ ] Login con admin funciona
- [ ] Al menos una pregunta de prueba responde correctamente
- [ ] SSL configurado (opcional)

### Fase 7: Claude API (cuando este listo)
- [ ] API key de Anthropic obtenida
- [ ] AI_PROVIDER=anthropic en .env
- [ ] ANTHROPIC_API_KEY configurada en .env
- [ ] Contenedores reiniciados
- [ ] Verificado que usa Claude en los logs
- [ ] Funcionalidad de documentos probada (si aplica)
- [ ] Comparacion Groq vs Claude documentada

---

## Notas de Seguridad

1. **NUNCA** commitear el archivo `.env` con credenciales reales al repositorio Git
2. **NUNCA** compartir credenciales de VPN por canales no seguros (usar Signal, WhatsApp cifrado, o en persona)
3. El usuario `ova` es de **solo lectura** -- no puede modificar datos de iDempiere bajo ninguna circunstancia
4. **Cambiar** la contrasena del admin de SantoniBot (`SantoniAdmin2026!`) despues del primer deploy
5. **Generar** un `SECRET_KEY` unico para produccion (no usar el de desarrollo)
6. Las credenciales de la VPN (`Santoni2022$`) pueden cambiar periodicamente. Si la VPN deja de conectar, contactar IT de Santoni
7. Si pierdes acceso SSH a la VM, contactar IT de Santoni para restablecer
8. Mantener el servidor actualizado: `sudo apt-get update && sudo apt-get upgrade` periodicamente

---

## Historial de Cambios de este Manual

| Fecha | Cambio |
|-------|--------|
| 2026-02-18 | Fase 5.2 actualizada: query_service.py ya tiene dual-mode implementado (no requiere cambios manuales). Templates .env corregidos: ANTHROPIC_MODEL fijo a claude-3-5-sonnet-20241022, agregadas ANTHROPIC_BASE_URL y SENTRY_*. Fase 6.4: deploy.sh ahora auto-detecta produccion y usa docker-compose.prod.yml. Quitada referencia a /api/docs en produccion. |
| 2026-02-10 | Reescritura completa con detalle de 7 fases, queries de exploracion por departamento, troubleshooting, y template .env |
