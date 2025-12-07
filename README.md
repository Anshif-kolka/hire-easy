Hiring AI Agent

An AI-powered hiring assistant that automates resume screening using Google Gemini API, FastAPI, and ChromaDB.
Features

    Job Description Analysis: Extracts key requirements, skills, and context from job descriptions
    Resume Parsing: Processes PDF resumes (including LinkedIn exports) and extracts structured candidate data
    AI-Powered Scoring: Uses Gemini to evaluate candidates against job requirements
    Semantic Search: ChromaDB-powered similarity matching between candidates and jobs
    Email Auto-Ingestion: Polls inbox for emails with format "JOB - {title} - APPLICATION" and auto-processes attachments
    RESTful API: Full API for managing jobs, candidates, and rankings

Tech Stack

    Backend: FastAPI with BackgroundTasks
    LLM: Google Gemini API
    Vector Store: ChromaDB (local)
    Database: SQLite
    PDF Parsing: PyPDF2
    Email: IMAP with APScheduler

P.S the frontend is vibe coded, so if you intend to use the front end for production proceed with caution or else a non vibe-coded one will be released soon.
