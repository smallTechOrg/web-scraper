from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

SMARTONE_URL = "https://www.smartoneblr.com/WssBBMPComplaintRequestDetails.htm"

class ComplaintNotFound(Exception):
    pass

def _extract_panel_data(panel):
    data = {}
    form_groups = panel.find_all("div", class_="form-group")
    for group in form_groups:
        label_tag = group.find("label")
        if not label_tag:
            continue
        value_container = label_tag.find_next("div")
        if not value_container:
            continue
        key = label_tag.get_text(strip=True).replace("\xa0", " ")
        value = value_container.get_text(strip=True)
        if key:
            data[key] = value
        img = group.find("img")
        if img and img.get("src"):
            data["Image URL"] = img["src"]
    return data

def _parse_complaint_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {"complaint_details": {}, "staff_details": {}}
    panels = soup.find_all("div", class_="panel panel-primary")

    print(f"[DEBUG] Found {len(panels)} primary panels")  # <-- debug

    if len(panels) < 2:
        raise ComplaintNotFound("Complaint details not found. Invalid ID?")
    
    result["complaint_details"] = _extract_panel_data(panels[0])
    result["staff_details"] = _extract_panel_data(panels[1])
    
    print(f"[DEBUG] Extracted complaint_details keys: {list(result['complaint_details'].keys())}")
    print(f"[DEBUG] Extracted staff_details keys: {list(result['staff_details'].keys())}")

    if not result["complaint_details"]:
        raise ComplaintNotFound("No complaint data extracted.")
    return result

def fetch_complaint_status(complaint_id: str) -> dict:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # <-- show browser for debugging
            context = browser.new_context()
            page = context.new_page()

            print(f"[DEBUG] Opening URL: {SMARTONE_URL}")
            page.goto(SMARTONE_URL, timeout=30000)

            print(f"[DEBUG] Filling complaint ID: {complaint_id}")
            page.fill("#complainantNo", complaint_id)

            print("[DEBUG] Clicking search button")
            page.click("button:has-text('search')")

            # Wait for the first panel to have some content
            print("[DEBUG] Waiting for complaint details panel to appear")
            page.wait_for_selector(
                f"div.panel.panel-primary:nth-of-type(1) div.col-sm-6:has-text('{complaint_id}')",
                timeout=15000
            )

            html = page.content()
            print(f"[DEBUG] HTML length after search: {len(html)}")  # <-- debug

            browser.close()

        parsed_data = _parse_complaint_details(html)
        return {"success": True, "complaint_id": complaint_id, **parsed_data}

    except PlaywrightTimeout:
        return {"success": False, "complaint_id": complaint_id,
                "error": "Request timed out while fetching complaint details."}
    except ComplaintNotFound as e:
        return {"success": False, "complaint_id": complaint_id, "error": str(e)}
    except Exception as e:
        return {"success": False, "complaint_id": complaint_id, "error": f"Unexpected error: {str(e)}"}