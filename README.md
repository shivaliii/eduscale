# EduScale — AI-Powered Learning Platform

> Adaptive educational platform with personalized learning, knowledge tracing, workload prediction, and predictive cloud autoscaling.

## Architecture

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19 · TypeScript · Vite 8 · Tailwind CSS v4 · Recharts · Lucide Icons |
| **Backend** | FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT Auth |
| **Database** | PostgreSQL 15 |
| **ML** | DKT (LSTM) · AKT (Transformer) · Heuristic fallback |
| **Cloud Research** | Workload simulation · Reactive & Predictive autoscaling · M/M/1 queueing model |
| **Deployment** | Docker Compose |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15 (or Docker)

### Option A: Docker (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

### Option B: Local development

**Backend:**
```bash
cd backend
cp ../.env.example .env          # edit DATABASE_URL if needed
pip install -r requirements.txt
python -m app.seed.seed_database  # seed demo data
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install                      # or pnpm install
npm run dev
```

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Teacher | `teacher@eduscale.demo` | `teacher123` |
| Student | `alex@eduscale.demo` | `student123` |
| Student | `priya@eduscale.demo` | `student123` |

All 8 demo students use password `student123`.

## Project Structure

```
EduScale/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (auth, students, teachers, experiments)
│   │   ├── models/          # SQLAlchemy ORM models (11 models, 22 DB tables)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (quiz, student, teacher, experiment)
│   │   └── seed/            # Database seeding with demo data
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios API client
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Student, Teacher, and Experiments pages
│   │   ├── store/           # Auth context
│   │   └── types/           # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── ml/
│   ├── models/            # DKT and AKT PyTorch implementations
│   ├── scripts/           # Preprocessing, training, evaluation, inference
│   ├── data/              # Datasets (gitignored)
│   └── checkpoints/       # Trained model weights (gitignored)
├── docker-compose.yml
└── .env.example
```

## Knowledge Tracing (ML)

### Models
- **DKT** — Deep Knowledge Tracing with LSTM backbone and learnable skill embeddings
- **AKT** — Attentive Knowledge Tracing with causal multi-head self-attention

### Training

```bash
# With synthetic data (no dataset download needed)
python -m ml.scripts.train --model dkt --generate-synthetic --epochs 20

# With ASSISTments dataset (download first — see ml/README.md)
python -m ml.scripts.preprocess_assistments
python -m ml.scripts.train --model dkt --epochs 50 --batch-size 64
```

### Evaluation

```bash
python -m ml.scripts.evaluate --model dkt --checkpoint ml/checkpoints/dkt_best.pt
```

### Integration
Set `DEMO_MODE=false` and `KT_MODEL_PATH=ml/checkpoints/dkt_best.pt` in `.env` to use
the trained model for mastery prediction instead of the heuristic fallback.

## Testing

```bash
# Backend tests (uses SQLite in-memory — no PostgreSQL required)
cd backend
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/auth/logout` | Logout |

### Student Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/students/me/dashboard` | Full dashboard data |
| GET | `/api/v1/students/me/mastery` | Topic mastery scores |
| GET | `/api/v1/students/me/quizzes` | Available quizzes |
| POST | `/api/v1/students/me/quizzes/{id}/start` | Start quiz attempt |
| POST | `/api/v1/students/me/attempts/{id}/respond` | Submit answer |
| POST | `/api/v1/students/me/attempts/{id}/submit` | Finish quiz |
| POST | `/api/v1/students/me/practice/generate` | Generate practice test |
| GET | `/api/v1/students/me/notes` | Educational notes |
| GET | `/api/v1/students/me/assignments` | Assignments |
| GET | `/api/v1/students/me/notifications` | Notifications |

### Teacher Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/teachers/me/dashboard` | Class analytics |
| GET | `/api/v1/teachers/me/classes` | Teacher's classes |
| GET | `/api/v1/teachers/students/{id}` | Student detail |
| POST | `/api/v1/teachers/assignments` | Create assignment |

### Cloud Experiments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/experiments/run` | Run simulation |
| GET | `/api/v1/experiments` | List experiments |
| GET | `/api/v1/experiments/{id}/metrics` | Time-series metrics |
| GET | `/api/v1/experiments/compare/{a}/{b}` | Compare experiments |
| GET | `/api/v1/experiments/{id}/export/csv` | Export CSV |
| GET | `/api/v1/experiments/{id}/export/json` | Export JSON |

## Cloud Research Features

### Workload Scenarios
- **Normal** — sinusoidal variation around base rate
- **Increasing** — linearly growing traffic
- **Burst** — normal traffic with sudden spikes
- **Deadline** — gradual increase then sharp peak (assessment deadline)
- **Low** — minimal traffic with occasional bumps
- **Mixed** — combination of all patterns

### Autoscaling Policies
- **Reactive** — scale based on observed CPU/memory thresholds
- **Predictive** — scale proactively using workload forecast with 30% safety margin

### Metrics Recorded
- Actual vs predicted request rate
- Inference latency (avg, p95, p99)
- CPU and memory utilization
- Active instances and scaling actions
- SLA violations
- Estimated cloud cost (EC2 t3.medium rates)
- Prediction accuracy (MAE, RMSE)

### Simulation Engine
The experiment service uses:
- M/M/1 queueing model for latency simulation
- Moving average + trend forecaster for workload prediction
- Per-step cost estimation using real EC2 hourly rates
- Configurable scaling cooldown, SLA thresholds, instance limits

All metrics are simulation-based and clearly labeled as such. No fabricated cloud deployment results.

## Educational Features

- **10 Python topics** with 50 MCQ questions
- **Adaptive quizzes** with instant answer evaluation
- **Topic mastery tracking** (heuristic: correct/attempted ratio)
- **Personalized recommendations** based on learning gaps
- **Important Notes** with structured content (definitions, examples, common mistakes)
- **Practice test generation** — prioritizes unseen questions
- **Teacher assignments** with automatic notifications
- **Student proficiency analytics** for teachers

## Environment Variables

See `.env.example` for all configuration options.

## License

Academic project — not for commercial use.

