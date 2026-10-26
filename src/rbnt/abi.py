"""The few pieces of the Ethereum ABI this report needs: function selectors,
calls with address arguments, and reading 32-byte words back."""

from Crypto.Hash import keccak as _keccak


def keccak256(raw: bytes) -> bytes:
    return _keccak.new(digest_bits=256, data=raw).digest()


def topic(event_signature):
    """Topic 0 of an event, as 0x-prefixed hex."""
    return "0x" + keccak256(event_signature.encode()).hex()


def selector(function_signature):
    return "0x" + keccak256(function_signature.encode()).hex()[:8]


def encode_call(function_signature, *address_args):
    padded = "".join(arg.lower().removeprefix("0x").zfill(64) for arg in address_args)
    return selector(function_signature) + padded


def unpack_words(returned_hex):
    body = returned_hex.removeprefix("0x")
    return [int(body[k:k + 64], 16) for k in range(0, len(body), 64)]


def topic_address(topic_hex):
    return "0x" + topic_hex[-40:].lower()
