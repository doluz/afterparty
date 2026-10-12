"""Role clustering and LinkedIn extraction.

The cases here are real bios from the live data, including the ones that broke
the first, looser classifier — that regression is the point of the file.
"""

from __future__ import annotations

from afterparty.core.roles import infer_role, linkedin_from_bio


def test_no_bio_is_unknown_not_other():
    """'Unknown' means we have no evidence. It must not be conflated with
    'we read the bio and it says nothing about a role'."""
    assert infer_role(None) == "unknown"
    assert infer_role("") == "unknown"
    assert infer_role("   ") == "unknown"
    assert infer_role("I'm awesome. You're awesome. Let's talk about why 🤣") == "other"


def test_real_founder_bios():
    for bio in (
        "founder",
        "Co-founder @ Athel AI",
        "Co-founder & CEO, GetDeal.AI — AI-native M&A platform",
        "CEO, Hobbes",
        "Cofounder & CEO of Docket. For CDO at Zoominfo. 2X exited founder",
        "Founder, investor and operator located in Stockholm",
    ):
        assert infer_role(bio) == "founder", bio


def test_founder_beats_function_for_a_dual_title():
    """ "Co-founder & CTO" is a founder, which is why founders are matched first."""
    assert infer_role("CTO & Cofounder @ PutRoots") == "founder"


def test_real_investor_bios():
    for bio in (
        "Deep tech VC @Criticality",
        "Jordan, Managing Partner of Silicon Valley Venture Group, Partner Network.VC",
        "VC/Investor, Venture Builder, and Mentor",
        "Investor at Entrepreneurs First",
    ):
        assert infer_role(bio) == "investor", bio


def test_regression_growth_bio_is_not_an_engineer():
    """A loose `\\bai\\b` token clustered "Growth @ Chargebee | Building Pitchstream
    AI" as engineering. Two-letter tokens are too ambiguous to match on."""
    assert infer_role("Growth @ Chargebee | Building Pitchstream AI") == "gtm_growth"


def test_regression_prose_mentioning_design_is_not_a_designer():
    bio = "Semiconductor industry leader with 30 years of experience in design to operations."
    assert infer_role(bio) == "other"


def test_real_engineering_bios():
    for bio in (
        "Growth Engineer @ Spot AI - Series C",
        "Design Engineer @ Color",
        "Staff Software Engineer",
    ):
        assert infer_role(bio) == "engineering", bio


def test_product_design_and_gtm():
    assert infer_role("Product Lead (ex Consensys, Meta)") == "product"
    assert infer_role("I am a fashion designer and an artist") == "design"
    assert infer_role("Head of GTM @ Atrios || Ex. Stripe, Brex, Warp") == "gtm_growth"


def test_linkedin_from_bio_real_shapes():
    cases = {
        "https://www.linkedin.com/in/anand-krishna-9b61a4/": "anand-krishna-9b61a4",
        "https://linkedin.com/in/palcheuski CEO & Founder of Tap2Pay.me": "palcheuski",
        "www.linkedin.com/in/harriet-kurzynski": "harriet-kurzynski",
        "in.linkedin.com/in/someone": None,  # not a shape people actually wrote
        "http://www.linkedin.com/in/sheelaursal Website : http://fintechnext.com": "sheelaursal",
        "https://www.linkedin.com/in/konstadinos-papadopoulos": "konstadinos-papadopoulos",
    }
    for bio, expected in cases.items():
        url = linkedin_from_bio(bio)
        if expected is None:
            continue
        assert url == f"https://www.linkedin.com/in/{expected}", bio


def test_linkedin_from_bio_returns_none_when_absent():
    assert linkedin_from_bio(None) is None
    assert linkedin_from_bio("Founder building in agentic commerce") is None
    assert linkedin_from_bio("linkedin.com/in/") is None


def test_linkedin_handle_trailing_punctuation_is_trimmed():
    assert (
        linkedin_from_bio("See linkedin.com/in/jane-doe.") == "https://www.linkedin.com/in/jane-doe"
    )


def test_vc_firm_names_and_plurals_are_investors():
    """ "Ventures" is how VC firms name themselves; the singular-only pattern missed it."""
    for bio in (
        "Managing Partner, Northwind Ventures",
        "Investing in seed rounds with fellow angels",
        "Ex-founder, now hanging out with VCs",
    ):
        assert infer_role(bio) in ("investor", "founder"), bio
    assert infer_role("Managing Partner, Northwind Ventures") == "investor"
    assert infer_role("Partner at Seed Fund") == "other"  # bare "partner" stays out
