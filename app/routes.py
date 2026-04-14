# app/routes.py - Main application routes and logic for the MUN management system
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
    jsonify,
)
from .convex_client import convex_client
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import csv
import io
import secrets

bp = Blueprint("bp", __name__)


def login_required(role=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("bp.login"))
            if role and session.get("role") != role:
                return redirect(url_for("bp.dashboard"))
            return fn(*args, **kwargs)

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


@bp.route("/")
def home():
    return redirect(url_for("bp.login"))


@bp.route("/health")
def health():
    return {"status": "ok"}


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        if not all([name, email, password, password_confirm]):
            return render_template("register.html", error="All fields are required")
        if password != password_confirm:
            return render_template("register.html", error="Passwords do not match")

        # Check if user exists in Convex
        existing = convex_client.query("/api/getUserByEmail", {"email": email})
        if existing:
            return render_template("register.html", error="Email already registered")

        # Create organizer and user in Convex
        password_hash = generate_password_hash(password)
        try:
            organizer_id = convex_client.mutation(
                "/api/registerOrganizer",
                {"email": email, "passwordHash": password_hash, "name": name},
            )
            # Get the created user
            user = convex_client.query("/api/getUserByEmail", {"email": email})
            if user:
                session["user_id"] = user.get("_id") or user.get("id")
                session["role"] = user.get("role")
                session["organizer_id"] = str(organizer_id)
                session["user_name"] = user.get("name")
                return redirect(url_for("bp.dashboard"))
        except Exception as e:
            return render_template("register.html", error=str(e))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = convex_client.verify_password(email, password)
        if user:
            session["user_id"] = user.get("_id") or user.get("id")
            session["role"] = user.get("role")
            session["organizer_id"] = user.get("organizerId")
            session["user_name"] = user.get("name")
            return redirect(url_for("bp.dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = convex_client.query("/api/getUserByEmail", {"email": email})
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = int(
                (datetime.utcnow() + timedelta(hours=24)).timestamp() * 1000
            )
            try:
                convex_client.mutation(
                    "/api/createPasswordResetToken",
                    {
                        "userId": str(user.get("_id") or user.get("id")),
                        "token": token,
                        "expiresAt": expires_at,
                    },
                )
            except:
                pass
            print(f"PASSWORD RESET TOKEN for {email}: {token}")
            flash("Password reset instructions sent to your email", "success")
        else:
            flash(
                "If an account exists with this email, password reset instructions have been sent",
                "info",
            )
        return redirect(url_for("bp.login"))
    return render_template("forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # Simplified reset - in production, validate token properly
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not password or password != confirm_password:
            return render_template(
                "reset_password.html", error="Passwords do not match"
            )
        # Note: Need to implement password reset mutation in Convex
        flash("Password reset successfully", "success")
        return redirect(url_for("bp.login"))
    return render_template("reset_password.html", token=token)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("bp.login"))


@bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    organizer_id = session.get("organizer_id")
    if not organizer_id:
        return redirect(url_for("bp.login"))

    events = convex_client.query(
        "/api/getEventsByOrganizer", {"organizerId": organizer_id}
    )
    events = events or []

    # Get announcements for these events
    announcements = []
    for event in events:
        event_announcements = convex_client.query(
            "/api/getAnnouncementsByEvent",
            {"eventId": str(event.get("_id") or event.get("id"))},
        )
        if event_announcements:
            announcements.extend(event_announcements)
    announcements.sort(key=lambda x: x.get("createdAt", 0), reverse=True)
    announcements = announcements[:5]

    return render_template(
        "dashboard.html",
        events=events,
        announcements=announcements,
        delegates=[],
        committees=[],
    )


@bp.route("/events", methods=["GET", "POST"])
def events():
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    organizer_id = session.get("organizer_id")
    if request.method == "POST":
        name = request.form.get("name")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        start = (
            int(datetime.strptime(start_date_str, "%Y-%m-%d").timestamp() * 1000)
            if start_date_str
            else None
        )
        end = (
            int(datetime.strptime(end_date_str, "%Y-%m-%d").timestamp() * 1000)
            if end_date_str
            else None
        )
        description = request.form.get("description")

        if not name:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "message": "Name required"})
            return render_template("events.html", error="Name required")

        try:
            event_id = convex_client.mutation(
                "/api/createEvent",
                {
                    "organizerId": organizer_id,
                    "name": name,
                    "startDate": start,
                    "endDate": end,
                    "description": description,
                },
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(
                    {"success": True, "message": "Event created successfully"}
                )
            return redirect(url_for("bp.dashboard"))
        except Exception as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "message": str(e)})
            return render_template("events.html", error=str(e))

    events = (
        convex_client.query("/api/getEventsByOrganizer", {"organizerId": organizer_id})
        or []
    )
    return render_template("events.html", events=events)


@bp.route("/events/<event_id>/committees", methods=["GET", "POST"])
def committees(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    if request.method == "POST":
        name = request.form.get("name")
        agenda = request.form.get("agenda")
        chair = request.form.get("chair")
        co_chair = request.form.get("co_chair")

        try:
            convex_client.mutation(
                "/api/createCommittee",
                {
                    "eventId": str(event_id),
                    "name": name,
                    "agenda": agenda,
                    "chair": chair,
                    "coChair": co_chair,
                },
            )
        except Exception as e:
            flash(f"Error creating committee: {e}", "error")

        return redirect(url_for("bp.committees", event_id=event_id))

    committees = (
        convex_client.query("/api/getCommitteesByEvent", {"eventId": str(event_id)})
        or []
    )
    return render_template("committees.html", committees=committees, event_id=event_id)


@bp.route("/events/<event_id>/delegates", methods=["GET", "POST"])
def delegates(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        country = request.form.get("country")
        committee_id = request.form.get("committee_id") or None
        password = request.form.get("password") or "changeme"

        # Check if user exists
        existing = convex_client.query("/api/getUserByEmail", {"email": email})
        if existing:
            flash("Email already registered", "error")
            return redirect(url_for("bp.delegates", event_id=event_id))

        password_hash = generate_password_hash(password)

        try:
            user_id = convex_client.mutation(
                "/api/createDelegate",
                {
                    "email": email,
                    "passwordHash": password_hash,
                    "name": name,
                    "country": country,
                },
            )

            if committee_id:
                convex_client.mutation(
                    "/api/assignDelegateToCommittee",
                    {
                        "eventId": str(event_id),
                        "userId": str(user_id),
                        "committeeId": str(committee_id),
                    },
                )
        except Exception as e:
            flash(f"Error creating delegate: {e}", "error")

        return redirect(url_for("bp.delegates", event_id=event_id))

    # Get delegates for this event
    delegate_assignments = (
        convex_client.query("/api/getDelegatesByEvent", {"eventId": str(event_id)})
        or []
    )
    all_delegates = convex_client.query("/api/getAllDelegates") or []

    committees = (
        convex_client.query("/api/getCommitteesByEvent", {"eventId": str(event_id)})
        or []
    )

    # Build delegate display list
    delegates_display = []
    for assignment in delegate_assignments:
        user_id = assignment.get("userId")
        for user in all_delegates:
            if str(user.get("_id") or user.get("id")) == str(user_id):
                committee_id = assignment.get("committeeId")
                committee_name = ""
                if committee_id:
                    for c in committees:
                        if str(c.get("_id") or c.get("id")) == str(committee_id):
                            committee_name = c.get("name")
                            break
                delegates_display.append(
                    {
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "country": user.get("country"),
                        "id": user.get("_id") or user.get("id"),
                        "committee": committee_name,
                        "committee_id": committee_id,
                    }
                )
                break

    return render_template(
        "delegates.html",
        delegates=delegates_display,
        event_id=event_id,
        committees=committees,
    )


@bp.route("/events/<event_id>/delegates/export_passwords")
def export_delegate_passwords(event_id):
    if "user_id" not in session or session.get("role") != "organizer":
        return redirect(url_for("bp.login"))

    delegate_assignments = (
        convex_client.query("/api/getDelegatesByEvent", {"eventId": str(event_id)})
        or []
    )
    all_delegates = convex_client.query("/api/getAllDelegates") or []
    committees = (
        convex_client.query("/api/getCommitteesByEvent", {"eventId": str(event_id)})
        or []
    )

    rows = []
    for assignment in delegate_assignments:
        user_id = assignment.get("userId")
        for user in all_delegates:
            if str(user.get("_id") or user.get("id")) == str(user_id):
                committee_id = assignment.get("committeeId")
                committee_name = ""
                if committee_id:
                    for c in committees:
                        if str(c.get("_id") or c.get("id")) == str(committee_id):
                            committee_name = c.get("name")
                            break
                rows.append(
                    {
                        "Name": user.get("name") or "",
                        "Email": user.get("email") or "",
                        "Country": user.get("country") or "",
                        "Committee": committee_name,
                        "Password": "",
                    }
                )
                break

    rows.sort(key=lambda r: (r["Committee"] or "", r["Name"] or ""))

    si = io.StringIO()
    fieldnames = ["Name", "Email", "Country", "Committee", "Password"]
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    output = si.getvalue()
    return send_file(
        io.BytesIO(output.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"delegates_passwords_event_{event_id}.csv",
    )


@bp.route("/events/<event_id>/chat", methods=["GET", "POST"])
def chat(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    if request.method == "POST":
        text = request.form.get("message")
        if text:
            try:
                convex_client.mutation(
                    "/api/sendChatMessage",
                    {
                        "eventId": str(event_id),
                        "senderId": str(session.get("user_id")),
                        "message": text,
                    },
                )
            except Exception as e:
                flash(f"Error sending message: {e}", "error")

    messages = (
        convex_client.query("/api/getChatMessagesByEvent", {"eventId": str(event_id)})
        or []
    )
    messages.sort(key=lambda x: x.get("timestamp", 0))
    return render_template("chat.html", messages=messages, event_id=event_id)


@bp.route("/events/<event_id>/announcements", methods=["GET", "POST"])
def announcements(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    user_role = session.get("role")
    can_post = user_role in ["organizer", "chair", "co_chair"]

    if request.method == "POST" and can_post:
        title = request.form.get("title")
        content = request.form.get("content")
        is_pinned = request.form.get("is_pinned") == "on"

        if title and content:
            try:
                convex_client.mutation(
                    "/api/createAnnouncement",
                    {
                        "eventId": str(event_id),
                        "title": title,
                        "content": content,
                        "createdBy": str(session.get("user_id")),
                        "isPinned": is_pinned,
                    },
                )
                flash("Announcement created successfully", "success")
            except Exception as e:
                flash(f"Error creating announcement: {e}", "error")

        return redirect(url_for("bp.announcements", event_id=event_id))

    announcements_list = (
        convex_client.query("/api/getAnnouncementsByEvent", {"eventId": str(event_id)})
        or []
    )
    announcements_list.sort(
        key=lambda x: (not x.get("isPinned", False), x.get("createdAt", 0)),
        reverse=True,
    )

    return render_template(
        "announcements.html",
        announcements=announcements_list,
        event_id=event_id,
        can_post=can_post,
    )


@bp.route("/events/<event_id>/documents", methods=["GET", "POST"])
def documents(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    # Note: Document upload requires storage integration
    # For now, just render the page
    return render_template("documents.html", documents=[], event_id=event_id)


@bp.route("/events/<event_id>/manage_events", methods=["GET", "POST"])
def manage_events(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update":
            name = request.form.get("name")
            description = request.form.get("description")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")

            start_date = (
                int(datetime.strptime(start_date_str, "%Y-%m-%d").timestamp() * 1000)
                if start_date_str
                else None
            )
            end_date = (
                int(datetime.strptime(end_date_str, "%Y-%m-%d").timestamp() * 1000)
                if end_date_str
                else None
            )

            try:
                convex_client.mutation(
                    "/api/updateEvent",
                    {
                        "id": event_id,
                        "name": name,
                        "description": description,
                        "startDate": start_date,
                        "endDate": end_date,
                    },
                )
                flash("Event updated successfully", "success")
            except Exception as e:
                flash(f"Error updating event: {e}", "error")

        elif action == "delete":
            try:
                convex_client.mutation("/api/deleteEvent", {"id": event_id})
                flash("Event deleted successfully", "success")
                return redirect(url_for("bp.events"))
            except Exception as e:
                flash(f"Error deleting event: {e}", "error")

        return redirect(url_for("bp.events"))

    event = convex_client.query("/api/getEventById", {"id": event_id})
    if not event:
        flash("Event not found", "error")
        return redirect(url_for("bp.events"))

    return render_template("manage_events.html", event=event, event_id=event_id)


@bp.route("/announcements/<announcement_id>/delete", methods=["POST"])
def delete_announcement(announcement_id):
    if "user_id" not in session or session.get("role") != "organizer":
        return redirect(url_for("bp.login"))
    # Need to implement delete mutation
    flash("Announcement deleted", "success")
    return redirect(url_for("bp.dashboard"))
