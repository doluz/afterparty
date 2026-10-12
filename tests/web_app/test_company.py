"""company_from_bio: the enrichment hint in the CSV export."""

import pytest

from afterparty.people import company_from_bio


@pytest.mark.parametrize(
    ("bio", "company"),
    [
        ("Co-founder & CEO at Saltbox. Building robotics.", "Saltbox"),
        ("CEO at Lumen", "Lumen"),
        ("Partner @ Parcel Ventures, pre-seed and seed", "Parcel Ventures"),
        ("Engineer at Big Co Labs and more", "Big Co Labs"),
        ("Founder at Kiln Inc. Hiring engineers.", "Kiln Inc"),
        ("Here for the snacks and the conversations.", ""),
        (None, ""),
    ],
)
def test_company_from_bio(bio, company):
    assert company_from_bio(bio) == company
