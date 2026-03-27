# Web Scraper Boilerplate

A scalable web scraping framework built with Flask and Playwright, featuring an action-based registry pattern for easy extensibility, automated captcha solving, and session persistence.

Currently implements scrapers for the **BBMP SmartOne Bangalore** government complaint portal (filing complaints and tracking status).

## Tech Stack

- **Framework:** Flask + Flask-Smorest (OpenAPI/Swagger)
- **Browser Automation:** Playwright (headless Chromium)
- **HTML Parsing:** BeautifulSoup4
- **Captcha Solving:** EasyOCR + OpenCV
- **Validation:** Marshmallow
- **Python:** 3.12

## Project Structure

```
web-scraper-boilerplate/
├── app.py                        # Flask app factory & entry point
├── config.py                     # Environment config
├── requirements.txt              # Dependencies
├── .env                          # Environment variables
│
├── api/                          # REST API layer
│   ├── health.py                 # GET /api/health
│   └── web_scrap.py              # POST /api/v1/scrape (unified scraping endpoint)
│
├── models/                       # Data models & validation
│   ├── enums.py                  # SourceEnum, PortalEnum, ActionTypeEnum
│   └── schemas.py                # Marshmallow request/response schemas
│
├── portals/                      # Scraper implementations
│   ├── __init__.py               # ActionHandlerRegistry (core dispatcher)
│   ├── bbmp_complaint.py         # raise_complaint() - form filling & submission
│   ├── bbmp_login.py             # login_user() - auth with captcha retry
│   ├── captcha_solver.py         # EasyOCR-based captcha OCR
│   ├── complaint_scraper.py      # fetch_complaint_status() - status tracking
│   └── handlers/
│       └── bbmp_handlers.py      # Handler registrations for BBMP portal
│
├── utils/
│   └── image_download.py         # Download images from URLs or resolve local paths
│
└── infra/                        # Deployment docs (GCP)
    ├── infrastructure.md
    └── deployment.md
```

## How It Works

### Architecture Overview

All scraping operations go through a **single API endpoint**: `POST /api/v1/scrape`. The request specifies *what* to scrape via three keys:

- **source** - the category of portal (e.g., `GOV_ISSUE_PORTAL`)
- **portal** - the specific portal (e.g., `SMARTONEBLR`)
- **action type** - the operation to perform (e.g., `REPORT_ISSUE`, `TRACK_ISSUE`)

These three values form a composite key that the **Action Registry** uses to dispatch to the correct handler function.

### Request Flow

```
Client Request
    │
    ▼
POST /api/v1/scrape          (api/web_scrap.py)
    │
    ├─ Validate request schema (Marshmallow)
    │
    ├─ Build registry key:  "source:portal:action_type"
    │
    ├─ Look up handler in ActionHandlerRegistry
    │
    ▼
Handler Function              (portals/handlers/*.py)
    │
    ├─ Authenticate if needed (Playwright + captcha solving)
    │
    ├─ Perform scraping logic (Playwright browser automation)
    │
    ├─ Parse results          (BeautifulSoup / Playwright selectors)
    │
    ▼
Return (success, result)  →  JSON Response to Client
```

### The Action Registry Pattern

The core of the architecture lives in `portals/__init__.py`. It provides a decorator-based system for registering handler functions:

```python
# portals/__init__.py
class ActionHandlerRegistry:
    def register(self, source, portal, action_type, description=""):
        """Decorator that registers a handler for a source:portal:action combo."""
        ...

    def dispatch(self, source, portal, action_type, action_data, context):
        """Looks up the registered handler and calls it."""
        ...

action_registry = ActionHandlerRegistry()  # Global singleton
```

Handlers register themselves using decorators:

```python
# portals/handlers/bbmp_handlers.py
@register_handler(
    source="GOV_ISSUE_PORTAL",
    portal="SMARTONEBLR",
    action_type="REPORT_ISSUE",
    description="Report a new complaint on BBMP portal"
)
def handle_report_issue(action_data: dict, context: dict) -> tuple[bool, dict]:
    # ... scraping logic ...
    return True, {"data": {"tracking_id": "12345"}}
```

This pattern eliminates if-else chains and makes adding new scrapers clean and modular.

### Scraping Pipeline (Example: Filing a Complaint)

The `raise_complaint()` function in `portals/bbmp_complaint.py` demonstrates the full pipeline:

1. **Launch headless browser** via Playwright
2. **Restore session** from `bbmp_auth.json` (cookies & localStorage)
3. **Check login status** - if expired, re-authenticate with captcha solving
4. **Navigate** to the target page and locate the form (inside an iframe)
5. **Fill form fields** - dropdowns, text areas, file uploads, location
6. **Submit** and handle confirmation popups
7. **Extract result** - parse the acknowledgement page for the complaint ID
8. **Persist session** - save updated cookies to `bbmp_auth.json`
9. **Return** structured result

### Captcha Solving

The `portals/captcha_solver.py` module uses EasyOCR with image preprocessing:

1. Screenshot the captcha element
2. Convert to grayscale
3. Upscale 2x for better OCR accuracy
4. Apply binary thresholding
5. Run EasyOCR text recognition
6. Filter to alphanumeric characters only

Login attempts retry up to 3 times if captcha recognition fails.

## API Reference

### Health Check

```
GET /api/health
```

Returns `200 OK` with status info. Used by load balancers.

### Scrape

```
POST /api/v1/scrape
Content-Type: application/json
```

**Request Body:**

```json
{
  "source": "GOV_ISSUE_PORTAL",
  "context": {
    "portal": "SMARTONEBLR",
    "action": {
      "type": "REPORT_ISSUE",
      "data": {
        "category": "Road Engineering",
        "sub_category": "Potholes",
        "description": "Large pothole on MG Road",
        "media_url": "https://example.com/photo.jpg",
        "latitude": "12.9716",
        "longitude": "77.5946"
      }
    },
    "auth": {
      "username": "9876543210",
      "password": "your_password"
    }
  }
}
```

**Successful Response:**

```json
{
  "data": {
    "tracking_id": "21025835"
  }
}
```

**Track Issue Example:**

```json
{
  "source": "GOV_ISSUE_PORTAL",
  "context": {
    "portal": "SMARTONEBLR",
    "action": {
      "type": "TRACK_ISSUE",
      "data": {
        "tracking_id": "21025835"
      }
    },
    "auth": { "username": "...", "password": "..." }
  }
}
```

**Response:**

```json
{
  "data": {
    "status": "CLOSED",
    "meta_data": {
      "remarks": "Issue resolved",
      "staff_name": "John Doe",
      "mobile_number": "1234567890"
    }
  }
}
```

Swagger UI is available at `/api/docs` when the server is running.

---

## How to Add a New Web Scraper

Follow these steps to add a scraper for a new portal or action.

### Step 1: Define Enums

Add your new source, portal, or action type to `models/enums.py`:

```python
class SourceEnum(str, Enum):
    GOV_ISSUE_PORTAL = "GOV_ISSUE_PORTAL"
    ECOMMERCE = "ECOMMERCE"               # New source

class PortalEnum(str, Enum):
    SMARTONEBLR = "SMARTONEBLR"
    AMAZON_IN = "AMAZON_IN"               # New portal

class ActionTypeEnum(str, Enum):
    REPORT_ISSUE = "REPORT_ISSUE"
    TRACK_ISSUE = "TRACK_ISSUE"
    FETCH_PRICE = "FETCH_PRICE"           # New action
```

### Step 2: Create the Scraper Logic

Create a new file under `portals/` with your scraping function. This is where the actual Playwright automation lives.

```python
# portals/amazon_scraper.py

from playwright.sync_api import sync_playwright

def fetch_product_price(product_url: str) -> dict:
    """Scrape product price from Amazon."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(product_url, timeout=30000)
            page.wait_for_selector("#priceblock_ourprice", timeout=10000)

            title = page.locator("#productTitle").inner_text().strip()
            price = page.locator("#priceblock_ourprice").inner_text().strip()

            return {
                "success": True,
                "title": title,
                "price": price
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            browser.close()
```

### Step 3: Register a Handler

Create a handler file (or add to an existing one) under `portals/handlers/`:

```python
# portals/handlers/amazon_handlers.py

from portals.handlers import register_handler
from portals.amazon_scraper import fetch_product_price

@register_handler(
    source="ECOMMERCE",
    portal="AMAZON_IN",
    action_type="FETCH_PRICE",
    description="Fetch product price from Amazon India"
)
def handle_fetch_price(action_data: dict, context: dict) -> tuple[bool, dict]:
    product_url = action_data.get("product_url")
    if not product_url:
        return False, {"error": "product_url is required"}

    result = fetch_product_price(product_url)

    if result.get("success"):
        return True, {
            "data": {
                "title": result["title"],
                "price": result["price"]
            }
        }

    return False, {"error": result.get("error", "Failed to fetch price")}
```

### Step 4: Import the Handler Module

Make sure your handler module gets imported at startup so the `@register_handler` decorators execute. Add the import in `portals/handlers/__init__.py`:

```python
# portals/handlers/__init__.py

from portals import action_registry

def register_handler(source, portal, action_type, description=""):
    return action_registry.register(source, portal, action_type, description)

# Import handler modules so they register on startup
import portals.handlers.bbmp_handlers
import portals.handlers.amazon_handlers    # Add this line
```

### Step 5: Add Validation Schemas

Add Marshmallow schemas for your new action's request/response data in `models/schemas.py`:

```python
class FetchPriceDataSchema(Schema):
    product_url = fields.Url(required=True)

class FetchPriceResponseSchema(Schema):
    title = fields.String()
    price = fields.String()
```

Then wire them into the existing validation logic in the same file.

### Step 6: Test It

Start the server and send a request:

```bash
python app.py
```

```bash
curl -X POST http://localhost:5001/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "source": "ECOMMERCE",
    "context": {
      "portal": "AMAZON_IN",
      "action": {
        "type": "FETCH_PRICE",
        "data": {
          "product_url": "https://www.amazon.in/dp/B09XYZ1234"
        }
      }
    }
  }'
```

### Summary of Files to Touch

| Step | File | What to do |
|------|------|------------|
| 1 | `models/enums.py` | Add new enum values |
| 2 | `portals/<your_scraper>.py` | Write the scraping logic |
| 3 | `portals/handlers/<your_handlers>.py` | Register handler with decorator |
| 4 | `portals/handlers/__init__.py` | Import your handler module |
| 5 | `models/schemas.py` | Add request/response validation |
| 6 | Test via `curl` or Swagger UI | Verify end-to-end |

## Local Development

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install --with-deps chromium

# Run the server
python app.py
# Server starts at http://localhost:5001
# Swagger UI at http://localhost:5001/api/docs
```

## Deployment

See [infra/deployment.md](infra/deployment.md) for GCP VM setup and [infra/infrastructure.md](infra/infrastructure.md) for load balancer configuration.
