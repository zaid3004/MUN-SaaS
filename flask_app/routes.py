# app/routes.py - Main application routes and logic for the MUN management system
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    jsonify,
)
from .convex_client import convex_client
from .stripe_utils import (
    create_checkout_session,
    verify_payment,
    PRICING,
    calculate_price,
    calculate_upgrade_price,
    construct_webhook_event,
)
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import csv
import io
import secrets
import bleach


def add_notification(message, category="info"):
    if "notifications" not in session:
        session["notifications"] = []

    # Create a simplified representation of existing notifications for comparison
    existing_notifications = set(item["message"] for item in session["notifications"])

    # Only add the new notification if its message is not already in the set
    if message not in existing_notifications:
        session["notifications"].append({"message": message, "category": category})
        session.modified = True


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


def check_event_access(event_id):
    """Check if event is paid and not expired. Returns (can_access, error_message)."""
    if not event_id:
        return False, "Event not found"

    try:
        status = (
            convex_client.query(
                "/api/getEventPaymentStatus", {"eventId": str(event_id)}
            )
            or {}
        )
        if not status:
            return False, "Event not found"

        if not status.get("isPaid"):
            return False, "unpaid"

        expires_at = status.get("expiresAt")
        if expires_at and expires_at < datetime.utcnow().timestamp() * 1000:
            return False, "expired"

        return True, None
    except:
        return False, "error"


def check_delegate_limit(event_id, current_count):
    """Check if delegate count is within plan limits. Returns (can_add, message)."""
    try:
        status = (
            convex_client.query(
                "/api/getEventPaymentStatus", {"eventId": str(event_id)}
            )
            or {}
        )
        if not status:
            return False, "Event not found"

        plan = status.get("plan", "small")
        delegate_count = status.get("delegateCount", 0)
        max_delegates = PRICING.get(plan, {}).get("max_delegates", 100)

        if current_count >= max_delegates:
            return False, f"limit_reached"

        return True, None
    except:
        return True, None


@bp.route("/")
def home():
    return redirect(url_for("bp.login"))


@bp.route("/health")
def health():
    return {"status": "ok"}


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = bleach.clean(request.form.get("name"))
        email = bleach.clean(request.form.get("email"))
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
                user_id = user.get("_id") or user.get("id")
                session["user_id"] = user_id
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
        email = bleach.clean(request.form.get("email"))
        password = request.form.get("password")

        user = convex_client.verify_password(email, password)
        if user:
            user_id = user.get("_id") or user.get("id")
            session["user_id"] = user_id
            session["role"] = user.get("role")
            session["organizer_id"] = user.get("organizerId")
            session["user_name"] = user.get("name")
            return redirect(url_for("bp.dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = bleach.clean(request.form.get("email"))
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
            add_notification(
                "Password reset instructions sent to your email", "success"
            )
        else:
            add_notification(
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
        add_notification("Password reset successfully", "success")
        return redirect(url_for("bp.login"))
    return render_template("reset_password.html", token=token)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("bp.login"))


@bp.route("/dashboard")
@login_required()
def dashboard():
    organizer_id = session.get("organizer_id")
    if not organizer_id:
        add_notification("Organizer ID not found in session.", "error")
        return redirect(url_for("bp.login"))

    try:
        events = convex_client.query(
            "/api/getEventsByOrganizer", {"organizerId": organizer_id}
        )
        events = events or []

        unpaid_event_id = None
        for event in events:
            event_id = str(event.get("_id") or event.get("id"))
            status = (
                convex_client.query("/api/getEventPaymentStatus", {"eventId": event_id})
                or {}
            )
            if not status.get("isPaid"):
                unpaid_event_id = event_id
                add_notification(
                    f'Event "{event.get("name")}" requires payment. Please complete billing.',
                    "warning",
                )
                break  # Stop after finding the first unpaid event

        # Get announcements for these events
        announcements = []
        if events:
            event_ids = [str(e.get("_id") or e.get("id")) for e in events]
            # This could be more efficient with a single query if the backend supports it
            for event_id in event_ids:
                event_announcements = convex_client.query(
                    "/api/getAnnouncementsByEvent", {"eventId": event_id}
                )
                if event_announcements:
                    # Augment announcement with event name
                    event_name = next(
                        (
                            e.get("name")
                            for e in events
                            if str(e.get("_id") or e.get("id")) == event_id
                        ),
                        "",
                    )
                    for ann in event_announcements:
                        ann["eventName"] = event_name
                    announcements.extend(event_announcements)

        announcements.sort(key=lambda x: x.get("_creationTime", 0), reverse=True)

        # Simplified data for now, will be fetched properly in their respective pages
        delegates = []
        committees = []

    except Exception as e:
        add_notification(f"An error occurred: {e}", "error")
        events = []
        announcements = []
        delegates = []
        committees = []
        unpaid_event_id = None

    return render_template(
        "dashboard.html",
        events=events,
        announcements=announcements[:5],  # Limit to 5 most recent
        delegates=delegates,
        committees=committees,
        unpaid_event_id=unpaid_event_id,
    )


@bp.route("/events", methods=["GET", "POST"])
def events():
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    organizer_id = session.get("organizer_id")
    if request.method == "POST":
        name = bleach.clean(request.form.get("name"))
        start_date_str = bleach.clean(request.form.get("start_date")) or None
        end_date_str = bleach.clean(request.form.get("end_date")) or None
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
        description = bleach.clean(request.form.get("description")) or ""

        if not name:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "message": "Name required"})
            return render_template("events.html", error="Name required")

        try:
            print(f"Creating event: {name}, organizer_id: {organizer_id}")
            event_id_obj = convex_client.mutation(
                "/api/createEvent",
                {
                    "organizerId": organizer_id,
                    "name": name,
                    "startDate": start,
                    "endDate": end,
                    "description": description,
                    "plan": "small",
                },
            )
            event_id = event_id_obj.get("eventId")
            print(f"Event created with ID: {event_id}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(
                    {
                        "success": True,
                        "message": "Event created successfully",
                        "eventId": str(event_id),
                    }
                )
            return redirect(url_for("bp.billing", event_id=str(event_id)))
        except Exception as e:
            print(f"Error creating event: {e}")
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

    can_access, error = check_event_access(event_id)
    if not can_access:
        if error == "unpaid":
            add_notification(
                "Event requires payment. Please complete billing to access committees.",
                "warning",
            )
            return redirect(url_for("bp.billing", event_id=event_id))
        elif error == "expired":
            add_notification("Event has expired. Please renew.", "error")
            return redirect(url_for("bp.billing", event_id=event_id))
        else:
            add_notification("Access denied", "error")
            return redirect(url_for("bp.dashboard"))

    if request.method == "POST":
        name = bleach.clean(request.form.get("name"))
        agenda = bleach.clean(request.form.get("agenda"))

        chair_name = bleach.clean(request.form.get("chair_name"))
        chair_email = bleach.clean(request.form.get("chair_email"))
        chair_password = request.form.get("chair_password") or "changeme"

        co_chair_name = bleach.clean(request.form.get("co_chair_name"))
        co_chair_email = bleach.clean(request.form.get("co_chair_email"))
        co_chair_password = request.form.get("co_chair_password") or "changeme"

        args = {"eventId": str(event_id), "name": name}
        if agenda:
            args["agenda"] = agenda
        if chair_name:
            args["chair"] = chair_name
        if co_chair_name:
            args["coChair"] = co_chair_name

        try:
            convex_client.mutation("/api/createCommittee", args)

            if chair_email:
                existing = convex_client.query(
                    "/api/getUserByEmail", {"email": chair_email}
                )
                if not existing:
                    chair_user_id = convex_client.mutation(
                        "/api/createDelegate",
                        {
                            "email": chair_email,
                            "passwordHash": generate_password_hash(chair_password),
                            "name": chair_name or "Chair",
                            "country": "Chair",
                        },
                    )

            if co_chair_email:
                existing = convex_client.query(
                    "/api/getUserByEmail", {"email": co_chair_email}
                )
                if not existing:
                    co_chair_user_id = convex_client.mutation(
                        "/api/createDelegate",
                        {
                            "email": co_chair_email,
                            "passwordHash": generate_password_hash(co_chair_password),
                            "name": co_chair_name or "Co-Chair",
                            "country": "Co-Chair",
                        },
                    )

        except Exception as e:
            add_notification(f"Error creating committee: {e}", "error")

        return redirect(url_for("bp.committees", event_id=event_id))

    committees = (
        convex_client.query("/api/getCommitteesByEvent", {"eventId": str(event_id)})
        or []
    )
    event = convex_client.query("/api/getEventById", {"id": str(event_id)})
    return render_template(
        "committees.html", committees=committees, event_id=event_id, event=event
    )


@bp.route("/events/<event_id>/delegates", methods=["GET", "POST"])
def delegates(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    can_access, error = check_event_access(event_id)
    if not can_access:
        if error == "unpaid":
            add_notification(
                "Event requires payment. Please complete billing to access delegates.",
                "warning",
            )
            return redirect(url_for("bp.billing", event_id=event_id))
        elif error == "expired":
            add_notification("Event has expired. Please renew.", "error")
            return redirect(url_for("bp.billing", event_id=event_id))
        else:
            add_notification("Access denied", "error")
            return redirect(url_for("bp.dashboard"))

    if request.method == "POST":
        name = bleach.clean(request.form.get("name"))
        email = bleach.clean(request.form.get("email"))
        country = bleach.clean(request.form.get("country"))
        committee_id = bleach.clean(request.form.get("committee_id")) or None
        password = request.form.get("password") or "changeme"

        # Check if user exists
        existing = convex_client.query("/api/getUserByEmail", {"email": email})
        if existing:
            add_notification("Email already registered", "error")
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

            new_count = len(delegate_assignments) + 1
            convex_client.mutation(
                "/api/updateEventDelegateCount",
                {
                    "eventId": str(event_id),
                    "count": new_count,
                },
            )
        except Exception as e:
            add_notification(f"Error creating delegate: {e}", "error")

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


@bp.route("/events/<event_id>/delegates/manage", methods=["GET", "POST"])
def manage_delegates(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    can_access, error = check_event_access(event_id)
    if not can_access:
        if error == "unpaid":
            add_notification(
                "Event requires payment. Please complete billing to manage delegates.",
                "warning",
            )
            return redirect(url_for("bp.billing", event_id=event_id))
        elif error == "expired":
            add_notification("Event has expired. Please renew.", "error")
            return redirect(url_for("bp.billing", event_id=event_id))
        else:
            add_notification("Access denied", "error")
            return redirect(url_for("bp.dashboard"))

    committee_id = request.args.get("committee_id")

    if request.method == "POST":
        name = bleach.clean(request.form.get("name"))
        email = bleach.clean(request.form.get("email"))
        country = bleach.clean(request.form.get("country"))
        delegate_committee_id = bleach.clean(request.form.get("committee_id")) or None
        password = request.form.get("password") or "changeme"

        args = {
            "email": email,
            "passwordHash": generate_password_hash(password),
            "name": name,
            "country": country,
        }
        try:
            user_id = convex_client.mutation("/api/createDelegate", args)
            if delegate_committee_id and user_id:
                convex_client.mutation(
                    "/api/assignDelegateToCommittee",
                    {
                        "eventId": str(event_id),
                        "userId": str(user_id),
                        "committeeId": str(delegate_committee_id),
                    },
                )
            add_notification("Delegate added successfully", "success")
        except Exception as e:
            add_notification(f"Error adding delegate: {e}", "error")

        return redirect(url_for("bp.manage_delegates", event_id=event_id))

    committees = (
        convex_client.query("/api/getCommitteesByEvent", {"eventId": str(event_id)})
        or []
    )

    event = convex_client.query("/api/getEventById", {"id": str(event_id)})

    delegate_assignments = (
        convex_client.query("/api/getDelegatesByEvent", {"eventId": str(event_id)})
        or []
    )
    all_delegates = convex_client.query("/api/getAllDelegates") or []

    delegates = []
    for assignment in delegate_assignments:
        user_id = assignment.get("userId")
        for user in all_delegates:
            if str(user.get("_id") or user.get("id")) == str(user_id):
                assignment_committee_id = assignment.get("committeeId")
                committee_name = ""
                if assignment_committee_id:
                    for c in committees:
                        if str(c.get("_id") or c.get("id")) == str(
                            assignment_committee_id
                        ):
                            committee_name = c.get("name")
                            break
                delegates.append(
                    {
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "country": user.get("country"),
                        "id": user.get("_id") or user.get("id"),
                        "committee": committee_name,
                        "committee_id": assignment_committee_id,
                    }
                )
                break

    sorted_committees = sorted(committees, key=lambda x: x.get("name", "").lower())

    all_users = convex_client.query("/api/getAllDelegates") or []

    def find_user_email_by_name(name):
        if not name:
            return None
        name_lower = name.lower()
        for u in all_users:
            if name_lower in u.get("name", "").lower():
                return u.get("email")
        return None

    grouped = []
    for c in sorted_committees:
        committee_delegates = [
            d
            for d in delegates
            if d.get("committee_id") == c.get("_id")
            or d.get("committee_id") == c.get("id")
        ]
        chair_name = c.get("chair")
        co_chair_name = c.get("coChair")
        c["chair_email"] = find_user_email_by_name(chair_name) if chair_name else None
        c["coChair_email"] = (
            find_user_email_by_name(co_chair_name) if co_chair_name else None
        )
        grouped.append({"committee": c, "delegates": committee_delegates})

    unassigned = [d for d in delegates if not d.get("committee_id")]

    return render_template(
        "delegates_manage.html",
        event_id=event_id,
        event=event,
        committees=committees,
        committee_id=committee_id,
        delegates=delegates,
        grouped=grouped,
        unassigned=unassigned,
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
        committee_id = assignment.get("committeeId")

        for user in all_delegates:
            if str(user.get("_id") or user.get("id")) == str(user_id):
                committee_name = ""
                role = "delegate"

                if committee_id:
                    for c in committees:
                        if str(c.get("_id") or c.get("id")) == str(committee_id):
                            committee_name = c.get("name")
                            chair = c.get("chair", "")
                            co_chair = c.get("coChair", "")

                            if (
                                chair
                                and user.get("email")
                                and chair.lower() in user.get("email", "").lower()
                            ):
                                role = "chair"
                            elif (
                                co_chair
                                and user.get("email")
                                and co_chair.lower() in user.get("email", "").lower()
                            ):
                                role = "co_chair"
                            break

                rows.append(
                    {
                        "Name": user.get("name") or "",
                        "Email": user.get("email") or "",
                        "Country": user.get("country") or "",
                        "Committee": committee_name,
                        "Role": role,
                        "Password": "",
                    }
                )
                break

    rows.sort(
        key=lambda r: (
            r["Committee"] or "",
            {"chair": 0, "co_chair": 1, "delegate": 2}.get(r["Role"], 2),
            r["Name"] or "",
        )
    )

    si = io.StringIO()
    fieldnames = ["Name", "Email", "Country", "Committee", "Role", "Password"]
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

    can_access, error = check_event_access(event_id)
    if not can_access:
        if error == "unpaid":
            add_notification(
                "Event requires payment. Please complete billing to access chat.",
                "warning",
            )
            return redirect(url_for("bp.billing", event_id=event_id))
        elif error == "expired":
            add_notification("Event has expired. Please renew.", "error")
            return redirect(url_for("bp.billing", event_id=event_id))
        else:
            add_notification("Access denied", "error")
            return redirect(url_for("bp.dashboard"))

    if request.method == "POST":
        text = bleach.clean(request.form.get("message"))
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
                add_notification(f"Error sending message: {e}", "error")

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

    can_access, error = check_event_access(event_id)
    if not can_access:
        if error == "unpaid":
            return redirect(url_for("bp.billing", event_id=event_id))
        elif error == "expired":
            add_notification("Event has expired. Please renew.", "error")
            return redirect(url_for("bp.billing", event_id=event_id))
        else:
            add_notification("Access denied", "error")
            return redirect(url_for("bp.dashboard"))

    if request.method == "POST":
        title = bleach.clean(request.form.get("title"))
        content = bleach.clean(request.form.get("content"))
        if title and content:
            try:
                convex_client.mutation(
                    "/api/createAnnouncement",
                    {
                        "eventId": str(event_id),
                        "title": title,
                        "content": content,
                        "createdBy": session.get("user_name"),
                    },
                )
                add_notification("Announcement created successfully", "success")
            except Exception as e:
                add_notification(f"Error creating announcement: {e}", "error")
        else:
            add_notification("Title and content are required", "error")
        return redirect(url_for("bp.announcements", event_id=event_id))

    announcements = (
        convex_client.query("/api/getAnnouncementsByEvent", {"eventId": str(event_id)})
        or []
    )
    event = convex_client.query("/api/getEventById", {"id": event_id})
    return render_template(
        "announcements.html",
        announcements=announcements,
        event=event,
        event_id=event_id,
    )


@bp.route("/events/<event_id>/manage", methods=["GET", "POST"])
def manage_event(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    event = convex_client.query("/api/getEventById", {"id": event_id})
    if not event:
        add_notification("Event not found", "error")
        return redirect(url_for("bp.events"))

    if request.method == "POST":
        action = bleach.clean(request.form.get("action"))

        if action == "update":
            name = bleach.clean(request.form.get("name"))
            description = bleach.clean(request.form.get("description"))
            start_date_str = bleach.clean(request.form.get("start_date"))
            end_date_str = bleach.clean(request.form.get("end_date"))

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
                add_notification("Event updated successfully", "success")
            except Exception as e:
                add_notification(f"Error updating event: {e}", "error")

        elif action == "delete":
            try:
                convex_client.mutation("/api/deleteEvent", {"id": event_id})
                add_notification("Event deleted successfully", "success")
                return redirect(url_for("bp.events"))
            except Exception as e:
                add_notification(f"Error deleting event: {e}", "error")

        return redirect(url_for("bp.manage_event", event_id=event_id))

    return render_template("manage_events.html", event=event, event_id=event_id)


@bp.route("/announcements/<announcement_id>/delete", methods=["POST"])
def delete_announcement(announcement_id):
    if "user_id" not in session or session.get("role") != "organizer":
        return redirect(url_for("bp.login"))
    # Need to implement delete mutation
    add_notification("Announcement deleted", "success")
    return redirect(url_for("bp.dashboard"))


@bp.route("/events/<event_id>/billing", methods=["GET", "POST"])
def billing(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    event = convex_client.query("/api/getEventById", {"id": str(event_id)})
    if not event:
        add_notification("Event not found", "error")
        return redirect(url_for("bp.dashboard"))

    status = (
        convex_client.query("/api/getEventPaymentStatus", {"eventId": str(event_id)})
        or {}
    )
    is_paid = status.get("isPaid", False)
    plan = status.get("plan", "small")
    delegate_count = status.get("delegateCount", 0)

    if request.method == "POST":
        selected_plan = bleach.clean(request.form.get("plan"))
        is_upgrade = bleach.clean(request.form.get("is_upgrade")) == "true"
        current_plan = bleach.clean(request.form.get("current_plan", plan))

        site_url = os.getenv("CONVEX_SITE_URL")
        success_url = f"{site_url}/events/{event_id}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{site_url}/events/{event_id}/billing?canceled=true"

        user = convex_client.query(
            "/api/getUserById", {"id": str(session.get("user_id"))}
        )

        checkout_url = create_checkout_session(
            user_email=user.get("email") if user else "",
            user_name=user.get("name") if user else "",
            event_id=str(event_id),
            event_name=event.get("name", ""),
            plan=selected_plan,
            success_url=success_url,
            cancel_url=cancel_url,
            is_upgrade=is_upgrade,
            current_plan=current_plan,
            delegate_count=delegate_count,
        )

        if checkout_url:
            return redirect(checkout_url)
        elif is_upgrade:
            add_notification("You're already on this plan or a higher plan", "info")
        else:
            add_notification(
                "Event created but payment skipped. Please complete payment.", "warning"
            )
            return redirect(url_for("bp.billing", event_id=event_id))

    max_delegates = PRICING.get(plan, {}).get("max_delegates", 100)
    can_upgrade = plan != "large"

    return render_template(
        "billing.html",
        event=event,
        event_id=event_id,
        is_paid=is_paid,
        plan=plan,
        delegate_count=delegate_count,
        max_delegates=max_delegates,
        pricing=PRICING,
        can_upgrade=can_upgrade,
    )


@bp.route("/events/<event_id>/billing/success")
def billing_success(event_id):
    if "user_id" not in session:
        return redirect(url_for("bp.login"))

    session_id = request.args.get("session_id")
    if not session_id:
        add_notification("Invalid session", "error")
        return redirect(url_for("bp.billing", event_id=event_id))

    verification = verify_payment(session_id)
    if not verification.get("paid"):
        add_notification("Payment not verified", "error")
        return redirect(url_for("bp.billing", event_id=event_id))

    event = convex_client.query("/api/getEventById", {"id": str(event_id)})
    if not event:
        add_notification("Event not found", "error")
        return redirect(url_for("bp.dashboard"))

    plan = request.args.get("plan", "small")
    expires_at = int((datetime.utcnow() + timedelta(days=90)).timestamp() * 1000)

    convex_client.mutation(
        "/api/updateEventPayment",
        {
            "eventId": str(event_id),
            "stripeSessionId": session_id,
            "stripePaymentIntentId": "",
            "plan": plan,
            "expiresAt": expires_at,
        },
    )

    add_notification("Payment successful! Your event is now active.", "success")
    return redirect(url_for("bp.manage_event", event_id=event_id))


@bp.route("/notifications")
@login_required()
def get_notifications():
    return jsonify(session.get("notifications", []))


@bp.route("/notifications/clear", methods=["POST"])
@login_required()
def clear_notifications():
    session["notifications"] = []
    return jsonify({"success": True})


@bp.route("/notifications/clear/<int:notification_index>", methods=["POST"])
@login_required()
def clear_notification(notification_index):
    if "notifications" in session and 0 <= notification_index < len(
        session["notifications"]
    ):
        session["notifications"].pop(notification_index)
        session.modified = True
    return jsonify({"success": True})


@bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")

    event = construct_webhook_event(payload, signature)
    if not event:
        return jsonify({"error": "Invalid webhook"}), 400

    if event.get("type") == "checkout.session.completed":
        data = event.get("data", {}).get("object", {})
        event_id = data.get("metadata", {}).get("event_id")
        plan = data.get("metadata", {}).get("plan", "small")

        if event_id:
            expires_at = int(
                (datetime.utcnow() + timedelta(days=90)).timestamp() * 1000
            )
            convex_client.mutation(
                "/api/updateEventPayment",
                {
                    "eventId": event_id,
                    "stripeSessionId": data.get("id", ""),
                    "stripePaymentIntentId": data.get("payment_intent", ""),
                    "plan": plan,
                    "expiresAt": expires_at,
                },
            )

    return jsonify({"success": True}), 200
