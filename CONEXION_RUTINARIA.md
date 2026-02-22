# Conexion Rutinaria al Servidor SantoniBot

## 1. Conectarse por SSH

```bash
ssh accinproa@192.168.1.73
```

Ingresa tu contraseña cuando la pida. Si estas fuera de la red de Santoni, necesitas VPN primero.

---

## 2. Ir al directorio del proyecto

```bash
cd /opt/santonibot
```

---

## 3. Verificar que todo esta corriendo

```bash
docker compose ps
```

Deberias ver 5 contenedores con estado `Up` o `Running`:

| Contenedor | Puerto | Funcion |
|---|---|---|
| santonibot-db-1 | 5433 | PostgreSQL (BD interna) |
| santonibot-chromadb-1 | 8001 | ChromaDB (vectores) |
| santonibot-backend-1 | 8000 | FastAPI (API) |
| santonibot-frontend-1 | 3000 | Next.js (interfaz web) |
| santonibot-nginx-1 | 80/443 | Nginx (proxy) |

Si algun contenedor esta apagado o dice `Exited`:

```bash
docker compose up -d
```

---

## 4. Si algo no funciona bien

### Ver logs de un contenedor especifico:

```bash
docker compose logs backend --tail 50
docker compose logs frontend --tail 50
docker compose logs nginx --tail 50
```

### Reiniciar un contenedor sin perder datos:

```bash
docker compose restart backend
docker compose restart frontend
```

### Reiniciar todo:

```bash
docker compose down && docker compose up -d
```

---

## 5. Aplicar cambios de codigo (deploy)

Cuando haya cambios nuevos en el repositorio:

```bash
cd /opt/santonibot

# Bajar los cambios
git pull origin main

# Rebuild y deploy del backend
docker compose build --no-cache backend && docker compose up -d backend

# Rebuild y deploy del frontend
docker compose build --no-cache frontend && docker compose up -d frontend

# O ambos a la vez:
docker compose build --no-cache backend frontend && docker compose up -d
```

**IMPORTANTE**: Cambios de frontend SIEMPRE necesitan `build --no-cache` porque Next.js compila el codigo dentro del contenedor.

---

## 6. Cambiar API keys u otras variables de entorno

```bash
nano /opt/santonibot/.env
```

Edita lo que necesites, guarda con `Ctrl+O`, sal con `Ctrl+X`, y reinicia:

```bash
docker compose restart backend
```

---

## 7. Backup manual de la base de datos

```bash
docker compose run --rm backup
```

Los backups se guardan automaticamente y se eliminan los de mas de 30 dias.

---

## 8. Ver usuarios conectados / actividad

```bash
# Logs en vivo del backend
docker compose logs -f backend

# Logs en vivo del nginx (peticiones HTTP)
docker compose logs -f nginx
```

`Ctrl+C` para dejar de ver los logs.

---

## Acceso rapido al bot

- **Desde la red de Santoni**: http://192.168.1.73
- **Panel de admin**: http://192.168.1.73/admin
