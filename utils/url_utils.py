from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def strip_utm_params(url: str | None) -> str | None:
    """Strip utm_* tracking query params from a link.

    Mirrors the one-time cleanup already applied to existing DB rows:
        UPDATE events SET link = regexp_replace(link, '&utm_[^&]*=[^&]*', '', 'g')
        WHERE link LIKE '%utm_%';

    Unlike that one-time regex (which only matched non-leading "&utm_..." params),
    this also strips a leading "?utm_...=..." param, so links that start with a
    utm param get cleaned too.

    Apply to every scraped link before comparing against existing_links or
    returning it for saving, so new rows stay consistent with the cleaned-up ones.
    """
    if not url:
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept_params = [
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith("utm_")
    ]
    new_query = urlencode(kept_params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
