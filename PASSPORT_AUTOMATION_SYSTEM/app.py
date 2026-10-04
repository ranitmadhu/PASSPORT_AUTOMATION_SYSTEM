import os
import random
import string
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    session, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
from config import Config
from models import (
    db, User, Application, Document, PoliceReport, 
    RegionalVerification, Appointment, AuditLog
)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

# Create database tables automatically
with app.app_context():
    db.create_all()

# --- HELPER FUNCTIONS & DECORATORS ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                flash('Unauthorized access for your account role.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(application_id, user_id, user_name, user_role, action, notes=None):
    audit = AuditLog(
        application_id=application_id,
        actor_id=user_id,
        actor_name=user_name,
        actor_role=user_role,
        action=action,
        notes=notes
    )
    db.session.add(audit)
    db.session.commit()

def generate_application_number():
    year = datetime.now().year
    digits = ''.join(random.choices(string.digits, k=6))
    return f"PAS-{year}-{digits}"

def generate_passport_number():
    prefix = random.choice(string.ascii_uppercase)
    digits = ''.join(random.choices(string.digits, k=7))
    return f"{prefix}{digits}"

def perform_automated_checks(application):
    """
    Simulates automated verification checks against centralized database:
    - Check duplicate active applications with same Aadhaar/PAN.
    - Check length & format of Aadhaar/PAN.
    - Check flag watchlists.
    """
    flags = []
    
    # 1. Format check
    if application.aadhaar_number and len(application.aadhaar_number.replace(" ", "").replace("-", "")) != 12:
        flags.append("Invalid Aadhaar card format (Must be 12 digits).")
        
    if application.pan_number and len(application.pan_number.strip()) != 10:
        flags.append("Invalid PAN card length (Must be 10 characters).")
        
    # 2. Check duplicate active application
    existing = Application.query.filter(
        Application.aadhaar_number == application.aadhaar_number,
        Application.id != application.id,
        Application.status.in_(['submitted', 'initial_check_passed', 'regional_approved', 'police_approved', 'passport_issued'])
    ).first()
    
    if existing:
        flags.append(f"Existing active passport/application found under same Aadhaar (#{existing.application_number}).")
        
    if flags:
        application.auto_check_status = 'flagged'
        application.auto_check_notes = " Automated Checks FLAGGED: " + " | ".join(flags)
        application.status = 'initial_check_failed'
    else:
        application.auto_check_status = 'passed'
        application.auto_check_notes = " All automated database checks PASSED cleanly (Aadhaar & Criminal records verified)."
        application.status = 'initial_check_passed'
        
    db.session.commit()
    return application.auto_check_status, application.auto_check_notes


# --- GLOBAL CONTEXT PROCESSOR ---
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
    return dict(current_user=user)


# --- PUBLIC & AUTH ROUTES ---

@app.route('/')
def index():
    total_apps = Application.query.count()
    issued_apps = Application.query.filter_by(status='passport_issued').count()
    pending_apps = Application.query.filter(Application.status.notin_(['passport_issued', 'dispatched', 'rejected'])).count()
    return render_template('index.html', total_apps=total_apps, issued_apps=issued_apps, pending_apps=pending_apps)

@app.route('/api/track/<app_number>')
def api_track(app_number):
    app_record = Application.query.filter_by(application_number=app_number.strip()).first()
    if not app_record:
        return jsonify({'found': False, 'message': 'Application record not found.'}), 404
    
    return jsonify({
        'found': True,
        'application_number': app_record.application_number,
        'applicant_name': f"{app_record.given_name} {app_record.surname}",
        'status': app_record.status,
        'application_type': app_record.application_type,
        'created_at': app_record.created_at.strftime('%Y-%m-%d %H:%M'),
        'passport_number': app_record.passport_number or 'N/A',
        'dispatch_tracking_id': app_record.dispatch_tracking_id or 'N/A'
    })

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        full_name = request.form.get('full_name').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'applicant')
        jurisdiction_pin = request.form.get('jurisdiction_pin', '').strip()
        admin_code = request.form.get('admin_code', '').strip()

        # SECURITY ENFORCEMENT: Restrict unauthorized Administrator self-registration
        if role != 'applicant':
            required_key = app.config.get('ADMIN_ACCESS_CODE', 'PAS-ADMIN-SECRET-2026')
            if admin_code != required_key:
                flash('🔒 Access Denied: Invalid Department Admin Authorization Key. Unauthorized admin registration attempt blocked.', 'danger')
                return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            role=role,
            full_name=full_name,
            phone=phone,
            jurisdiction_pin=jurisdiction_pin
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Automatically log in the newly registered user
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['full_name'] = user.full_name

        if user.role == 'applicant':
            flash('Registration successful! Complete your passport application below.', 'success')
            return redirect(url_for('apply_passport'))
        else:
            flash(f'Registration successful! Logged in as {user.full_name} ({user.role.upper()}).', 'success')
            return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            session['full_name'] = user.full_name
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/demo-login/<role>')
def demo_login(role):
    user = User.query.filter_by(role=role).first()
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['full_name'] = user.full_name
        flash(f'Switched to {user.full_name} ({user.role.upper()}).', 'info')
        return redirect(url_for('dashboard'))
    else:
        flash(f'No demo account found for role: {role}. Please run seed.py script.', 'danger')
        return redirect(url_for('login'))

@app.route('/portal/applicant')
def portal_applicant():
    if session.get('user_role') == 'applicant':
        return redirect(url_for('applicant_dashboard'))
    flash('Please log in with your Applicant account credentials.', 'info')
    return redirect(url_for('login'))

@app.route('/portal/admin')
def portal_admin():
    if session.get('user_role') in ['passport_admin', 'regional_admin', 'police']:
        return redirect(url_for('dashboard'))
    flash('Please log in with your Administrator account credentials.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('user_role')
    if role == 'applicant':
        return redirect(url_for('applicant_dashboard'))
    elif role == 'passport_admin':
        return redirect(url_for('passport_admin_dashboard'))
    elif role == 'regional_admin':
        return redirect(url_for('regional_admin_dashboard'))
    elif role == 'police':
        return redirect(url_for('police_dashboard'))
    else:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('index'))


# --- APPLICANT ROUTES ---

@app.route('/applicant/dashboard')
@login_required
@role_required(['applicant'])
def applicant_dashboard():
    applications = Application.query.filter_by(applicant_id=session['user_id']).order_by(Application.created_at.desc()).all()
    return render_template('applicant_dashboard.html', applications=applications)

@app.route('/applicant/apply', methods=['GET', 'POST'])
@login_required
@role_required(['applicant'])
def apply_passport():
    if request.method == 'POST':
        app_num = generate_application_number()
        
        dob_str = request.form.get('dob')
        try:
            dob_val = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format for Date of Birth.', 'danger')
            return redirect(url_for('apply_passport'))

        application = Application(
            application_number=app_num,
            applicant_id=session['user_id'],
            application_type=request.form.get('application_type', 'new'),
            passport_type=request.form.get('passport_type', 'ordinary_36'),
            given_name=request.form.get('given_name').strip(),
            surname=request.form.get('surname').strip(),
            dob=dob_val,
            gender=request.form.get('gender'),
            place_of_birth=request.form.get('place_of_birth').strip(),
            aadhaar_number=request.form.get('aadhaar_number', '').strip(),
            pan_number=request.form.get('pan_number', '').strip(),
            voter_id=request.form.get('voter_id', '').strip(),
            father_name=request.form.get('father_name', '').strip(),
            mother_name=request.form.get('mother_name', '').strip(),
            spouse_name=request.form.get('spouse_name', '').strip(),
            present_address=request.form.get('present_address').strip(),
            permanent_address=request.form.get('permanent_address').strip(),
            pin_code=request.form.get('pin_code').strip(),
            police_station_name=request.form.get('police_station_name').strip(),
            emergency_contact_name=request.form.get('emergency_contact_name', '').strip(),
            emergency_contact_phone=request.form.get('emergency_contact_phone', '').strip(),
            status='submitted'
        )
        
        db.session.add(application)
        db.session.flush() # get application.id

        # File Upload Handling
        doc_types = ['identity_proof', 'address_proof', 'dob_proof']
        for doc_type in doc_types:
            file = request.files.get(doc_type)
            if file and file.filename != '' and allowed_file(file.filename):
                sec_filename = secure_filename(file.filename)
                saved_filename = f"app_{application.id}_{doc_type}_{sec_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
                file.save(file_path)
                
                doc = Document(
                    application_id=application.id,
                    doc_type=doc_type,
                    file_name=saved_filename,
                    original_filename=sec_filename
                )
                db.session.add(doc)

        db.session.commit()
        
        log_audit(
            application.id, 
            session['user_id'], 
            session['full_name'], 
            session['user_role'], 
            'Application Submitted', 
            f'Submitted new passport application #{app_num}.'
        )

        flash(f'Application #{app_num} submitted successfully! Initial automated database check queued.', 'success')
        return redirect(url_for('applicant_dashboard'))

    applications = Application.query.filter_by(applicant_id=session['user_id']).order_by(Application.created_at.desc()).all()
    return render_template('applicant_dashboard.html', applications=applications, show_modal=True)


@app.route('/applicant/schedule_appointment/<int:app_id>', methods=['POST'])
@login_required
@role_required(['applicant'])
def applicant_schedule_appointment(app_id):
    application = db.get_or_404(Application, app_id)
    if application.applicant_id != session['user_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('applicant_dashboard'))

    appt_date_str = request.form.get('appointment_date')
    time_slot = request.form.get('time_slot')
    office_location = request.form.get('office_location', 'Regional Passport Office (RPO)')

    try:
        appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date selected for appointment.', 'danger')
        return redirect(url_for('application_detail', app_id=app_id))

    if application.appointment:
        application.appointment.appointment_date = appt_date
        application.appointment.time_slot = time_slot
        application.appointment.office_location = office_location
        application.appointment.status = 'scheduled'
    else:
        appt = Appointment(
            application_id=app_id,
            appointment_date=appt_date,
            time_slot=time_slot,
            office_location=office_location,
            status='scheduled'
        )
        db.session.add(appt)

    application.status = 'appointment_scheduled'
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Appointment Scheduled', f'Scheduled appointment on {appt_date} ({time_slot}) at {office_location}.'
    )
    flash('Passport office appointment scheduled successfully!', 'success')
    return redirect(url_for('application_detail', app_id=app_id))


# --- PASSPORT ADMIN ROUTES ---

@app.route('/passport_admin/dashboard')
@login_required
@role_required(['passport_admin'])
def passport_admin_dashboard():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    query = Application.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    if search_query:
        query = query.filter(
            (Application.application_number.ilike(f"%{search_query}%")) |
            (Application.given_name.ilike(f"%{search_query}%")) |
            (Application.surname.ilike(f"%{search_query}%")) |
            (Application.aadhaar_number.ilike(f"%{search_query}%"))
        )

    applications = query.order_by(Application.created_at.desc()).all()

    # Dashboard Metrics
    total = Application.query.count()
    submitted = Application.query.filter_by(status='submitted').count()
    in_verification = Application.query.filter(Application.status.in_(['initial_check_passed', 'regional_review_pending', 'police_verification_pending'])).count()
    ready_for_issuance = Application.query.filter(Application.status.in_(['police_approved', 'regional_approved'])).count()
    issued = Application.query.filter_by(status='passport_issued').count()

    return render_template(
        'passport_admin_dashboard.html',
        applications=applications,
        total=total,
        submitted=submitted,
        in_verification=in_verification,
        ready_for_issuance=ready_for_issuance,
        issued=issued,
        selected_status=status_filter,
        search_query=search_query
    )

@app.route('/passport_admin/auto_check/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin'])
def run_auto_check(app_id):
    application = db.get_or_404(Application, app_id)
    status, notes = perform_automated_checks(application)
    
    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Automated Checks Executed', f'Status: {status.upper()}. Notes: {notes}'
    )
    
    if status == 'passed':
        flash('Automated database verification checks PASSED successfully.', 'success')
    else:
        flash(f'Automated verification check FLAGGED issues: {notes}', 'warning')
        
    return redirect(url_for('application_detail', app_id=app_id))

@app.route('/passport_admin/route_regional/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin'])
def route_to_regional(app_id):
    application = db.get_or_404(Application, app_id)
    application.status = 'regional_review_pending'
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Routed to Regional MEA', 'Application forwarded to Regional Administrator for secondary verification.'
    )
    flash('Application forwarded to Regional Administrator (MEA).', 'info')
    return redirect(url_for('application_detail', app_id=app_id))

@app.route('/passport_admin/route_police/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin'])
def route_to_police(app_id):
    application = db.get_or_404(Application, app_id)
    application.status = 'police_verification_pending'
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Routed to Police Station', f'Automated police verification request sent to station: {application.police_station_name} (PIN: {application.pin_code}).'
    )
    flash(f'Automated verification request sent to local police station ({application.police_station_name}).', 'info')
    return redirect(url_for('application_detail', app_id=app_id))

@app.route('/passport_admin/approve/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin'])
def approve_and_issue(app_id):
    application = db.get_or_404(Application, app_id)
    
    pass_num = generate_passport_number()
    issue_dt = date.today()
    validity_years = 10 if application.passport_type != 'ordinary_60' else 10
    expiry_dt = issue_dt + timedelta(days=validity_years*365)

    application.status = 'passport_issued'
    application.passport_number = pass_num
    application.issue_date = issue_dt
    application.expiry_date = expiry_dt
    
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Passport Approved & Issued', f'Generated Passport #{pass_num}. Valid: {issue_dt} to {expiry_dt}.'
    )
    flash(f'Passport approved and document generated! Number: {pass_num}', 'success')
    return redirect(url_for('application_detail', app_id=app_id))

@app.route('/passport_admin/dispatch/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin'])
def dispatch_passport(app_id):
    application = db.get_or_404(Application, app_id)
    tracking_id = request.form.get('tracking_id', '').strip()
    
    if not tracking_id:
        tracking_id = f"SPEEDPOST-IN-{random.randint(10000000, 99999999)}"

    application.status = 'dispatched'
    application.dispatch_tracking_id = tracking_id
    application.dispatch_date = date.today()
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Passport Dispatched', f'Passport dispatched via Speed Post. Tracking ID: {tracking_id}'
    )
    flash(f'Passport marked as dispatched! Tracking ID: {tracking_id}', 'success')
    return redirect(url_for('application_detail', app_id=app_id))

@app.route('/passport_admin/reject/<int:app_id>', methods=['POST'])
@login_required
@role_required(['passport_admin', 'regional_admin'])
def reject_application(app_id):
    application = db.get_or_404(Application, app_id)
    reason = request.form.get('rejection_reason', 'Failed mandatory document verification.').strip()

    application.status = 'rejected'
    application.rejection_reason = reason
    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        'Application Rejected', f'Reason: {reason}'
    )
    flash('Application rejected.', 'danger')
    return redirect(url_for('application_detail', app_id=app_id))


# --- REGIONAL ADMIN (MEA) ROUTES ---

@app.route('/regional_admin/dashboard')
@login_required
@role_required(['regional_admin'])
def regional_admin_dashboard():
    pending_apps = Application.query.filter_by(status='regional_review_pending').order_by(Application.created_at.asc()).all()
    processed_apps = Application.query.join(RegionalVerification).filter(RegionalVerification.regional_officer_id == session['user_id']).all()
    
    return render_template(
        'regional_admin_dashboard.html', 
        pending_apps=pending_apps, 
        processed_apps=processed_apps
    )

@app.route('/regional_admin/verify/<int:app_id>', methods=['POST'])
@login_required
@role_required(['regional_admin'])
def regional_verify(app_id):
    application = db.get_or_404(Application, app_id)
    decision = request.form.get('decision') # verified, flagged, rejected
    remarks = request.form.get('remarks', '').strip()
    data_val = request.form.get('data_validated') == 'on'
    id_conf = request.form.get('identity_confirmed') == 'on'

    reg_ver = RegionalVerification.query.filter_by(application_id=app_id).first()
    if not reg_ver:
        reg_ver = RegionalVerification(
            application_id=app_id,
            regional_officer_id=session['user_id'],
            verification_status=decision,
            data_validated=data_val,
            identity_confirmed=id_conf,
            remarks=remarks
        )
        db.session.add(reg_ver)
    else:
        reg_ver.verification_status = decision
        reg_ver.data_validated = data_val
        reg_ver.identity_confirmed = id_conf
        reg_ver.remarks = remarks

    if decision == 'verified':
        application.status = 'regional_approved'
    elif decision == 'flagged':
        application.status = 'regional_flagged'
    elif decision == 'rejected':
        application.status = 'rejected'
        application.rejection_reason = f"Regional MEA rejection: {remarks}"

    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        f'Regional Verification ({decision.upper()})', f'Remarks: {remarks}'
    )
    flash(f'Regional MEA verification submitted: {decision.upper()}', 'success')
    return redirect(url_for('application_detail', app_id=app_id))


# --- LOCAL POLICE ROUTES ---

@app.route('/police/dashboard')
@login_required
@role_required(['police'])
def police_dashboard():
    officer = db.session.get(User, session['user_id'])
    
    # Filter by PIN code or police station if assigned
    query = Application.query.filter_by(status='police_verification_pending')
    if officer.jurisdiction_pin:
        query = query.filter_by(pin_code=officer.jurisdiction_pin)
        
    pending_verifications = query.order_by(Application.created_at.asc()).all()
    completed_verifications = Application.query.join(PoliceReport).filter(PoliceReport.police_officer_id == session['user_id']).all()

    return render_template(
        'police_dashboard.html',
        pending_verifications=pending_verifications,
        completed_verifications=completed_verifications,
        officer=officer
    )

@app.route('/police/submit_report/<int:app_id>', methods=['POST'])
@login_required
@role_required(['police'])
def police_submit_report(app_id):
    application = db.get_or_404(Application, app_id)

    ver_status = request.form.get('verification_status') # clear, adverse, incomplete
    address_ver = request.form.get('address_verified') == 'on'
    criminal_rec = request.form.get('criminal_records_found') == 'on'
    w1_name = request.form.get('witness1_name', '').strip()
    w1_phone = request.form.get('witness1_contact', '').strip()
    w2_name = request.form.get('witness2_name', '').strip()
    w2_phone = request.form.get('witness2_contact', '').strip()
    remarks = request.form.get('remarks', '').strip()

    pvr = PoliceReport.query.filter_by(application_id=app_id).first()
    if not pvr:
        pvr = PoliceReport(
            application_id=app_id,
            police_officer_id=session['user_id'],
            station_name=application.police_station_name or 'Local Station',
            verification_status=ver_status,
            address_verified=address_ver,
            criminal_records_found=criminal_rec,
            witness1_name=w1_name,
            witness1_contact=w1_phone,
            witness2_name=w2_name,
            witness2_contact=w2_phone,
            remarks=remarks
        )
        db.session.add(pvr)
    else:
        pvr.verification_status = ver_status
        pvr.address_verified = address_ver
        pvr.criminal_records_found = criminal_rec
        pvr.witness1_name = w1_name
        pvr.witness1_contact = w1_phone
        pvr.witness2_name = w2_name
        pvr.witness2_contact = w2_phone
        pvr.remarks = remarks

    if ver_status == 'clear':
        application.status = 'police_approved'
    elif ver_status == 'adverse':
        application.status = 'police_rejected'
        application.rejection_reason = f"Police adverse report: {remarks}"
    else:
        application.status = 'police_verification_pending'

    db.session.commit()

    log_audit(
        app_id, session['user_id'], session['full_name'], session['user_role'],
        f'Police Report Submitted ({ver_status.upper()})', f'PVR Status: {ver_status}. Address Verified: {address_ver}, Criminal Records: {criminal_rec}. Remarks: {remarks}'
    )
    flash(f'Police Verification Report (PVR) submitted successfully ({ver_status.upper()}).', 'success')
    return redirect(url_for('application_detail', app_id=app_id))


# --- APPLICATION DETAIL ROUTE ---

@app.route('/application/<int:app_id>')
@login_required
def application_detail(app_id):
    application = db.get_or_404(Application, app_id)
    user_role = session.get('user_role')
    user_id = session.get('user_id')

    # Security check: applicants can only view their own applications
    if user_role == 'applicant' and application.applicant_id != user_id:
        flash('Unauthorized access to application record.', 'danger')
        return redirect(url_for('applicant_dashboard'))

    audit_logs = AuditLog.query.filter_by(application_id=app_id).order_by(AuditLog.created_at.desc()).all()
    today_str = date.today().strftime('%Y-%m-%d')
    
    return render_template(
        'application_detail.html',
        application=application,
        audit_logs=audit_logs,
        today_str=today_str
    )

@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
