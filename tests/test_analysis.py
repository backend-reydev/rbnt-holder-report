import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rbnt import analysis as A  # noqa: E402
from rbnt import rlp  # noqa: E402

W = A.WEI


def test_band_index_uses_lower_bounds():
    edges = [1, 100, 1000]
    assert A.band_index(W, edges) == 0
    assert A.band_index(99 * W, edges) == 0
    assert A.band_index(100 * W, edges) == 1
    assert A.band_index(10 ** 6 * W, edges) == 2
    assert A.band_index(W // 2, edges) == -1


def test_gini_extremes():
    assert A.gini([5, 5, 5, 5]) == 0
    assert abs(A.gini([0, 0, 0, 100]) - 0.75) < 1e-12   # n=4, one holder has all
    assert A.gini([]) == 0


def test_top_share_and_count_to_half():
    vals = [50, 30, 10, 5, 5]
    assert A.top_share(vals, 1) == 0.5
    assert A.top_share(vals, 2) == 0.8
    assert A.count_to_half(vals) == 2         # 50 alone is not more than half
    assert A.count_to_half([60, 20, 20]) == 1


def test_lorenz_ends():
    pts = A.lorenz([1, 2, 3, 4], 4)
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (1.0, 1.0)
    assert abs(pts[2][1] - 0.3) < 1e-12        # smallest half holds 3 of 10


def test_classify_change():
    assert A.classify_change(100 * W, 102 * W) == "added"
    assert A.classify_change(100 * W, 100 * W + W // 2) == "steady"
    assert A.classify_change(100 * W, 98 * W) == "reduced"
    assert A.classify_change(100 * W, W // 10) == "exited"


def test_merge_small_never_leaves_a_small_band():
    rows = [{"lo": 1, "hi": 10, "n": 50}, {"lo": 10, "hi": 100, "n": 8}, {"lo": 100, "hi": 1000, "n": 3},
            {"lo": 1000, "hi": None, "n": 1}]
    out = A.merge_small(rows, "n", 5)
    assert all(r["n"] >= 5 for r in out)
    assert sum(r["n"] for r in out) == 62
    assert out[-1]["hi"] is None


def test_rlp_finds_addresses():
    addr = bytes.fromhex("11" * 20)
    # list [ list [ 20-byte string ], 0x05 ]
    inner = bytes([0x80 + 20]) + addr
    lst = bytes([0xc0 + len(inner)]) + inner
    data = bytes([0xc0 + len(lst) + 1]) + lst + b"\x05"
    assert rlp.addresses("0x" + data.hex()) == ["0x" + "11" * 20]
    assert rlp.addresses("0x") == []
