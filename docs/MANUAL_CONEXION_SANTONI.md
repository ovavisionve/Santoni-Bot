# Manual de Conexión al Entorno de Santoni

## Información del Entorno

### Red Interna Santoni
| Recurso | IP/Host | Puerto | Notas |
|---------|---------|--------|-------|
| VM SantoniBot | 192.168.1.26 | 22 (SSH) | Ubuntu 25.10, 16GB RAM, 8 vCPU, 512GB SSD |
| iDempiere DB | 192.168.1.73 | 5432 | PostgreSQL 13, DB: idempiere_produccion |
| SQL Server (asistencia) | Por confirmar | 1433 | SQL Server 11, sistema de asistencia |
| IP Pública | 201.249.55.198 | 80/443 | Acceso externo |

### Credenciales

#### VPN (FortiClient)
| Campo | Valor |
|-------|-------|
| Tipo | FortiClient VPN |
| Servidor | 201.249.55.198 (o el gateway que indique Santoni) |
| Usuario | `OVA` |
| Contraseña | `Santoni2022$` |
| Puerto | 443 o 10443 (verificar con Santoni IT) |

#### VM (SSH)
| Campo | Valor |
|-------|-------|
| Host | 192.168.1.26 |
| Usuario | `accinproa` |
| Contraseña | `pTTkL3gHLYmj5$BL1oFq` |

#### iDempiere Database
| Campo | Valor |
|-------|-------|
| Host | 192.168.1.73 |
| Puerto | 5432 |
| Base de datos | `idempiere_produccion` |
| Usuario | `ova` |
| Contraseña | `ova2026*` |
| Acceso | Solo lectura (SELECT) |

---

## Paso 1: Conectar VPN con FortiClient

### Instalar FortiClient

**macOS:**
```bash
brew install --cask forticlient-vpn
# O descargar de: https://www.fortinet.com/support/product-downloads
```

**Windows:**
- Descargar FortiClient VPN de https://www.fortinet.com/support/product-downloads
- Instalar la versión "VPN Only"

**Linux (Ubuntu/Debian):**
```bash
# Opción 1: FortiClient
wget -O - https://repo.fortinet.com/repo/forticlient/7.4/ubuntu/DEB-GPG-KEY | sudo apt-key add -
echo "deb https://repo.fortinet.com/repo/forticlient/7.4/ubuntu/ stable non-free" | sudo tee /etc/apt/sources.list.d/forticlient.list
sudo apt-get update
sudo apt-get install forticlient

# Opción 2: openfortivpn (línea de comandos)
sudo apt-get install openfortivpn
```

### Conectar

**FortiClient GUI:**
1. Abrir FortiClient
2. VPN → Configurar nueva conexión
3. Tipo: SSL-VPN
4. Nombre: `Santoni VPN`
5. Gateway: `201.249.55.198`
6. Puerto: `443` (o `10443`, verificar con IT de Santoni)
7. Usuario: `OVA`
8. Guardar
9. Conectar → Ingresar contraseña: `Santoni2022$`

**openfortivpn (Linux CLI):**
```bash
sudo openfortivpn 201.249.55.198:443 \
  --username=OVA \
  --password='Santoni2022$' \
  --trusted-cert <fingerprint>
```
> El fingerprint lo obtienes en la primera conexión. Santoni IT debe confirmarlo.

### Verificar conexión VPN
```bash
# Ping al VM
ping 192.168.1.26

# Ping al servidor iDempiere
ping 192.168.1.73

# Si ambos responden, la VPN funciona
```

---

## Paso 2: Conectar al VM por SSH

### Conexión directa
```bash
ssh accinproa@192.168.1.26
# Contraseña: pTTkL3gHLYmj5$BL1oFq
```

### Configurar acceso SSH con clave (recomendado)
```bash
# En tu máquina local, generar clave si no tienes
ssh-keygen -t ed25519 -C "ova@santonibot"

# Copiar clave al VM
ssh-copy-id accinproa@192.168.1.26

# Ahora puedes conectar sin contraseña
ssh accinproa@192.168.1.26
```

### Configurar alias SSH (opcional, facilita conexión)
Agregar a `~/.ssh/config`:
```
Host santoni-vm
    HostName 192.168.1.26
    User accinproa
    Port 22
    # IdentityFile ~/.ssh/id_ed25519
```

Ahora puedes conectar con:
```bash
ssh santoni-vm
```

---

## Paso 3: Verificar acceso a iDempiere Database

### Desde tu máquina local (con VPN activa)
```bash
# Instalar psql si no lo tienes
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql-client

# Conectar
psql -h 192.168.1.73 -p 5432 -U ova -d idempiere_produccion
# Contraseña: ova2026*
```

### Desde el VM
```bash
ssh accinproa@192.168.1.26

psql -h 192.168.1.73 -p 5432 -U ova -d idempiere_produccion
# Contraseña: ova2026*
```

### Queries de verificación
Una vez conectado a iDempiere, ejecutar estas queries para verificar acceso:

```sql
-- Verificar conexión
SELECT version();

-- Ver esquemas disponibles
SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;

-- Ver tablas principales (iDempiere usa el schema 'adempiere')
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
ORDER BY table_name
LIMIT 30;

-- Tablas clave que SantoniBot necesita:

-- Clientes/Socios de negocio
SELECT COUNT(*) FROM adempiere.c_bpartner WHERE isactive = 'Y';

-- Facturas
SELECT COUNT(*) FROM adempiere.c_invoice WHERE isactive = 'Y';

-- Productos
SELECT COUNT(*) FROM adempiere.m_product WHERE isactive = 'Y';

-- Órdenes de venta
SELECT COUNT(*) FROM adempiere.c_order WHERE isactive = 'Y';

-- Pagos/Cobranzas
SELECT COUNT(*) FROM adempiere.c_payment WHERE isactive = 'Y';

-- Empleados (si HR está configurado)
SELECT COUNT(*) FROM adempiere.c_bpartner WHERE isemployee = 'Y';

-- Cuentas bancarias
SELECT COUNT(*) FROM adempiere.c_bankaccount WHERE isactive = 'Y';
```

> **IMPORTANTE:** El usuario `ova` tiene acceso de solo lectura. No puedes hacer INSERT, UPDATE, DELETE.

### Mapeo de tablas iDempiere → Agentes SantoniBot

| Agente | Tablas iDempiere principales |
|--------|------------------------------|
| Ventas | `c_invoice`, `c_invoiceline`, `c_bpartner`, `c_order`, `c_payment`, `c_bpartner_location` |
| Finanzas | `c_bankaccount`, `c_bankstatement`, `c_bankstatementline`, `c_payment`, `c_invoice` |
| Contabilidad | `fact_acct`, `c_elementvalue`, `c_period`, `gl_journal`, `gl_journalline` |
| RRHH | `c_bpartner` (employees), `hr_payroll`, `hr_movement`, `hr_concept` |
| Producción | `m_production`, `m_productionline`, `m_product`, `pp_order` |
| Compras Insumos | `c_order` (purchase), `c_orderline`, `m_product`, `c_bpartner` (vendors) |
| Compras Productores | Tablas personalizadas de Santoni (verificar con IT) |

> **Nota:** Los nombres exactos de tablas y columnas pueden variar según la personalización de Santoni. Usar las queries de verificación para confirmar estructura.

---

## Paso 4: Deploy en el VM

### Primera vez (setup inicial)
```bash
# Conectar al VM
ssh accinproa@192.168.1.26

# Ejecutar setup del VM
# (esto instala Docker, configura firewall, etc.)
cd /tmp
git clone <url-del-repo> santonibot-setup
cd santonibot-setup
bash scripts/setup-vm.sh

# Clonar el proyecto en su ubicación final
sudo mkdir -p /opt/santonibot
sudo chown accinproa:accinproa /opt/santonibot
git clone <url-del-repo> /opt/santonibot
cd /opt/santonibot

# Configurar .env con valores de PRODUCCIÓN
cp .env.example .env
nano .env
```

### Valores de .env para PRODUCCIÓN
```env
APP_NAME=SantoniBot
APP_ENV=production
DEBUG=false

BACKEND_PORT=8000
SECRET_KEY=<GENERAR-CLAVE-ALEATORIA-DE-64-CARACTERES>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=santonibot
POSTGRES_USER=santonibot
POSTGRES_PASSWORD=<GENERAR-PASSWORD-FUERTE>

IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=ova2026*

GROQ_API_KEY=<tu-groq-api-key-aqui>
GROQ_MODEL=llama-3.1-70b-versatile

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

CHROMA_HOST=chromadb
CHROMA_PORT=8001

NEXT_PUBLIC_API_URL=http://192.168.1.26:8000
NEXT_PUBLIC_APP_NAME=SantoniBot

DOMAIN=192.168.1.26
```

> **Generar claves seguras:**
> ```bash
> # SECRET_KEY
> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
>
> # POSTGRES_PASSWORD
> python3 -c "import secrets; print(secrets.token_urlsafe(24))"
> ```

### Desplegar
```bash
cd /opt/santonibot
bash scripts/deploy.sh
```

### Acceder
- **Desde red interna Santoni:** http://192.168.1.26
- **Desde internet (con port forwarding):** http://201.249.55.198
- **API docs:** http://192.168.1.26:8000/docs

---

## Paso 5: Mapear tablas reales de iDempiere

Una vez conectado a `idempiere_produccion`, necesitamos:

### 5.1 Explorar la estructura
```sql
-- Columnas de una tabla específica
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'adempiere' AND table_name = 'c_invoice'
ORDER BY ordinal_position;

-- Buscar tablas personalizadas de Santoni
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adempiere'
  AND (table_name LIKE '%santoni%'
       OR table_name LIKE '%arroz%'
       OR table_name LIKE '%productor%'
       OR table_name LIKE '%xx_%')
ORDER BY table_name;
```

### 5.2 Verificar datos de ventas (agente prioritario)
```sql
-- Vendedores activos
SELECT bp.value, bp.name, sr.name as sales_region
FROM adempiere.c_bpartner bp
LEFT JOIN adempiere.c_salesregion sr ON bp.c_salesregion_id = sr.c_salesregion_id
WHERE bp.issalesrep = 'Y' AND bp.isactive = 'Y';

-- Facturas recientes
SELECT i.documentno, bp.name as cliente, i.dateinvoiced, i.grandtotal
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'Y'
ORDER BY i.dateinvoiced DESC
LIMIT 20;

-- Cobranzas
SELECT p.documentno, bp.name as cliente, p.datetrx, p.payamt
FROM adempiere.c_payment p
JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id
WHERE p.isreceipt = 'Y'
ORDER BY p.datetrx DESC
LIMIT 20;
```

### 5.3 Siguiente paso: actualizar query_service.py
Una vez mapeadas las tablas reales, actualizaremos `backend/app/services/query_service.py` para que los agentes consulten datos reales de iDempiere en vez de las tablas demo.

---

## Checklist de Conexión

- [ ] Instalar FortiClient VPN
- [ ] Conectar VPN con credenciales OVA/Santoni2022$
- [ ] Verificar ping a 192.168.1.26 (VM)
- [ ] Verificar ping a 192.168.1.73 (iDempiere)
- [ ] Conectar SSH al VM (accinproa@192.168.1.26)
- [ ] Conectar psql a iDempiere (ova@192.168.1.73)
- [ ] Ejecutar queries de verificación
- [ ] Explorar tablas personalizadas de Santoni
- [ ] Mapear tablas de ventas (agente prioritario)
- [ ] Configurar .env de producción
- [ ] Ejecutar deploy en VM
- [ ] Verificar acceso web en http://192.168.1.26

---

## Contactos

| Rol | Persona | Para qué |
|-----|---------|----------|
| IT Santoni | (preguntar) | Problemas de VPN, firewall, acceso DB |
| Ventas | Marlenis Figueredo | Validar datos de ventas |
| Compras Productores | Marlenis Figueredo | Validar datos de compras |
| Compras Insumos | Onofrio Gueccia, Jorge Chahine | Validar datos de insumos |
| Producción | (preguntar) | Validar datos de producción |

## Notas de Seguridad

1. **NUNCA** commitear el archivo `.env` con credenciales reales
2. **NUNCA** compartir las credenciales de VPN por canales no seguros
3. El usuario `ova` es de solo lectura - no puede modificar datos de iDempiere
4. Cambiar la contraseña del admin de SantoniBot (`SantoniAdmin2026!`) después del primer deploy
5. Generar un `SECRET_KEY` único para producción (no usar el de desarrollo)
