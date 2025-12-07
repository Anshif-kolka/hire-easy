# Testing Guide - Hiring AI Agent

## ✅ Server Status

Your server is running at `http://localhost:8000`

**Interactive API Docs**: http://localhost:8000/docs

---

## 🧪 Testing the API

### 1. **Create a Job** (Test JD Extraction)

**Endpoint**: `POST /api/jobs/`

**Request**:
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "description": "We are looking for a Senior Python Developer with 5+ years of experience. Required skills: Python, FastAPI, PostgreSQL. Nice to have: Docker, Kubernetes. Responsibilities: design APIs, mentor junior developers, code reviews."
  }'
```

**Response**:
```json
{
  "job_id": "job_12345",
  "title": "Senior Python Developer",
  "company": "Your Company",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "preferred_skills": ["Docker", "Kubernetes"],
  "experience_years": 5,
  "status": "created"
}
```

---

### 2. **Upload a Resume** (Test Resume Parsing)

**Endpoint**: `POST /api/resumes/upload/{job_id}`

First, create a simple PDF resume or use an existing one.

**Request**:
```bash
curl -X POST http://localhost:8000/api/resumes/upload/job_12345 \
  -F "file=@your_resume.pdf"
```

**Response**:
```json
{
  "candidate_id": "cand_67890",
  "name": "John Doe",
  "email": "john@example.com",
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "experience": [...],
  "status": "ingested"
}
```

---

### 3. **Get Candidates for a Job**

**Endpoint**: `GET /api/resumes/job/{job_id}`

```bash
curl http://localhost:8000/api/resumes/job/job_12345
```

---

### 4. **Rank Candidates**

**Endpoint**: `POST /api/ranking/{job_id}/rank`

```bash
curl -X POST http://localhost:8000/api/ranking/job_12345/rank
```

**Response**:
```json
{
  "job_id": "job_12345",
  "total_candidates": 3,
  "rankings": [
    {
      "rank": 1,
      "candidate_id": "cand_67890",
      "name": "John Doe",
      "overall_score": 92.5,
      "skills_match_score": 95,
      "experience_score": 90,
      "recommendation": "Highly Recommended"
    },
    ...
  ]
}
```

---

### 5. **Get Ranking Results**

**Endpoint**: `GET /api/ranking/{job_id}/results`

```bash
curl http://localhost:8000/api/ranking/job_12345/results
```

---

## 📧 Email Auto-Ingestion Testing

### How to Test Email Polling

1. **Send yourself an email** with:
   - **Subject**: `JOB - Python Backend Engineer - APPLICATION`
   - **Attachment**: Your resume PDF

2. **Server automatically**:
   - Polls every 5 minutes
   - Detects the email
   - Downloads the PDF
   - Extracts resume data
   - Creates candidate record
   - Stores in database & vector store

3. **Check results**:
   ```bash
   curl http://localhost:8000/api/resumes/job/job_12345
   ```

---

## 🔍 What to Look For

✅ **Success Indicators**:
- Server logs show: `Starting Hiring AI Agent...`
- Email polling shows: `Email polling enabled (every 5 minutes)`
- API responds at `/docs`
- Jobs are created with extracted data
- Resumes are parsed correctly
- Rankings are generated with scores

❌ **Common Issues**:
- Missing `GEMINI_API_KEY` in `.env` → Check API key validity
- Email not detected → Check subject format: `JOB - TITLE - APPLICATION`
- Resume parsing fails → Check if PDF is text-based (not scanned image)
- Permission errors → Check file permissions

---

## 📊 Database Check

Check if data is being stored:

```bash
# List all jobs
curl http://localhost:8000/api/jobs/

# List all candidates for a job
curl http://localhost:8000/api/resumes/job/job_12345

# Get candidate details
curl http://localhost:8000/api/resumes/cand_67890
```

---

## 🛠️ Debugging

### Check Server Logs

Watch the terminal running the server for:
- Database operations
- Email polling events
- API requests
- Errors

### Logs Location

If logging is configured:
- `logs/hiring_agent.log`

### Environment Variables

Verify all settings:

```bash
# Check which environment file is loaded
grep -E "GEMINI_API_KEY|EMAIL_ADDRESS" .env
```

---

## 📝 Test Workflow

**Complete test flow**:

1. ✅ Create a job with detailed description
2. ✅ Upload a PDF resume
3. ✅ Check candidates are listed
4. ✅ Rank all candidates
5. ✅ View ranking results
6. ✅ (Optional) Send email with attachment
7. ✅ Wait 5 min for email polling
8. ✅ Check new candidate was auto-ingested

---

## 🚀 Next Steps

- Integrate into your workflow
- Monitor email polling in logs
- Adjust weights in `.env` if needed
- Customize prompts in `prompts/` folder
- Add more test resumes
