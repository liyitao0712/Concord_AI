# Concord AI

AI-powered business automation platform.

## Quick Start

### 1. Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your settings (API keys, etc.)
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Check services are running
docker-compose ps
```

### 3. Install Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Application

```bash
# From backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Project Structure

```
concord-ai/
├── docker-compose.yml      # Infrastructure
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI entry
│   │   ├── api/            # API routes
│   │   ├── core/           # Config, DB, Redis
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── agents/         # AI agents
│   └── alembic/            # Database migrations
└── tests/
```
