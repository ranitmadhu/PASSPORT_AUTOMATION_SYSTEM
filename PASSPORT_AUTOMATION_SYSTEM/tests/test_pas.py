import unittest
import os
import sys

# Add project root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from app import app
from models import db, User, Application, PoliceReport, RegionalVerification, Appointment

class PassportAutomationSystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed Test Users
            self.applicant = User(username='test_applicant', email='app@test.com', role='applicant', full_name='Test Applicant', jurisdiction_pin='110001')
            self.applicant.set_password('pass123')

            self.admin = User(username='test_admin', email='admin@test.com', role='passport_admin', full_name='Test Admin', jurisdiction_pin='110001')
            self.admin.set_password('pass123')

            self.regional = User(username='test_regional', email='regional@test.com', role='regional_admin', full_name='Test Regional', jurisdiction_pin='110001')
            self.regional.set_password('pass123')

            self.police = User(username='test_police', email='police@test.com', role='police', full_name='Test Police', jurisdiction_pin='110001')
            self.police.set_password('pass123')

            db.session.add_all([self.applicant, self.admin, self.regional, self.police])
            db.session.commit()
            self.applicant_id = self.applicant.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_user_login_and_logout(self):
        res = self.login('test_applicant', 'pass123')
        self.assertIn(b'Welcome back, Test Applicant', res.data)

        res = self.logout()
        self.assertIn(b'Logged out successfully', res.data)

    def test_unauthorized_admin_registration_blocked(self):
        # Attempt to register as passport_admin without security code
        res = self.client.post('/register', data=dict(
            username='hacker_admin',
            email='hacker@test.com',
            password='password123',
            full_name='Hacker Admin',
            role='passport_admin',
            admin_code='invalid_code'
        ), follow_redirects=True)

        self.assertIn(b'Unauthorized admin registration attempt blocked', res.data)

        # Verify user was NOT created
        with app.app_context():
            user = User.query.filter_by(username='hacker_admin').first()
            self.assertIsNone(user)

        # Attempt registration WITH correct admin authorization key
        res_success = self.client.post('/register', data=dict(
            username='valid_admin',
            email='valid_admin@test.com',
            password='password123',
            full_name='Valid Admin',
            role='passport_admin',
            admin_code='PAS-ADMIN-SECRET-2026'
        ), follow_redirects=True)

        self.assertIn(b'Registration successful', res_success.data)

    def test_full_passport_workflow_lifecycle(self):
        # 1. Login as Applicant & Submit Application
        self.login('test_applicant', 'pass123')
        res = self.client.post('/applicant/apply', data=dict(
            application_type='new',
            passport_type='ordinary_36',
            given_name='Rahul',
            surname='Sharma',
            dob='1995-05-15',
            gender='Male',
            place_of_birth='Delhi',
            aadhaar_number='123456789012',
            pan_number='ABCDE1234F',
            voter_id='DL123456',
            father_name='Rakesh Sharma',
            mother_name='Anita Sharma',
            present_address='123 Park Street, Delhi',
            permanent_address='123 Park Street, Delhi',
            pin_code='110001',
            police_station_name='Central Police Station'
        ), follow_redirects=True)

        self.assertIn(b'submitted successfully', res.data)

        with app.app_context():
            app_record = Application.query.filter_by(given_name='Rahul').first()
            self.assertIsNotNone(app_record)
            app_id = app_record.id
            self.assertEqual(app_record.status, 'submitted')

        self.logout()

        # 2. Login as Passport Admin & Run Automated DB Checks
        self.login('test_admin', 'pass123')
        res = self.client.post(f'/passport_admin/auto_check/{app_id}', follow_redirects=True)
        self.assertIn(b'Automated database verification checks PASSED', res.data)

        with app.app_context():
            app_record = db.session.get(Application, app_id)
            self.assertEqual(app_record.status, 'initial_check_passed')

        # Forward to Regional & Police
        self.client.post(f'/passport_admin/route_regional/{app_id}', follow_redirects=True)
        self.client.post(f'/passport_admin/route_police/{app_id}', follow_redirects=True)

        self.logout()

        # 3. Login as Regional Admin & Submit Verification
        self.login('test_regional', 'pass123')
        res = self.client.post(f'/regional_admin/verify/{app_id}', data=dict(
            decision='verified',
            data_validated='on',
            identity_confirmed='on',
            remarks='All documents verified'
        ), follow_redirects=True)
        self.assertIn(b'Regional MEA verification submitted: VERIFIED', res.data)

        self.logout()

        # 4. Login as Police & Submit PVR
        self.login('test_police', 'pass123')
        res = self.client.post(f'/police/submit_report/{app_id}', data=dict(
            verification_status='clear',
            address_verified='on',
            witness1_name='Neighbor 1',
            witness1_contact='9999999999',
            remarks='Residence address physically verified. No criminal record.'
        ), follow_redirects=True)
        self.assertIn(b'Police Verification Report (PVR) submitted successfully (CLEAR)', res.data)

        self.logout()

        # 5. Login as Passport Admin, Issue Passport & Dispatch
        self.login('test_admin', 'pass123')
        res = self.client.post(f'/passport_admin/approve/{app_id}', follow_redirects=True)
        self.assertIn(b'Passport approved and document generated', res.data)

        res = self.client.post(f'/passport_admin/dispatch/{app_id}', data=dict(
            tracking_id='SPEEDPOST-IN-TEST123'
        ), follow_redirects=True)
        self.assertIn(b'Passport marked as dispatched', res.data)

        with app.app_context():
            app_record = db.session.get(Application, app_id)
            self.assertEqual(app_record.status, 'dispatched')
            self.assertIsNotNone(app_record.passport_number)
            self.assertEqual(app_record.dispatch_tracking_id, 'SPEEDPOST-IN-TEST123')

    def test_public_tracking_api(self):
        with app.app_context():
            app_obj = Application(
                application_number='PAS-2026-999999',
                applicant_id=self.applicant_id,
                given_name='Test',
                surname='User',
                dob=date(1990, 1, 1),
                gender='Male',
                place_of_birth='City',
                present_address='Addr',
                permanent_address='Addr',
                pin_code='110001',
                police_station_name='Station',
                status='submitted'
            )
            db.session.add(app_obj)
            db.session.commit()

        res = self.client.get('/api/track/PAS-2026-999999')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data['found'])
        self.assertEqual(json_data['application_number'], 'PAS-2026-999999')

if __name__ == '__main__':
    unittest.main()
