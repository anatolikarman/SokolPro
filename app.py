"""Flask application mirroring ClientController.java / SokolProApplication.java.

Run with `python app.py`; it starts a local server and opens the app in the
default browser automatically, just like the original Spring Boot app did.
"""
import webbrowser
from datetime import date, datetime
from datetime import time as dtime
from threading import Timer
from urllib.parse import quote

from flask import Flask, Response, abort, redirect, render_template, request, url_for

import calendar_utils as cal
import models
import pdf_exporter
import repository as repo
import word_exporter
from db import init_db
from sanitize import sanitize_notes

app = Flask(__name__)

PORT = 8080


def url_for_clean(endpoint, **kwargs):
    """Like url_for, but drops any keyword arguments whose value is None -
    mirrors Thymeleaf's @{...} link builder, which omits a query parameter
    entirely when its value is null rather than emitting "param=None"."""
    clean = {k: v for k, v in kwargs.items() if v is not None}
    return url_for(endpoint, **clean)


app.jinja_env.globals["url_for_clean"] = url_for_clean


def _is_ajax() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _find_client_or_404(client_id: int) -> models.Client:
    client = repo.find_client_by_id(client_id)
    if client is None:
        abort(404, description="Клиент не найден")
    return client


def _load_notes_sessions(client_id: int):
    sessions = repo.find_sessions_by_client_id_order_by_date_desc(client_id)
    sessions = [s for s in sessions if s.notes and s.notes.strip()]
    sessions.sort(key=lambda s: (s.date, s.time is not None, s.time or dtime.min))
    return sessions


def _content_disposition(client_name: str, extension: str) -> str:
    filename = f"Заметки - {client_name}.{extension}"
    encoded = quote(filename, safe="")
    return f"attachment; filename*=UTF-8''{encoded}"


def _current_year_month(year, month):
    if year is not None and month is not None:
        return year, month
    today = date.today()
    return today.year, today.month


# --------------------------------------------------------------- list page --

@app.route("/")
def list_view():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    selected_date_str = request.args.get("selectedDate")
    selected_date = date.fromisoformat(selected_date_str) if selected_date_str else None

    all_clients = repo.find_all_clients()
    clients = [c for c in all_clients if c.active]
    inactive_clients = [c for c in all_clients if not c.active]

    today = date.today()
    now = datetime.now().time()
    upcoming_sessions = [
        s for s in repo.find_sessions_by_date_gte_order_by_date_asc_time_asc(today)
        if today != s.date or s.time is None or not (s.time < now)
    ]
    next_session_text = cal.build_next_session_text(all_clients, upcoming_sessions)

    cur_year, cur_month = _current_year_month(year, month)
    prev_year, prev_month = cal.add_months(cur_year, cur_month, -1)
    next_year, next_month = cal.add_months(cur_year, cur_month, 1)

    month_start = date(cur_year, cur_month, 1)
    month_end = date(cur_year, cur_month, cal.days_in_month(cur_year, cur_month))
    month_sessions = repo.find_sessions_by_date_between(month_start, month_end)
    days_with_session = {s.date.day for s in month_sessions}

    day_dates = cal.build_day_dates(cur_year, cur_month)
    day_classes = cal.build_overview_day_classes(day_dates, days_with_session, selected_date)

    selected_sessions = (
        repo.find_sessions_by_date_with_client_order_by_time(selected_date)
        if selected_date is not None else []
    )

    context = dict(
        clients=clients,
        inactive_clients=inactive_clients,
        next_session_text=next_session_text,
        calendar_weeks=cal.build_calendar_weeks(cur_year, cur_month),
        month_title=cal.month_title(cur_year, cur_month),
        calendar_year=cur_year,
        calendar_month=cur_month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        day_dates=day_dates,
        day_classes=day_classes,
        days_with_session=days_with_session,
        selected_date=selected_date,
        selected_date_formatted=selected_date.strftime("%d.%m.%Y") if selected_date else None,
        selected_sessions=selected_sessions,
    )

    template = "_calendar_list.html" if _is_ajax() else "list.html"
    return render_template(template, **context)


# --------------------------------------------------------------- add client --

@app.route("/add")
def add_form():
    return render_template("add.html")


@app.route("/add", methods=["POST"])
def add_client():
    name = request.form.get("name", "")
    dob_str = request.form.get("dateOfBirth")
    if name and name.strip():
        dob = date.fromisoformat(dob_str) if dob_str else None
        repo.save_client(models.Client(id=None, name=name.strip(), date_of_birth=dob, active=True, backstory=None))
    return redirect(url_for("list_view"))


# --------------------------------------------------------------- client page --

@app.route("/clients/<int:client_id>")
def view_client(client_id):
    client = _find_client_or_404(client_id)
    edit_backstory = (request.args.get("editBackstory") or "").lower() == "true"

    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    selected_date_str = request.args.get("selectedDate")
    selected_date = date.fromisoformat(selected_date_str) if selected_date_str else None
    error = request.args.get("error")
    conflict_client = request.args.get("conflictClient")

    all_sessions = repo.find_sessions_by_client_id_order_by_date_desc(client_id)

    cur_year, cur_month = _current_year_month(year, month)
    prev_year, prev_month = cal.add_months(cur_year, cur_month, -1)
    next_year, next_month = cal.add_months(cur_year, cur_month, 1)
    today = date.today()

    day_dates = cal.build_day_dates(cur_year, cur_month)
    day_status = cal.build_day_status(cur_year, cur_month, all_sessions, today)
    day_classes = cal.build_day_classes(day_dates, day_status, selected_date)

    selected_sessions = (
        [s for s in all_sessions if s.date == selected_date]
        if selected_date is not None else []
    )

    context = dict(
        client=client,
        edit_backstory=edit_backstory,
        calendar_weeks=cal.build_calendar_weeks(cur_year, cur_month),
        month_title=cal.month_title(cur_year, cur_month),
        calendar_year=cur_year,
        calendar_month=cur_month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        day_dates=day_dates,
        day_classes=day_classes,
        days_with_session=set(day_status.keys()),
        selected_date=selected_date,
        selected_date_formatted=selected_date.strftime("%d.%m.%Y") if selected_date else None,
        selected_sessions=selected_sessions,
        overlap_error=(error == "overlap"),
        conflict_client_name=conflict_client,
    )

    template = "_calendar_view.html" if _is_ajax() else "view.html"
    return render_template(template, **context)


@app.route("/clients/<int:client_id>/notes-document")
def notes_document(client_id):
    client = _find_client_or_404(client_id)
    sessions = _load_notes_sessions(client_id)
    return render_template("notes-document.html", client=client, sessions=sessions)


@app.route("/clients/<int:client_id>/notes-document.pdf")
def notes_document_pdf(client_id):
    client = _find_client_or_404(client_id)
    sessions = _load_notes_sessions(client_id)
    pdf_bytes = pdf_exporter.build(client, sessions)
    resp = Response(pdf_bytes, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = _content_disposition(client.name, "pdf")
    return resp


@app.route("/clients/<int:client_id>/notes-document.docx")
def notes_document_docx(client_id):
    client = _find_client_or_404(client_id)
    sessions = _load_notes_sessions(client_id)
    docx_bytes = word_exporter.build(client, sessions)
    resp = Response(
        docx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    resp.headers["Content-Disposition"] = _content_disposition(client.name, "docx")
    return resp


@app.route("/clients/<int:client_id>", methods=["POST"])
def update_active(client_id):
    client = _find_client_or_404(client_id)
    client.active = request.form.get("active") is not None
    repo.save_client(client)
    return redirect(url_for("view_client", client_id=client_id, saved="true"))


@app.route("/clients/<int:client_id>/backstory", methods=["POST"])
def update_backstory(client_id):
    client = _find_client_or_404(client_id)
    client.backstory = sanitize_notes(request.form.get("backstory"))
    repo.save_client(client)
    return redirect(url_for("view_client", client_id=client_id, editBackstory="true", saved="true"))


# ------------------------------------------------------------------ sessions --

@app.route("/clients/<int:client_id>/sessions", methods=["POST"])
def add_session(client_id):
    d = date.fromisoformat(request.form["date"])
    t = dtime.fromisoformat(request.form["time"])
    length = int(request.form["length"])
    paid = request.form.get("paid") is not None
    notes = request.form.get("notes")

    client = _find_client_or_404(client_id)
    if not client.active:
        return redirect(url_for("view_client", client_id=client_id, year=d.year, month=d.month))
    if repo.find_session_by_client_id_and_date(client_id, d) is not None:
        return redirect(url_for("view_client", client_id=client_id, year=d.year, month=d.month))

    sessions_on_date = repo.find_sessions_by_date_with_client_order_by_time(d)
    conflict = cal.find_overlapping_session(d, sessions_on_date, t, length, None)
    if conflict is not None:
        return redirect(url_for(
            "view_client", client_id=client_id, year=d.year, month=d.month,
            selectedDate=d, error="overlap", conflictClient=conflict.client.name,
        ))

    repo.save_session(models.Session(
        id=None, client_id=client_id, date=d, time=t,
        duration_minutes=length, paid=paid, notes=sanitize_notes(notes),
    ))
    return redirect(url_for("view_client", client_id=client_id, year=d.year, month=d.month, saved="true"))


@app.route("/clients/<int:client_id>/sessions/<int:session_id>", methods=["POST"])
def update_session(client_id, session_id):
    t = dtime.fromisoformat(request.form["time"])
    length = int(request.form["length"])
    paid = request.form.get("paid") is not None
    notes = request.form.get("notes")

    session = repo.find_session_by_id(session_id)
    if session is None:
        abort(404, description="Сеанс не найден")
    d = session.date

    sessions_on_date = repo.find_sessions_by_date_with_client_order_by_time(d)
    conflict = cal.find_overlapping_session(d, sessions_on_date, t, length, session_id)
    if conflict is not None:
        return redirect(url_for(
            "view_client", client_id=client_id, year=d.year, month=d.month,
            selectedDate=d, error="overlap", conflictClient=conflict.client.name,
        ))

    session.time = t
    session.duration_minutes = length
    session.paid = paid
    session.notes = sanitize_notes(notes)
    repo.save_session(session)
    return redirect(url_for(
        "view_client", client_id=client_id, year=d.year, month=d.month,
        selectedDate=d, saved="true",
    ))


@app.route("/clients/<int:client_id>/sessions/<int:session_id>/delete", methods=["POST"])
def delete_session(client_id, session_id):
    session = repo.find_session_by_id(session_id)
    d = session.date if session is not None else date.today()
    repo.delete_session_by_id(session_id)
    return redirect(url_for("view_client", client_id=client_id, year=d.year, month=d.month))


@app.route("/remove/<int:client_id>", methods=["POST"])
def remove_client(client_id):
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    selected_date_str = request.args.get("selectedDate")

    repo.delete_sessions(repo.find_sessions_by_client_id_order_by_date_desc(client_id))
    repo.delete_client_by_id(client_id)

    if year is not None and month is not None:
        return redirect(url_for("list_view", year=year, month=month, selectedDate=selected_date_str))
    return redirect(url_for("list_view"))


@app.errorhandler(404)
def not_found(err):
    message = getattr(err, "description", None) or "Страница не найдена"
    return message, 404


if __name__ == "__main__":
    init_db()

    def _open_browser():
        try:
            webbrowser.open(f"http://localhost:{PORT}/")
        except Exception:
            pass  # Opening the browser is a convenience, not critical to the app running.

    Timer(1.0, _open_browser).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
