from .enums import ChannelType
from typing import Any

channel_keys: dict[int, list[str]] = {
    ChannelType.text: ["id", "name", "type", "topic", "position", "rate_limit_per_user", "parent_id", "nsfw", "guild_id"],
    ChannelType.voice: ["id", "name", "type", "topic", "bitrate", "user_limit", "position", "parent_id", "guild_id"]
}

def filter_channel_keys(channel: dict[str, Any]) -> dict[str, Any]:
    type: int = channel["type"]
    keys: list[str] = channel_keys[type]
    return {k: v for k, v in channel.items() if k in keys}
