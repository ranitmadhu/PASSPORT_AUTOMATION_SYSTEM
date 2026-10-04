import unittest
import os
import io
import sys

# Add project root path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from models import db, User, Application, Document, PoliceReport, RegionalVerification, Appointment, AuditLog

class ComprehensivePASFlowTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed demo data
            from seed import seed_database
            seed_database()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_all_pages_and_routes(self):
        # 1. Public Home Page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Passport Automation System', res.data)

        # 2. Public Tracking API
        res = self.client.get('/api/track/PAS-2026-104821')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'PAS-2026-104821', res.data)

        # 3. Login for all 4 Roles & View Dashboards
        creds = [
            ('applicant', 'password123'),
            ('admin', 'password123'),
            ('regional_mea', 'password123'),
            ('police_officer', 'password123')
        ]
        for username, password in creds:
            res = self.client.post('/login', data=dict(username=username, password=password), follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Dashboard', res.data)

        # 4. View Application Detail Pages for each role
        with app.app_context():
            apps = Application.query.all()
            for app_obj in apps:
                # Passport Admin viewing detail
                self.client.post('/login', data=dict(username='admin', password='password123'), follow_redirects=True)
                res = self.client.get(f'/application/{app_obj.id}')
                self.assertEqual(res.status_code, 200)
                self.assertIn(app_obj.application_number.encode(), res.data)

        # 5. File Upload & Apply Passport as Applicant
        self.client.post('/login', data=dict(username='applicant', password='password123'), follow_redirects=True)
        doc1 = (io.BytesIO(b"Dummy Aadhaar File Content"), "test_aadhaar.pdf")
        doc2 = (io.BytesIO(b"Dummy Address File Content"), "test_address.pdf")
        
        res = self.client.post('/applicant/apply', data=dict(
            application_type='new',
            passport_type='ordinary_36',
            given_name='Integration',
            surname='Tester',
            dob='1999-09-09',
            gender='Male',
            place_of_birth='TestCity',
            aadhaar_number='999988887777',
            pan_number='TESTP1234F',
            voter_id='VOTER123',
            father_name='Father Tester',
            mother_name='Mother Tester',
            present_address='123 Test Street',
            permanent_address='123 Test Street',
            pin_code='110001',
            police_station_name='Test Police Station',
            identity_proof=doc1,
            address_proof=doc2
        ), content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'submitted successfully', res.data)

        # 6. Admin auto check, route regional, route police
        with app.app_context():
            new_app = Application.query.filter_by(given_name='Integration').first()
            new_app_id = new_app.id

        self.client.post('/login', data=dict(username='admin', password='password123'), follow_redirects=True)
        res = self.client.post(f'/passport_admin/auto_check/{new_app_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        res = self.client.post(f'/passport_admin/route_regional/{new_app_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        res = self.client.post(f'/passport_admin/route_police/{new_app_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 7. Regional Admin verification
        self.client.post('/login', data=dict(username='regional_mea', password='password123'), follow_redirects=True)
        res = self.client.post(f'/regional_admin/verify/{new_app_id}', data=dict(
            decision='verified',
            data_validated='on',
            identity_confirmed='on',
            remarks='Data verified by MEA'
        ), follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 8. Police report submission
        self.client.post('/login', data=dict(username='police_officer', password='password123'), follow_redirects=True)
        res = self.client.post(f'/police/submit_report/{new_app_id}', data=dict(
            verification_status='clear',
            address_verified='on',
            witness1_name='Witness A',
            witness1_contact='1234567890',
            remarks='Address clear'
        ), follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 9. Passport Admin issue & dispatch
        self.client.post('/login', data=dict(username='admin', password='password123'), follow_redirects=True)
        res = self.client.post(f'/passport_admin/approve/{new_app_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Passport approved and document generated', res.data)

        res = self.client.post(f'/passport_admin/dispatch/{new_app_id}', data=dict(
            tracking_id='SPEEDPOST-TEST-123'
        ), follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Passport marked as dispatched', res.data)

if __name__ == '__main__':
    unittest.main()
