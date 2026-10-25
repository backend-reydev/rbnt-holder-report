"""Minimal RLP decoder, enough to read addresses out of block extraData."""


def decode(data, pos=0):
    """Return (item, next_pos). Items are bytes or lists."""
    b = data[pos]
    if b < 0x80:
        return data[pos:pos + 1], pos + 1
    if b < 0xb8:
        n = b - 0x80
        return data[pos + 1:pos + 1 + n], pos + 1 + n
    if b < 0xc0:
        ln = b - 0xb7
        n = int.from_bytes(data[pos + 1:pos + 1 + ln], "big")
        start = pos + 1 + ln
        return data[start:start + n], start + n
    if b < 0xf8:
        n, start = b - 0xc0, pos + 1
    else:
        ln = b - 0xf7
        n = int.from_bytes(data[pos + 1:pos + 1 + ln], "big")
        start = pos + 1 + ln
    items, p = [], start
    while p < start + n:
        item, p = decode(data, p)
        items.append(item)
    return items, start + n


def addresses(extra_hex):
    """Every 20-byte string anywhere in the RLP structure of extraData."""
    raw = bytes.fromhex(extra_hex[2:])
    if not raw:
        return []
    try:
        item, _ = decode(raw)
    except (IndexError, ValueError):
        return []
    out, stack = [], [item]
    while stack:
        x = stack.pop()
        if isinstance(x, list):
            stack.extend(x)
        elif len(x) == 20:
            out.append("0x" + x.hex())
    return out
