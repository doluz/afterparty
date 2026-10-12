"""Role clusters and LinkedIn extraction.

Two honest constraints shape this module:

1. **Partiful has no role field.** ``_tags`` holds only ``employee`` / ``vip`` /
   ``spammer``, and there is no LinkedIn field either. The only signal is the free
   -text ``bio``, which ~14% of guests fill in (404 of 2,843 on real data).
2. **Precision beats recall.** A wrong cluster is worse than no cluster, so a
   candidate must contain an explicit role word. Loose tokens (``ai``, ``ml``,
   ``pm``, ``bd``) were deliberately dropped after they classified
   "Growth @ Chargebee" as an engineer. Everything unmatched stays ``other``;
   guests with no bio are ``unknown``.

Bios are also where people paste their LinkedIn URL, which is the only
self-declared — and therefore trustworthy — source of a LinkedIn profile.
"""

from __future__ import annotations

import re

#: Ordered: first match wins, so seniority words come before function words.
#: "Co-founder & CTO" is a founder, "Growth Engineer" is engineering.
CLUSTERS: tuple[tuple[str, str], ...] = (
    (
        "founder",
        r"\bco-?founders?\b|\bfounders?\b|\bfounding\b|\bfounded\b|\bceo\b|\bowner\b"
        r"|\bchairman\b|\bentrepreneur\b",
    ),
    # "Managing Partner" is deliberately NOT a founder signal: on real data it is
    # a venture-group partner, and the investor pattern catches it correctly.
    # Bare "partner" is left out too — it matches law and accounting firms.
    (
        "investor",
        # Plurals matter: VC firms are "X Ventures", and bios say "VCs" and "angels".
        r"\binvestors?\b|\bventures?\b|\bvcs?\b|\bangels?\b|\bcapital\b"
        r"|limited partner",
    ),
    (
        "engineering",
        r"\bengineers?\b|\bengineering\b|\bdeveloper\b|\bcto\b|\bsde\b|\bswe\b|\bdevops\b"
        r"|\bsoftware\b|\bfull-?stack\b|\bbackend\b|\bfrontend\b"
        r"|machine learning|\bdata scientist\b",
    ),
    ("product", r"product (manager|management|lead|owner)|\bcpo\b|head of product"),
    ("design", r"\bdesigners?\b|\bdesign lead\b|\bux\b|product design"),
    (
        "gtm_growth",
        r"\bgtm\b|go-to-market|\bgrowth\b|\bmarketing\b|\bcmo\b|\bsales\b"
        r"|business development|partnerships|\brevenue\b",
    ),
)

_COMPILED = tuple((key, re.compile(pattern, re.IGNORECASE)) for key, pattern in CLUSTERS)

ROLE_LABELS = {
    "founder": "Founders",
    "investor": "Investors",
    "engineering": "Engineers",
    "product": "Product",
    "design": "Design",
    "gtm_growth": "GTM / Growth",
    "other": "Other",
    "unknown": "Unknown",
}

#: Presentation order and colours, shared with the HTML report.
ROLE_ORDER = (
    "founder",
    "investor",
    "engineering",
    "product",
    "design",
    "gtm_growth",
    "other",
    "unknown",
)
ROLE_COLORS = {
    "founder": "#6ee7ff",
    "investor": "#f0abfc",
    "engineering": "#4ade80",
    "product": "#fbbf24",
    "design": "#fb7185",
    "gtm_growth": "#a78bfa",
    "other": "#94a3b8",
    "unknown": "#5b6472",
}

LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/([A-Za-z0-9\-_%.]{2,80})", re.IGNORECASE
)


def infer_role(bio: str | None) -> str:
    """Cluster a guest from their bio. No bio -> ``unknown``."""
    if not bio or not bio.strip():
        return "unknown"
    text = bio.lower()
    for key, pattern in _COMPILED:
        if pattern.search(text):
            return key
    return "other"


def linkedin_from_bio(bio: str | None) -> str | None:
    """Pull a LinkedIn profile URL out of a bio, if the guest pasted one.

    This is the highest-confidence LinkedIn source there is: the person typed it
    themselves. Returns a normalised ``https://www.linkedin.com/in/<handle>``.
    """
    if not bio:
        return None
    match = LINKEDIN_RE.search(bio)
    if not match:
        return None
    handle = match.group(1).strip().strip(".,;").rstrip("/")
    if not handle:
        return None
    return f"https://www.linkedin.com/in/{handle}"
