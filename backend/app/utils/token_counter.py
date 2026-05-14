import tiktoken


_encoder = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        # cl100k_base is compatible with most modern LLMs including Groq-hosted models
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    enc = _get_encoder()
    return len(enc.encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    enc = _get_encoder()
    total = 0
    for msg in messages:
        # 4 tokens per message overhead (role, content delimiters)
        total += 4
        for value in msg.values():
            if isinstance(value, str):
                total += len(enc.encode(value))
    total += 2  # reply priming tokens
    return total


def trim_messages_to_limit(
    messages: list[dict],
    max_tokens: int = 6000,
    preserve_system: bool = True,
) -> list[dict]:
    if not messages:
        return messages

    system_messages = []
    non_system = []

    for msg in messages:
        if msg.get("role") == "system":
            system_messages.append(msg)
        else:
            non_system.append(msg)

    system_tokens = count_messages_tokens(system_messages) if preserve_system else 0
    budget = max_tokens - system_tokens

    # Trim from oldest non-system messages first
    while non_system and count_messages_tokens(non_system) > budget:
        non_system.pop(0)

    return (system_messages + non_system) if preserve_system else non_system


def is_within_limit(text: str, max_tokens: int = 6000) -> bool:
    return count_tokens(text) <= max_tokens