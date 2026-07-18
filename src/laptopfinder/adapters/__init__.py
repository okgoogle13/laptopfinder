"""
Platform-agnostic listing schema and adapter contract.

Every source (eBay, Scorptec, JB Hi-Fi, OEM outlets) must map into `Listing`
before entering the scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Listing:
    """Canonical neutral schema every source maps into before scoring."""
    platform: str  # 'ebay', 'scorptec', 'jb_hifi', 'direct_oem', 'EBAY', 'SCORPTEC', 'JB_HIFI', 'LENOVO_OUTLET_AU', 'HP_STORE_AU'
    listing_id: str
    title: str
    url: str
    vendor_name: str
    price_aud: float | None
    currency_original: str = "AUD"
    is_active: bool = True
    condition: str = "UNKNOWN"  # 'NEW', 'REFURB', 'USED', 'OPEN_BOX', 'UNKNOWN'
    gpu: str | None = None
    vram_gb: float | None = None
    ram_gb: float | None = None
    cpu_model: str | None = None
    screen_size_inches: float | None = None
    screen_type: str | None = None  # 'IPS', 'OLED', 'MiniLED', 'UNKNOWN'
    touch: bool = False
    paradigm: str = "discrete_cuda"  # 'apple_silicon_uma', 'discrete_cuda', 'discrete_rocm', 'amd_uma'
    connectivities: list[str] = field(default_factory=list)
    vendor_type: str = "MARKETPLACE_PRIVATE"  # 'MARKETPLACE_PRIVATE', 'RETAILER', 'OEM_OUTLET', 'OEM_DIRECT', 'Specialist retailer', 'National retailer', 'OEM outlet', 'OEM direct'
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "listing_id": self.listing_id,
            "title": self.title,
            "url": self.url,
            "vendor_name": self.vendor_name,
            "vendor_type": self.vendor_type,
            "price_aud": self.price_aud,
            "currency_original": self.currency_original,
            "is_active": self.is_active,
            "condition": self.condition,
            "gpu": self.gpu,
            "vram_gb": self.vram_gb,
            "ram_gb": self.ram_gb,
            "cpu_model": self.cpu_model,
            "screen_size_inches": self.screen_size_inches,
            "screen_type": self.screen_type,
            "touch": self.touch,
            "paradigm": self.paradigm,
            "connectivities": self.connectivities,
        }


AdapterFunc = Callable[[dict[str, Any]], Listing]
