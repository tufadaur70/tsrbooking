import os
import json
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env
# Per production, usa un path assoluto sicuro come /etc/tsrbooking/.env
env_path = '/var/www/tsrbooking/.env'
load_dotenv(env_path)


# Percorsi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
DB_PATH = os.path.join(BASE_DIR, 'data', 'cinema.db')
IMG_PATH = os.path.join(BASE_DIR, 'static', 'img')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'posters')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Carica configurazione da JSON (solo dati non sensibili)
def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

CONFIG = load_config()

# Configurazioni da variabili d'ambiente (dati sensibili)
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'default_password')
SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key')

# Configurazioni Stripe da variabili d'ambiente
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL')
STRIPE_CANCEL_URL = os.getenv('STRIPE_CANCEL_URL')
print(f"STRIPE_SUCCESS_URL: {STRIPE_SUCCESS_URL}")
print(f"STRIPE_CANCEL_URL: {STRIPE_CANCEL_URL}")
print(f"STRIPE_SECRET_KEY: {STRIPE_SECRET_KEY}")
print(f"STRIPE_PUBLISHABLE_KEY: {STRIPE_PUBLISHABLE_KEY}")






# Configurazioni Email da variabili d'ambiente
EMAIL_SENDER = 'booking@tsrbooking.it'
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
SMTP_SERVER = 'smtp.ionos.it'
SMTP_PORT = 587

# Configurazioni Teatro dal JSON
UNAVAILABLE_SEATS = set(CONFIG['unavailable_seats'])
ROW_LETTERS = CONFIG['row_letters']
COLS = 27

