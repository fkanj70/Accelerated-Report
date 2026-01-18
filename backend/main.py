import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# AI imports
try:
    import google.generativeai as genai
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    AI_ENABLED = True
except ImportError:
    AI_ENABLED = False
    print("⚠️  AI libraries not installed. Install with: pip install google-generativeai numpy scikit-learn")

# Load environment variables
load_dotenv()

# Initialize Gemini AI if API key provided
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if AI_ENABLED and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    print("✅ Gemini AI enabled")
else:
    gemini_model = None
    print("⚠️  Gemini AI disabled (set GEMINI_API_KEY to enable)")

# Initialize Yellowcake for finding helpful resources
YELLOWCAKE_API_KEY = os.getenv("YELLOWCAKE_API_KEY")
if YELLOWCAKE_API_KEY:
    print("✅ Yellowcake enabled (will fetch helpful resources)")
else:
    print("⚠️  Yellowcake disabled (set YELLOWCAKE_API_KEY to enable)")

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=float(os.getenv("TRACES_SAMPLE_RATE", "1.0")),
    environment=os.getenv("ENVIRONMENT", "dev"),
    integrations=[
        FastApiIntegration(),
    ],
    # Enable performance monitoring
    enable_tracing=True,
    # Add data like request headers and IP for users
    send_default_pii=True,
)

# Print Sentry status
if os.getenv("SENTRY_DSN"):
    print("✅ Sentry monitoring enabled")
else:
    print("⚠️  Sentry monitoring disabled (set SENTRY_DSN to enable)")

# Database setup
DB_NAME = "reports.db"


def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            platform TEXT,
            app_version TEXT,
            status TEXT DEFAULT 'received',
            description TEXT,
            category TEXT,
            severity TEXT,
            developer_action TEXT,
            confidence REAL,
            similar_reports TEXT,
            helpful_resources TEXT,
            sentry_event_id TEXT,
            screenshot_url TEXT
        )
    """)
    conn.commit()
    conn.close()


# AI Enrichment Functions

async def enrich_with_gemini(report_data: dict, screenshot_path: str = None) -> dict:
    """
    Use Gemini AI to analyze report with screenshot context.
    
    Analyzes: report type, user message, screenshot (if available)
    Returns: comprehensive summary, categorization, severity, and action items
    """
    if not gemini_model:
        return {}
    
    try:
        with sentry_sdk.start_span(op="ai.inference", description="gemini_enrichment"):
            # Prepare content for Gemini
            parts = []
            
            # Add text prompt
            prompt = f"""You are an expert bug report analyzer. Analyze this user feedback:

REPORT DETAILS:
- Type: {report_data['type']} (crash/slow/bug/suggestion)
- User's Message: "{report_data['message']}"
- Platform: {report_data.get('platform', 'unknown')}"""

            if screenshot_path:
                prompt += "\n- Screenshot: Provided (see image)"
            
            prompt += """

YOUR ANALYSIS TASK:
1. DESCRIPTION: Write a comprehensive 2-3 sentence summary interpreting what the user experienced. If there's a screenshot, describe what you see and how it relates to the reported issue.

2. CATEGORY: Classify into one of: crash/performance/bug/feature_request/ui_issue/network/data_issue

3. SEVERITY: Assess impact: critical/high/medium/low
   - critical: app unusable, data loss, security issue
   - high: major feature broken, affects many users
   - medium: feature partially broken, workaround exists
   - low: minor issue, cosmetic, edge case

4. DEVELOPER_ACTION: Provide specific actionable steps for the developer (1-2 sentences). If screenshot shows specific UI elements, mention them.

5. CONFIDENCE: Your confidence in this analysis (0.0-1.0)

Respond in this exact format:
DESCRIPTION: [your detailed interpretation]
CATEGORY: [category]
SEVERITY: [severity]
DEVELOPER_ACTION: [specific action steps]
CONFIDENCE: [score]"""

            parts.append(prompt)
            
            # Add screenshot if available
            if screenshot_path:
                try:
                    import PIL.Image
                    image = PIL.Image.open(screenshot_path)
                    parts.append(image)
                except Exception as e:
                    print(f"Failed to load screenshot for Gemini: {e}")
            
            # Generate analysis
            response = gemini_model.generate_content(parts)
            result_text = response.text.strip()
            
            # Parse response
            enrichment = {}
            for line in result_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    enrichment[key] = value
            
            # Add to Sentry context for better issue grouping
            sentry_sdk.set_context("ai_analysis", {
                "description": enrichment.get('description', ''),
                "category": enrichment.get('category', ''),
                "severity": enrichment.get('severity', 'medium'),
                "developer_action": enrichment.get('developer_action', ''),
                "confidence": enrichment.get('confidence', '0.5'),
            })
            
            return {
                'description': enrichment.get('description', report_data['message']),
                'category': enrichment.get('category', 'unknown'),
                'severity': enrichment.get('severity', 'medium'),
                'developer_action': enrichment.get('developer_action', 'Investigate issue'),
                'confidence': float(enrichment.get('confidence', '0.5')),
            }
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Gemini AI enrichment failed: {e}")
        return {}


async def send_to_sentry_for_grouping(report_data: dict, ai_enrichment: dict):
    """
    Send report to Sentry for automatic issue grouping.
    
    For bug reports (crash/bug/slow), also triggers an actual error in Sentry
    so you can see the full error tracking capabilities.
    
    Sentry's built-in grouping will:
    - Group similar errors together
    - Detect duplicate issues
    - Show related problems in dashboard
    """
    try:
        # Create a custom exception with enriched context
        with sentry_sdk.push_scope() as scope:
            # Add all context for Sentry's grouping
            scope.set_tag("report_type", report_data['type'])
            scope.set_tag("platform", report_data.get('platform', 'unknown'))
            scope.set_tag("ai_category", ai_enrichment.get('category', 'unknown'))
            scope.set_tag("severity", ai_enrichment.get('severity', 'medium'))
            
            # Add user context
            scope.set_context("report", {
                "original_message": report_data['message'],
                "ai_description": ai_enrichment.get('description', ''),
                "developer_action": ai_enrichment.get('developer_action', ''),
                "app_version": report_data.get('app_version', '1.0.0'),
            })
            
            # Set fingerprint for Sentry's grouping
            # Reports with same type and similar AI category will be grouped
            scope.fingerprint = [
                report_data['type'],
                ai_enrichment.get('category', 'unknown'),
                report_data.get('platform', 'unknown')
            ]
            
            # For bug/crash/slow reports, trigger an actual error in Sentry
            if report_data['type'] in ['crash', 'bug', 'slow']:
                # Create a custom exception based on the report type
                error_messages = {
                    'crash': f"Application Crash: {ai_enrichment.get('description', report_data['message'])}",
                    'bug': f"Bug Report: {ai_enrichment.get('description', report_data['message'])}",
                    'slow': f"Performance Issue: {ai_enrichment.get('description', report_data['message'])}"
                }
                
                # Create custom exception
                exception = Exception(error_messages[report_data['type']])
                
                # Capture as error so it shows in Issues tab
                sentry_sdk.capture_exception(exception)
            else:
                # For suggestions, just capture as message
                sentry_sdk.capture_message(
                    f"User Suggestion: {ai_enrichment.get('description', report_data['message'])}",
                    level='info'
                )
            
    except Exception as e:
        print(f"Failed to send to Sentry: {e}")


async def find_similar_reports(report_data: dict, conn) -> List[str]:
    """
    Find similar reports in local database by category and type.
    Note: Sentry's Yellowcake does the real similarity detection in the dashboard.
    """
    try:
        with sentry_sdk.start_span(op="db.query", description="find_similar_local"):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, message, category FROM reports 
                WHERE type = ? AND category IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 10
            """, (report_data['type'],))
            
            existing_reports = cursor.fetchall()
            similar_ids = []
            
            # Simple keyword matching (real similarity is in Sentry's Yellowcake)
            for report_id, message, category in existing_reports:
                if category == report_data.get('category'):
                    similar_ids.append(report_id)
                
                if len(similar_ids) >= 3:
                    break
            
            return similar_ids
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return []


async def find_helpful_resources_with_yellowcake(report_data: dict, ai_enrichment: dict) -> List[dict]:
    """
    Use Yellowcake to find helpful resources for developers:
    - Stack Overflow solutions
    - Official documentation
    - GitHub issues
    - Tutorial articles
    """
    if not YELLOWCAKE_API_KEY:
        return []
    
    try:
        with sentry_sdk.start_span(op="yellowcake.search", description="find_helpful_resources"):
            import httpx
            
            # Build search query from AI analysis
            error_description = ai_enrichment.get('description', report_data['message'])
            category = ai_enrichment.get('category', 'unknown')
            platform = report_data.get('platform', 'unknown')
            
            # Search Stack Overflow for solutions
            stackoverflow_query = f"{category} {platform} error solution"
            
            resources = []
            
            # Use Yellowcake to extract Stack Overflow solutions
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.yellowcake.dev/v1/extract",
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": YELLOWCAKE_API_KEY,
                        },
                        json={
                            "url": f"https://stackoverflow.com/search?q={stackoverflow_query}",
                            "prompt": f"Find top 3 relevant solutions for: {error_description}"
                        }
                    )
                    
                    if response.status_code == 200:
                        stackoverflow_data = response.json()
                        if stackoverflow_data.get('results'):
                            resources.append({
                                "type": "stackoverflow",
                                "title": "Stack Overflow Solutions",
                                "links": stackoverflow_data.get('results', [])[:3],
                                "description": "Community solutions for similar issues"
                            })
            except Exception as e:
                print(f"Yellowcake Stack Overflow search failed: {e}")
            
            # Search for official documentation
            if platform in ['ios', 'android', 'web']:
                doc_url = {
                    'ios': 'https://developer.apple.com',
                    'android': 'https://developer.android.com',
                    'web': 'https://developer.mozilla.org'
                }.get(platform)
                
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            "https://api.yellowcake.dev/v1/extract",
                            headers={
                                "Content-Type": "application/json",
                                "X-API-Key": YELLOWCAKE_API_KEY,
                            },
                            json={
                                "url": doc_url,
                                "prompt": f"Find documentation for: {error_description}"
                            }
                        )
                        
                        if response.status_code == 200:
                            doc_data = response.json()
                            if doc_data.get('results'):
                                resources.append({
                                    "type": "documentation",
                                    "title": f"{platform.upper()} Official Documentation",
                                    "links": doc_data.get('results', [])[:2],
                                    "description": "Official platform documentation"
                                })
                except Exception as e:
                    print(f"Yellowcake documentation search failed: {e}")
            
            # Add to Sentry context
            if resources:
                sentry_sdk.set_context("helpful_resources", {
                    "resources": resources,
                    "source": "yellowcake"
                })
            
            return resources
            
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Yellowcake resource search failed: {e}")
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed


# Create FastAPI app
app = FastAPI(
    title="Accelerated Report API",
    description="Fast, reliable in-app reporting with Sentry monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for screenshots
from fastapi.staticfiles import StaticFiles
import os
screenshots_dir = "screenshots"
os.makedirs(screenshots_dir, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")


# Request/Response models
class ReportCreate(BaseModel):
    type: str  # crash | slow | bug | suggestion
    message: str
    platform: Optional[str] = "web"
    app_version: Optional[str] = "1.0.0"
    screenshot: Optional[str] = None  # base64 encoded image


class ReportResponse(BaseModel):
    report_id: str
    status: str
    ai_enriched: bool = False
    category: Optional[str] = None
    severity: Optional[str] = None
    similar_count: int = 0
    helpful_resources: List[dict] = []


class Report(BaseModel):
    id: str
    created_at: str
    type: str
    message: str
    platform: Optional[str]
    app_version: Optional[str]
    status: str
    summary: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None


# Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Accelerated Report API"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/boom")
async def boom():
    """Test endpoint to trigger a Sentry error"""
    # This is intentional for testing Sentry
    raise Exception("💥 Boom! This is a test error for Sentry.")


@app.get("/sentry-debug")
async def sentry_debug():
    """Official Sentry verification endpoint"""
    division_by_zero = 1 / 0
    return {"status": "This should never return"}


@app.post("/reports", response_model=ReportResponse)
async def create_report(report: ReportCreate):
    """
    Create a new report.
    This is the CRITICAL EXPERIENCE that must succeed.
    """
    # Start Sentry transaction for critical experience
    with sentry_sdk.start_transaction(
        op="critical.experience",
        name="critical.report_submit"
    ) as transaction:
        
        # Add tags for better filtering in Sentry
        transaction.set_tag("critical_experience", "report_submit")
        transaction.set_tag("report_type", report.type)
        transaction.set_tag("platform", report.platform)
        
        # Add breadcrumb
        sentry_sdk.add_breadcrumb(
            category="report",
            message=f"Submitting {report.type} report",
            level="info",
        )
        
        # Span 1: Validate input
        with sentry_sdk.start_span(op="validate", description="validate_input"):
            if not report.message or len(report.message) < 3:
                raise HTTPException(status_code=400, detail="Message must be at least 3 characters")
            
            valid_types = ["crash", "slow", "bug", "suggestion"]
            if report.type not in valid_types:
                raise HTTPException(status_code=400, detail=f"Type must be one of: {valid_types}")
        
        # Generate report ID
        report_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Save screenshot first if provided (needed for Gemini analysis)
        screenshot_url = None
        screenshot_path = None
        if report.screenshot:
            try:
                import base64
                import os
                
                # Create screenshots directory
                screenshots_dir = "screenshots"
                os.makedirs(screenshots_dir, exist_ok=True)
                
                # Extract base64 data
                if report.screenshot.startswith('data:image'):
                    # Remove data:image/png;base64, prefix
                    screenshot_data = report.screenshot.split(',')[1]
                else:
                    screenshot_data = report.screenshot
                
                # Save to file
                screenshot_filename = f"{report_id}.png"
                screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
                with open(screenshot_path, 'wb') as f:
                    f.write(base64.b64decode(screenshot_data))
                
                screenshot_url = f"/screenshots/{screenshot_filename}"
                transaction.set_tag("has_screenshot", True)
            except Exception as e:
                print(f"Failed to save screenshot: {e}")
                sentry_sdk.capture_exception(e)
        
        # Span 2: AI Enrichment with Gemini (analyzes report + screenshot)
        ai_enrichment = {}
        if gemini_model:
            ai_enrichment = await enrich_with_gemini(report.dict(), screenshot_path)
            transaction.set_tag("ai_enriched", True)
            transaction.set_tag("ai_category", ai_enrichment.get('category', 'unknown'))
            transaction.set_tag("ai_severity", ai_enrichment.get('severity', 'medium'))
        
        # Span 3: Find helpful resources with Yellowcake
        helpful_resources = []
        if YELLOWCAKE_API_KEY:
            helpful_resources = await find_helpful_resources_with_yellowcake(report.dict(), ai_enrichment)
            if helpful_resources:
                transaction.set_tag("has_helpful_resources", True)
                transaction.set_data("resources_found", len(helpful_resources))
        
        # Span 4: Send to Sentry for automatic grouping
        await send_to_sentry_for_grouping(report.dict(), ai_enrichment)
        
        # Span 5: Find similar reports in local DB
        conn = sqlite3.connect(DB_NAME)
        similar_reports = await find_similar_reports({**report.dict(), **ai_enrichment}, conn)
        if similar_reports:
            transaction.set_tag("has_local_duplicates", True)
            transaction.set_data("similar_count", len(similar_reports))
        
        # Span 6: Store in database
        with sentry_sdk.start_span(op="db.query", description="store_report_db"):
            try:
                import json
                
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reports (
                        id, created_at, type, message, platform, app_version, status,
                        description, category, severity, developer_action, confidence, 
                        similar_reports, helpful_resources, screenshot_url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id, created_at, report.type, report.message, 
                    report.platform, report.app_version, "received",
                    ai_enrichment.get('description'),
                    ai_enrichment.get('category'),
                    ai_enrichment.get('severity'),
                    ai_enrichment.get('developer_action'),
                    ai_enrichment.get('confidence'),
                    ','.join(similar_reports) if similar_reports else None,
                    json.dumps(helpful_resources) if helpful_resources else None,
                    screenshot_url
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                sentry_sdk.capture_exception(e)
                raise HTTPException(status_code=500, detail="Failed to store report")
        
        # Track metric: report submitted successfully
        try:
            from sentry_sdk import metrics
            metrics.incr(
                "reports.submitted",
                tags={
                    "type": report.type,
                    "platform": report.platform,
                    "ai_enriched": str(bool(ai_enrichment)),
                    "has_resources": str(bool(helpful_resources)),
                }
            )
        except Exception:
            pass  # Metrics not critical
        
        return ReportResponse(
            report_id=report_id,
            status="received",
            ai_enriched=bool(ai_enrichment),
            category=ai_enrichment.get('category'),
            severity=ai_enrichment.get('severity'),
            similar_count=len(similar_reports),
            helpful_resources=helpful_resources
        )


@app.get("/reports")
async def list_reports():
    """Get all reports"""
    try:
        import json
        import traceback
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        
        reports = []
        for row in rows:
            # Convert Row to dict for easy access
            row_dict = dict(row)
            
            # Parse JSON fields
            helpful_resources = None
            if row_dict.get("helpful_resources"):
                try:
                    helpful_resources = json.loads(row_dict["helpful_resources"])
                except:
                    pass
            
            reports.append({
                "id": row_dict["id"],
                "created_at": row_dict["created_at"],
                "type": row_dict["type"],
                "message": row_dict["message"],
                "platform": row_dict.get("platform"),
                "app_version": row_dict.get("app_version"),
                "status": row_dict.get("status"),
                "description": row_dict.get("description"),
                "category": row_dict.get("category"),
                "severity": row_dict.get("severity"),
                "developer_action": row_dict.get("developer_action"),
                "confidence": row_dict.get("confidence"),
                "similar_reports": row_dict.get("similar_reports"),
                "helpful_resources": helpful_resources,
                "sentry_event_id": row_dict.get("sentry_event_id"),
                "screenshot_url": row_dict.get("screenshot_url"),
            })
        
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        import traceback
        print(f"ERROR in list_reports: {e}")
        print(traceback.format_exc())
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reports: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
