import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH
#peppe
def get_db():
    """Ottieni connessione al database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def reset_transazioni_scadute():
    """Reset delle transazioni scadute (chiamata dal scheduler)"""
    conn = get_db() 
    cur = conn.cursor()

    # Calcolo soglia temporale (ora - 5 minuti)
    limite = datetime.now() - timedelta(minutes=5)
    cur.execute("""
        UPDATE bookings
        SET status = 0
        WHERE status = 1 AND created_at <= ?
    """, (limite.strftime("%d-%m-%Y %H:%M:%S"),))

    conn.commit()
    conn.close()

def get_all_events():
    """Ottieni tutti gli eventi visibili"""
    conn = get_db()
    events = conn.execute('SELECT * FROM events WHERE visible = 1').fetchall()
    conn.close()
    return events

def get_all_events_admin():
    """Ottieni tutti gli eventi (inclusi quelli nascosti) per admin"""
    conn = get_db()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return events

def get_event_by_id(event_id):
    """Ottieni evento per ID"""
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    conn.close()
    return event

def create_event(title, date, time, price, poster_url=None):
    """Crea nuovo evento"""
    conn = get_db()
    conn.execute(
        "INSERT INTO events (title, date, time, price, poster_url, visible) VALUES (?, ?, ?, ?, ?, ?)",
        (title, date, time, price, poster_url, 1)
    )
    conn.commit()
    conn.close()

def update_event(event_id, title, date, time, price, poster_url, visible=1):
    """Aggiorna evento esistente"""
    conn = get_db()
    conn.execute(
        "UPDATE events SET title=?, date=?, time=?, price=?, poster_url=?, visible=? WHERE id=?",
        (title, date, time, price, poster_url, visible, event_id)
    )
    conn.commit()
    conn.close()

def hide_event(event_id):
    """Nasconde evento impostando visible=0"""
    conn = get_db()
    conn.execute('UPDATE events SET visible=0 WHERE id=?', (event_id,))
    conn.commit()
    conn.close()

def show_event(event_id):
    """Rende visibile evento impostando visible=1"""
    conn = get_db()
    conn.execute('UPDATE events SET visible=1 WHERE id=?', (event_id,))
    conn.commit()
    conn.close()

def delete_event(event_id):
    """Elimina definitivamente evento e relative prenotazioni (solo per emergenze)"""
    conn = get_db()
    conn.execute('DELETE FROM bookings WHERE event_id=?', (event_id,))
    conn.execute('DELETE FROM events WHERE id=?', (event_id,))
    conn.commit()
    conn.close()

def get_booking_by_id(booking_id):
    """Ottieni prenotazione per ID"""
    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    conn.close()
    return booking

def get_bookings_by_event(event_id, statuses=None):
    """Ottieni prenotazioni per evento"""
    conn = get_db()
    if statuses:
        placeholders = ','.join(['?'] * len(statuses))
        bookings = conn.execute(
            f'SELECT seats FROM bookings WHERE event_id=? AND status IN ({placeholders})', 
            (event_id, *statuses)
        ).fetchall()
    else:
        bookings = conn.execute(
            'SELECT * FROM bookings WHERE event_id=? ORDER BY created_at DESC', 
            (event_id,)
        ).fetchall()
    conn.close()
    return bookings

def create_booking(event_id, name, email, seats_str, status=1):
    """Crea nuova prenotazione"""
    conn = get_db()
    now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    conn.execute(
        'INSERT INTO bookings (event_id, name, email, seats, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (event_id, name, email, seats_str, status, now)
    )
    conn.commit()
    booking_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return booking_id

def update_booking_status(booking_id, status):
    """Aggiorna status prenotazione"""
    conn = get_db()
    conn.execute('UPDATE bookings SET status=? WHERE id=?', (status, booking_id))
    conn.commit()
    conn.close()

def delete_booking(booking_id):
    """Elimina prenotazione"""
    conn = get_db()
    conn.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()

def get_event_stats(event_id):
    """Ottieni statistiche evento (pending, sold, validated)"""
    conn = get_db()
    
    # Posti pending
    pending = conn.execute(
        'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS pending_count '
        'FROM bookings WHERE event_id=? AND status=1', (event_id,)
    ).fetchone()['pending_count'] or 0

    # Posti pagati (venduti)
    sold = conn.execute(
        'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS sold_count '
        'FROM bookings WHERE event_id=? AND status =2', (event_id,)
    ).fetchone()['sold_count'] or 0

    # Posti validati
    validated = conn.execute(
        'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS validated_count '
        'FROM bookings WHERE event_id=? AND status=3', (event_id,)
    ).fetchone()['validated_count'] or 0
    
    conn.close()
    return {'pending': pending, 'sold': sold, 'validated': validated}