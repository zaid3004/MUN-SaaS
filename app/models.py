# app/models.py - Database models for the MUN management system
from datetime import datetime
from . import db

# Core user model (organizers and delegates)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    password_plain = db.Column(db.String(128), nullable=True)  # explicit plaintext password for admin use (MVP only)
    role = db.Column(db.String(20), nullable=False)  # 'organizer' or 'delegate'
    # simple tenancy: organizer relationship via organizer_id (nullable for delegates under admin domain)
    organizer_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(60), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

class Organizer(db.Model):
    __tablename__ = 'organizers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Organizer {self.name}>"

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organizer = db.relationship('Organizer', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f"<Event {self.name}>"

class Committee(db.Model):
    __tablename__ = 'committees'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    agenda = db.Column(db.Text, nullable=True)
    chair = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('committees', lazy=True))

    def __repr__(self):
        return f"<Committee {self.name}>"

class DelegateAssignment(db.Model):
    __tablename__ = 'delegate_assignments'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    committee_id = db.Column(db.Integer, db.ForeignKey('committees.id'), nullable=True)

    event = db.relationship('Event', backref=db.backref('delegate_assignments', lazy=True))
    user = db.relationship('User', backref=db.backref('delegate_assignments', lazy=True))
    committee = db.relationship('Committee', backref=db.backref('delegates', lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DelegateAssignment event_id={self.event_id} user_id={self.user_id}>"

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=True)  # e.g., position_paper, draft_resolution, notes
    filename = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=True)
    storage_url = db.Column(db.String(1024), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('documents', lazy=True))
    uploader = db.relationship('User', backref=db.backref('documents', lazy=True))

    def __repr__(self):
        return f"<Document {self.filename} for event {self.event_id}>"

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('chat_messages', lazy=True))
    sender = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

    def __repr__(self):
        return f"<ChatMessage {self.id} by {self.sender_id}>"


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy=True))

    def __repr__(self):
        return f"<PasswordResetToken for user {self.user_id}>"


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)

    event = db.relationship('Event', backref=db.backref('announcements', lazy=True, order_by='Announcement.created_at.desc()'))
    creator = db.relationship('User', backref=db.backref('announcements', lazy=True))

    def __repr__(self):
        return f"<Announcement {self.title} for event {self.event_id}>"
