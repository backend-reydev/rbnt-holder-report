"""How numbers are written in the report text and tables."""


def grouped(v):
    """12,345,678"""
    return f"{v:,.0f}"


def words(v, places=1):
    """Size in words: 754.8 million, 500 million, 1.74 billion, 12,345, 5.84."""
    size = abs(v)
    if size >= 1e9:
        return f"{v / 1e9:,.2f} billion"
    if size >= 1e6:
        text = f"{v / 1e6:,.{places}f}"
        return f"{text[:-2] if text.endswith('.0') else text} million"
    if size >= 100:
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def plus(v, writer=grouped):
    """Signed: +1,234 or -1,234."""
    return ("+" if v > 0 else "") + writer(v)


def percent(v, places=1):
    return f"{v:.{places}f}%"


def points(v):
    return f"{v:+.1f} pts"
