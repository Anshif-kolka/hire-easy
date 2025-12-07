📘 HIRING AI AGENT – PROJECT ARCHITECTURE DOCUMENTATION

hiring-ai-agent/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   │
│   ├── agents/
│   │   ├── jd_context_agent.py
│   │   ├── resume_analysis_agent.py
│   │   ├── ranking_agent.py
│   │   ├── browser_agent.py
│   │   └── email_ingest_agent.py
│   │
│   ├── workflows/
│   │   ├── job_context_workflow.py
│   │   ├── resume_ingestion_workflow.py
│   │   ├── assessment_workflow.py
│   │   └── ranking_workflow.py
│   │
│   ├── services/
│   │   ├── gemini_llm.py
│   │   ├── chroma_db.py
│   │   ├── pdf_parser.py
│   │   ├── resume_extractor.py
│   │   ├── safe_link_checker.py
│   │   └── scoring_utils.py
│   │
│   ├── models/
│   │   ├── job_context.py
│   │   ├── candidate.py
│   │   └── score_report.py
│   │
│   ├── database/
│   │   ├── store.py
│   │   └── schemas.sql
│   │
│   ├── utils/
│   │   ├── text_cleaner.py
│   │   ├── logger.py
│   │   └── error_handler.py
│   │
│   └── api/
│       ├── routes_job.py
│       ├── routes_resume.py
│       └── routes_ranking.py
│
├── tests/
│   ├── test_agents.py
│   ├── test_db.py
│   └── test_api.py
│
├── prompts/
│   ├── jd_context.txt
│   ├── resume_analysis.txt
│   ├── ranking.txt
│   └── safety_browser.txt
│
├── requirements.txt
├── README.md
└── .env


#️⃣ 2. DIRECTORY-WISE EXPLANATION

📂 agents/ — All Autonomous Agents

jd_context_agent.py → 
Purpose:

Extract job role context from a conversation between the hiring manager and the system.

When triggered:

When a hiring manager submits job details (chat, form, text).

Main responsibilities:

Understand the job description or hiring manager messages

Extract structured data (role, experience, must-have skills, nice-to-have skills, soft skills, domain)

Clean noisy descriptions

Generate a final JobContext model
class JDContextAgent:
    def __init__(self, llm):
        self.llm = llm

    def extract_job_context(self, raw_text: str) -> JobContext:
        """
        Calls LLM to convert messy JD text into structured fields.
        """
LLM duties:

Break down messy JD text

Normalize skill names

Infer missing details (e.g., domain, seniority level)

Write a summary of the job

Tag key skills by category
Typical output:
{
  "role": "AI Engineer",
  "experience_required": 3,
  "mandatory_skills": ["Python", "FastAPI", "LLMs", "LangChain"],
  "optional_skills": ["Docker", "RAG systems"],
  "domain": "Generative AI",
  "job_summary": "Looking for an engineer to build LLM-driven workflows..."
}


resume_analysis_agent.py → Parses resume, extracts structured candidate information
Purpose:

Convert a candidate’s resume into structured machine-readable data.

Triggered when:

A resume (PDF/text/image) is uploaded.

pdf_parser.py extracts raw text.

Main responsibilities:

Clean raw text

Extract:

name

contact info

experience years

projects

skills

work history

education

Infer missing values with LLM reasoning

Produce a Candidate model object
class ResumeAnalysisAgent:
    def __init__(self, llm):
        self.llm = llm

    def parse_resume(self, raw_resume_text: str) -> Candidate:
        """
        Extract structured candidate data using the LLM.
        """
LLM duties:

Identify key sections even if resume layout is inconsistent

Normalize skill names

Extract project descriptions

Provide clean summaries (technical + non-technical)
output: {
  "name": "Rahul Nair",
  "email": "rahul@example.com",
  "skills": ["Python", "Docker", "LangChain"],
  "experience_years": 2.5,
  "projects": ["RAG-based FAQ bot", "Image classifier"],
  "education": "B.Tech CSE"
}


ranking_agent.py → Computes match score + strengths/weaknesses
Purpose:

Evaluate each candidate based on job context + resume and generate:

🔹 Match score
🔹 Pros & Cons (written by LLM)
🔹 Skill mismatch reasoning
🔹 Final shortlisting recommendation

Triggered when:

Multiple candidates are processed

JD context is already known

Main responsibilities:

Compare candidate skills ↔ job skills

Compute structured scores:

skill match

experience match

domain match

Ask LLM to:

Generate natural language pros & cons

Create a final ranking score

Give reasoning

Core methods inside:
class RankingAgent:
    def __init__(self, llm):
        self.llm = llm

    def generate_candidate_rank(self, candidate: Candidate, job: JobContext) -> ScoreReport:
        """
        Combines heuristic scoring + LLM reasoning to generate ranking output.
        """
LLM duties:

Explain strengths & weaknesses

Identify gaps

Produce a final score and explanation

Compare multiple candidates if needed

Typical output:
{
  "candidate_name": "Rahul Nair",
  "score": 82,
  "pros": ["Strong Python background", "Hands-on LLM integrations"],
  "cons": ["Limited system design experience"],
  "reasoning": "Overall strong match for an AI engineer role..."
}

browser_agent.py → Visits GitHub/LinkedIn safely
Purpose:

Safely visit GitHub/LinkedIn and extract relevant publicly available data.

Triggered when:

Candidate provides GitHub/LinkedIn URLs

Your workflow needs additional signals

Main responsibilities:

Use safe_link_checker.py to avoid unsafe URLs

Scrape (lightweight):

GitHub contribution score

Number of repos

Main languages

LinkedIn bio summary

Pass cleaned text to LLM for:

Summaries

Code quality remarks

Repo expertise categorization

Core methods inside:
class BrowserAgent:
    def __init__(self, llm, browser):
        self.llm = llm
        self.browser = browser

    def scan_profile(self, url: str) -> dict:
        """
        Scrape + analyze GitHub/LinkedIn.
        """
LLM duties:

Summarize GitHub profile

Extract candidate signals (AI experience, writing quality, recency of contributions)

email_ingest_agent.py → Reads resumes from email inbox

Purpose:

Automatically fetch resumes from a monitored email inbox.

Triggered when:

HR forwards resumes to a specific email ID

Cron job or manual API call triggers ingestion

Main responsibilities:

Connect to IMAP inbox

Parse attachments

Extract PDF resumes

Store metadata in DB

Pass raw PDFs → pdf_parser.py → LLM for analysis

Avoid duplicates

Core methods inside:
class EmailIngestAgent:
    def __init__(self, email_client, parser):
        self.email_client = email_client
        self.parser = parser

    def fetch_and_process_resumes(self):
        """
        Fetch unread emails, extract resumes, parse them.
        """
LLM duties:

None directly
LLM is used downstream in the resume analysis agent.
📂 workflows/ — Multi-step orchestrated processes

job_context_workflow.py → JD ingestion → extract → embed → store
Purpose

Convert a messy job description (JD) or hiring-manager conversation into:

A structured JobContext model

Embeddings

Stored job profile in vector DB + normal DB

Used Agents / Services

JDContextAgent

chroma_db.py (embedding + upsert)

gemini_llm.py (LLM for extraction)

Workflow Steps

Receive raw JD text or chat transcript

Call JDContextAgent.extract_job_context()

Generate embeddings of:

Mandatory skills

Optional skills

Job summary

Store:

Structured job context in DB

Embeddings in Chroma/Pinecone

Return a clean JobContext object + job_id

Outpu:
{
  "job_id": "JOB-2024-001",
  "role": "AI Engineer",
  "mandatory_skills": ["Python", "LLMs", "FastAPI"],
  "optional_skills": ["RAG", "Docker"],
  "summary": "We are hiring an engineer who can build AI workflows..."
}


resume_ingestion_workflow.py → Parse → embed → store

Purpose

Process incoming resumes (PDF/text), convert them into structured candidate profiles, embed them, and store them.

Used Agents / Services

EmailIngestAgent (optional)

ResumeAnalysisAgent

pdf_parser.py

resume_extractor.py

chroma_db.py

Workflow Steps

Fetch resumes:

from email inbox (IMAP)

OR from API upload

Extract text from PDF → pdf_parser.py

Pass text to ResumeAnalysisAgent → Candidate model

Embed candidate skills, experience, summary

Store:

candidate profile in DB

embeddings in vector DB

Return Candidate model

Output:
{
  "candidate_id": "CAND-552",
  "name": "Rahul Nair",
  "skills": ["Python", "LangChain"],
  "experience": 2.5,
  "projects": ["LLM chatbot", "RAG system"],
  "vector_id": "vec_11224"
}


assessment_workflow.py → Compare resume vs JD → scoring
Purpose

Compare one candidate vs one job role using:

Skill match

Experience match

LLM reasoning (gap analysis)

Generate a raw score (pre-ranking)

Used Agents / Services

RankingAgent (scoring logic + LLM-based pros/cons)

scoring_utils.py

Workflow Steps

Load job context by job_id

Load candidate data by candidate_id

Compute:

skill overlap

experience gap

domain similarity

Ask RankingAgent to generate:

overall score

pros

cons

reasoning

Output:

{
  "candidate_id": "CAND-552",
  "job_id": "JOB-2024-001",
  "score": 82,
  "pros": ["Strong Python skills", "LLM project experience"],
  "cons": ["Limited cloud exposure"],
  "reasoning": "Good match for backend AI development..."
}

ranking_workflow.py → Full ranking pipeline
Purpose

Generate final ranking for all candidates for a job.
This is the full end-to-end ranking system over multiple profiles.

Used Agents / Services

RankingAgent

Vector DB (semantic candidate search)

Normal DB (candidate/job lookup)

Workflow Steps

Load job context

Query vector DB for top-K relevant candidates

For each candidate:

Run assessment_workflow logic

Sort candidates by score

Generate LLM-based:

final ranking summary

best candidates

role fit explanation

Return final ranking report

Output:
{
  "job_id": "JOB-2024-001",
  "ranking": [
    {
      "candidate_id": "C1",
      "score": 91,
      "pros": [...],
      "cons": [...]
    },
    {
      "candidate_id": "C2",
      "score": 78
    }
  ],
  "final_summary": "Top candidate is best fit due to strong ML experience..."
}

📂 services/ — Shared reusable logic

gemini_llm.py → Unified LLM wrapper
Purpose

Central wrapper around Gemini API (or any LLM) so the rest of the project never interacts with raw API calls directly.

What it should contain

Class: GeminiLLM

Methods:

generate_text(prompt, temperature, ...)

generate_structured(output_schema, prompt)

embed_text(text)

Automatic:

retry logic

rate limit handling

input token trimming

error normalisation

Why?

All agents use LLMs → but we don’t want duplicated messy API calls in every agent.
One clean interface.
chroma_db.py → Vector store operations
Purpose

Wrapper around ChromaDB to store and retrieve embeddings.

What it should contain

Class: ChromaStore

Methods:

add_embeddings(collection_name, ids, embeddings, metadata)

query_similar(collection_name, embedding, top_k)

delete(collection_name, ids)

create_or_load(collection_name)

Used by

JD ingestion workflow

Resume ingestion workflow

Ranking workflow

Why?

Agents must not write DB code.
All vector DB operations remain centralized.

pdf_parser.py → Extract raw text + metadata from resumes
Purpose

Takes any uploaded PDF (resume, LinkedIn profile, portfolio PDF) and extracts text.

What it should contain

Function: extract_text_from_pdf(file_path)

Optional:

page-wise extraction

image-based OCR fallback via Tesseract (if needed)

PDF metadata extraction

Additionally

Detect:

LinkedIn-style PDFs

Resume PDFs

Scanned documents

Output example:
{
  "raw_text": "...",
  "pages": ["page1 text", "page2 text"],
  "metadata": {...}
}


resume_extractor.py → Clean + structure resume text
Purpose

Uses LLM + heuristics to convert raw resume text into structured JSON.

What it should contain

Class: ResumeExtractor

Methods:

clean_text(raw_text)

parse_with_llm(raw_text) → calls GeminiLLM.generate_structured()

detect_sections(raw_text)

extract_skills(raw_text) (regex + LLM)

extract_experience(raw_text)

extract_education(raw_text)

safe_link_checker.py → Block dangerous URLs before opening
Purpose

Before the browser agent visits GitHub or portfolio websites,
this service ensures the URL is:

safe

not phishing

not a malware domain

not performing downloads

not LinkedIn (blocked)

What it should contain

Function: is_safe(url: str) -> bool

Checks:

Allowed domain list (github.com, gitlab.com, personal domains)

Blocked domain list (LinkedIn, login pages, shortened links)

Detect suspicious patterns:

exe, zip, rar, auto-download links

javascript injection

known phishing lookups.
scoring_utils.py → Match scoring, weights, similarity functions
Purpose

Compute candidate scores based on similarity, skill match, seniority match, and experience relevance.

What it should contain

Functions:

semantic_similarity(a, b) using embeddings

calculate_skill_match(resume_skills, jd_skills)

experience_alignment(resume_exp, jd_exp)

weight_based_score(similarity, skill_match, experience_match)

final_score(resume_structured, jd_structured, embeddings_store)

Optional

Reusable scoring weights:
WEIGHTS = {
    "semantic_similarity": 0.5,
    "skills": 0.3,
    "experience": 0.2
}
Output
{
  "score": 84.5,
  "skill_match": 78,
  "experience_match": 90,
  "summary": "Strong fit, lacks AWS but good overall."
}

📂 models/ — Pydantic data models

job_context.py → JD structure
Purpose

Stores the cleaned, structured representation of a job role extracted by the JD Context Agent.

What it should contain

A Pydantic model like:
from pydantic import BaseModel
from typing import List, Optional

class JobContext(BaseModel):
    job_title: str
    seniority: str
    required_skills: List[str]
    preferred_skills: List[str]
    responsibilities: List[str]
    experience_required: Optional[str]
    domain: Optional[str]
    embedding_vector: Optional[List[float]]  # stored after embedding
Usage

For storing JD embeddings in Chroma

For comparing with resumes

For ranking candidates

candidate.py → Candidate profile
Purpose

Stores all extracted resume information after parsing + cleaning.

It contains:
from pydantic import BaseModel
from typing import List, Optional

class Candidate(BaseModel):
    id: str
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    headline: Optional[str]

    skills: List[str]
    experience: List[str]   # raw or structured
    education: List[str]
    projects: List[str]

    github_url: Optional[str]
    portfolio_url: Optional[str]
    linkedin_pdf: bool = False  # if resume came from LinkedIn export

    embedding_vector: Optional[List[float]]
Used by

Resume Analysis Agent

Assessment Workflow

Scoring Utilities

Ranking Agent

score_report.py → Ranking results
Purpose

Represents the final evaluation of a candidate after scoring & ranking.

It contains
from pydantic import BaseModel
from typing import List, Optional

class ScoreReport(BaseModel):
    candidate_id: str
    score: float
    skill_match: float
    experience_match: float
    semantic_similarity: float

    strengths: List[str]
    weaknesses: List[str]

    summary: str
Used by

Ranking Agent

Ranking Workflow

API Response (for frontend dashboards)
📂 api/ — FastAPI Routes

routes_job.py → Create job context
Endpoints
POST /job/create

Input: Raw JD text OR hiring manager conversation transcript

Process:

Calls JD Context Workflow

Extracts structured JD

Embeds it

Stores in vector DB

Output: JobContext object

GET /job/{job_id}

Returns job context metadata (skills, responsibilities, etc.)

routes_resume.py → Upload + parse resume
Endpoints
POST /resume/upload

Input: PDF file

Process:

Extract text (pdf_parser)

Clean & structure (resume_extractor)

Generate embeddings

Store in Chroma

Output: Candidate model response

POST /resume/email-ingest

Input: Email metadata (links, attachments)

Processed by: email_ingest_agent

GET /resume/{candidate_id}

Returns parsed candidate profile.

routes_ranking.py → Get ranked list
GET /ranking/{job_id}

Returns a ranked list of candidates for the job:

Process:

Load JD embeddings

Load candidate embeddings

Run assessment workflow

For each candidate:

compute score

compute strengths/weaknesses

generate summary

Ranking workflow sorts and returns

Output: List of ScoreReport

GET /ranking/{job_id}/{candidate_id}

Returns the individual score report of a candidate.

#️⃣ 3. UML SYSTEM ARCHITECTURE DIAGRAM

+---------------------+
|       API Layer     |
| (FastAPI Endpoints) |
+---------+-----------+
          |
          v
+-----------------------------+
|         Workflows           |
|  (JD, Resume, Ranking)     |
+-------+------+--------------+
        |      |
   uses |      | orchestrates
        v      v
+---------------+   +-----------------+
|    Agents     |   |    Services     |
| (LLM-based)   |   | (Parsing, DB,   |
|               |   |  Scoring, etc)  |
+------+--------+   +--------+--------+
       |                     |
       | calls               | interacts
       v                     v
+-----------------+    +---------------+
| Gemini LLM API  |    | Vector Store  |
+-----------------+    |  (Chroma)     |
                       +---------------+
#️⃣ 4. DATA FLOW DIAGRAM

Hiring Manager → JD Context Agent → Job Context Workflow
                       |
                       v
           Embeddings Stored in Vector DB
                       |
       Candidate Email Received → Email Agent
                       |
                       v
Resume PDF → PDF Parser → Resume Agent → Resume Workflow
                       |
                      (Embed + Store)
                       |
                       v
              Ranking Workflow
       (JD Embeddings + Resume Embeddings)
                       |
                       v
         Final Ranked Candidate List (API)
#️⃣ 5. END-TO-END REQUEST → WORKFLOW → RESPONSE FLOW
A. Job Context Creation Flow
POST /job/create
        │
        ▼
JD Context Agent
        │
Parse → Extract → Summarize skills
        │
        ▼
Job Context Workflow
        │
Store embeddings in Chroma
        │
        ▼
Response → {job_id, structured_context}


B. Resume Ingestion Flow
POST /resume/upload
        │
        ▼
PDF parser → Raw text
        │
        ▼
Resume Analysis Agent
        │
Extract skills, experience, projects
        │
        ▼
Resume Ingestion Workflow
        │
Store embeddings
        │
        ▼
Response → {resume_id, parsed_profile}

C. Ranking Flow
GET /ranking?job_id=123
        │
        ▼
Ranking Workflow
        │
Fetch JD context + candidates embeddings
        │
Compute similarity + scoring weights
        │
Use Ranking Agent for final evaluation
        │
        ▼
Return sorted list:
[
 {candidate: X, score: 92, strengths: [], weaknesses: []},
 {candidate: Y, score: 85, ...}
]

#️⃣ 6. AGENT INTERACTION FLOW
 JD Context Agent
        |
        v
 Resume Analysis Agent
        |
        v
 Ranking Agent <---- Browser Agent checks GitHub/LinkedIn

#️⃣ 7. EMBEDDING + RANKING ARCHITECTURE
+------------------------+
| Job Context Embedding  |
+------------------------+

+------------------------+        +-----------------------+
| Resume Embeddings      | -----> | Similarity Matching   |
+------------------------+        +-----------------------+
                                          |
                                          v
                                Weighted Scoring + LLM
                                          |
                                          v
                                 Final Ranking Output

#️⃣ 8. EMAIL → RESUME → RANKING FLOW
Email → Email Agent
           |
           v
Extract PDF → Resume Workflow → Store → Rank → Output

#️⃣ 9. FRONTEND ARCHITECTURE

The frontend is a React-based Single Page Application (SPA) built with Vite and styled with Tailwind CSS. It communicates with the FastAPI backend via REST API.

## Tech Stack
- **Framework**: React 19 (Vite)
- **Styling**: Tailwind CSS v4 (Corporate Slate/Sky palette)
- **Icons**: Lucide React (No emojis)
- **Routing**: React Router DOM v7
- **HTTP Client**: Axios

## Directory Structure
frontend/
├── src/
│   ├── api/
│   │   └── client.js       # Centralized API calls
│   ├── components/
│   │   ├── Layout.jsx      # Sidebar + Main Content wrapper
│   │   └── JobForm.jsx     # Job creation form
│   ├── pages/
│   │   ├── Dashboard.jsx   # Stats + Email Trigger
│   │   ├── Jobs.jsx        # Job listing
│   │   ├── Candidates.jsx  # Candidate listing + Ranking
│   │   └── Compare.jsx     # Side-by-side candidate comparison
│   ├── App.jsx             # Routing configuration
│   ├── main.jsx            # Entry point
│   └── index.css           # Tailwind directives + Custom utilities

## Key Features
1. **Dashboard**: Overview of system stats and manual email ingestion trigger.
2. **Job Management**: Create and view job descriptions.
3. **Candidate Management**: View parsed candidates, filter by job.
4. **Ranking System**: Trigger AI ranking for candidates against a specific job.
5. **Comparison**: Select two candidates to compare their skills, experience, and education side-by-side.

## Design Philosophy
- **Minimalistic Corporate**: Clean lines, professional typography, neutral colors (Slate/Gray) with blue accents (Sky).
- **No Emojis**: Professional iconography using Lucide React.
- **Responsive**: Adapts to different screen sizes (though primarily desktop-focused for admin use).
