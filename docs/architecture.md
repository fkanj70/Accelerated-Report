# Architecture - Accelerated Report App

## Overview

The Accelerated Report is a lightweight in-app reporting system designed to make submitting feedback fast and reliable. The main goal is to make sure reports are never lost, even when the network is unstable or the backend is under stress.

The system is built around Sentry, which is used to monitor the full reporting flow as a critical user experience rather than just logging errors.

## System Architecture
At a high level, the system has three parts:

a frontend that simulates in-app reporting

a Python backend that receives and stores reports

observability and enrichment services that help developers understand what went wrong

```
┌─────────────────────────────────────────────────────────────┐
│                         USER LAYER                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Demo Web Page (simulates in-app reporting)          │  │
│  │  • Report Form (1 dropdown + 1 text field)           │  │
│  │  • Offline Queue (localStorage)                      │  │
│  │  • Auto-Retry Logic                                  │  │
│  │  • Chaos Mode Toggle                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP POST /reports
                            │ (JSON)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND LAYER                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (Python)                             │  │
│  │                                                       │  │
│  │  Critical Experience: report.submit                  │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │  Transaction: critical.report_submit        │    │  │
│  │  │  ├─ Span: validate_input                    │    │  │
│  │  │  ├─ Span: store_report_db                   │    │  │
│  │  │  └─ Span: ai_enrich (future)                │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  Metrics:                                            │  │
│  │  • reports.submitted (counter)                       │  │
│  │  • reports.failed (counter)                          │  │
│  │  • report.submit.latency_ms (distribution)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ Store             │ Enrich             │ Monitor
         ▼                    ▼                    ▼
┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│   SQLite    │    │   AI Services    │    │    Sentry    │
│             │    │                  │    │              │
│  • reports  │    │  • Gemini API    │    │  • Errors    │
│  • metadata │    │  • Yellowcake    │    │  • Traces    │
│             │    │  • Enrichment    │    │  • Metrics   │
└─────────────┘    └──────────────────┘    │  • Logs      │
                                            │  • Seer      │
                                            └──────────────┘
```

## Data Flow

### 1. Normal Report Submission

```
User submits report
    ↓
Frontend validates input
    ↓
POST /reports (with report data)
    ↓
Backend receives request
    ↓
Sentry transaction starts: critical.report_submit
    ↓
Span: validate_input
    ↓
Span: store_report_db (SQLite)
    ↓
[Future] Span: ai_enrich (Gemini + Yellowcake)
    ↓
Return success response
    ↓
Sentry transaction completes
    ↓
Frontend shows "✅ Sent"
```

### 2. Failed Report Submission (Offline/Error)

```
1. Failed Submission (Offline or Error)
2. User submits a report
3. Network or server error occurs
4. Frontend stores the report in localStorage
5. UI shows “Queued for retry”
6. Background retry attempts continue
7. Once successful, the report is removed from the queue
8. UI updates to “Delivered”
9. This ensures no report is silently lost.
```

### 3. Chaos Mode (Demo)

```
User enables Chaos Mode
    ↓
30% chance: random delay (800ms)
30% chance: random failure
    ↓
Simulates poor network / backend issues
    ↓
Demonstrates queue + retry logic
    ↓
Shows Sentry capturing errors + slow traces
```

## Critical Experience Definition

### What is the Critical Experience?

**"report.submit must succeed and be fast"**

This means:
- Reports are **never lost**
- Failures are **queued and retried**
- Slowdowns are **detected and traced**
- Errors are **captured with full context**

### How Sentry Monitors It

1. **Transaction**: Every report submission creates a `critical.report_submit` transaction
2. **Tags**: 
   - `critical_experience=report_submit`
   - `report_type=crash|slow|bug|suggestion`
   - `platform=web|ios|android`
3. **Spans**: Break down time spent in each step
4. **Metrics**: Track success rate, latency distribution
5. **Errors**: Capture exceptions with logs and breadcrumbs
6. **Seer**: Suggests next actions when issues occur

## Technology Stack

### Backend
- **Python 3.10+**
- **FastAPI** - Modern, fast web framework
- **SQLite** - Embedded database (zero config)
- **Sentry SDK** - Observability
- **Uvicorn** - ASGI server

### Frontend
- **Pure HTML/CSS/JS** - No build step
- **Fetch API** - HTTP requests
- **localStorage** - Offline queue persistence

### Observability
- **Sentry** - Complete observability platform
  - Error tracking
  - Performance monitoring (traces)
  - Metrics
  - Logs & breadcrumbs
  - Seer (AI debugger)

### Optional Intelligence (Person 3)
- **Gemini API** - AI summarization & classification
- **Yellowcake API** - Similarity search & clustering

## Database Schema

```sql
CREATE TABLE reports (
    id TEXT PRIMARY KEY,              -- UUID
    created_at TEXT NOT NULL,         -- ISO timestamp
    type TEXT NOT NULL,               -- crash|slow|bug|suggestion
    message TEXT NOT NULL,            -- User's description
    platform TEXT,                    -- web|ios|android
    app_version TEXT,                 -- App version
    status TEXT DEFAULT 'received',   -- received|enriched|pending
    
    -- AI Enrichment (added by Person 3)
    summary TEXT,                     -- AI-generated summary
    category TEXT,                    -- AI-classified category
    severity TEXT,                    -- low|medium|high
    confidence REAL                   -- 0-1 confidence score
);
```

## API Contract

### POST /reports

**Request:**
```json
{
  "type": "crash",
  "message": "App crashes when clicking submit",
  "platform": "web",
  "app_version": "1.0.0"
}
```

**Response (Success):**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "received"
}
```

**Response (Error):**
```json
{
  "detail": "Message must be at least 3 characters"
}
```

### GET /reports

**Response:**
```json
{
  "reports": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-01-17T12:34:56.789Z",
      "type": "crash",
      "message": "App crashes when clicking submit",
      "platform": "web",
      "app_version": "1.0.0",
      "status": "received",
      "summary": null,
      "category": null,
      "severity": null,
      "confidence": null
    }
  ],
  "count": 1
}
```

## Security Considerations

1. **No PII Collection**: Don't collect emails, names, etc. unless necessary
2. **Secrets Management**: Use `.env` for Sentry DSN and API keys
3. **CORS**: Backend allows all origins (fine for demo, restrict in production)
4. **Rate Limiting**: Not implemented (add in production)
5. **Input Validation**: Basic validation in place

## Scalability Considerations

### Current Design (Hackathon)
- SQLite (single file)
- Single server
- No caching
- Good for: demos, small deployments

### Production Design (Future)
- PostgreSQL or similar
- Multiple backend instances
- Redis for caching/queuing
- Load balancer
- CDN for frontend

## Future Enhancements

1. **Mobile SDKs** (iOS, Android)
2. **Screenshot capture**
3. **Session replay**
4. **Advanced clustering**
5. **User authentication**
6. **Team dashboards**
7. **Webhooks & integrations**
8. **Custom fields per app**

## Why This Architecture Wins

1. **Simple but complete** - Everything needed, nothing extra
2. **Sentry-first** - Observability built in from day 1
3. **Reliable by design** - Queue + retry = never lose reports
4. **Demonstrable** - Chaos mode proves it works under stress
5. **Production-ready patterns** - Uses real patterns, not toy code
