import re
import time

from langchain_groq import ChatGroq

_MIN_INTERVAL = 2.15   # seconds between calls → ~28 RPM, under Groq's 30 RPM on-demand limit
_last_call_time = 0.0


def invoke_llm(messages: list) -> object:
    """Call Groq LLM with rate limiting (2.15 s gap) and retry on 429 (up to 3 retries)."""
    global _last_call_time
    from config import GROQ_API_KEY, GROQ_MODEL_NAME

    for attempt in range(4):
        elapsed = time.time() - _last_call_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        try:
            llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=GROQ_MODEL_NAME)
            _last_call_time = time.time()
            return llm.invoke(messages)
        except Exception as e:
            msg = str(e).lower()
            if "rate_limit" in msg or "429" in msg:
                wait = _parse_retry_after(str(e), default=5.0 * (2 ** attempt))
                print(f"[LLM] Rate limited, waiting {wait:.1f}s (attempt {attempt + 1})")
                time.sleep(wait)
                if attempt == 3:
                    raise
            else:
                raise


def _parse_retry_after(error_msg: str, default: float) -> float:
    m = re.search(r"try again in (\d+\.?\d*)s", error_msg, re.IGNORECASE)
    return float(m.group(1)) + 0.5 if m else default


def fetch_existing_links(portal: str, backend_url: str | None = None) -> set[str]:
    """Return the set of event links already stored in the backend for the given portal.

    `backend_url` is passed per-request via the X-Backend-Url header (validated against
    ALLOWED_BACKEND_URLS — see api/web_scrap.py) since staging and production #local share
    this scraper deployment and each must dedupe against its own database. Returns an empty
    set on failure or when the header wasn't provided/valid, so callers can proceed without
    skipping anything.
    """
    url = backend_url
    if not url:
        return set()
    try:
        from curl_cffi import requests
        resp = requests.get(
            f"{url}/api/v1/events/links",
            params={"portal": portal},
            timeout=10,
        )
        if resp.ok:
            data = resp.json().get("data", [])
            print(f"[backend] {len(data)} existing links loaded for portal {portal}")
            return set(data)
        print(f"[backend] Failed to fetch existing links for {portal}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"[backend] Failed to fetch existing links for {portal}: {e}")
    return set()
