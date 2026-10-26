"""Just enough RLP decoding to pull 20-byte values out of block extraData,
which is where Redbelly lists the governors that receive fees."""


def _item(raw, at):
    lead = raw[at]
    if lead < 0x80:
        return raw[at:at + 1], at + 1
    if lead < 0xb8:
        end = at + 1 + lead - 0x80
        return raw[at + 1:end], end
    if lead < 0xc0:
        size_len = lead - 0xb7
        size = int.from_bytes(raw[at + 1:at + 1 + size_len], "big")
        begin = at + 1 + size_len
        return raw[begin:begin + size], begin + size
    if lead < 0xf8:
        size, begin = lead - 0xc0, at + 1
    else:
        size_len = lead - 0xf7
        size = int.from_bytes(raw[at + 1:at + 1 + size_len], "big")
        begin = at + 1 + size_len
    children, cur = [], begin
    while cur < begin + size:
        child, cur = _item(raw, cur)
        children.append(child)
    return children, begin + size


def twenty_byte_values(extra_data_hex):
    raw = bytes.fromhex(extra_data_hex.removeprefix("0x"))
    if not raw:
        return []
    try:
        tree, _ = _item(raw, 0)
    except (IndexError, ValueError):
        return []
    found, todo = [], [tree]
    while todo:
        node = todo.pop()
        if isinstance(node, list):
            todo.extend(node)
        elif len(node) == 20:
            found.append("0x" + node.hex())
    return found
