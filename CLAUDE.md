# SantoniBot - Sistema Inteligente de Análisis de Datos Empresariales

## Project Overview
Enterprise AI data analysis system for Alimentos Santoni, C.A.
Built by OVA Agency. Multi-agent architecture with 7 specialized department agents.

## Tech Stack
- **Frontend**: Next.js 14 + React + TypeScript + Tailwind CSS
- **Backend**: Python FastAPI
- **Database**: PostgreSQL 16 (internal) + PostgreSQL 13 (iDempiere ERP)
- **Vector DB**: ChromaDB
- **AI**: Groq (Llama 3.1 70B) primary, Claude API secondary
- **Orchestration**: LangChain
- **Deploy**: Docker Compose + Coolify + Nginx

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Docker: `docker-compose up -d`
- Tests backend: `cd backend && pytest`
- Tests frontend: `cd frontend && npm test`
- Migrations: `cd backend && alembic upgrade head`

## Architecture
- `/frontend` - Next.js app (chat UI, login, admin panel)
- `/backend/app/api` - FastAPI routes
- `/backend/app/agents` - AI agents (orchestrator + 7 department agents)
- `/backend/app/models` - SQLAlchemy models
- `/backend/app/schemas` - Pydantic schemas
- `/backend/app/services` - Business logic services
- `/backend/app/middleware` - Auth, security, audit middleware

## Agents
1. Finanzas - Financial queries (cash flow, receivables, payables)
2. Contabilidad - Accounting (balance sheet, P&L, ledgers)
3. Ventas - Sales (rankings, clients, collections, zones)
4. RRHH - Human Resources (payroll, attendance, employees)
5. Producción - Production (daily output, efficiency, waste)
6. Compras Insumos - Supplies procurement
7. Compras Productores - Producer purchases (rice, corn)

## Client Info
- ERP: iDempiere on PostgreSQL 13 (192.168.1.73:5432)
- All data comes from iDempiere, no Excel
- RBAC: each department sees only its own data
- Spanish language throughout
