from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from .storage_r2 import upload_to_r2
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Organizer, Event, Committee, DelegateAssignment, Document, ChatMessage, PasswordResetToken, Announcement
import os
from werkzeug.utils import secure_filename
import csv
import io
from flask import send_file
import secrets

bp = Blueprint('bp', __name__)

def login_required(role=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('bp.login'))
            if role and session.get('role') != role:
                return redirect(url_for('bp.dashboard'))
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

@bp.route('/')
def home():
    return redirect(url_for('bp.login'))

@bp.route('/health')
def health():
    return {'status': 'ok'}

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        if not all([name, email, password, password_confirm]):
            return render_template('register.html', error='All fields are required')
        if password != password_confirm:
            return render_template('register.html', error='Passwords do not match')
        # Create Organizer and initial organizer user
        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('register.html', error='Email already registered')
        organizer = Organizer(name=name, email=email)
        db.session.add(organizer)
        db.session.commit()
        user = User(email=email, password_hash=generate_password_hash(password), role='organizer', organizer_id=organizer.id, name=name)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['role'] = user.role
        session['organizer_id'] = organizer.id
        return redirect(url_for('bp.dashboard'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['organizer_id'] = user.organizer_id
            return redirect(url_for('bp.dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
            db.session.add(reset_token)
            db.session.commit()
            # In production, send email. For MVP, log to console
            print(f"PASSWORD RESET TOKEN for {email}: {token}")
            flash('Password reset instructions sent to your email', 'success')
        else:
            # Don't reveal if email exists
            flash('If an account exists with this email, password reset instructions have been sent', 'info')
        return redirect(url_for('bp.login'))
    return render_template('forgot_password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    if not reset_token or reset_token.used or reset_token.expires_at < datetime.utcnow():
        return render_template('reset_password.html', error='Invalid or expired token')
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not password or password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match')
        user = User.query.get(reset_token.user_id)
        user.password_hash = generate_password_hash(password)
        user.password_plain = password  # Update plain text for MVP
        reset_token.used = True
        db.session.commit()
        flash('Password reset successfully', 'success')
        return redirect(url_for('bp.login'))
    return render_template('reset_password.html', token=token)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('bp.login'))

@bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    organizer_id = session.get('organizer_id')
    events = Event.query.filter_by(organizer_id=organizer_id).all()
    # Get recent announcements for these events
    event_ids = [e.id for e in events]
    announcements = []
    if event_ids:
        announcements = Announcement.query.filter(Announcement.event_id.in_(event_ids)).order_by(Announcement.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', events=events, announcements=announcements, delegates=[], committees=[])

@bp.route('/events', methods=['GET', 'POST'])
def events():
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        description = request.form.get('description')
        organizer_id = session.get('organizer_id')
        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Name required'})
            return render_template('events.html', error='Name required')
        event = Event(organizer_id=organizer_id, name=name, start_date=start, end_date=end, description=description)
        db.session.add(event)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Event created successfully'})
        return redirect(url_for('bp.dashboard'))
    events = []
    if session.get('organizer_id'):
        events = Event.query.filter_by(organizer_id=session['organizer_id']).all()
    return render_template('events.html', events=events)

@bp.route('/events/<int:event_id>/committees', methods=['GET', 'POST'])
def committees(event_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        agenda = request.form.get('agenda')
        chair = request.form.get('chair')
        c = Committee(event_id=event_id, name=name, agenda=agenda, chair=chair)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('bp.committees', event_id=event_id))
    committees = Committee.query.filter_by(event_id=event_id).all()
    return render_template('committees.html', committees=committees, event_id=event_id)

@bp.route('/events/<int:event_id>/delegates', methods=['GET', 'POST'])
def delegates(event_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        country = request.form.get('country')
        committee_id = request.form.get('committee_id') or None
        password = request.form.get('password')
        # Create a delegate user belonging to current organizer with explicit password
        existing = User.query.filter_by(email=email).first()
        if existing:
            return redirect(url_for('bp.delegates', event_id=event_id))
        pw_hash = generate_password_hash(password) if password else generate_password_hash('changeme')
        delegate_user = User(email=email, password_hash=pw_hash, password_plain=password, role='delegate', organizer_id=session.get('organizer_id'), name=name, country=country)
        db.session.add(delegate_user)
        db.session.commit()
        assignment = DelegateAssignment(event_id=event_id, user_id=delegate_user.id, committee_id=int(committee_id) if committee_id else None)
        db.session.add(assignment)
        db.session.commit()
        return redirect(url_for('bp.delegates', event_id=event_id))
    # Optional: filter delegates by committee via query param
    committee_filter = request.args.get('committee_id')
    if committee_filter:
        try:
            delegates = DelegateAssignment.query.filter_by(event_id=event_id, committee_id=int(committee_filter)).all()
        except Exception:
            # Fallback if column doesn't exist yet
            delegates = DelegateAssignment.query.filter_by(event_id=event_id).all()
    else:
        delegates = DelegateAssignment.query.filter_by(event_id=event_id).all()
    # Build a simple list of delegates for display
    delegates_display = []
    for da in delegates:
        u = da.user
        committee_name = da.committee.name if da.committee else ''
        delegates_display.append({'name': u.name, 'email': u.email, 'country': u.country, 'id': u.id, 'committee': committee_name, 'committee_id': getattr(da, 'committee_id', None), 'password_plain': u.password_plain})
    committees = Committee.query.filter_by(event_id=event_id).all()
    return render_template('delegates.html', delegates=delegates_display, event_id=event_id, committees=committees)

@bp.route('/events/<int:event_id>/delegates/export_passwords')
def export_delegate_passwords(event_id):
    if 'user_id' not in session or session.get('role') != 'organizer':
        return redirect(url_for('bp.login'))
    # Gather delegates for this event with committee mapping
    assignments = DelegateAssignment.query.filter_by(event_id=event_id).all()
    rows = []
    for a in assignments:
        u = a.user
        committee_name = a.committee.name if a.committee else ''
        rows.append({'Name': u.name or '', 'Email': u.email or '', 'Country': u.country or '', 'Committee': committee_name, 'Password': (u.password_plain or '')})
    # Sort: by Committee then by Name ascending
    rows.sort(key=lambda r: (r['Committee'] or '', r['Name'] or ''))
    # Build CSV in memory
    si = io.StringIO()
    fieldnames = ['Name','Email','Country','Committee','Password']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({'Name': r['Name'], 'Email': r['Email'], 'Country': r['Country'], 'Committee': r['Committee'], 'Password': r['Password']})
    output = si.getvalue()
    return send_file(io.BytesIO(output.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'delegates_passwords_event_{event_id}.csv')

@bp.route('/events/<int:event_id>/delegates/manage', methods=['GET','POST'])
def delegates_manage(event_id):
    # Per-event, per-committee delegate management UI
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        country = request.form.get('country')
        committee_id = request.form.get('committee_id') or None
        password = request.form.get('password')
        existing = User.query.filter_by(email=email).first()
        if existing:
            return redirect(url_for('bp.delegates_manage', event_id=event_id))
        pw_hash = generate_password_hash(password) if password else generate_password_hash('changeme')
        delegate_user = User(email=email, password_hash=pw_hash, password_plain=password, role='delegate', organizer_id=session.get('organizer_id'), name=name, country=country)
        db.session.add(delegate_user)
        db.session.commit()
        assignment = DelegateAssignment(event_id=event_id, user_id=delegate_user.id, committee_id=int(committee_id) if committee_id else None)
        db.session.add(assignment)
        db.session.commit()
        return redirect(url_for('bp.delegates_manage', event_id=event_id))
    # Build grouped delegates by committee
    committees = Committee.query.filter_by(event_id=event_id).all()
    grouped = []
    for c in committees:
        assigns = DelegateAssignment.query.filter_by(event_id=event_id, committee_id=c.id).all()
        delegates = []
        for a in assigns:
            u = a.user
            delegates.append({
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'country': u.country,
            })
        grouped.append({'committee': c, 'delegates': delegates})
    # Unassigned delegates
    unassigned_assignments = DelegateAssignment.query.filter_by(event_id=event_id, committee_id=None).all()
    unassigned = []
    for a in unassigned_assignments:
        u = a.user
        unassigned.append({ 'id': u.id, 'name': u.name, 'email': u.email, 'country': u.country })
    return render_template('delegates_manage.html', grouped=grouped, unassigned=unassigned, event_id=event_id)

@bp.route('/events/<int:event_id>/delegates/<int:delegate_id>/documents')
def delegate_documents(event_id, delegate_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    docs = Document.query.filter_by(event_id=event_id, uploader_id=delegate_id).order_by(Document.uploaded_at.desc()).all()
    return render_template('delegate_documents.html', documents=docs, event_id=event_id, delegate_id=delegate_id)

@bp.route('/events/<int:event_id>/delegates/<int:delegate_id>/edit', methods=['GET', 'POST'])
def edit_delegate(event_id, delegate_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    user = User.query.get(delegate_id)
    if not user:
        return redirect(url_for('bp.delegates', event_id=event_id))
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.country = request.form.get('country')
        new_password = request.form.get('password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            user.password_plain = new_password
        committee_id = request.form.get('committee_id')
        # Update assignment
        assignment = DelegateAssignment.query.filter_by(event_id=event_id, user_id=delegate_id).first()
        if assignment:
            assignment.committee_id = int(committee_id) if committee_id else None
        db.session.commit()
        return redirect(url_for('bp.delegates', event_id=event_id))
    # GET: render a simple edit form
    assignment = DelegateAssignment.query.filter_by(event_id=event_id, user_id=delegate_id).first()
    committee_id = assignment.committee_id if assignment else None
    committees = Committee.query.filter_by(event_id=event_id).all()
    return render_template('delegate_edit.html', user=user, event_id=event_id, committee_id=committee_id, committees=committees)

@bp.route('/events/<int:event_id>/documents', methods=['GET', 'POST'])
def documents(event_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        # handle file upload to Cloudflare R2
        uploaded_file = request.files.get('document')
        doc_type = request.form.get('doc_type')
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            bucket = os.getenv('R2_BUCKET') or os.getenv('R2_BUCKET_NAME')
            if not bucket:
                return 'R2 bucket not configured', 500
            object_key = f"documents/event_{event_id}/{filename}"
            storage_url = upload_to_r2(uploaded_file, bucket, object_key, content_type=uploaded_file.mimetype or 'application/pdf')
            document = Document(event_id=event_id, uploader_id=session.get('user_id'), doc_type=doc_type, filename=filename, storage_url=storage_url)
            db.session.add(document)
            db.session.commit()
    # List documents for the event
    docs = Document.query.filter_by(event_id=event_id).order_by(Document.uploaded_at.desc()).all()
    return render_template('documents.html', documents=docs, event_id=event_id)

@bp.route('/documents/<int:doc_id>/download')
def download_document(doc_id):
    doc = Document.query.get(doc_id)
    if not doc:
        return 'Not found', 404
    if getattr(doc, 'storage_url', None):
        return redirect(doc.storage_url)
    if getattr(doc, 'file_path', None):
        return send_file(doc.file_path, as_attachment=True, download_name=doc.filename)
    return 'No storage URL available', 404

@bp.route('/events/<int:event_id>/chat', methods=['GET', 'POST'])
def chat(event_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    if request.method == 'POST':
        text = request.form.get('message')
        if text:
            msg = ChatMessage(event_id=event_id, sender_id=session.get('user_id'), message=text)
            db.session.add(msg)
            db.session.commit()
    messages = ChatMessage.query.filter_by(event_id=event_id).order_by(ChatMessage.timestamp).all()
    return render_template('chat.html', messages=messages, event_id=event_id)


@bp.route('/events/<int:event_id>/announcements', methods=['GET', 'POST'])
def announcements(event_id):
    if 'user_id' not in session:
        return redirect(url_for('bp.login'))
    # Only organizers can create announcements
    if request.method == 'POST' and session.get('role') == 'organizer':
        title = request.form.get('title')
        content = request.form.get('content')
        is_pinned = request.form.get('is_pinned') == 'on'
        if title and content:
            announcement = Announcement(
                event_id=event_id,
                title=title,
                content=content,
                created_by=session.get('user_id'),
                is_pinned=is_pinned
            )
            db.session.add(announcement)
            db.session.commit()
            flash('Announcement created successfully', 'success')
        return redirect(url_for('bp.announcements', event_id=event_id))
    # Show announcements with pinned first
    announcements_list = Announcement.query.filter_by(event_id=event_id).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).all()
    return render_template('announcements.html', announcements=announcements_list, event_id=event_id)


@bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
def delete_announcement(announcement_id):
    if 'user_id' not in session or session.get('role') != 'organizer':
        return redirect(url_for('bp.login'))
    announcement = Announcement.query.get_or_404(announcement_id)
    event_id = announcement.event_id
    db.session.delete(announcement)
    db.session.commit()
    flash('Announcement deleted', 'success')
    return redirect(url_for('bp.announcements', event_id=event_id))

@bp.route('/debug/schema', methods=['GET'])
def debug_schema():
    # Simple schema inspector for debugging during MVP
    from sqlalchemy import inspect
    try:
        inspector = inspect(db.engine)
        cols = inspector.get_columns('delegate_assignments')
        columns = []
        for c in cols:
            columns.append({
                'name': c.get('name'),
                'type': str(c.get('type')),
                'nullable': c.get('nullable', True),
                'default': c.get('default')
            })
        return {
            'table': 'delegate_assignments',
            'columns': columns,
        }
    except Exception as e:
        return {'error': str(e)}, 500
