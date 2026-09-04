"""Calendar/status-building helpers mirroring the private methods of ClientController.java."""
import calendar
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from models import Client, Session

MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

STATUS_PRIORITY = ["day-unpaid", "day-upcoming", "day-paid"]


def month_title(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def add_months(year: int, month: int, delta: int) -> tuple:
    total = (year * 12 + (month - 1)) + delta
    return total // 12, total % 12 + 1


def build_calendar_weeks(year: int, month: int) -> List[List[int]]:
    weeks: List[List[int]] = []
    week: List[int] = []

    first_weekday = date(year, month, 1).weekday()  # Monday = 0, matches ISO getDayOfWeek().getValue()-1
    for _ in range(first_weekday):
        week.append(0)

    for day in range(1, days_in_month(year, month) + 1):
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []

    if week:
        while len(week) < 7:
            week.append(0)
        weeks.append(week)

    return weeks


def build_day_dates(year: int, month: int) -> Dict[int, date]:
    return {day: date(year, month, day) for day in range(1, days_in_month(year, month) + 1)}


def build_next_session_text(clients: List[Client], upcoming_sessions: List[Session]) -> Dict[int, str]:
    next_by_client: Dict[int, Session] = {}
    for session in upcoming_sessions:
        next_by_client.setdefault(session.client_id, session)

    text: Dict[int, str] = {}
    for client in clients:
        nxt = next_by_client.get(client.id)
        if nxt is None:
            text[client.id] = "Нет предстоящих сеансов"
        else:
            when = nxt.formatted_date + (f", {nxt.formatted_time}" if nxt.time is not None else "")
            text[client.id] = f"Ближайший сеанс: {when}"
    return text


def _higher_priority(a: str, b: str) -> str:
    return a if STATUS_PRIORITY.index(a) <= STATUS_PRIORITY.index(b) else b


def build_day_status(year: int, month: int, sessions: List[Session], today: date) -> Dict[int, str]:
    status_by_day: Dict[int, str] = {}
    for session in sessions:
        d = session.date
        if d is None or d.year != year or d.month != month:
            continue
        status = ("day-paid" if session.paid else "day-unpaid") if d < today else "day-upcoming"
        day = d.day
        if day in status_by_day:
            status_by_day[day] = _higher_priority(status_by_day[day], status)
        else:
            status_by_day[day] = status
    return status_by_day


def build_overview_day_classes(day_dates: Dict[int, date], days_with_session: set,
                                selected_date: Optional[date]) -> Dict[int, str]:
    classes: Dict[int, str] = {}
    for day, d in day_dates.items():
        css = "calendar-day"
        if day in days_with_session:
            css += " day-has-session"
        if selected_date is not None and selected_date == d:
            css += " day-selected"
        classes[day] = css
    return classes


def build_day_classes(day_dates: Dict[int, date], day_status: Dict[int, str],
                       selected_date: Optional[date]) -> Dict[int, str]:
    classes: Dict[int, str] = {}
    for day, d in day_dates.items():
        css = "calendar-day"
        status = day_status.get(day)
        if status:
            css += f" {status}"
        if selected_date is not None and selected_date == d:
            css += " day-selected"
        classes[day] = css
    return classes


def find_overlapping_session(session_date: date, sessions_on_date: List[Session], time_, length_minutes: int,
                              exclude_session_id: Optional[int]) -> Optional[Session]:
    """sessions_on_date must be the list returned by find_sessions_by_date_with_client_order_by_time
    for session_date."""
    this_start = datetime.combine(session_date, time_)
    this_end = this_start + timedelta(minutes=length_minutes)
    for other in sessions_on_date:
        if exclude_session_id is not None and exclude_session_id == other.id:
            continue
        if other.time is None:
            continue
        other_start = datetime.combine(other.date, other.time)
        other_end = other_start + timedelta(minutes=other.duration_minutes)
        if this_start < other_end and other_start < this_end:
            return other
    return None
