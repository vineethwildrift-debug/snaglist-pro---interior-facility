import pytest

from snaglist_pro.conversational_filter import classify, is_snag
from snaglist_pro.parse_export import parse_whatsapp_text, filter_snag_records


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ok noted", False),
        ("thanks!", False),
        ("will check", False),
        ("roger, on it", False),
        ("crack in the wall near the window", True),
        ("water leak under the sink in the pantry", True),
        ("door handle broken on the fire escape stair", True),
        ("plumbing pipe behind wc pan", True),
    ],
)
def test_classify(text, expected):
    result = classify(text)
    assert result["is_snag"] is expected
    assert 0.0 <= result["score"] <= 1.0
    assert result["reason"]


def test_short_acknowledgement_not_snag():
    assert is_snag("ok") is False
    assert is_snag("roger") is False


def test_empty_and_media_only():
    assert classify("")["is_snag"] is False
    res = classify("IMG-20260725-WA0001.jpg (file attached)")
    assert res["is_snag"] is False
    assert res["score"] < 0.30  # media-only references have no description


def test_keyword_not_substring():
    # "crack" must not match the "ack" keyword; "behind" must not match "hi".
    assert classify("crack in the wall near the window")["is_snag"] is True
    assert classify("plumbing pipe behind wc pan")["is_snag"] is True


def test_parse_annotates_when_classify_enabled(sample_chat_text):
    records = parse_whatsapp_text(sample_chat_text, classify_conversations=True)
    assert records
    # At least some real snag message got flagged.
    assert any(r["is_snag"] for r in records)


def test_filter_snag_records_removes_chatter():
    records = parse_whatsapp_text(
        "[9/18/26, 6:05 PM] Nasar: ok noted\n"
        "[9/18/26, 6:06 PM] Nasar: crack in the wall near window\n",
        classify_conversations=True,
    )
    kept = filter_snag_records(records)
    assert len(kept) == 1
    assert kept[0]["message"] == "crack in the wall near window"
