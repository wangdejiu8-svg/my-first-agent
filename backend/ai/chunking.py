from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int
    token_count: int


def split_text_into_chunks(text, *, chunk_size=900, overlap=120):
    cleaned = _normalize_input(text)
    if not cleaned:
        return []

    chunk_size = max(int(chunk_size or 900), 200)
    overlap = max(min(int(overlap or 120), chunk_size - 1), 0)

    chunks = []
    cursor = 0
    chunk_index = 0
    text_length = len(cleaned)

    while cursor < text_length:
        end = min(cursor + chunk_size, text_length)
        if end < text_length:
            natural_break = cleaned.rfind("\n", cursor, end)
            if natural_break > cursor + (chunk_size // 2):
                end = natural_break

        chunk_text = cleaned[cursor:end].strip()
        if chunk_text:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_offset=cursor,
                    end_offset=end,
                    token_count=_estimate_token_count(chunk_text),
                )
            )
            chunk_index += 1

        if end >= text_length:
            break
        cursor = max(end - overlap, cursor + 1)

    return chunks


def _normalize_input(text):
    lines = [line.rstrip() for line in (text or "").splitlines()]
    normalized = []
    last_blank = False
    for line in lines:
        if not line.strip():
            if not last_blank:
                normalized.append("")
            last_blank = True
            continue
        normalized.append(line.strip())
        last_blank = False
    return "\n".join(normalized).strip()


def _estimate_token_count(text):
    # A stable, cheap approximation is enough for MVP metadata.
    return max(1, len(text) // 4)
