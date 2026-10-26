import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rbnt.rules import problems_in  # noqa: E402

PUBLIC = {"0x43a1dc107bbb06df266278056055ae7fc5bd2817"}


def broken(text):
    return sorted({p["rule"] for p in problems_in(text, PUBLIC)})


def test_public_address_passes_in_any_case():
    assert broken("pool 0x43A1DC107BBB06DF266278056055AE7FC5BD2817") == []


def test_other_address_fails():
    assert broken("someone at 0x" + "c3" * 20) == ["address"]


def test_hash_is_not_an_address():
    assert broken("tx 0x" + "c3" * 32) == []


def test_each_rule():
    assert broken("a – b") == ["dash"]
    assert broken("great \U0001F680") == ["emoji"]
    assert broken("RBNT is going to pump") == ["price"]
    assert broken("about $2 a coin") == ["price"]
    assert broken("Designed by somebody") == ["credit"]


def test_disclaimer_is_fine():
    assert broken("We make no price forecasts.") == []
