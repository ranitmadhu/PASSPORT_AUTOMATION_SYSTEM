from datetime import date, datetime, timedelta
from app import app
from models import (
    db, User, Application, Document, PoliceReport, 
    RegionalVerification, Appointment, AuditLog
)

def seed_database():
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding demo users across all 4 system roles...")

        # -------------------------------------------------------------
        # 1. APPLICANTS
        # -------------------------------------------------------------
        applicant1 = User(
            username='applicant',
            email='applicant@example.com',
            role='applicant',
            full_name='Rajesh Kumar',
            phone='+91 9876543210',
            jurisdiction_pin='110001'
        )
        applicant1.set_password('password123')

        applicant2 = User(
            username='applicant2',
            email='priya.sharma@example.com',
            role='applicant',
            full_name='Priya Sharma',
            phone='+91 9811122334',
            jurisdiction_pin='110075'
        )
        applicant2.set_password('password123')

        applicant3 = User(
            username='applicant3',
            email='vikram.sengupta@example.com',
            role='applicant',
            full_name='Vikramaditya Sengupta',
            phone='+91 9833344455',
            jurisdiction_pin='700001'
        )
        applicant3.set_password('password123')

        applicant4 = User(
            username='applicant4',
            email='kavita.reddy@example.com',
            role='applicant',
            full_name='Kavita Reddy',
            phone='+91 9844455566',
            jurisdiction_pin='560001'
        )
        applicant4.set_password('password123')

        db.session.add_all([applicant1, applicant2, applicant3, applicant4])

        # -------------------------------------------------------------
        # 2. PASSPORT ADMINISTRATORS
        # -------------------------------------------------------------
        admin1 = User(
            username='admin',
            email='admin@passportindia.gov.in',
            role='passport_admin',
            full_name='Suresh Sharma (Chief Passport Officer)',
            phone='+91 9811100001',
            jurisdiction_pin='110001'
        )
        admin1.set_password('password123')

        admin2 = User(
            username='admin2',
            email='mehta.sunil@passportindia.gov.in',
            role='passport_admin',
            full_name='Sunil Mehta (Senior Admin Officer)',
            phone='+91 9811100002',
            jurisdiction_pin='110001'
        )
        admin2.set_password('password123')

        db.session.add_all([admin1, admin2])

        # -------------------------------------------------------------
        # 3. REGIONAL ADMINISTRATORS (MEA)
        # -------------------------------------------------------------
        regional1 = User(
            username='regional_mea',
            email='mea.delhi@passportindia.gov.in',
            role='regional_admin',
            full_name='Ananya Sen (Regional MEA Director - Northern Zone)',
            phone='+91 9822200001',
            jurisdiction_pin='110001'
        )
        regional1.set_password('password123')

        regional2 = User(
            username='regional_mea2',
            email='mea.kolkata@passportindia.gov.in',
            role='regional_admin',
            full_name='Dr. Arindam Bose (Regional MEA Director - Eastern Zone)',
            phone='+91 9822200002',
            jurisdiction_pin='700001'
        )
        regional2.set_password('password123')

        db.session.add_all([regional1, regional2])

        # -------------------------------------------------------------
        # 4. LOCAL POLICE OFFICERS
        # -------------------------------------------------------------
        police1 = User(
            username='police_officer',
            email='station.head@delhipolice.gov.in',
            role='police',
            full_name='Inspector Vikram Singh (Connaught Place PS)',
            phone='+91 9833300001',
            jurisdiction_pin='110001'
        )
        police1.set_password('password123')

        police2 = User(
            username='police_officer2',
            email='station.dwarka@delhipolice.gov.in',
            role='police',
            full_name='Inspector Rajeev Meena (Dwarka Sector 9 PS)',
            phone='+91 9833300002',
            jurisdiction_pin='110075'
        )
        police2.set_password('password123')

        police3 = User(
            username='police_officer3',
            email='station.parkstreet@kolkatapolice.gov.in',
            role='police',
            full_name='Sub-Inspector Subhash Ghosh (Park Street PS)',
            phone='+91 9833300003',
            jurisdiction_pin='700001'
        )
        police3.set_password('password123')

        db.session.add_all([police1, police2, police3])
        db.session.commit()
        print("Demo users seeded successfully.")

        # -------------------------------------------------------------
        # 5. SAMPLE APPLICATIONS ACROSS LIFECYCLE STAGES
        # -------------------------------------------------------------
        print("Seeding sample passport applications...")

        # Application 1: Newly Submitted (Fresh Passport)
        app1 = Application(
            application_number='PAS-2026-104821',
            applicant_id=applicant1.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Rajesh',
            surname='Kumar',
            dob=date(1995, 5, 14),
            gender='Male',
            place_of_birth='New Delhi',
            aadhaar_number='987654321012',
            pan_number='ABCDE1234F',
            voter_id='DL1234567',
            father_name='Ramesh Kumar',
            mother_name='Sunita Devi',
            spouse_name='',
            present_address='H.No 42, Connaught Place, New Delhi',
            permanent_address='H.No 42, Connaught Place, New Delhi',
            pin_code='110001',
            police_station_name='Connaught Place Police Station',
            emergency_contact_name='Ramesh Kumar',
            emergency_contact_phone='+91 9876500000',
            status='submitted',
            created_at=datetime.now() - timedelta(hours=2)
        )

        # Application 2: Regional Review Pending (Automated Checks Passed)
        app2 = Application(
            application_number='PAS-2026-209482',
            applicant_id=applicant2.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Priya',
            surname='Sharma',
            dob=date(1998, 8, 22),
            gender='Female',
            place_of_birth='Jaipur',
            aadhaar_number='876543210987',
            pan_number='FGHIJ5678K',
            voter_id='RJ9876543',
            father_name='Mahesh Sharma',
            mother_name='Kavita Sharma',
            spouse_name='',
            present_address='Flat 201, Rosewood Heights, Dwarka, New Delhi',
            permanent_address='Flat 201, Rosewood Heights, Dwarka, New Delhi',
            pin_code='110075',
            police_station_name='Dwarka Sector 9 Police Station',
            emergency_contact_name='Mahesh Sharma',
            emergency_contact_phone='+91 9876511111',
            status='regional_review_pending',
            auto_check_status='passed',
            auto_check_notes='All automated database checks PASSED cleanly (Aadhaar & Criminal records verified).',
            created_at=datetime.now() - timedelta(days=1)
        )

        # Application 3: Police Verification Pending (Renewal)
        app3 = Application(
            application_number='PAS-2026-304918',
            applicant_id=applicant1.id,
            application_type='renewal',
            passport_type='ordinary_60',
            given_name='Amitabh',
            surname='Verma',
            dob=date(1988, 11, 30),
            gender='Male',
            place_of_birth='Lucknow',
            aadhaar_number='765432109876',
            pan_number='LMNOP9012Q',
            voter_id='UP4567890',
            father_name='Satish Verma',
            mother_name='Rita Verma',
            spouse_name='Neha Verma',
            present_address='Block B, House 12, Janakpuri, New Delhi',
            permanent_address='Block B, House 12, Janakpuri, New Delhi',
            pin_code='110001',
            police_station_name='Connaught Place Police Station',
            emergency_contact_name='Neha Verma',
            emergency_contact_phone='+91 9876522222',
            status='police_verification_pending',
            auto_check_status='passed',
            auto_check_notes='Automated checks PASSED.',
            created_at=datetime.now() - timedelta(days=2)
        )

        # Application 4: Passport Issued & Dispatched
        app4 = Application(
            application_number='PAS-2026-409123',
            applicant_id=applicant1.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Siddharth',
            surname='Malhotra',
            dob=date(1992, 3, 10),
            gender='Male',
            place_of_birth='Mumbai',
            aadhaar_number='654321098765',
            pan_number='RSTUV3456W',
            voter_id='MH1122334',
            father_name='Vinod Malhotra',
            mother_name='Sushma Malhotra',
            spouse_name='',
            present_address='Plot 15, Vasant Vihar, New Delhi',
            permanent_address='Plot 15, Vasant Vihar, New Delhi',
            pin_code='110057',
            police_station_name='Vasant Vihar Police Station',
            emergency_contact_name='Vinod Malhotra',
            emergency_contact_phone='+91 9876533333',
            status='passport_issued',
            auto_check_status='passed',
            auto_check_notes='Automated checks PASSED.',
            passport_number='Z8492019',
            issue_date=date.today() - timedelta(days=5),
            expiry_date=date.today() + timedelta(days=3645),
            dispatch_tracking_id='SPEEDPOST-IN-98210492',
            dispatch_date=date.today() - timedelta(days=3),
            created_at=datetime.now() - timedelta(days=7)
        )

        # Application 5: Police Approved (Ready for Admin Final Approval)
        app5 = Application(
            application_number='PAS-2026-551092',
            applicant_id=applicant4.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Kavita',
            surname='Reddy',
            dob=date(1996, 7, 18),
            gender='Female',
            place_of_birth='Bengaluru',
            aadhaar_number='543210987654',
            pan_number='UVWXY7890Z',
            voter_id='KA9988776',
            father_name='Narasimha Reddy',
            mother_name='Lakshmi Reddy',
            spouse_name='',
            present_address='12th Main, Indiranagar, Bengaluru',
            permanent_address='12th Main, Indiranagar, Bengaluru',
            pin_code='560001',
            police_station_name='Indiranagar Police Station',
            emergency_contact_name='Narasimha Reddy',
            emergency_contact_phone='+91 9844400000',
            status='police_approved',
            auto_check_status='passed',
            auto_check_notes='Automated checks PASSED.',
            created_at=datetime.now() - timedelta(days=4)
        )

        # Application 6: Appointment Scheduled (Kolkata Office)
        app6 = Application(
            application_number='PAS-2026-663910',
            applicant_id=applicant3.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Vikramaditya',
            surname='Sengupta',
            dob=date(1994, 1, 25),
            gender='Male',
            place_of_birth='Kolkata',
            aadhaar_number='432109876543',
            pan_number='BCDEF2345G',
            voter_id='WB5566778',
            father_name='Debabrata Sengupta',
            mother_name='Monika Sengupta',
            spouse_name='',
            present_address='Flat 4B, Park Street, Kolkata',
            permanent_address='Flat 4B, Park Street, Kolkata',
            pin_code='700001',
            police_station_name='Park Street Police Station',
            emergency_contact_name='Debabrata Sengupta',
            emergency_contact_phone='+91 9833300000',
            status='appointment_scheduled',
            auto_check_status='passed',
            auto_check_notes='Automated checks PASSED.',
            created_at=datetime.now() - timedelta(days=3)
        )

        # Application 7: Initial Check Failed (Flagged for Format/Duplicate)
        app7 = Application(
            application_number='PAS-2026-778102',
            applicant_id=applicant2.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Rohan',
            surname='Verma',
            dob=date(2001, 9, 12),
            gender='Male',
            place_of_birth='Jaipur',
            aadhaar_number='11112222', # Invalid length flag
            pan_number='INVALIDPAN',
            voter_id='RJ00000',
            father_name='Sunil Verma',
            mother_name='Aarti Verma',
            spouse_name='',
            present_address='House 88, Civil Lines, Jaipur',
            permanent_address='House 88, Civil Lines, Jaipur',
            pin_code='302006',
            police_station_name='Civil Lines PS',
            emergency_contact_name='Sunil Verma',
            emergency_contact_phone='+91 9876544444',
            status='initial_check_failed',
            auto_check_status='flagged',
            auto_check_notes='Automated Checks FLAGGED: Invalid Aadhaar card format (Must be 12 digits).',
            created_at=datetime.now() - timedelta(days=2)
        )

        # Application 8: Police Rejected (Adverse Field Report)
        app8 = Application(
            application_number='PAS-2026-889314',
            applicant_id=applicant4.id,
            application_type='new',
            passport_type='ordinary_36',
            given_name='Deepak',
            surname='Nair',
            dob=date(1991, 12, 5),
            gender='Male',
            place_of_birth='Kochi',
            aadhaar_number='321098765432',
            pan_number='CDEFG3456H',
            voter_id='KL4433221',
            father_name='Gopal Nair',
            mother_name='Radha Nair',
            spouse_name='',
            present_address='Flat 10, MG Road, Bengaluru',
            permanent_address='Flat 10, MG Road, Bengaluru',
            pin_code='560001',
            police_station_name='Commercial Street Police Station',
            emergency_contact_name='Gopal Nair',
            emergency_contact_phone='+91 9844411111',
            status='police_rejected',
            auto_check_status='passed',
            auto_check_notes='Automated checks PASSED.',
            rejection_reason='Police adverse report: Physical verification failed. Applicant not residing at stated address.',
            created_at=datetime.now() - timedelta(days=5)
        )

        db.session.add_all([app1, app2, app3, app4, app5, app6, app7, app8])
        db.session.commit()

        # -------------------------------------------------------------
        # 6. DOCUMENTS, POLICE REPORTS & APPOINTMENTS SEEDING
        # -------------------------------------------------------------
        doc1 = Document(
            application_id=app1.id,
            doc_type='identity_proof',
            file_name='sample_aadhaar_rajesh.pdf',
            original_filename='Aadhaar_Card_Rajesh.pdf'
        )
        doc2 = Document(
            application_id=app1.id,
            doc_type='address_proof',
            file_name='sample_utility_rajesh.pdf',
            original_filename='Electricity_Bill_Address.pdf'
        )

        doc3 = Document(
            application_id=app2.id,
            doc_type='identity_proof',
            file_name='sample_pan_priya.pdf',
            original_filename='PAN_Card_Priya.pdf'
        )
        doc4 = Document(
            application_id=app2.id,
            doc_type='address_proof',
            file_name='sample_passport_priya.pdf',
            original_filename='Rent_Agreement_Dwarka.pdf'
        )

        doc5 = Document(
            application_id=app5.id,
            doc_type='identity_proof',
            file_name='sample_aadhaar_kavita.pdf',
            original_filename='Aadhaar_Card_Kavita.pdf'
        )
        doc6 = Document(
            application_id=app5.id,
            doc_type='address_proof',
            file_name='sample_water_kavita.pdf',
            original_filename='Water_Bill_Bengaluru.pdf'
        )

        db.session.add_all([doc1, doc2, doc3, doc4, doc5, doc6])

        # Police Report for App 5 (Kavita Reddy - Clear PVR)
        pvr5 = PoliceReport(
            application_id=app5.id,
            police_officer_id=police1.id,
            station_name='Indiranagar Police Station',
            verification_status='clear',
            address_verified=True,
            criminal_records_found=False,
            witness1_name='Srinivas Murthy',
            witness1_contact='+91 9845011111',
            witness2_name='Anita Rao',
            witness2_contact='+91 9845022222',
            remarks='Residence address physically verified. No criminal records found. Neighbors verified stay of 5+ years.',
            submitted_at=datetime.now() - timedelta(days=1)
        )
        db.session.add(pvr5)

        # Police Report for App 8 (Deepak Nair - Adverse PVR)
        pvr8 = PoliceReport(
            application_id=app8.id,
            police_officer_id=police1.id,
            station_name='Commercial Street Police Station',
            verification_status='adverse',
            address_verified=False,
            criminal_records_found=False,
            witness1_name='Prem Kumar',
            witness1_contact='+91 9845033333',
            witness2_name='',
            witness2_contact='',
            remarks='Field inspection team visited premise. Property owner stated applicant moved out 6 months ago.',
            submitted_at=datetime.now() - timedelta(days=2)
        )
        db.session.add(pvr8)

        # Appointment for App 6 (Vikramaditya Sengupta)
        appt6 = Appointment(
            application_id=app6.id,
            appointment_date=date.today() + timedelta(days=4),
            time_slot='11:00 AM - 12:00 PM',
            office_location='Passport Seva Kendra (PSK Kolkata Central)',
            status='scheduled'
        )
        db.session.add(appt6)

        # Audit Logs
        audit1 = AuditLog(
            application_id=app1.id,
            actor_id=applicant1.id,
            actor_name=applicant1.full_name,
            actor_role=applicant1.role,
            action='Application Submitted',
            notes='Submitted fresh passport application.'
        )
        audit2 = AuditLog(
            application_id=app4.id,
            actor_id=admin1.id,
            actor_name=admin1.full_name,
            actor_role=admin1.role,
            action='Passport Issued & Dispatched',
            notes='Approved Passport #Z8492019. Dispatched via Speed Post ID: SPEEDPOST-IN-98210492'
        )
        db.session.add_all([audit1, audit2])

        db.session.commit()
        print("Database seeded with 8 comprehensive demo applications & verification records successfully!")

if __name__ == '__main__':
    seed_database()
