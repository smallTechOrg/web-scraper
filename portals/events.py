import re
import json
import socket
from pathlib import Path
from datetime import datetime, timezone, timedelta
from curl_cffi import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from config import GROQ_API_KEY, GROQ_MODEL_NAME
from models.enums import EventTypeEnum

TEAMEVEREST_BASE_URL = "https://www.teameverest.ngo"
TEAMEVEREST_EVENTS_URL = f"{TEAMEVEREST_BASE_URL}/events"

# IST = UTC+5:30
_IST = timezone(timedelta(hours=5, minutes=30))

# data-inline-binding keys used by the site builder
_BINDING_NAME        = "dynamic_page_collection.Header Text"
_BINDING_DATE        = "dynamic_page_collection.Orientation Date Formula"
_BINDING_LOCATION    = "dynamic_page_collection.IPE Location (Formula)"
_BINDING_TIME_DESC   = "dynamic_page_collection.Time commitment Description\u200b"

_EVENT_TYPE_VALUES = [e.value for e in EventTypeEnum]

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "event_filter.txt"
_LLM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _local_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def _make_session() -> requests.Session:
    return requests.Session(impersonate="chrome120")


# ---------------------------------------------------------------------------
# LLM: classify and filter event
# ---------------------------------------------------------------------------

def _detect_info_with_llm(page_text: str, event_filter: str, category_filter: str) -> dict:
    """Use Groq LLM to decide if event matches filter and classify its type."""
    _default = {"select_event": False, "type": EventTypeEnum.OTHER.value}
    try:
        llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=GROQ_MODEL_NAME)
        prompt_content = (
            _LLM_PROMPT
            .replace("{event_types}", ", ".join(_EVENT_TYPE_VALUES))
            .replace("{event_filter}", event_filter)
            .replace("{category_filter}", category_filter)
            .replace("{event_content}", page_text[:6000])  # cap to avoid token overflow
        )
        response = llm.invoke([SystemMessage(content=prompt_content)])
        response_text = response.content.strip().strip("`").replace("json\n", "")
        print(f"[LLM] Response: {response_text}")
        result = json.loads(response_text)
        # Validate type is a known enum value
        if result.get("type") not in _EVENT_TYPE_VALUES:
            result["type"] = EventTypeEnum.OTHER.value
        return result
    except json.JSONDecodeError:
        print(f"[LLM] Failed to parse response as JSON")
        return _default
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return _default


# ---------------------------------------------------------------------------
# Step 1: Get in-person event detail URLs from the events list page
# ---------------------------------------------------------------------------

def _get_inperson_event_urls(html: str) -> list[str]:
    """Collect all unique in-person event URLs from the events page."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/in-person-volunteering/" not in href:
            continue
        url = href if href.startswith("http") else f"{TEAMEVEREST_BASE_URL}{href}"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# Step 2: Extract event details from a detail page
# ---------------------------------------------------------------------------

def _binding(soup: BeautifulSoup, key: str) -> str | None:
    """Get the text content of a span by its data-inline-binding value."""
    span = soup.find("span", attrs={"data-inline-binding": key})
    return span.get_text(strip=True) or None if span else None


def _meta(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", property=prop)
    return tag["content"].strip() if tag and tag.get("content") else None


def _parse_ist_to_iso(date_str: str) -> str | None:
    """
    Parse "March 14, 2026 | 10:00 am IST" → "2026-03-14T04:30:00.000Z"
    Strips IST label, treats as UTC+5:30, converts to UTC ISO 8601.
    """
    try:
        cleaned = date_str.replace(" IST", "").strip()
        parts = cleaned.split("|")
        date_part = parts[0].strip()        # "March 14, 2026"
        time_part = parts[1].strip() if len(parts) > 1 else "12:00 am"  # "10:00 am"
        dt = datetime.strptime(f"{date_part} {time_part}", "%B %d, %Y %I:%M %p")
        dt_ist = dt.replace(tzinfo=_IST)
        dt_utc = dt_ist.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None


def _extract_hours(time_desc: str) -> int:
    """Extract number of hours from 'commit 2 hours of your time' style text."""
    m = re.search(r"(\d+)\s+hours?", time_desc, re.IGNORECASE)
    return int(m.group(1)) if m else 2  # default 2 hours


def _add_hours_to_iso(iso: str, hours: int) -> str:
    """Add N hours to an ISO 8601 UTC string."""
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
    return (dt + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _event_image_url(soup: BeautifulSoup) -> str | None:
    """Resolve the event banner image URL. Returns a fresh signed URL each scrape."""
    for img in soup.find_all("img", attrs={"data-dm-image-path": True}):
        dm = img["data-dm-image-path"]
        if "airtableusercontent.com" in dm:
            return dm
    return _meta(soup, "og:image")


def _parse_event_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Name
    name = _binding(soup, _BINDING_NAME)
    if not name:
        og_title = _meta(soup, "og:title")
        if og_title and "|" in og_title:
            candidate = og_title.split("|")[0].strip()
            generic = {"volunteering opportunities", "in person volunteering", "events"}
            name = candidate if candidate.lower() not in generic else None
        if not name:
            slug = url.rstrip("/").split("/")[-1]
            name = slug.replace("-", " ").title()

    # Image: fresh signed URL (valid at scrape time — consumer should store promptly)
    image = _event_image_url(soup)

    # Canonical link
    link = _meta(soup, "og:url") or url

    # Organisation
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    organisation = "Team Everest"
    if "|" in title_text:
        organisation = title_text.split("|")[-1].strip()

    # Start / end time from date binding + duration
    start_time = None
    end_time = None
    date_text = _binding(soup, _BINDING_DATE)
    if date_text:
        start_time = _parse_ist_to_iso(date_text)
        if start_time:
            time_desc = _binding(soup, _BINDING_TIME_DESC) or ""
            hours = _extract_hours(time_desc)
            end_time = _add_hours_to_iso(start_time, hours)

    # Address (single-line from binding — no newline issues)
    address = _binding(soup, _BINDING_LOCATION)

    return {
        "name": name,
        "image": image,
        "portal": "TEAMEVEREST",
        "start_time": start_time,
        "end_time": end_time,
        "address": address,
        "link": link,
        "organisation": organisation,
        "type": "In Person Volunteering",
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_events(category_filter: str = "", event_filter: str = "") -> dict:
    try:
        ipv4 = _local_ipv4()
        session = _make_session()

        list_resp = session.get(TEAMEVEREST_EVENTS_URL, timeout=15, interface=ipv4)
        list_resp.raise_for_status()
        event_urls = _get_inperson_event_urls(list_resp.text)

        if not event_urls:
            return {"events": []}

        use_llm = bool(event_filter or category_filter)
        events = []
        for url in event_urls:
            # Step 2: fetch detail page
            detail_resp = session.get(url, timeout=15, interface=ipv4)
            if detail_resp.status_code != 200:
                continue

            html = detail_resp.text

            if use_llm:
                # Step 2a: LLM decides if event passes filter — skip scraping if not
                page_text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
                llm_result = _detect_info_with_llm(page_text, event_filter, category_filter)
                if not llm_result.get("select_event", False):
                    print(f"[LLM] Skipping {url} — did not match filter")
                    continue
                # Step 3: event passed — extract structured details and merge LLM type
                event = _parse_event_detail(html, url)
                event["type"] = llm_result.get("type", EventTypeEnum.OTHER.value)
            else:
                event = _parse_event_detail(html, url)

            events.append(event)

        return {"events": events}

    except Exception as e:
        return {"events": [], "error": f"Unexpected error: {str(e)}"}
