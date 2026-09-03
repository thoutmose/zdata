"""Build a real emote image URL from `(service, emote_id)`.

The warehouse's emote catalog (`stg.stg_bronze__emote_catalog`) has no image
URL column — only the id each service assigned the emote. Every service that
feeds the catalog publishes a stable, public CDN URL scheme keyed by that same
id, so the URL is built here rather than stored.
"""

from __future__ import annotations

_CDN_BY_SERVICE = {
    "twitch": "https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/dark/3.0",
    "7tv": "https://cdn.7tv.app/emote/{id}/4x.webp",
    "bttv": "https://cdn.betterttv.net/emote/{id}/3x.webp",
    "ffz": "https://cdn.frankerfacez.com/emote/{id}/4",
}


def emote_image_url(service: str, emote_id: str) -> str | None:
    """Return the CDN image URL for one emote, or `None` for an unknown service.

    Args:
        service: The catalog's `service` value (`"twitch"`, `"7tv"`, `"bttv"`, or `"ffz"`).
        emote_id: The catalog's `emote_id` value for that service.

    Returns:
        A CDN image URL, or `None` if `service` isn't one of the four known providers.
    """
    template = _CDN_BY_SERVICE.get(service)
    return template.format(id=emote_id) if template else None
