import json
import re
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from curl_cffi import requests
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from config import GROQ_API_KEY, GROQ_MODEL_NAME
from models.enums import EventTypeEnum

IVOLUNTEER_BASE_URL = "https://www.ivolunteer.in"

# Placeholder image when the opportunity has no image
_PLACEHOLDER_IMAGE = (
    "https://cdn0.handsonconnect.org/00006c/images/__thumbs/"
    "Square%20logo_green.png/Square%20logo_green__300x300.png"
)
IVOLUNTEER_SEARCH_API = f"{IVOLUNTEER_BASE_URL}/search/GetOpportunitiesSearchResultBlockListing"

# Pagination
_PAGE_SIZE = 48           # matches the site's default block size
_MAX_PAGES = 10           # safety cap

# IST = UTC+5:30
_IST = timezone(timedelta(hours=5, minutes=30))

_EVENT_TYPE_VALUES = [e.value for e in EventTypeEnum]

_BATCH_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "event_filter_batch.txt"
_LLM_BATCH_PROMPT = _BATCH_PROMPT_PATH.read_text(encoding="utf-8")

_BATCH_SIZE = 8   # events per LLM call

# Default Solr exclusion query (filters out sub-site partner listings)
_SOLR_EXCLUDE = (
    '-wsTag:"Subsite RBL" AND -wsTag:"Brillio-BringingSmiles" '
    'AND -wsTag:"Subsite-Welspun" AND -wsTag:"DAV-Sushrusha" '
    'AND -wsTag:"VFS Global" AND -wsTag:"ACTcorp"'
)


def _local_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def _make_session() -> requests.Session:
    return requests.Session(impersonate="chrome120")


# ---------------------------------------------------------------------------
# LLM: classify and filter events (batch) — same as mybharat_events
# ---------------------------------------------------------------------------

def _detect_batch_with_llm(
    event_texts: list[str],
    event_filter: str,
    category_filter: str,
) -> list[dict]:
    _default = [
        {"index": i, "select_event": False, "type": EventTypeEnum.OTHER.value}
        for i in range(len(event_texts))
    ]

    batch_block = "\n\n".join(
        f"--- Event {i} ---\n{text[:1500]}"
        for i, text in enumerate(event_texts)
    )

    try:
        llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=GROQ_MODEL_NAME)
        prompt_content = (
            _LLM_BATCH_PROMPT
            .replace("{event_types}", ", ".join(_EVENT_TYPE_VALUES))
            .replace("{event_filter}", event_filter)
            .replace("{category_filter}", category_filter)
            .replace("{events_batch}", batch_block)
        )
        response = llm.invoke([SystemMessage(content=prompt_content)])
        response_text = response.content.strip().strip("`").replace("json\n", "")
        print(f"[LLM-batch] Response length: {len(response_text)} chars")
        results = json.loads(response_text)

        if not isinstance(results, list):
            print("[LLM-batch] Response is not a list, falling back")
            return _default

        for r in results:
            if r.get("type") not in _EVENT_TYPE_VALUES:
                r["type"] = EventTypeEnum.OTHER.value

        return results

    except json.JSONDecodeError:
        print("[LLM-batch] Failed to parse response as JSON")
        return _default
    except Exception as e:
        print(f"[LLM-batch] Error: {e}")
        return _default


# ---------------------------------------------------------------------------
# Step 1: Fetch opportunities from iVolunteer search API
# ---------------------------------------------------------------------------

def _build_form_data(current_rows: int = 0) -> dict:
    """Build the form-encoded parameters for the search API."""
    return {
        "parameters[solrQuery]": _SOLR_EXCLUDE,
        "parameters[sort_by]": "Distance",
        "parameters[searchvo_date_from]": "",
        "parameters[searchvo_date_to]": "",
        "parameters[age_volunteer_specific]": "",
        "parameters[my_saved_searches]": "",
        "parameters[share_search_result]": "",
        "parameters[save_current_search_as]": "",
        "parameters[keyword]": "",
        "parameters[location-type]": "Address",
        "parameters[temporal_auxiliar]": "",
        "parameters[location]": "",
        "parameters[distance]": "Any",
        "parameters[address-suggestion-bias]": "in",
        "parameters[countRegular]": "0",
        "parameters[countTraining]": "0",
        "parameters[countFilled]": "0",
        "parameters[countEvents]": "0",
        "parameters[countOpp55]": "0",
        "parameters[language]": "en-IN",
        "currentRows": str(current_rows),
        "isSearch": "true",
        "blockId": "486",
    }


def _post_search(session: requests.Session, ipv4: str, current_rows: int) -> dict:
    """POST to the iVolunteer search API and return parsed JSON."""
    form_data = _build_form_data(current_rows)
    kwargs = dict(
        data=urlencode(form_data),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": IVOLUNTEER_BASE_URL,
            "Referer": f"{IVOLUNTEER_BASE_URL}/search",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=15,
    )
    if ipv4 and not ipv4.startswith("127."):
        kwargs["interface"] = ipv4

    resp = session.post(IVOLUNTEER_SEARCH_API, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _fetch_all_opportunities(session: requests.Session, ipv4: str) -> list[dict]:
    """Paginate through all opportunities."""
    all_opps: list[dict] = []
    page = 0

    while page < _MAX_PAGES:
        current_rows = page * _PAGE_SIZE
        data = _post_search(session, ipv4, current_rows)

        opps = data.get("opportunities", [])
        all_opps.extend(opps)

        total = data.get("total", 0)
        print(f"[iVolunteer] page {page + 1}: got {len(opps)} opportunities (total={total})")

        if not opps or len(all_opps) >= total:
            break
        page += 1

    return all_opps


# ---------------------------------------------------------------------------
# Step 2: Parse opportunity into standard event dict
# ---------------------------------------------------------------------------

def _parse_datetime(iso_str: str | None) -> str | None:
    """Normalise StartDateTimeValue to ISO 8601 UTC."""
    if not iso_str:
        return None
    try:
        # Already in ISO format from API (e.g. "2026-04-04T11:00:00Z")
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None


def _parse_end_date(end_date_str: str | None, start_iso: str | None) -> str | None:
    """
    Parse endDate from dd-MM-yy format (e.g. '04-04-26') to ISO 8601 UTC.
    Falls back to start_iso if parsing fails.
    """
    if not end_date_str:
        return start_iso
    try:
        dt = datetime.strptime(end_date_str, "%d-%m-%y")
        # Treat as end-of-day IST
        dt_ist = dt.replace(hour=23, minute=59, second=59, tzinfo=_IST)
        dt_utc = dt_ist.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return start_iso


def _strip_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _build_event_text(opp: dict) -> str:
    """Build a human-readable text summary for LLM classification."""
    start = opp.get("StartDateTimeValue", "")
    end = opp.get("endDate", "")
    parts = [
        f"Event Name: {opp.get('Title', '')}",
        f"Organisation: {opp.get('OrganizationName', '')}",
        f"Location: {opp.get('Location', '')}",
        f"Type: {opp.get('TypeIndicator', '')}",
        f"Duration: {opp.get('Duration', '')}",
        f"Date: {start} to {end}",
        f"Ongoing: {'yes' if opp.get('isOngoing') else 'no'}",
        f"Spots Available: {opp.get('SpotsAvailable', '')}",
    ]
    desc = opp.get("Description", "")
    if desc:
        parts.append(f"Description: {_strip_html(desc)}")
    # TimeColumnDataAriaLabel often has structured date/time info
    aria = opp.get("TimeColumnDataAriaLabel", "")
    if aria:
        parts.append(f"Schedule: {_strip_html(aria)}")
    return "\n".join(parts)


def _parse_opportunity(opp: dict) -> dict:
    """Transform a raw API opportunity into our standard event dict."""
    start_time = _parse_datetime(opp.get("StartDateTimeValue"))
    end_time = _parse_end_date(opp.get("endDate"), start_time)

    link = opp.get("OccurrenceUrl") or ""
    if link and not link.startswith("http"):
        link = f"{IVOLUNTEER_BASE_URL}{link}"

    image = opp.get("ImageURL") or None

    address = (opp.get("Location") or "").strip() or None

    return {
        "name": opp.get("Title"),
        "image": image if image else _PLACEHOLDER_IMAGE,
        "portal": "IVOLUNTEERIN",
        "start_time": start_time,
        "end_time": end_time,
        "address": address,
        "link": link,
        "organisation": opp.get("OrganizationName") or "iVolunteer",
        "type": EventTypeEnum.OTHER.value,
    }


# ---------------------------------------------------------------------------
# Step 3: Enrich events with missing addresses from the detail page
# ---------------------------------------------------------------------------

_LOCATION_PATTERNS = [
    re.compile(r"📍\s*Location\s*[:\-–]\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*Location\s*[:\-–]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:^|\n)\s*Where\s*[:\-–]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:^|\n)\s*Venue\s*[:\-–]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:^|\n)\s*Address\s*[:\-–]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    # "📍 Mode: In-person (locations across Bengaluru)" -> extract city from parenthetical
    re.compile(r"📍[^\n]*\(locations?\s+(?:across|in|around)\s+([^)]+)\)", re.IGNORECASE),
    # "locations across <City>"
    re.compile(r"locations?\s+(?:across|in|around)\s+(\w[\w\s,]+)", re.IGNORECASE),
]

# Strings that indicate the match is not a real address
_ADDRESS_REJECT = {"mode", "in-person", "online", "virtual", "remote", "flexible", "tbd", "tba"}


def _extract_address_from_text(text: str) -> str | None:
    """Try to extract a location from free-form description text."""
    for pattern in _LOCATION_PATTERNS:
        m = pattern.search(text)
        if m:
            addr = m.group(1).strip().rstrip(".•")
            if not addr or len(addr) <= 3:
                continue
            # Reject false positives like "Mode:", "In-person", "Online"
            first_word = addr.split(":")[0].split(",")[0].split("(")[0].strip().lower()
            if first_word in _ADDRESS_REJECT:
                continue
            if "to be shared" in addr.lower() or "to be confirmed" in addr.lower():
                continue
            return addr
    return None


def _scrape_address_from_detail(session: requests.Session, ipv4: str, url: str) -> str | None:
    """Fetch the opportunity detail page and extract the address.

    Tries three sources in order:
    1. Hidden input.occurrence-location-name
    2. Location patterns in the description text (📍, Location:, Where:, etc.)
    """
    try:
        kwargs = dict(timeout=15)
        if ipv4 and not ipv4.startswith("127."):
            kwargs["interface"] = ipv4
        resp = session.get(url, **kwargs)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Structured hidden input
        loc_input = soup.find("input", class_="occurrence-location-name")
        if loc_input:
            val = (loc_input.get("value") or "").strip()
            if val:
                return val

        # 2. Parse description body for location patterns
        body = soup.find("div", id="content-page")
        if body:
            text = body.get_text("\n", strip=True)
            addr = _extract_address_from_text(text)
            if addr:
                return addr

    except Exception as e:
        print(f"[iVolunteer] Failed to scrape address from {url}: {e}")
    return None


def _enrich_missing_addresses(
    session: requests.Session, ipv4: str, events: list[dict]
) -> None:
    """For events with no address, attempt to scrape it from the detail page."""
    for event in events:
        if event.get("address"):
            continue
        link = event.get("link")
        if not link:
            continue
        address = _scrape_address_from_detail(session, ipv4, link)
        if address:
            print(f"[iVolunteer] Enriched address for '{event['name']}': {address}")
            event["address"] = address


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_ivolunteer_events(category_filter: str = "", event_filter: str = "") -> dict:
    """
    Fetch volunteering opportunities from iVolunteer.in.

    1. Calls the iVolunteer search API to fetch all opportunities (paginated).
    2. Uses LLM to filter events matching event_filter / category_filter
       and classify their type.
    3. Returns structured event dicts for matching events.

    Args:
        category_filter: Category keywords for LLM filtering
        event_filter: Event keywords for LLM filtering

    Returns:
        {"events": [list of event dicts]}
    """
    try:
        ipv4 = _local_ipv4()
        session = _make_session()

        raw_opps = _fetch_all_opportunities(session, ipv4)

        if not raw_opps:
            return {"events": []}

        # De-duplicate by SID
        seen_ids: set[str] = set()
        unique_opps: list[dict] = []
        for opp in raw_opps:
            sid = opp.get("SID")
            if sid and sid in seen_ids:
                continue
            seen_ids.add(sid)
            unique_opps.append(opp)

        use_llm = bool(event_filter or category_filter)
        events = []

        if use_llm:
            total = len(unique_opps)
            for start in range(0, total, _BATCH_SIZE):
                batch = unique_opps[start : start + _BATCH_SIZE]
                batch_texts = [_build_event_text(o) for o in batch]

                print(f"[LLM-batch] Processing opportunities {start + 1}-{start + len(batch)} of {total}")
                results = _detect_batch_with_llm(batch_texts, event_filter, category_filter)

                result_map = {r["index"]: r for r in results}
                for i, opp in enumerate(batch):
                    verdict = result_map.get(i, {"select_event": False})
                    if not verdict.get("select_event", False):
                        continue
                    event = _parse_opportunity(opp)
                    event["type"] = verdict.get("type", EventTypeEnum.OTHER.value)
                    events.append(event)

            print(f"[LLM-batch] {len(events)} events matched out of {total}")
        else:
            events = [_parse_opportunity(o) for o in unique_opps]

        # Enrich events that have no address by scraping the detail page
        _enrich_missing_addresses(session, ipv4, events)

        # Drop events that still have no address after enrichment
        before = len(events)
        events = [e for e in events if e.get("address")]
        if before != len(events):
            print(f"[iVolunteer] Dropped {before - len(events)} events with no address")

        return {"events": events}

    except Exception as e:
        return {"events": [], "error": f"Unexpected error: {str(e)}"}
