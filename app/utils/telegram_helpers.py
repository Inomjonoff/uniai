"""
Telegram helpers: message link construction, formatting, chunking.
"""
from typing import Optional, List


def make_telegram_message_link(
    chat_id: int,
    message_id: int,
    chat_username: Optional[str] = None
) -> str:
    """
    Generates a clickable link to a Telegram message.
    For public channels/groups with username: https://t.me/{username}/{message_id}
    For private supergroups (-100...): https://t.me/c/{chat_id_without_-100}/{message_id}
    """
    if chat_username:
        clean_user = chat_username.lstrip("@")
        return f"https://t.me/{clean_user}/{message_id}"
    
    # Telegram private supergroup IDs start with -100
    str_id = str(chat_id)
    if str_id.startswith("-100"):
        internal_id = str_id[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"
    elif str_id.startswith("-"):
        internal_id = str_id[1:]
        return f"https://t.me/c/{internal_id}/{message_id}"
    
    return f"https://t.me/c/{chat_id}/{message_id}"


def split_message_text(text: str, max_chars: int = 4000) -> List[str]:
    """Splits long text into chunks adhering to Telegram's 4096 character limit."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = len(line)
            else:
                # Line itself exceeds max_chars
                for i in range(0, len(line), max_chars):
                    chunks.append(line[i : i + max_chars])
                current_chunk = []
                current_len = 0
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
