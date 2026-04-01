import json
import re
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi import requests
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from config import GROQ_API_KEY, GROQ_MODEL_NAME
from models.enums import EventTypeEnum

MYBHARAT_SEARCH_API = "https://search-api-prod.mybharats.in/events"
MYBHARAT_CDN_URL = "https://cdn-prod.mybharats.in/"
MYBHARAT_BASE_URL = "https://mybharat.gov.in"

# Pagination
_PAGE_LIMIT = 12          # matches the site's default page size
_MAX_PAGES  = 20          # safety cap to avoid runaway pagination

# IST = UTC+5:30
_IST = timezone(timedelta(hours=5, minutes=30))

_EVENT_TYPE_VALUES = [e.value for e in EventTypeEnum]

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "event_filter.txt"
_LLM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_BATCH_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "event_filter_batch.txt"
_LLM_BATCH_PROMPT = _BATCH_PROMPT_PATH.read_text(encoding="utf-8")

_BATCH_SIZE = 8   # events per LLM call


def _local_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def _make_session() -> requests.Session:
    return requests.Session(impersonate="chrome120")


# ---------------------------------------------------------------------------
# LLM: classify and filter events (batch)
# ---------------------------------------------------------------------------

def _detect_batch_with_llm(
    event_texts: list[str],
    event_filter: str,
    category_filter: str,
) -> list[dict]:
    """
    Send a batch of event summaries to the LLM in a single call.
    Returns a list of {"index": int, "select_event": bool, "type": str} dicts.
    On failure, returns all-reject defaults.
    """
    _default = [
        {"index": i, "select_event": False, "type": EventTypeEnum.OTHER.value}
        for i in range(len(event_texts))
    ]

    # Build the numbered events block
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

        # Normalise: ensure every entry has valid type
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
# Step 1: Fetch events from the MY Bharat search API
# ---------------------------------------------------------------------------

def _build_query(tab: str = "Upcoming", page: int = 1) -> dict:
    """
    Build the Elasticsearch-style query body for the MY Bharat search API.
    Fetches ALL volunteering events (type=vo) — filtering is done later by LLM.
    """
    today = datetime.now(_IST).strftime("%Y-%m-%d")

    filters = [
        {"term": {"type": "vo"}},
    ]

    if tab == "Upcoming":
        filters.append({"range": {"event_from_date": {"gt": today}}})
    elif tab == "Ongoing":
        filters.append({"range": {"event_to_date": {"gte": today}}})
        filters.append({"range": {"event_from_date": {"lte": today}}})
    elif tab == "Past":
        filters.append({"range": {"event_to_date": {"lt": today}}})

    return {
        "query": {
            "bool": {
                "must": filters,
                "should": [],
            }
        },
        "sort": [{"event_from_date": {"order": "asc"}}],
        "page": str(page),
        "limit": _PAGE_LIMIT,
    }


def _post_search(session: requests.Session, ipv4: str, body: dict) -> dict:
    """POST to the MY Bharat search API and return the parsed JSON response."""
    kwargs = dict(
        json=body,
        headers={
            "Content-Type": "application/json",
            "Origin": MYBHARAT_BASE_URL,
            "Referer": f"{MYBHARAT_BASE_URL}/",
        },
        timeout=15,
    )
    if ipv4 and not ipv4.startswith("127."):
        kwargs["interface"] = ipv4

    resp = session.post(MYBHARAT_SEARCH_API, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _fetch_all_events(session: requests.Session, ipv4: str, tab: str = "Upcoming") -> list[dict]:
    """Paginate through ALL events for a given tab and return raw records."""
    all_records: list[dict] = []
    page = 1

    while page <= _MAX_PAGES:
        body = _build_query(tab, page=page)
        data = _post_search(session, ipv4, body)

        records = data.get("records", [])
        sources = [r["_source"] for r in records if "_source" in r]
        all_records.extend(sources)

        total = data.get("total", 0)
        print(f"[MY Bharat] {tab} page {page}: got {len(sources)} records (total={total})")

        # Stop when we've fetched everything or the page came back empty
        if not sources or len(all_records) >= total:
            break
        page += 1

    return all_records


# ---------------------------------------------------------------------------
# Step 2: Parse event details from a raw API record
# ---------------------------------------------------------------------------

def _image_url(image_path: str | None) -> str | None:
    """Resolve full CDN image URL from the image_path field."""
    if not image_path:
        return None
    return f"{MYBHARAT_CDN_URL}events/{image_path}"


def _parse_datetime_ist(date_str: str, time_str: str | None) -> str | None:
    """
    Combine date ('2026-03-28') and time ('10:00:00') into ISO 8601 UTC.
    Treats input as IST (UTC+5:30).
    """
    try:
        if time_str:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt_ist = dt.replace(tzinfo=_IST)
        dt_utc = dt_ist.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None


def _strip_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _build_event_text(record: dict) -> str:
    """Build a human-readable text summary of the event for LLM classification."""
    parts = [
        f"Event Name: {record.get('event_name', '')}",
        f"Organisation: {record.get('org_name', '')}",
        f"Partner: {record.get('partner_name', '')}",
        f"Location: {record.get('event_address', '')} {record.get('district', '')} {record.get('state', '')}",
        f"Date: {record.get('event_from_date', '')} to {record.get('event_to_date', '')}",
    ]
    desc = record.get("description", "")
    if desc:
        parts.append(f"Description: {_strip_html(desc)}")

    activities = record.get("geteventactivity", [])
    if activities:
        act_names = [a.get("name", "") for a in activities if a.get("name")]
        if act_names:
            parts.append(f"Activities: {', '.join(act_names)}")

    return "\n".join(parts)


def _build_address(record: dict) -> str | None:
    """Build a single-line address from available location fields."""
    parts = []
    addr = record.get("event_address") or record.get("event_address_1")
    if addr:
        parts.append(addr.strip())
    district = record.get("district")
    if district:
        parts.append(district)
    state = record.get("state")
    if state:
        parts.append(state)
    pincode = record.get("nyf_event_pincode")
    if pincode:
        parts.append(str(pincode))
    return ", ".join(parts) if parts else None


def _parse_event_record(record: dict) -> dict:
    """Transform a raw API record into our standard event dict."""
    start_time = _parse_datetime_ist(
        record.get("event_from_date", ""),
        record.get("event_start_time"),
    )
    end_time = _parse_datetime_ist(
        record.get("event_to_date", ""),
        record.get("event_end_time"),
    )

    event_link = record.get("event_link") or ""
    if not event_link:
        # Construct fallback link
        slug = (record.get("event_name") or "").replace(" ", "-")
        event_id = record.get("id", "")
        event_link = f"{MYBHARAT_BASE_URL}/pages/event_detail?event_name={slug}&key={event_id}"

    return {
        "name": record.get("event_name"),
        "image": _image_url(record.get("image_path")),
        "portal": "MYBHARATGOVIN",
        "start_time": start_time,
        "end_time": end_time,
        "address": _build_address(record),
        "link": event_link,
        "organisation": record.get("org_name") or record.get("partner_name") or "MY Bharat",
        "type": EventTypeEnum.OTHER.value,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_mybharat_events(category_filter: str = "", event_filter: str = "") -> dict:
    """
    Fetch volunteering events from the MY Bharat portal.

    1. Calls the MY Bharat search API to fetch ALL upcoming / ongoing events
       (paginates through every page).
    2. Uses LLM to filter events matching event_filter / category_filter
       and classify their type.
    3. Returns structured event dicts for matching events.

    Args:
        category_filter: Category keywords for LLM filtering (e.g. "civic engagement")
        event_filter: Event keywords for LLM filtering (e.g. "cleanliness drive")

    Returns:
        {"events": [list of event dicts]}
    """
    try:
        ipv4 = _local_ipv4()
        session = _make_session()

        # Fetch upcoming + ongoing events (all pages)
        raw_events = []
        for tab in ("Upcoming", "Ongoing"):
            raw_events.extend(_fetch_all_events(session, ipv4, tab))

        if not raw_events:
            return {"events": []}

        # De-duplicate by event id
        seen_ids: set[int] = set()
        unique_events: list[dict] = []
        for record in raw_events:
            eid = record.get("id")
            if eid and eid in seen_ids:
                continue
            seen_ids.add(eid)
            unique_events.append(record)

        use_llm = bool(event_filter or category_filter)
        events = []

        if use_llm:
            # Process in batches to minimise LLM calls
            total = len(unique_events)
            for start in range(0, total, _BATCH_SIZE):
                batch = unique_events[start : start + _BATCH_SIZE]
                batch_texts = [_build_event_text(r) for r in batch]

                print(f"[LLM-batch] Processing events {start+1}-{start+len(batch)} of {total}")
                results = _detect_batch_with_llm(batch_texts, event_filter, category_filter)

                # Map results back by index
                result_map = {r["index"]: r for r in results}
                for i, record in enumerate(batch):
                    verdict = result_map.get(i, {"select_event": False})
                    if not verdict.get("select_event", False):
                        continue
                    event = _parse_event_record(record)
                    event["type"] = verdict.get("type", EventTypeEnum.OTHER.value)
                    events.append(event)

            print(f"[LLM-batch] {len(events)} events matched out of {total}")
        else:
            events = [_parse_event_record(r) for r in unique_events]

        return {"events": events}

    except Exception as e:
        return {"events": [], "error": f"Unexpected error: {str(e)}"}
