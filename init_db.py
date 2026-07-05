import mysql.connector
from werkzeug.security import generate_password_hash

import os
from dotenv import load_dotenv

def init_db():
    load_dotenv()
    
    db_password = os.environ.get("DB_PASSWORD")
    if db_password:
        db_config = {
            "host": "gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
            "port": 4000,
            "user": "5MLJE6RAQwcNfyu.root",
            "password": db_password,
            "database": "healthcare_appointment",
            "ssl_ca": os.path.join(os.path.dirname(__file__), "isrgrootx1.pem")
        }
        print("Connecting to TiDB Cloud Database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    else:
        print("Connecting to Local Database...")
        conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='teja@266'
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS healthcare_appointment")
        cursor.execute("USE healthcare_appointment")



    # ── patients ──────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id   INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(100) NOT NULL,
            age          INT NOT NULL,
            gender       VARCHAR(10)  NOT NULL,
            phone_number VARCHAR(15)  NOT NULL,
            email        VARCHAR(100) NOT NULL UNIQUE,
            password     VARCHAR(255),
            address      TEXT,
            profile_pic  VARCHAR(255) DEFAULT NULL,
            auth_provider VARCHAR(20) DEFAULT 'local',
            google_id    VARCHAR(100) DEFAULT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── hospitals ──────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            hospital_id  INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(100) NOT NULL,
            address      VARCHAR(255) NOT NULL,
            phone_number VARCHAR(15)  NOT NULL,
            email        VARCHAR(100),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── doctors ───────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id       INT AUTO_INCREMENT PRIMARY KEY,
            hospital_id     INT,
            name            VARCHAR(100) NOT NULL,
            specialization  VARCHAR(100) NOT NULL,
            experience      INT DEFAULT 0,
            phone_number    VARCHAR(15)  NOT NULL,
            email           VARCHAR(100) NOT NULL UNIQUE,
            password        VARCHAR(255),
            available_slots TEXT DEFAULT NULL,
            bio             TEXT,
            profile_pic     VARCHAR(255) DEFAULT NULL,
            auth_provider   VARCHAR(20)  DEFAULT 'local',
            google_id       VARCHAR(100) DEFAULT NULL,
            rating          DECIMAL(3,1) DEFAULT 4.5,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE SET NULL
        )
    """)

    # ── appointments ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id       INT AUTO_INCREMENT PRIMARY KEY,
            patient_id           INT NOT NULL,
            doctor_id            INT NOT NULL,
            appointment_date     DATE NOT NULL,
            appointment_time     VARCHAR(20) NOT NULL,
            status               VARCHAR(20) DEFAULT 'Pending',
            cancellation_reason  TEXT,
            notes                TEXT,
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id)   ON DELETE CASCADE
        )
    """)

    # ── prescriptions ─────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id INT AUTO_INCREMENT PRIMARY KEY,
            appointment_id  INT NOT NULL,
            doctor_id       INT NOT NULL,
            patient_id      INT NOT NULL,
            medicines       TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id)      REFERENCES doctors(doctor_id)           ON DELETE CASCADE,
            FOREIGN KEY (patient_id)     REFERENCES patients(patient_id)         ON DELETE CASCADE
        )
    """)

    # ── admin ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            admin_id   INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(50)  NOT NULL UNIQUE,
            password   VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── password_reset_tokens ─────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            email      VARCHAR(100) NOT NULL,
            user_type  VARCHAR(20)  NOT NULL,
            token      VARCHAR(255) NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            used       TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── contact_messages ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            message_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            subject VARCHAR(200),
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── video_consultations ───────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_consultations (
            consultation_id INT AUTO_INCREMENT PRIMARY KEY,
            appointment_id  INT NOT NULL UNIQUE,
            room_token      VARCHAR(100) NOT NULL UNIQUE,
            is_active       TINYINT(1) DEFAULT 1,
            started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at        DATETIME DEFAULT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id) ON DELETE CASCADE
        )
    """)

    # ── appointment_type column (migration safe) ──────────────────
    try:
        cursor.execute("""
            ALTER TABLE appointments
            ADD COLUMN appointment_type VARCHAR(20) DEFAULT 'In-Person'
        """)
    except Exception:
        pass  # Column already exists

    # ── hospital_id column in doctors (migration safe) ────────────
    try:
        cursor.execute("""
            ALTER TABLE doctors
            ADD COLUMN hospital_id INT,
            ADD CONSTRAINT fk_doctor_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE SET NULL
        """)
    except Exception:
        pass  # Column/constraint already exists

    # ── default admin ─────────────────────────────────────
    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (%s, %s)",
            ('admin', generate_password_hash('admin123'))
        )

    # ── sample hospitals ──────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    if cursor.fetchone()[0] == 0:
        sample_hospitals = [
            ('City Central Hospital', '123 Health Ave, Metro City', '555-0100', 'info@citycentral.com'),
            ('Grace Memorial Clinic', '456 Care Blvd, Westside', '555-0200', 'contact@gracememorial.com'),
            ('St. Jude Medical Center', '789 Hope St, East End', '555-0300', 'appointments@stjude.com')
        ]
        for h in sample_hospitals:
            cursor.execute(
                "INSERT INTO hospitals (name, address, phone_number, email) VALUES (%s, %s, %s, %s)",
                h
            )
        conn.commit()

    # Map existing doctors to the first hospital if they don't have one
    cursor.execute("UPDATE doctors SET hospital_id = 1 WHERE hospital_id IS NULL")
    conn.commit()

    # ── sample doctors ────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] == 0:
        dp = generate_password_hash('doctor123')
        sample = [
            ('Rajesh Kumar',  'Cardiology',      12, '9876543210', 'rajesh.kumar@hospital.com',  '09:00 AM - 01:00 PM, 02:00 PM - 05:00 PM', 4.8, 1),
            ('Priya Sharma',  'Dermatology',      8, '9876543211', 'priya.sharma@hospital.com',  '10:00 AM - 02:00 PM, 03:00 PM - 06:00 PM', 4.7, 1),
            ('Amit Patel',    'Orthopedics',     15, '9876543212', 'amit.patel@hospital.com',    '08:00 AM - 12:00 PM, 01:00 PM - 04:00 PM', 4.6, 1),
            ('Sunita Reddy',  'Neurology',       10, '9876543213', 'sunita.reddy@hospital.com',  '09:00 AM - 01:00 PM, 03:00 PM - 06:00 PM', 4.9, 1),
            ('Vikram Singh',  'Pediatrics',       7, '9876543214', 'vikram.singh@hospital.com',  '08:00 AM - 12:00 PM, 02:00 PM - 05:00 PM', 4.5, 2),
            ('Meera Iyer',    'Gynecology',       9, '9876543215', 'meera.iyer@hospital.com',    '10:00 AM - 01:00 PM, 02:00 PM - 05:00 PM', 4.8, 2),
            ('Anil Deshmukh', 'ENT',              6, '9876543216', 'anil.deshmukh@hospital.com', '09:00 AM - 12:00 PM, 01:00 PM - 04:00 PM', 4.4, 2),
            ('Kavita Nair',   'Ophthalmology',   11, '9876543217', 'kavita.nair@hospital.com',   '10:00 AM - 02:00 PM, 03:00 PM - 06:00 PM', 4.7, 2),
            ('Suresh Gupta',  'General Medicine', 14, '9876543218', 'suresh.gupta@hospital.com', '08:00 AM - 01:00 PM, 02:00 PM - 06:00 PM', 4.6, 3),
            ('Deepa Joshi',   'Psychiatry',       5, '9876543219', 'deepa.joshi@hospital.com',   '11:00 AM - 03:00 PM, 04:00 PM - 07:00 PM', 4.9, 3),
            ('Rahul Verma',   'Dentistry',        8, '9876543220', 'rahul.verma@hospital.com',   '09:00 AM - 01:00 PM, 02:00 PM - 06:00 PM', 4.5, 3),
            ('Anjali Mehta',  'Cardiology',      13, '9876543221', 'anjali.mehta@hospital.com',  '10:00 AM - 02:00 PM, 03:00 PM - 05:00 PM', 4.8, 3),
        ]
        for d in sample:
            cursor.execute(
                "INSERT INTO doctors (name,specialization,experience,phone_number,email,password,available_slots,rating,hospital_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (d[0], d[1], d[2], d[3], d[4], dp, d[5], d[6], d[7])
            )

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully!")
    print("   Admin login  -> username: admin   | password: admin123")
    print("   Doctor login -> any sample email  | password: doctor123")

if __name__ == '__main__':
    init_db()