import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pas-secret-key-super-secure-2026'
    
    # Defaults to SQLite DB, can be overridden with environment variable for MySQL
    # e.g., DATABASE_URL=mysql+pymysql://root:password@localhost/pas_db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'pas.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security: Secret key required to register administrative roles (Passport Admin, Regional Admin, Police)
    ADMIN_ACCESS_CODE = os.environ.get('ADMIN_ACCESS_CODE') or 'PAS-ADMIN-SECRET-2026'
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}
