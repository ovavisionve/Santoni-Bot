# Coolify Deployment - SantoniBot

## Setup in Coolify

1. **Add Resource**: In Coolify dashboard, add a new "Docker Compose" resource
2. **Connect Repo**: Point to this repository
3. **Set Compose File**: Use `coolify/docker-compose.coolify.yml`
4. **Configure Environment Variables** in Coolify:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Internal DB password | (generate strong password) |
| `SECRET_KEY` | JWT secret key (32+ chars) | (generate random string) |
| `GROQ_API_KEY` | Groq API key | `gsk_...` |
| `IDEMPIERE_DB_HOST` | iDempiere DB host | `192.168.1.73` |
| `IDEMPIERE_DB_PASSWORD` | iDempiere DB password | (provided by Santoni IT) |
| `DOMAIN` | Public domain | `santonibot.santoni.com` |

### Optional Variables

| Variable | Default |
|----------|---------|
| `POSTGRES_DB` | `santonibot` |
| `POSTGRES_USER` | `santonibot` |
| `IDEMPIERE_DB_PORT` | `5432` |
| `IDEMPIERE_DB_NAME` | `idempiere_produccion` |
| `IDEMPIERE_DB_USER` | `ova` |
| `ANTHROPIC_API_KEY` | (empty) |

5. **Deploy**: Click deploy in Coolify

## SSL

Coolify handles SSL automatically via Let's Encrypt when a domain is configured.

## Monitoring

Coolify provides built-in monitoring. Additionally:
- API health: `GET /api/health`
- Logs: Available in Coolify dashboard per service
