"""Home-page payload -> classified events, without a database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from afterparty.sync import event_image, events_from_home, needs_guest_pull, safe_socials

from .conftest import HOME, ME


def roles():
    return {e.id: e.role for e in events_from_home(HOME, ME)}


def test_buckets_dedupe_and_roles():
    r = roles()
    assert set(r) == {"ev-past", "ev-wait", "ev-host", "ev-next", "ev-mine-next"}
    assert r["ev-past"] == "attended"
    assert r["ev-host"] == "hosting"
    # In the past bucket, but you never got in: not attended.
    assert r["ev-wait"] == "waitlisted"
    # Approved for a future event: going, never attended.
    assert r["ev-next"] == "going"
    # Hosting wins over dates; the API decides "met" by date (see test_api).
    assert r["ev-mine-next"] == "hosting"


def test_newest_first():
    ids = [e.id for e in events_from_home(HOME, ME)]
    assert ids[:2] == ["ev-mine-next", "ev-next"]


def test_event_image_prefers_imgix_path():
    url = event_image({"image": {"upload": {"path": "/external/user/x/abc"}}})
    assert url.startswith("https://partiful.imgix.net/external/user/x/abc?")
    assert event_image({}) is None


def test_settled_past_events_are_not_repulled():
    from afterparty.core.models import Event

    now = datetime.now(UTC)
    old = Event(id="a", end_date=(now - timedelta(days=30)).isoformat())
    fresh = Event(id="b", end_date=(now - timedelta(hours=5)).isoformat())
    pulled = now - timedelta(days=1)
    assert needs_guest_pull(old, None, full=False)  # never pulled
    assert not needs_guest_pull(old, pulled, full=False)  # settled
    assert needs_guest_pull(old, pulled, full=True)  # forced
    assert needs_guest_pull(fresh, pulled, full=False)  # still settling
    # Pulled only before the event (an RSVP list): pull again even long after.
    assert needs_guest_pull(old, now - timedelta(days=31), full=False)


def test_social_links_must_point_at_their_platform():
    assert safe_socials(
        {
            "twitter": "https://x.com/ada",
            "instagram": "https://phish.example/instagram",
            "linkedin": "https://www.linkedin.com/in/ada",
            "facebook": "javascript:alert(1)",
        }
    ) == {"twitter": "https://x.com/ada", "linkedin": "https://www.linkedin.com/in/ada"}
    assert event_image({"image": {"url": "https://tracker.example/pixel.gif"}}) is None


def test_refresh_errors_only_fatal_when_the_session_is_dead():
    import httpx
    import pytest

    from afterparty.partiful_api import PartifulApiError, PartifulAuthError, refresh

    def client_returning(status, message):
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(status, json={"error": {"message": message}})
            )
        )

    with pytest.raises(PartifulAuthError):
        refresh("rt", "key", client_returning(400, "INVALID_REFRESH_TOKEN"))
    with pytest.raises(PartifulApiError):  # a referrer block is ours to fix, not the user's
        refresh("rt", "key", client_returning(403, "API_KEY_HTTP_REFERRER_BLOCKED"))
    with pytest.raises(PartifulApiError):
        refresh("rt", "key", client_returning(503, ""))
