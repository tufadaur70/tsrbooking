import re
from database import get_bookings_by_event

def allowed_file(filename):
    """Verifica se il file ha estensione consentita"""
    from config import ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_seats_available(event_id, seats_to_check):
    """
    Restituisce True se tutti i posti sono ancora disponibili per l'evento, 
    False se almeno uno è già prenotato.
    """
    bookings = get_bookings_by_event(event_id, statuses=[1, 2, 3])
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b['seats'].split(','))
    return all(seat not in booked_seats for seat in seats_to_check)

def get_booked_seats(event_id):
    """Ottieni set dei posti già prenotati per un evento"""
    bookings = get_bookings_by_event(event_id, statuses=[1, 2, 3])
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b['seats'].split(','))
    return booked_seats

def validate_email(email):
    """Valida formato email"""
    email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(email_regex, email) is not None

def validate_booking_form(name, email, selected_seats, booked_seats, unavailable_seats):
    """
    Valida form di prenotazione.
    Ritorna (is_valid, error_message)
    """
    if not selected_seats:
        return False, 'Seleziona almeno un posto!'
    
    if not name or not email:
        return False, 'Inserisci nome ed email!'
    
    if not validate_email(email):
        return False, 'Inserisci un indirizzo email valido!'
    
    if any(seat in booked_seats or seat in unavailable_seats for seat in selected_seats):
        return False, 'Alcuni posti selezionati non sono più disponibili.'
    
    return True, None

def validate_admin_booking_form(name, selected_seats, booked_seats, unavailable_seats):
    """
    Valida form di prenotazione admin.
    Ritorna (is_valid, error_message)
    """
    if not selected_seats:
        return False, 'Seleziona almeno un posto!'
    
    if not name:
        return False, 'Inserisci il nome del cliente!'
    
    if any(seat in booked_seats or seat in unavailable_seats for seat in selected_seats):
        return False, 'Alcuni posti selezionati non sono più disponibili.'
    
    return True, None