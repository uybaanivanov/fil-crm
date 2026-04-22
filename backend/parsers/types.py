from dataclasses import asdict, dataclass


@dataclass
class ParsedListing:
    source: str
    source_url: str
    title: str | None = None
    address: str | None = None
    price_per_night: int | None = None
    rooms: str | None = None
    area_m2: int | None = None
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
