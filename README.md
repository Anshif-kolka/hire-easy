# Hiring AI Agent

An AI-powered hiring assistant that automates resume screening using Google Gemini API, FastAPI, and ChromaDB.

## Features

- **Job Description Analysis**: Extracts key requirements, skills, and context from job descriptions
- **Resume Parsing**: Processes PDF resumes (including LinkedIn exports) and extracts structured candidate data
- **AI-Powered Scoring**: Uses Gemini to evaluate candidates against job requirements
- **Semantic Search**: ChromaDB-powered similarity matching between candidates and jobs
- **Email Auto-Ingestion**: Polls inbox for emails with format "JOB - {title} - APPLICATION" and auto-processes attachments
- **RESTful API**: Full API for managing jobs, candidates, and rankings

## Tech Stack

- **Backend**: FastAPI with BackgroundTasks
- **LLM**: Google Gemini API
- **Vector Store**: ChromaDB (local)
- **Database**: SQLite
- **PDF Parsing**: PyPDF2
- **Email**: IMAP with APScheduler

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:

- `GEMINI_API_KEY`: Your Google Gemini API key
- `EMAIL_HOST`: IMAP server (e.g., imap.gmail.com)
- `EMAIL_USER`: Email address
- `EMAIL_PASSWORD`: Email password or app-specific password

### 4. Initialize Database

# Hiring AI Agent

An AI-powered hiring assistant that automates resume screening using Google Gemini API, FastAPI, and ChromaDB.

## Highlights

- Automates resume ingestion from uploads and email attachments.
- Persists original resumes for audit/compliance and provides a download endpoint.
- Performs semantic matching with a vector store and generates explainable candidate rankings.
- Caches numeric scores and LLM narratives to control token usage and cost.

## Features

- **Job Description Analysis**: Extracts key requirements, skills, and context from job descriptions
- **Resume Parsing**: Processes PDF resumes (including LinkedIn exports) and extracts structured candidate data
- **AI-Powered Scoring**: Uses Gemini to evaluate candidates against job requirements
- **Semantic Search**: ChromaDB-powered similarity matching between candidates and jobs
- **Email Auto-Ingestion**: Polls inbox for emails with format "JOB - {title} - APPLICATION" and auto-processes attachments
- **RESTful API**: Full API for managing jobs, candidates, and rankings
- **Persistent Score Caching**: Numeric scores and optional LLM narratives are stored in the DB (`score_reports`) so repeated views don't re-run LLMs
- **Background Precompute**: A background endpoint allows bulk precompute of rankings to avoid synchronous LLM runs on page load
- **Token-efficient LLM Usage**: Cache-first design, background precompute, and optional lazy LLM narratives minimize token consumption

## Tech Stack

- **Backend**: FastAPI with BackgroundTasks
- **LLM**: Google Gemini API
- **Vector Store**: ChromaDB (local)
- **Database**: SQLite
- **PDF Parsing**: PyPDF2
- **Email**: IMAP with APScheduler

> Note: this is a prototyping-sized implementation. For production scale, add a dedicated task queue, encrypted file storage, and monitoring for LLM jobs.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:

- `GEMINI_API_KEY`: Your Google Gemini API key
- `EMAIL_HOST`: IMAP server (e.g., imap.gmail.com)
- `EMAIL_USER`: Email address
- `EMAIL_PASSWORD`: Email password or app-specific password

### 4. Initialize Database

The database is auto-initialized on first run.

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

## Architecture & Components

### Data storage
- SQLite DB (`data/hiring_agent.db`) — canonical candidate and score data (`score_reports`).
- Disk storage under `data/resumes/` — original PDFs are persisted and downloadable via API.
- ChromaDB local persistence (`data/chroma_db`) — stores embeddings for semantic searches.

### Agents (what we built)
- **Resume Ingest Agent** — saves PDFs, extracts text and structured candidate fields.
- **Email Ingest Agent** — polls IMAP and processes application attachments automatically.
- **Embedding Agent (ChromaStore)** — creates and retrieves embeddings for jobs and candidates.
- **Ranking Agent** — computes numeric scores and generates LLM-based narratives (strengths, weaknesses, reasoning, recommendation).

### Workflows
- **Resume Ingestion Workflow** — saves files, parses, and creates candidate records; writes embeddings.
- **Assessment Workflow** — cache-first candidate assessment: returns DB report if present, otherwise computes scores and stores them.
- **Ranking Workflow** — finds relevant candidates (direct applicants + vector-similar), runs assessments for each (cached), sorts, and generates a top-candidates summary.

## Caching & Token-saving Strategies (why this matters)

- Score reports (`score_reports` table) store both numerical metrics and optional LLM fields. The pipeline checks the DB first and returns cached results unless `force_refresh` is requested.
- Background precompute: `POST /ranking/{job_id}/refresh` schedules a full ranking pass to precompute and store score reports (non-blocking). Useful after bulk uploads to prevent synchronous LLM runs on page load.
- Prevent duplicate reports: insertion logic removes any existing candidate+job score report before storing the new one — this keeps a single canonical report per candidate-job pair.
- Optional lazy narratives (recommended next step): compute numeric scores for all candidates, then run LLM narratives only for top-K candidates or when the user expands a candidate card. This dramatically cuts token usage.

## API Endpoints (key ones)

Base URL: `http://localhost:8000`

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/job/create` | Create a job from description |
| GET | `/job/` | List jobs |
| GET | `/job/{job_id}` | Get job details |
| DELETE | `/job/{job_id}` | Delete a job (DB row) |

### Resumes / Candidates

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/resume/upload` | Upload resume PDF (multipart form, pass `job_id` as a param) |
| POST | `/resume/email-ingest` | Trigger IMAP email ingestion (scan inbox and process attachments) |
| GET | `/resume/{candidate_id}` | Get candidate details |
| GET | `/resume/{candidate_id}/download` | Download original PDF resume (served from `data/resumes`) |
| DELETE | `/resume/{candidate_id}` | Delete candidate row, associated score reports, vector embeddings and file on disk |
| GET | `/resume/` | List resumes (optionally `?job_id=`)

### Ranking & Assessment

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ranking/{job_id}` | Get ranking report for a job (returns cached `score_reports` if present) |
| POST | `/ranking/{job_id}/refresh` | Trigger background precompute of rankings for a job (non-blocking) |
| GET | `/ranking/{job_id}/{candidate_id}` | Get or compute assessment for a single candidate (cache-first) |
| POST | `/ranking/assess` | Programmatic assess endpoint (accepts candidate_id, job_id, force_refresh) |
| GET | `/ranking/{job_id}/top/{limit}` | Get top N candidates for a job |

### Admin / Job-specific deletes

| Method | Endpoint | Description |
|--------|----------|-------------|
| DELETE | `/job/{job_id}` | Delete job row (vector store deletion should be done by caller) |
| DELETE | `/job/{job_id}/candidates` | Delete all candidates and their reports for a job (also removes files if present) |

## Usage Examples

### 1. Create a Job

```bash
curl -X POST http://localhost:8000/job/create \
  -H "Content-Type: application/json" \
  -d '{"description": "We are looking for a Senior Python Developer..."}'
```

### 2. Upload Resume

```bash
curl -X POST "http://localhost:8000/resume/upload?job_id={job_id}" \
  -F "file=@resume.pdf"
```

### 3. Get Rankings

```bash
curl http://localhost:8000/ranking/{job_id}
```

### 4. Precompute Rankings (recommended for large applicant sets)

```bash
# Trigger background precompute (non-blocking)
curl -X POST http://localhost:8000/ranking/{job_id}/refresh

# Then fetch cached results
curl http://localhost:8000/ranking/{job_id}
```

## Project Structure

```
app/
├── agents/           # AI agents
│   ├── jd_context_agent.py
│   ├── resume_analysis_agent.py
│   ├── ranking_agent.py
│   └── email_ingest_agent.py
├── api/              # FastAPI routes
│   ├── routes_job.py
│   ├── routes_resume.py
│   └── routes_ranking.py
├── database/         # SQLite storage
│   ├── store.py
│   └── schemas.sql
├── models/           # Pydantic models
│   ├── job_context.py
│   ├── candidate.py
│   └── score_report.py
├── services/         # Core services
│   ├── gemini_llm.py
│   ├── chroma_db.py
│   ├── pdf_parser.py
│   ├── resume_extractor.py
│   └── scoring_utils.py
├── utils/            # Utilities
│   ├── logger.py
│   ├── text_cleaner.py
│   └── error_handler.py
├── workflows/        # Processing pipelines
│   ├── job_context_workflow.py
│   ├── resume_ingestion_workflow.py
│   ├── assessment_workflow.py
│   └── ranking_workflow.py
├── config.py
├── dependencies.py
└── main.py
prompts/              # LLM prompt templates
tests/                # Unit tests
```

## Design notes & tradeoffs

- BackgroundTasks is used for convenience; for heavy production workloads use a task queue (RQ, Celery) and a worker pool for reliability and monitoring.
- Score reports currently store LLM output; add `model_version`, `scored_at`, and `llm_generated` fields to support deterministic invalidation when job or resume data changes.
- Resumes are stored as files — consider encrypting on disk or adding stricter RBAC for sensitive production deployments.

## Next steps (recommended)

- Implement lazy LLM narratives: compute numeric scores for all candidates, then generate LLM narratives only for a top-K subset or on-demand when users open candidate details.
- Add `scored_at`/`model_version` metadata to `score_reports` and invalidate when the job description or candidate resume changes.
- Integrate a background worker (Redis + RQ or Celery) for resilient, observable processing.
- Add unit and integration tests for deletion, ingestion, scoring and ranking flows.

## License

MIT

---

If you'd like, I can also:
- Add a troubleshooting section (common errors & fixes).
- Produce a Notebooks LM prompt to render the short video from the LinkedIn script.
- Implement lazy narratives and metadata invalidation next.
