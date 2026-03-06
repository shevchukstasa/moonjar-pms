# Moonjar PMS — Production Management System

Multi-factory production management system for stone products manufacturer.

## Features

- **8 User Roles**: Owner, Administrator, CEO, Production Manager, Quality Manager, Warehouse, Sorter/Packer, Purchaser
- **Order Management**: Webhook intake, PDF upload, manual entry, change requests
- **Production Pipeline**: Recipe → Material reservation → Glazing → Kiln → Sorting → Packing → QC → Shipment
- **Kiln Scheduling**: TOC/DBR with automatic assignment, batch formation, co-firing validation
- **Material Management**: BOM-based reservation, purchase requests, supplier tracking
- **Quality Control**: Random sampling (2%), mandatory QC flags, problem cards, QM blocks
- **Real-time Tablo**: Drag-and-drop production board with WebSocket updates
- **Warehouse PWA**: Offline-capable mobile app for warehouse operations
- **Analytics**: TPS/Lean metrics, kiln utilization, KPI dashboards
- **AI Chat**: RAG-powered assistant with pgvector embeddings
- **Integrations**: Sales webhook, Telegram bot (Indonesian), Google OAuth

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, APScheduler |
| Frontend | React 18, TypeScript, Vite 5, Tailwind CSS 3 |
| State | TanStack Query 5 (server), Zustand 4 (client) |
| Auth | JWT HttpOnly cookies, Google OAuth, TOTP 2FA |
| Search | pgvector (RAG embeddings) |
| Storage | Supabase Storage (photos, PDFs) |
| PWA | Vite PWA plugin, Workbox |
| Deploy | Docker Compose, nginx reverse proxy |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for running the generator)

### 1. Generate the project
```bash
python3 generate_project.py
cd moonjar-pms
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Set up Supabase
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Enable the `pgvector` extension: SQL Editor → `CREATE EXTENSION IF NOT EXISTS vector;`
3. Copy the connection string to `.env` → `DATABASE_URL`
4. Create Storage buckets:
   - `packing-photos` (public)
   - `pdf-orders` (private)
   - `defect-photos` (private)
   - `qc-photos` (private)
   - `worker-media` (private)
   - `exports` (private)
5. Copy Supabase URL and anon key to `.env`

### 4. Run with Docker
```bash
# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d
```

### 5. Initialize database
```bash
# Run migrations
docker compose exec api alembic upgrade head

# Seed owner account
docker compose exec api python scripts/seed_owner.py

# Seed reference data
docker compose exec api python scripts/seed_reference_data.py
```

### 6. Access the application
- **Dashboard**: http://localhost:5174
- **API Docs**: http://localhost:8000/docs
- **Warehouse PWA**: http://localhost:5175

### 7. First login
Use the owner key from `.env` → `OWNER_SETUP_KEY` at `/api/auth/verify-owner-key` to create the first admin account.

## Project Structure

```
moonjar-pms/
├── api/                    # FastAPI backend
│   ├── main.py            # App entry + middleware + router mounting
│   ├── config.py          # Pydantic Settings
│   ├── database.py        # SQLAlchemy engine + session
│   ├── models.py          # 78 SQLAlchemy models
│   ├── schemas.py         # 234 Pydantic schemas
│   ├── auth.py            # JWT + Google OAuth + TOTP + CSRF
│   ├── roles.py           # RBAC decorators
│   ├── middleware.py      # CSRF + request logging
│   ├── scheduler.py       # APScheduler (10 jobs)
│   ├── websocket.py       # WebSocket connection manager
│   └── routers/           # 40 router files
├── business/              # Business logic layer
│   ├── services/          # 20 service modules
│   ├── kiln/              # Kiln assignment + capacity + rules
│   ├── planning_engine/   # Production scheduling
│   └── rag/               # AI embeddings + retriever
├── presentation/
│   ├── dashboard/         # React 18 SPA
│   └── warehouse-pwa/     # Offline-capable PWA
├── tests/                 # Unit + integration + security tests
├── scripts/               # Seed data, backup
├── alembic/               # Database migrations
├── nginx/                 # Reverse proxy config
├── docker-compose.yml     # Development setup
└── docker-compose.prod.yml
```

## Hosting Recommendations

### Railway.app (Recommended)
- Simplest deployment: connect GitHub repo → auto-deploy
- ~$5/month for small workloads
- Auto-HTTPS, managed PostgreSQL available
- `railway up` from CLI

### DigitalOcean App Platform
- $12/month (Basic plan)
- Managed PostgreSQL add-on
- Auto-deploy from GitHub
- Good for teams

### VPS (Hetzner / DigitalOcean Droplet)
- Full control, $6-12/month
- Requires Docker setup
- Use `docker-compose.prod.yml`
- Manual HTTPS via Let's Encrypt

## Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `JWT_SECRET_KEY` | Secret for JWT signing (generate with `openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications |
| `OPENAI_API_KEY` | OpenAI API key for RAG embeddings |
| `OWNER_SETUP_KEY` | Key for initial owner account setup |

## Architecture Documents

All architecture is documented in `docs/`:
- `DATABASE_SCHEMA.sql` — 78 tables, 50 enums, indexes, triggers
- `API_CONTRACTS.md` — 203 API endpoints with schemas
- `BUSINESS_LOGIC.md` — 45 algorithms in pseudocode
- `FRONTEND_ARCHITECTURE.md` — Component tree, routing, state management
- `INFRASTRUCTURE.md` — Docker, nginx, security, deployment
- `IMPLEMENTATION_GUIDE.md` — Roadmap, status machine, gap analysis

## License

Proprietary — Moonjar PMS. All rights reserved.
