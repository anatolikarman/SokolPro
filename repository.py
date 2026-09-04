"""Query functions mirroring ClientRepository / SessionRepository (Spring Data JPA)."""
from datetime import date
from typing import List, Optional

from db import get_connection
from models import Client, Session


# ---------------------------------------------------------------- clients --

def find_all_clients() -> List[Client]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM client ORDER BY id").fetchall()
        return [Client.from_row(r) for r in rows]
    finally:
        conn.close()


def find_client_by_id(client_id: int) -> Optional[Client]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM client WHERE id = ?", (client_id,)).fetchone()
        return Client.from_row(row) if row else None
    finally:
        conn.close()


def save_client(client: Client) -> Client:
    conn = get_connection()
    try:
        if client.id is None:
            cur = conn.execute(
                "INSERT INTO client (name, date_of_birth, active, backstory) VALUES (?, ?, ?, ?)",
                (client.name, client.date_of_birth.isoformat() if client.date_of_birth else None,
                 1 if client.active else 0, client.backstory),
            )
            client.id = cur.lastrowid
        else:
            conn.execute(
                "UPDATE client SET name = ?, date_of_birth = ?, active = ?, backstory = ? WHERE id = ?",
                (client.name, client.date_of_birth.isoformat() if client.date_of_birth else None,
                 1 if client.active else 0, client.backstory, client.id),
            )
        conn.commit()
        return client
    finally:
        conn.close()


def delete_client_by_id(client_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM client WHERE id = ?", (client_id,))
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------- sessions --

def _row_to_session(row, with_client: bool) -> Session:
    client = None
    if with_client:
        client = Client(
            id=row["c_id"],
            name=row["c_name"],
            date_of_birth=row["c_date_of_birth"],
            active=bool(row["c_active"]),
            backstory=row["c_backstory"],
        )
        # normalize date_of_birth like Client.from_row does
        from models import _parse_date
        client.date_of_birth = _parse_date(client.date_of_birth)
    return Session.from_row(row, client=client)


def find_sessions_by_client_id_order_by_date_desc(client_id: int) -> List[Session]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM session WHERE client_id = ? ORDER BY date DESC, id",
            (client_id,),
        ).fetchall()
        return [Session.from_row(r) for r in rows]
    finally:
        conn.close()


def find_session_by_client_id_and_date(client_id: int, on_date: date) -> Optional[Session]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM session WHERE client_id = ? AND date = ?",
            (client_id, on_date.isoformat()),
        ).fetchone()
        return Session.from_row(row) if row else None
    finally:
        conn.close()


def find_sessions_by_date_between(start: date, end: date) -> List[Session]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM session WHERE date BETWEEN ? AND ? ORDER BY id",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [Session.from_row(r) for r in rows]
    finally:
        conn.close()


def find_sessions_by_date_gte_order_by_date_asc_time_asc(start: date) -> List[Session]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM session WHERE date >= ? ORDER BY date ASC, time ASC",
            (start.isoformat(),),
        ).fetchall()
        return [Session.from_row(r) for r in rows]
    finally:
        conn.close()


def find_sessions_by_date_with_client_order_by_time(on_date: date) -> List[Session]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.*, c.id AS c_id, c.name AS c_name, c.date_of_birth AS c_date_of_birth,
                   c.active AS c_active, c.backstory AS c_backstory
            FROM session s JOIN client c ON c.id = s.client_id
            WHERE s.date = ?
            ORDER BY s.time
            """,
            (on_date.isoformat(),),
        ).fetchall()
        return [_row_to_session(r, with_client=True) for r in rows]
    finally:
        conn.close()


def find_session_by_id(session_id: int) -> Optional[Session]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM session WHERE id = ?", (session_id,)).fetchone()
        return Session.from_row(row) if row else None
    finally:
        conn.close()


def save_session(session: Session) -> Session:
    conn = get_connection()
    try:
        if session.id is None:
            cur = conn.execute(
                "INSERT INTO session (client_id, date, time, duration_minutes, paid, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session.client_id, session.date.isoformat(),
                 session.time.isoformat() if session.time else None,
                 session.duration_minutes, 1 if session.paid else 0, session.notes),
            )
            session.id = cur.lastrowid
        else:
            conn.execute(
                "UPDATE session SET client_id = ?, date = ?, time = ?, duration_minutes = ?, "
                "paid = ?, notes = ? WHERE id = ?",
                (session.client_id, session.date.isoformat(),
                 session.time.isoformat() if session.time else None,
                 session.duration_minutes, 1 if session.paid else 0, session.notes, session.id),
            )
        conn.commit()
        return session
    finally:
        conn.close()


def delete_session_by_id(session_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM session WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def delete_sessions(sessions: List[Session]) -> None:
    if not sessions:
        return
    conn = get_connection()
    try:
        conn.executemany("DELETE FROM session WHERE id = ?", [(s.id,) for s in sessions])
        conn.commit()
    finally:
        conn.close()
