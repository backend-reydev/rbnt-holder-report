"""Chart styling from the Task Board brand kit (brand/tokens.json).

One accent only: brand red for the series that matters, slate neutrals for
everything else. Be Vietnam Pro for text, JetBrains Mono for numbers on axes.
"""

BRAND_RED = "#EF5350"
ACCENT_TEXT_LIGHT = "#B3272A"
INK = "#0F1A22"
INK_DIM = "#394853"
LINE = "#C3CDD4"
SURFACE = "#FFFFFF"
STEEL_DARK = "#1d3140"
# Slate steps for secondary series, darkest first.
NEUTRALS = ["#394853", "#596975", "#8fa1ad", "#C3CDD4"]

SANS = ["Be Vietnam Pro", "DejaVu Sans", "sans-serif"]
MONO = ["JetBrains Mono", "DejaVu Sans Mono", "monospace"]


def apply(plt):
    plt.rcParams.update({
        "font.family": SANS,
        "font.size": 11,
        "axes.edgecolor": LINE,
        "axes.labelcolor": INK_DIM,
        "axes.titlecolor": INK,
        "axes.titleweight": 600,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": LINE,
        "grid.linewidth": 0.6,
        "xtick.color": INK_DIM,
        "ytick.color": INK_DIM,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })
