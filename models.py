"""Domain model classes mirroring the original Client.java / Session.java entities."""
from dataclasses import dataclass
from datetime import date, time
from typing import Optional


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _parse_time(value) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    return time.fromisoformat(value)


@dataclass
class Client:
    id: Optional[int]
    name: str
    date_of_birth: Optional[date]
    active: bool
    backstory: Optional[str]

    @property
    def formatted_date_of_birth(self) -> str:
        if self.date_of_birth is None:
            return ""
        return self.date_of_birth.strftime("%d.%m.%Y")

    @classmethod
    def from_row(cls, row) -> "Client":
        return cls(
            id=row["id"],
            name=row["name"],
            date_of_birth=_parse_date(row["date_of_birth"]),
            active=bool(row["active"]),
            backstory=row["backstory"],
        )


@dataclass
class Session:
    id: Optional[int]
    client_id: int
    date: date
    time: Optional[time]
    duration_minutes: int
    paid: bool
    notes: Optional[str]
    client: Optional[Client] = None

    @property
    def formatted_date(self) -> str:
        if self.date is None:
            return ""
        return self.date.strftime("%d.%m.%Y")

    @property
    def formatted_time(self) -> str:
        if self.time is None:
            return ""
        return self.time.strftime("%H:%M")

    @classmethod
    def from_row(cls, row, client: Optional[Client] = None) -> "Session":
        return cls(
            id=row["id"],
            client_id=row["client_id"],
            date=_parse_date(row["date"]),
            time=_parse_time(row["time"]),
            duration_minutes=row["duration_minutes"] if row["duration_minutes"] is not None else 0,
            paid=bool(row["paid"]),
            notes=row["notes"],
            client=client,
        )
