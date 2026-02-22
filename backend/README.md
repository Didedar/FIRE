# FIRE Backend

**F**reedom **I**ntelligent **R**outing **E**ngine - Automated customer ticket processing and distribution system for Freedom Finance Bank.

## Features

- AI-powered ticket classification using Groq LLM (Llama 3.3 70B)
- Automatic geocoding with Nominatim OSM + Kazakhstan city fallback
- Intelligent routing to 15 offices across Kazakhstan
- Skill-based manager matching (VIP, KZ, ENG)
- Load-balanced round-robin assignment
- Real-time analytics and statistics

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Groq API Key (free at https://console.groq.com)

### 2. Setup

```bash
# Clone the repository
cd backend

# Copy environment template
cp .env.example .env

# Edit .env and add your GROQ_API_KEY
nano .env

# Start PostgreSQL
docker-compose up -d postgres

# Wait for database to be ready (check with docker logs fire-postgres)

# Install Python dependencies (for local development)
pip install -r requirements.txt

# Run the backend
uvicorn app.main:app --reload --port 8000
```

### 3. Process All Tickets

Once the backend is running, process all 200 tickets:

```bash
curl -X POST http://localhost:8000/api/v1/process-all
```

This will:
1. Load `business_units.csv` (15 offices)
2. Load `managers.csv` (51 managers)
3. Load `tickets.csv` (200 tickets)
4. Run AI analysis on each ticket
5. Geocode addresses and find nearest office
6. Assign tickets to appropriate managers

## API Endpoints

### Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/process-all` | Load CSVs and process all 200 tickets |
| POST | `/api/v1/process` | Process a single ticket by GUID |
| POST | `/api/v1/batch` | Upload and process tickets CSV |

### Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tickets` | List tickets with filters |
| GET | `/api/tickets/{id}` | Get single ticket details |
| GET | `/api/managers` | List all managers with workload |
| GET | `/api/managers/offices` | List all business units |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/stats` | Dashboard statistics |
| POST | `/api/ai-assistant` | Natural language analytics queries |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with DB connectivity |
| GET | `/` | Service info |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM |
| `DATABASE_URL` | No | `postgresql://...localhost:5433/fire_db` | PostgreSQL URL |
| `BATCH_SEMAPHORE_LIMIT` | No | `10` | Parallel processing limit |

## Pipeline

### 1. CSV Loading
- Uses `utf-8-sig` encoding (handles BOM)
- Strips trailing whitespace from column names
- Parses skills as comma-separated list

### 2. AI Analysis (Groq LLM)
Extracts from ticket description:
- `ticket_type`: Complaint, Data Change, Consultation, Claim, App Issue, Fraud, Spam
- `sentiment`: Positive, Neutral, Negative
- `priority`: 1-10
- `language`: KZ, ENG, RU
- `summary`: 1-2 sentences + recommendation

### 3. Geocoding
Cascade:
1. Nominatim OSM API
2. Kazakhstan city dictionary fallback
3. Foreign/unknown → 50/50 split between Astana and Almaty

### 4. Routing Rules
- VIP/Priority segment → requires VIP skill
- Data Change tickets → requires "Главный специалист" position
- KZ language → requires KZ skill
- ENG language → requires ENG skill

### 5. Assignment
- Filter managers by nearest office
- Apply skill filters
- Sort by workload (ascending)
- Pick top 2, assign round-robin

## Office Locations

All 15 offices with exact coordinates:

| Office | Coordinates |
|--------|-------------|
| Актау | 43.6355, 51.1680 |
| Актобе | 50.2839, 57.1670 |
| Алматы | 43.2380, 76.9458 |
| Астана | 51.1694, 71.4491 |
| Атырау | 47.1068, 51.9032 |
| Караганда | 49.8047, 73.1094 |
| Кокшетау | 53.2836, 69.3783 |
| Костанай | 53.2144, 63.6246 |
| Кызылорда | 44.8488, 65.5093 |
| Павлодар | 52.2873, 76.9674 |
| Петропавловск | 54.8720, 69.1414 |
| Тараз | 42.9000, 71.3667 |
| Уральск | 51.2333, 51.3667 |
| Усть-Каменогорск | 49.9482, 82.6279 |
| Шымкент | 42.3154, 69.5967 |

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 16 + SQLAlchemy
- **LLM**: Groq API (Llama 3.3 70B Versatile)
- **Geocoding**: Nominatim OSM
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic v2
- **Retries**: tenacity
