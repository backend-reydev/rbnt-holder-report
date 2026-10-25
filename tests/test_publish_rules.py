import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rbnt.publish_rules import scan_text  # noqa: E402

NAMED = {"0x6ed1f491e2d31536d6561f6bdb2adc8f092a6076"}


def kinds(text):
    return {p["kind"] for p in scan_text(text, NAMED)}


def test_named_address_is_allowed_and_case_insensitive():
    assert kinds("WRBNT 0x6ED1F491E2D31536D6561F6BDB2ADC8F092A6076") == set()


def test_unlabelled_address_is_caught():
    assert kinds("a wallet 0x" + "ab" * 20) == {"address"}


def test_transaction_hash_is_not_an_address():
    assert kinds("tx 0x" + "ab" * 32) == set()


def test_dashes_emoji_price_and_credit():
    assert "dash" in kinds("one — two")
    assert "emoji" in kinds("up \U0001F680")
    assert "price" in kinds("RBNT will rise next month")
    assert "price" in kinds("worth $5 each")
    assert "credit" in kinds("Made by someone")


def test_disclaimer_wording_is_allowed():
    assert kinds("This report makes no price predictions.") == set()
