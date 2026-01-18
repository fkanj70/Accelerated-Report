# Team Division - 3 Person Roles

## Overview

This document breaks down the work for **3 people** working on the Accelerated Report App. Each person has clear ownership and can work mostly independently after initial setup.

---

## FIRST STEP (EVERYONE TOGETHER - 15 minutes)

Before anyone can work independently, **one person** (recommend Person 1) must do this:

### Setup Checklist
1. Create Sentry project at [sentry.io](https://sentry.io)
   - Choose Python platform
   - Copy the DSN
   
2. Create repository structure
   - Already done if using this repo!
   
3. Agree on API contract
   - POST /reports format (already defined in docs)
   - Response format
   
4. Share Sentry DSN with team (via secure method)

**Once this is done, everyone can work in parallel.**

---

##  Person 1: Backend + Sentry (MOST CRITICAL ROLE)

### Responsibility
Build the FastAPI backend and ensure Sentry is used perfectly. This is the most important role for "Best Use of Sentry" scoring.

### Skills Needed
- Python (beginner-friendly)
- Basic understanding of APIs
- Reading documentation

### Your Mission
Make sure **every report submission is tracked, traced, and measured in Sentry**.

---

### Tasks (In Order)

#### Phase 1: Setup (30 minutes)
- [x] Create Sentry project
- [ ] Set up Python virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Create `.env` file with Sentry DSN
- [ ] Run backend: `uvicorn main:app --reload`
- [ ] Test `/boom` endpoint → verify error shows in Sentry

**Success Check:** You see the test error in Sentry dashboard.

---

#### Phase 2: Core API (1 hour)
- [ ] Implement `POST /reports` endpoint
- [ ] Add SQLite database storage
- [ ] Implement `GET /reports` endpoint
- [ ] Test with curl or Postman

**Success Check:** You can create and retrieve reports.

---

#### Phase 3: Sentry Instrumentation (1-2 hours)  MOST IMPORTANT
- [ ] Add transaction: `critical.report_submit`
- [ ] Add spans:
  - `validate_input`
  - `store_report_db`
- [ ] Add tags:
  - `critical_experience=report_submit`
  - `report_type`
  - `platform`
- [ ] Add breadcrumbs for key actions
- [ ] Add metrics:
  - `reports.submitted`
  - `reports.failed`
  - `report.submit.latency_ms`

**Success Check:** In Sentry Performance tab, you see `critical.report_submit` transactions with spans.

---

#### Phase 4: Reliability Features (1 hour)
- [ ] Add error handling
- [ ] Test failure scenarios
- [ ] Add chaos mode support (optional delay/error)
- [ ] Ensure all errors are captured in Sentry

---

#### Phase 5: Integration with Person 3 (when ready)
- [ ] Add `ai_enrich` span
- [ ] Wrap Gemini API calls with Sentry span
- [ ] Wrap Yellowcake API calls with Sentry span
- [ ] Track enrichment failures separately

---

### Files You Own
- `backend/main.py`
- `backend/.env`
- `backend/requirements.txt`
- Database: `backend/reports.db`

### What to Show Judges
- Sentry transaction for `critical.report_submit`
- Spans showing time breakdown
- Error captured with tags and breadcrumbs
- Metrics dashboard

---

##  Person 2: Frontend + UX (USER EXPERIENCE)

### Responsibility
Build the web interface that users see. Make reporting **fast** and **reliable** (offline queue).

### Skills Needed
- HTML/CSS/JavaScript (beginner-friendly)
- Basic understanding of fetch API
- Understanding of localStorage

### Your Mission
Make sure users can report in **under 10 seconds** and reports **never get lost**.

---

### Tasks (In Order)

#### Phase 1: Setup (15 minutes)
- [x] Files already created
- [ ] Open `frontend/index.html` in browser
- [ ] Verify it loads correctly

**Success Check:** You see the report form.

---

#### Phase 2: Core Form (1 hour)
- [ ] Test form inputs
- [ ] Verify dropdown and textarea work
- [ ] Add form validation (client-side)
- [ ] Connect to backend API
- [ ] Test successful submission

**Success Check:** You can submit a report and see success message.

---

#### Phase 3: Offline Queue (1-2 hours)  KEY FEATURE
- [ ] Implement localStorage queue
- [ ] Save failed reports to queue
- [ ] Show "⏳ Queued" status
- [ ] Implement auto-retry (every 5 seconds)
- [ ] Remove from queue on success
- [ ] Show queue count badge

**Success Check:** 
1. Kill backend
2. Submit report
3. See it queued
4. Start backend
5. Watch it deliver automatically

---

#### Phase 4: Chaos Mode (1 hour)
- [ ] Add toggle switch for Chaos Mode
- [ ] Simulate random delays (30% chance, 800ms)
- [ ] Simulate random failures (30% chance)
- [ ] Show different status messages

**Success Check:** With Chaos Mode ON, some reports fail and queue.

---

#### Phase 5: Developer Dashboard (1 hour)
- [ ] Build dashboard page
- [ ] Fetch all reports from API
- [ ] Display reports in cards
- [ ] Show stats (total, by type)
- [ ] Add auto-refresh (every 10 seconds)

---

#### Phase 6: Polish (30 minutes)
- [ ] Make it look clean (already styled)
- [ ] Add loading states
- [ ] Test on different screen sizes
- [ ] Add recent submissions list

---

### Files You Own
- `frontend/index.html`
- `frontend/dashboard.html`
- `frontend/app.js`
- `frontend/dashboard.js`
- `frontend/styles.css`

### What to Show Judges
- Fast submission (< 10 seconds)
- Chaos Mode in action
- Queue working (reports retry automatically)
- Clean, simple UI

---

## 👤 Person 3: Intelligence (AI ENRICHMENT)

### Responsibility
Add AI-powered features: summarization, classification, and similarity search. **Keep it simple and safe.**

### Skills Needed
- Python (beginner-friendly)
- Basic understanding of API calls
- Reading API documentation

### Your Mission
Make reports **intelligent** without breaking **reliability**.

---

### Tasks (In Order)

#### Phase 1: Design (30 minutes)
- [ ] Read Gemini API docs
- [ ] Read Yellowcake API docs (if available)
- [ ] Design JSON output format
- [ ] Design confidence scoring logic

**Success Check:** You have a clear plan.

---

#### Phase 2: Gemini Integration (1-2 hours)
- [ ] Get Gemini API key
- [ ] Create enrichment function
- [ ] Call Gemini with report message
- [ ] Parse JSON response:
  - `summary` (1-2 sentences)
  - `category` (crash/perf/ui/auth/etc)
  - `severity` (low/medium/high)
  - `confidence` (0-1 score)
- [ ] Handle errors gracefully (never crash)

**Success Check:** Given a report message, you get back structured data.

---

#### Phase 3: Integration with Backend (1 hour)
- [ ] Work with Person 1 to add enrichment
- [ ] Call enrichment after saving report
- [ ] Update report in database with enrichment
- [ ] Ensure failures don't break report submission

**Key Rule:** If enrichment fails, report still succeeds.

---

#### Phase 4: Yellowcake Integration (1 hour)
- [ ] Integrate Yellowcake API
- [ ] Find similar reports
- [ ] Store cluster_id or similar_report_ids
- [ ] Handle errors gracefully

---

#### Phase 5: Confidence Logic (30 minutes)
- [ ] Calculate confidence score:
  - +0.4 if Gemini returns clean data
  - +0.4 if Yellowcake finds matches
  - +0.2 if summary makes sense
- [ ] If confidence < 0.6 → mark for escalation

---

#### Phase 6: Dashboard Display (30 minutes)
- [ ] Work with Person 2
- [ ] Show enrichment data in dashboard
- [ ] Display summary, category, severity
- [ ] Show confidence score

---

### Files You'll Create/Modify
- `backend/enrichment.py` (new file)
- `backend/main.py` (add enrichment call)

### What to Show Judges
- AI summary of a report
- Category and severity classification
- Confidence score
- Similar reports grouped together

---

## Integration Points

### When Person 1 & Person 2 Connect
- **What:** Frontend calls backend API
- **When:** After Person 1 has POST /reports working
- **How:** Person 2 updates `API_BASE_URL` if needed

### When Person 1 & Person 3 Connect
- **What:** Backend calls enrichment function
- **When:** After Person 3 has enrichment function working
- **How:** Person 1 adds enrichment call after saving report

### When Person 2 & Person 3 Connect
- **What:** Dashboard displays enrichment data
- **When:** After enrichment is working
- **How:** Person 2 adds fields to dashboard

---

##  Daily Standup (Suggested)

**Each person answers:**
1. What did I complete yesterday?
2. What am I working on today?
3. Am I blocked by anything?

**Example:**

**Person 1:** "Backend is working. Today I'm adding Sentry spans. Not blocked."

**Person 2:** "Form works. Today I'm adding offline queue. Not blocked."

**Person 3:** "Researching Gemini API. Today I'll test enrichment. Need API key."

---

## Priority Order

If you run out of time, focus on this order:

### Must Have (for demo)
1. Person 1: Backend + basic Sentry (transactions)
2. Person 2: Form + submit
3. Person 1: Sentry spans + metrics

### Should Have (for scoring well)
4. Person 2: Offline queue
5. Person 2: Chaos Mode
6. Person 1: Error capture in Sentry

### Nice to Have (for winning)
7. Person 3: Gemini enrichment
8. Person 2: Dashboard
9. Person 3: Yellowcake similarity

---

## Emergency Protocol

**If someone gets blocked:**
1. Don't stay blocked - ask for help immediately
2. Use minimal working version
3. Move to next task

**If running out of time:**
- Focus on Sentry instrumentation (Person 1)
- Focus on offline queue (Person 2)
- AI is bonus, not required

---

## Communication

**Use a shared channel (Discord/Slack) to:**
- Share the Sentry DSN
- Coordinate API changes
- Share blockers
- Celebrate wins

**Quick updates > Long meetings**

---

## Final Checklist (Before Demo)

### Person 1
- [ ] Backend running
- [ ] Sentry DSN configured
- [ ] POST /reports works
- [ ] GET /reports works
- [ ] Sentry shows transactions with spans
- [ ] Errors captured in Sentry
- [ ] Metrics configured

### Person 2
- [ ] Frontend loads
- [ ] Can submit reports
- [ ] Offline queue works
- [ ] Chaos Mode works
- [ ] Dashboard shows reports

### Person 3
- [ ] Enrichment function works
- [ ] Integrated with backend
- [ ] Shows in dashboard
- [ ] Handles failures gracefully

### Everyone
- [ ] Practiced demo script together
- [ ] Know what to say to judges
- [ ] Understand how Sentry is used
- [ ] Can explain the "critical experience"

---


