from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='applicant') # applicant, passport_admin, regional_admin, police
    full_name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    jurisdiction_pin = db.Column(db.String(10)) # For filtering police / regional jurisdiction
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    applications = db.relationship('Application', backref='applicant', lazy=True, foreign_keys='Application.applicant_id')
    police_reports = db.relationship('PoliceReport', backref='officer', lazy=True)
    regional_verifications = db.relationship('RegionalVerification', backref='officer', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='actor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    application_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Passport Application Details
    application_type = db.Column(db.String(32), nullable=False, default='new') # new, renewal
    passport_type = db.Column(db.String(32), nullable=False, default='ordinary_36') # ordinary_36, ordinary_60, official, diplomatic
    given_name = db.Column(db.String(64), nullable=False)
    surname = db.Column(db.String(64), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(16), nullable=False)
    place_of_birth = db.Column(db.String(128), nullable=False)
    
    # Identification
    aadhaar_number = db.Column(db.String(20), index=True)
    pan_number = db.Column(db.String(20))
    voter_id = db.Column(db.String(20))
    
    # Family Details
    father_name = db.Column(db.String(128))
    mother_name = db.Column(db.String(128))
    spouse_name = db.Column(db.String(128))
    
    # Address Details
    present_address = db.Column(db.Text, nullable=False)
    permanent_address = db.Column(db.Text, nullable=False)
    pin_code = db.Column(db.String(10), nullable=False, index=True)
    police_station_name = db.Column(db.String(128), nullable=False)
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(128))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Lifecycle & Workflow Status
    # Status options: 
    # 'submitted', 'initial_check_passed', 'initial_check_failed',
    # 'regional_review_pending', 'regional_approved', 'regional_flagged',
    # 'police_verification_pending', 'police_approved', 'police_rejected',
    # 'appointment_scheduled', 'approved_for_issuance',
    # 'passport_issued', 'dispatched', 'rejected'
    status = db.Column(db.String(32), nullable=False, default='submitted', index=True)
    
    # Automated Database Check Status
    auto_check_status = db.Column(db.String(32), default='pending') # pending, passed, flagged
    auto_check_notes = db.Column(db.Text)
    
    # Final Issued Passport Information
    passport_number = db.Column(db.String(32), unique=True, index=True)
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    dispatch_tracking_id = db.Column(db.String(64))
    dispatch_date = db.Column(db.Date)
    rejection_reason = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = db.relationship('Document', backref='application', cascade='all, delete-orphan', lazy=True)
    police_report = db.relationship('PoliceReport', backref='application', uselist=False, cascade='all, delete-orphan', lazy=True)
    regional_verification = db.relationship('RegionalVerification', backref='application', uselist=False, cascade='all, delete-orphan', lazy=True)
    appointment = db.relationship('Appointment', backref='application', uselist=False, cascade='all, delete-orphan', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='application', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Application {self.application_number} - {self.status}>'


class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    doc_type = db.Column(db.String(64), nullable=False) # identity_proof, address_proof, dob_proof, photo
    file_name = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Document {self.doc_type} for App #{self.application_id}>'


class PoliceReport(db.Model):
    __tablename__ = 'police_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), unique=True, nullable=False)
    police_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    station_name = db.Column(db.String(128), nullable=False)
    verification_status = db.Column(db.String(32), nullable=False) # clear, adverse, incomplete
    address_verified = db.Column(db.Boolean, default=False)
    criminal_records_found = db.Column(db.Boolean, default=False)
    witness1_name = db.Column(db.String(128))
    witness1_contact = db.Column(db.String(32))
    witness2_name = db.Column(db.String(128))
    witness2_contact = db.Column(db.String(32))
    remarks = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class RegionalVerification(db.Model):
    __tablename__ = 'regional_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), unique=True, nullable=False)
    regional_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    verification_status = db.Column(db.String(32), nullable=False) # verified, flagged, rejected
    data_validated = db.Column(db.Boolean, default=True)
    identity_confirmed = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.Text)
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), unique=True, nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(32), nullable=False)
    office_location = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(32), default='scheduled') # scheduled, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor_name = db.Column(db.String(128), nullable=False)
    actor_role = db.Column(db.String(32), nullable=False)
    action = db.Column(db.String(128), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
