import re

_UTM_PARAM_PATTERN = re.compile(r"&utm_[^&]*=[^&]*")


def strip_utm_params(url: str | None) -> str | None:
    """Strip utm_* tracking query params from a link.

    Mirrors the one-time cleanup already applied to existing DB rows:
        UPDATE events SET link = regexp_replace(link, '&utm_[^&]*=[^&]*', '', 'g')
        WHERE link LIKE '%utm_%';

    Apply to every scraped link before comparing against existing_links or
    returning it for saving, so new rows stay consistent with the cleaned-up ones.
    """
    if not url:
        return url
    return _UTM_PARAM_PATTERN.sub("", url)
