# Demo Script - Accelerated Report App

**Duration:** 60-90 seconds  
**Goal:** Show how Sentry monitors critical experiences in an AI-powered reporting system

---

## Setup (Before Demo)

1. Backend running: `uvicorn main:app --reload`
2. Frontend open: `frontend/index.html` in browser
3. Sentry dashboard open in another tab/window
4. Have 1-2 test reports already submitted (so dashboard isn't empty)

---

## Script (What to Say & Do)

### Opening (10 seconds)

**Say:**  
*"We built Accelerated Report - a fast in-app reporting system that users actually use, because it takes only 10 seconds."*

**Do:**  
Show the report form on screen

---

### Part 1: Normal Flow (15 seconds)

**Say:**  
*"Watch how fast this is - one dropdown, one message, done."*

**Do:**
1. Select "Bug" from dropdown
2. Type: "Search not working on iPhone"
3. Click "Send Report"
4. Point to "✅ Sent" message

---

### Part 2: The Critical Part - Sentry (20 seconds)

**Say:**  
*"Here's what makes this special. We defined 'report submission' as a critical experience. Sentry monitors it end-to-end."*

**Do:**
1. Switch to Sentry dashboard
2. Click on **Performance** tab
3. Show the `critical.report_submit` transaction
4. Open one transaction, show the spans:
   - `validate_input`
   - `store_report_db`

**Say:**  
*"Sentry shows us exactly where time is spent and where failures happen."*

---

### Part 3: Chaos Mode (The Wow Moment) (25 seconds)

**Say:**  
*"Now let's break it. I'll turn on Chaos Mode to simulate bad network and failures."*

**Do:**
1. Switch back to the form
2. Toggle **Chaos Mode ON**
3. Submit 2-3 reports quickly
4. Point out:
   - Some fail immediately
   - They queue automatically
   - Show "⏳ Queued" status

**Say:**  
*"Notice - reports don't disappear. They queue and retry automatically. This is reliability by design."*

**Do:**
5. Turn Chaos Mode OFF
6. Wait 5 seconds
7. Point to "✅ Delivered" messages as queued reports succeed

---

### Part 4: Sentry Catches Everything (15 seconds)

**Say:**  
*"Back in Sentry, every failure is captured with full context."*

**Do:**
1. Switch to Sentry dashboard
2. Click **Issues** tab
3. Open a captured error from Chaos Mode
4. Show:
   - Error message
   - Tags (`critical_experience`, `report_type`)
   - Breadcrumbs
   - Trace link

**Say:**  
*"We can see exactly what failed, why, and we can even ask Seer for next steps."*

---

### Part 5: Metrics (10 seconds)

**Say:**  
*"We also track metrics like submission rate, failure rate, and latency."*

**Do:**
1. Show Sentry **Metrics** (if time) or mention it

---

### Closing (5 seconds)

**Say:**  
*"This is how we use Sentry to monitor critical user experiences - not just log errors, but ensure reliability."*

**Optional Add:**  
*"We also added AI enrichment that categorizes and summarizes reports automatically."*

---

## Backup Talking Points

If judges ask questions, use these:

### "Why did you build this?"
*"Users don't report bugs anymore because it's too slow and annoying. We made it 10 seconds, guaranteed delivery, and added intelligence."*

### "Where does Sentry fit in?"
*"Sentry is the core reliability engine. It monitors the critical experience end-to-end, so we know exactly when and why things fail."*

### "What's the critical experience?"
*"Report submission must succeed. If it fails, we queue it. If it's slow, Sentry shows us exactly where. The system never fails silently."*

### "How would real apps use this?"
*"They'd integrate our SDK. When users click 'Report a Problem', our system handles submission, context capture, and delivery - all monitored by Sentry."*

### "What about the AI part?"
*"We use Gemini to automatically summarize reports, classify severity, and group similar issues. If AI fails, reports still get saved - reliability first."*

### "Can you show Seer?"
*"Yes!" - Go to an error in Sentry, click the Seer/AI assistant button, show it suggesting next steps.*

---

## Demo Checklist

Before starting:
- [ ] Backend running
- [ ] Frontend open
- [ ] Sentry dashboard open
- [ ] At least 1 test report already submitted
- [ ] Chaos Mode toggle OFF initially

During demo:
- [ ] Show normal submission (fast!)
- [ ] Show Sentry transaction with spans
- [ ] Turn on Chaos Mode
- [ ] Submit multiple reports (show failures)
- [ ] Show queue + retry
- [ ] Show Sentry captured error
- [ ] Mention metrics

After demo:
- [ ] Answer questions confidently
- [ ] Show dashboard if time permits
- [ ] Emphasize "observability-driven reliability"

---

## What NOT to Say

❌ "This is just a prototype"  
✅ "This demonstrates production-ready patterns"

❌ "We ran out of time to..."  
✅ "We focused on the core critical experience"

❌ "Sentry was hard to integrate"  
✅ "Sentry made it easy to monitor the full flow"

---

## Emergency Fallbacks

**If backend crashes:**
- Show the queue working in frontend
- Explain that this proves offline-safe design

**If Sentry doesn't show data:**
- Show the code where Sentry is instrumented
- Walk through what *would* appear

**If Chaos Mode doesn't work:**
- Kill the backend temporarily
- Show reports queuing

---

## Time Variations

**30-second version:**
1. Show fast submission
2. Turn on Chaos Mode
3. Show Sentry error

**60-second version:**
Use the script above

**2-minute version:**
Add:
- Developer dashboard walkthrough
- Show metrics in detail
- Demonstrate Seer

---

## Judge Appeal Strategy

**Appeal to "Best Use of Sentry":**
- Emphasize "critical experience monitoring"
- Show traces, errors, metrics together
- Demonstrate observability-driven decisions (Auto-Protect)

**Appeal to practicality:**
- This solves a real problem
- Real apps could use this
- Production-ready patterns

**Appeal to intelligence:**
- AI enrichment is smart
- But reliability comes first
- System adapts to failures

---

