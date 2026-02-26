import ipaddress
from datetime import datetime, timezone


class FeedCache:
    def __init__(self):
        self._tags: dict[str, list[str]] = {}
        self.change_number: int | None = None
        self.last_refresh: datetime | None = None

    def load(self, data: dict) -> None:
        new_tags: dict[str, list[str]] = {}
        for entry in data.get("values", []):
            name = entry["name"]
            prefixes = entry.get("properties", {}).get("addressPrefixes", [])
            new_tags[name] = prefixes
        # Atomic swap — prevents torn reads during concurrent access
        self._tags = new_tags
        self.change_number = data["changeNumber"]
        self.last_refresh = datetime.now(timezone.utc)

    def get_all_tags(self) -> list[str]:
        return sorted(self._tags.keys())

    def get_tag(self, name: str, include_ipv6: bool = False) -> list[str] | None:
        prefixes = self._tags.get(name)
        if prefixes is None:
            return None
        if include_ipv6:
            return prefixes
        return [p for p in prefixes if _is_ipv4(p)]


def _is_ipv4(prefix: str) -> bool:
    try:
        return isinstance(ipaddress.ip_network(prefix, strict=False), ipaddress.IPv4Network)
    except ValueError:
        return False
