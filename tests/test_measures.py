import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rbnt import measures  # noqa: E402
from rbnt.rlp import twenty_byte_values  # noqa: E402

R = measures.ONE_RBNT


def test_band_of_uses_floors():
    floors = [1, 10, 100]
    assert [measures.band_of(x * R, floors) for x in (1, 9, 10, 99, 100, 5000)] == [0, 0, 1, 1, 2, 2]
    assert measures.band_of(R // 3, floors) == -1


def test_band_names_read_naturally():
    assert measures.band_name(1, 100) == "1 up to 100"
    assert measures.band_name(10_000_000, None) == "10 million or more"
    assert measures.band_name(0, 1000) == "Under 1,000"


def test_share_of_top_and_majority():
    amounts = [40, 25, 20, 10, 5]
    assert measures.share_of_top(amounts, 1) == 0.40
    assert measures.share_of_top(amounts, 3) == 0.85
    assert measures.holders_for_majority(amounts) == 2          # 40 alone is not more than half
    assert measures.holders_for_majority([70, 20, 10]) == 1


def test_gini_index():
    assert measures.gini_index([3, 3, 3]) == 0
    assert abs(measures.gini_index([0, 0, 0, 0, 8]) - 0.8) < 1e-12    # one of five holds everything
    assert measures.gini_index([]) == 0


def test_lorenz_points_run_corner_to_corner():
    pts = measures.lorenz_points([2, 2, 4, 12], 4)
    assert pts[0] == (0.0, 0.0) and pts[-1] == (1.0, 1.0)
    assert pts[2] == (0.5, 0.2)                                # the smaller half holds 4 of 20


def test_outcome_labels():
    assert measures.outcome(200 * R, 203 * R) == "up"
    assert measures.outcome(200 * R, 201 * R) == "flat"
    assert measures.outcome(200 * R, 197 * R) == "down"
    assert measures.outcome(200 * R, R // 2) == "emptied"


def test_fold_small_bands_keeps_totals():
    bands = [{"floor": 1, "ceiling": 10, "n": 40}, {"floor": 10, "ceiling": 100, "n": 6},
             {"floor": 100, "ceiling": 1000, "n": 2}, {"floor": 1000, "ceiling": None, "n": 4}]
    folded = measures.fold_small_bands(bands, "n", 5)
    assert [b["n"] for b in folded] == [40, 6, 6]
    assert folded[-1]["ceiling"] is None


def test_twenty_byte_values_from_nested_rlp():
    value = bytes(range(1, 21))
    inner = bytes([0x80 + 20]) + value
    nested = bytes([0xc0 + len(inner)]) + inner
    outer = bytes([0xc0 + len(nested) + 1]) + nested + b"\x07"
    assert twenty_byte_values("0x" + outer.hex()) == ["0x" + value.hex()]
    assert twenty_byte_values("0x") == []
