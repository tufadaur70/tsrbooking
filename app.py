import os, sqlite3, io, json, secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session
import stripe
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.message import EmailMessage


app = Flask(__name__)
app.secret_key = 'supersecretkey'   


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, 'config.json')
DB_PATH = os.path.join(BASE_DIR, 'data', 'cinema.db')
IMG_PATH = os.path.join(BASE_DIR, 'static', 'img')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'posters')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# ---------- CARICA FILE DI CONFIG ----------
with open(config_path) as f:
    CONFIG = json.load(f)

# ---------- STRIPE CONFIGURAZIONE ----------
stripe.api_key = CONFIG['stripe']['secret_key']


# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- FUNZIONI  ----------
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now}

def reset_transazioni_scadute(db_path="database.db"):

    conn = get_db() 
    cur = conn.cursor()

    # Calcolo soglia temporale (ora - 10 minuti)
    limite = datetime.now() - timedelta(minutes=5)
    cur.execute("""
        UPDATE bookings
        SET status = 0
        WHERE status = 1 AND created_at <= ?
    """, (limite.strftime("%d-%m-%Y %H:%M:%S"),))

    conn.commit()
    conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(reset_transazioni_scadute, 'interval', seconds=300)
scheduler.start()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_booking_email_html(booking_id):
    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    event = conn.execute('SELECT * FROM events WHERE id=?', (booking['event_id'],)).fetchone()
    conn.close()
    event_title = event['title']
    event_date = event['date']
    event_time = event['time']
    seats = booking['seats']
    to_email = booking['email']
    name = booking['name']

    subject = f'ACQUISTO CONFERMATO {event_title}'
    sender = 'booking@tsrbooking.it'
    password = 'hafpec-xecMuh-woqxe7'
    smtp_server = 'smtp.ionos.it'
    smtp_port = 587

        # Percorsi immagini


    logo_url = 'https://booking.tfnmusic.it/static/img/logo.png'
    poster_url = ''
    if event['poster_url']:
        if event['poster_url'].startswith('http'):
            poster_url = event['poster_url']
        else:
            poster_url = f"https://booking.tfnmusic.it{event['poster_url']}"
    poster_img_html = f"<img src='{poster_url}' alt='Locandina evento' style='max-width:220px;border-radius:8px;box-shadow:0 1px 6px #0002;margin:0 auto 10px auto;display:block;'>" if poster_url else ''

    html = f"""
        <div style='max-width:480px;margin:0 auto;background:#fff;border-radius:14px;box-shadow:0 2px 12px #0001;padding:24px 18px 18px 18px;font-family:Roboto,Arial,sans-serif;'>
            <div style='text-align:center;margin-bottom:18px;'>
                <img src='{logo_url}' alt='Teatro San Raffaele' style='max-width:180px;margin-bottom:10px;'><br>
                <h2 style='text-align:center;color:#e53935;margin-bottom:18px;'>Teatro San Raffaele</h2>
            </div>
            <h2 style='text-align:center;color:#e53935;margin-bottom:18px;'>Acquisto Confermato</h2>
            <div style='text-align:center;margin-bottom:18px;'>
                {poster_img_html}
            </div>
            <div style='font-size:1.08em;color:#222;margin-bottom:18px;text-align:center;'>
                <h2>{event_title}</h2>
                <h3>Data: {event_date} &nbsp;|&nbsp; Ora: {event_time}</h3><br>
                Nominativo: <b>{name}</b>
                Email: <b>{to_email}</b><br>
                <h2>Posti: <b>{seats}</b></h2><br>
                Ticket N: : <b>{booking_id}</b>
            </div>
            <div style='text-align:center;color:#555;font-size:0.98em;margin-top:18px;'>
                <br>
                Grazie per l'acquisto!
            </div>
        </div>
        """

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email
    msg.set_content("Conferma di acquisto")
    msg.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return "Message sent!"
    except Exception as e:
        return f"Errore invio email: {e}"
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function


# ---------- ROUTE  ----------

@app.route('/')
def index():
    conn = get_db()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return render_template('index.html', events=events)

@app.route('/admin', methods=['GET','POST'])
def admin():
    error = None
    if request.method == 'POST':
        if request.form['username'] == CONFIG['admin_user'] and request.form['password'] == CONFIG['admin_password']:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Credenziali non valide'
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('admin'))

@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        poster_url = None
        poster = request.files.get('poster')
        if poster and allowed_file(poster.filename):
            filename = secure_filename(poster.filename)
            poster.save(os.path.join(UPLOAD_FOLDER, filename))
            poster_url = f'/static/posters/{filename}'
        
        dt = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')


        # Salva l'evento nel database (aggiungi qui la tua logica)
        conn = get_db()
        conn.execute(
            "INSERT INTO events (title, date, time, price, poster_url) VALUES (?, ?, ?, ?, ?)",
            (title, dt, time, price, poster_url)
        )
        conn.commit()
        conn.close()
        flash('Evento aggiunto con successo!')
        return redirect(url_for('dashboard'))

    # Passa il dizionario delle sale al template
    return render_template('add_event.html')

def check_seats_available(event_id, seats_to_check):
    """Restituisce True se tutti i posti sono ancora disponibili per l'evento, False se almeno uno è già prenotato."""
    conn = get_db()
    bookings = conn.execute(
        'SELECT seats FROM bookings WHERE event_id=? AND status IN (1,2,3)', (event_id,)
    ).fetchall()
    conn.close()
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b['seats'].split(','))
    return all(seat not in booked_seats for seat in seats_to_check)

@app.route('/select_seats/<int:event_id>', methods=['GET', 'POST'])
def select_seats(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    cols = 27
    unavailable = set(CONFIG['unavailable_seats'])
    row_letters = CONFIG['row_letters']

    # Recupera i posti già prenotati per l'evento (status 1, 2, 3)
    bookings = conn.execute(
        'SELECT seats FROM bookings WHERE event_id=? AND status IN (1,2,3)', (event_id,)
    ).fetchall()
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b['seats'].split(','))

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        if not selected_seats:
            flash('Seleziona almeno un posto!')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        # Verifica che i posti selezionati siano ancora disponibili (prima verifica veloce)
        if any(seat in booked_seats or seat in unavailable for seat in selected_seats):
            flash('Alcuni posti selezionati non sono più disponibili.')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        # Raccogli dati utente (qui esempio semplice, puoi aggiungere un form per nome/email)
        name = request.form.get('name')
        email = request.form.get('email')
        import re
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not name or not email:
            flash('Inserisci nome ed email!')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        if not re.match(email_regex, email):
            flash('Inserisci un indirizzo email valido!')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        seats_str = ','.join(selected_seats)
        # --- VERIFICA CONCORRENZA: controllo finale prima di inserire la prenotazione ---
        if not check_seats_available(event_id, selected_seats):
            flash('Alcuni posti sono appena stati prenotati da un altro utente. Riprova!')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        
        conn.execute(
            'INSERT INTO bookings (event_id, name, email, seats, status, created_at) VALUES (?, ?, ?, ?, ?,?)',
            (event_id, name, email, seats_str, 1, now)
        )
        conn.commit()
        booking_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        return redirect(url_for('createcheckoutsession', booking_id=booking_id))
      

    return render_template(
        'select_seats.html',
        event=event,
        row_letters=row_letters,
        cols=cols,
        booked_seats=booked_seats,
        unavailable=unavailable
    )

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    events = conn.execute('SELECT * FROM events').fetchall()

    event_list = []
    for event in events:
        event_id = event['id']

        # Posti pending
        pending = conn.execute(
            'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS pending_count '
            'FROM bookings WHERE event_id=? AND status=1', (event_id,)
        ).fetchone()['pending_count'] or 0

        # Posti pagati (venduti)
        sold = conn.execute(
            'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS sold_count '
            'FROM bookings WHERE event_id=? AND status IN (2, 3)', (event_id,)
        ).fetchone()['sold_count'] or 0

        # Posti validati
        validated = conn.execute(
            'SELECT SUM(LENGTH(seats) - LENGTH(REPLACE(seats, ",", "")) + 1) AS validated_count '
            'FROM bookings WHERE event_id=? AND status=3', (event_id,)
        ).fetchone()['validated_count'] or 0

        #

        event_list.append({
            'id': event_id,
            'title': event['title'],
            'date': event['date'],
            'sold': sold,
            'validated': validated,
        })

    conn.close()
    return render_template('dashboard.html', events=event_list)

@app.route('/createcheckoutsession', methods=['GET'])
def createcheckoutsession():
    booking_id = int(request.args['booking_id'])

    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    event = conn.execute('SELECT * FROM events WHERE id=?', (booking['event_id'],)).fetchone()
    conn.close()

      # Prepara i dati del prodotto con immagine se disponibile
    product_data = {
        'name': f"{event['title']} : {event['date']}:  {event['time']}",
        'description': f"Posti: {booking['seats']} TICKET N: {booking_id}",
        
    }

    session_stripe = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        customer_email=booking['email'],
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'unit_amount': int(event['price'] * 100),
                'product_data': product_data
            },
            'quantity': len(booking['seats'].split(','))
        }],
        metadata={
            'booking_id': booking_id 
            
        },
        success_url=CONFIG['stripe']['success_url'],
        cancel_url=CONFIG['stripe']['cancel_url']
    )

    return redirect(session_stripe.url, code=303)

@app.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Errore: sessione non trovata", "danger")
        return redirect(url_for('index'))

    session_stripe = stripe.checkout.Session.retrieve(session_id)
    booking_id = int(session_stripe.metadata['booking_id'])

    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    event = conn.execute('SELECT * FROM events WHERE id=?', (booking['event_id'],)).fetchone()
    if booking and booking['status'] == 1:
        conn.execute('UPDATE bookings SET status=2 WHERE id=?', (booking_id,))
        conn.commit()
        conn.close()

        # invia la mail 
        send_booking_email_html(booking['id'])
      
    else:
        flash("Prenotazione non trovata o già pagata", "danger")

    return render_template('payment_success.html', event=event, booking=booking)

@app.route('/payment/cancel')
def payment_cancel():
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Errore: sessione non trovata", "danger")
        return redirect(url_for('index'))

    session_stripe = stripe.checkout.Session.retrieve(session_id)
    booking_id = int(session_stripe.metadata['booking_id'])
    conn = get_db()
    
    conn.execute(
        'DELETE FROM bookings WHERE WHERE id=?', (booking_id,))
    
    conn.commit()
    conn.close()
    return render_template('payment_cancel.html')

@app.route('/event/<int:event_id>/transactions')
@login_required
def event_transactions(event_id):
    conn = get_db()
    event = conn.execute('SELECT title FROM events WHERE id=?', (event_id,)).fetchone()
    transactions = conn.execute(
        'SELECT * FROM bookings WHERE event_id=? ORDER BY created_at DESC', (event_id,)
    ).fetchall()
    conn.close()
    return render_template(
        'event_transactions.html',
        event_title=event['title'] if event else 'Evento sconosciuto',
        transactions=transactions
    )

@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    if not event:
        conn.close()
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        poster_url = event['poster_url']
        poster = request.files.get('poster')
        if poster and allowed_file(poster.filename):
            filename = secure_filename(poster.filename)
            poster.save(os.path.join(UPLOAD_FOLDER, filename))
            poster_url = f'/static/posters/{filename}'
        # Salva la data in formato gg/mm/aaaa
        dt = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
        conn.execute(
            "UPDATE events SET title=?, date=?, time=?, price=?, poster_url=? WHERE id=?",
            (title, dt, time, price, poster_url, event_id)
        )
        conn.commit()
        conn.close()
        flash('Evento modificato con successo!')
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('edit_event.html', event=event)

@app.route('/qrcode/<token>')

@app.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    conn = get_db()
    conn.execute('DELETE FROM bookings WHERE event_id=?', (event_id,))
    conn.execute('DELETE FROM events WHERE id=?', (event_id,))
    conn.commit()
    conn.close()
    flash('Evento eliminato con successo!')
    return redirect(url_for('dashboard'))

@app.route('/resend_ticket/<int:booking_id>', methods=['POST'])
@login_required
def resend_ticket(booking_id):
    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not booking:
        conn.close()
        flash('Prenotazione non trovata.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    if booking['status'] not in (2, 3):
        conn.close()
        flash('Solo le prenotazioni pagate o validate possono ricevere il biglietto.', 'warning')
        return redirect(request.referrer or url_for('dashboard'))
    conn.close()
    send_booking_email_html(booking_id)
    flash('Biglietto inviato nuovamente a ' + booking['email'], 'success')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/print_ticket/<int:booking_id>')
@login_required
def print_ticket(booking_id):
    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return 'Prenotazione non trovata', 404
    event = conn.execute('SELECT * FROM events WHERE id=?', (booking['event_id'],)).fetchone()
    conn.close()
  
    return render_template('print_ticket.html', booking=booking, event=event)

@app.route('/event/<int:event_id>/admin_book_seats', methods=['GET', 'POST'])
@login_required
def admin_book_seats(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    if not event:
        conn.close()
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    cols = 27
    unavailable = set(CONFIG['unavailable_seats'])
    row_letters = CONFIG['row_letters']
    bookings = conn.execute(
        'SELECT seats FROM bookings WHERE event_id=? AND status IN (1,2,3)', (event_id,)
    ).fetchall()
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b['seats'].split(','))

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        if not selected_seats:
            flash('Seleziona almeno un posto!')
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        if any(seat in booked_seats or seat in unavailable for seat in selected_seats):
            flash('Alcuni posti selezionati non sono più disponibili.')
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        name = request.form.get('name')
        email = request.form.get('email')
        if not name:
            flash('Inserisci il nome del cliente!')
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        seats_str = ','.join(selected_seats)
        # Verifica concorrenza
        if not check_seats_available(event_id, selected_seats):
            flash('Alcuni posti sono appena stati prenotati da un altro utente. Riprova!')
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=row_letters,
                cols=cols,
                booked_seats=booked_seats,
                unavailable=unavailable
            )
        now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        # Status 2 = pagato
        conn.execute(
            'INSERT INTO bookings (event_id, name, email, seats, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (event_id, name, email, seats_str, 2, now)
        )
        conn.commit()
        booking_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        flash('Prenotazione registrata con successo!')
        return redirect(url_for('print_ticket', booking_id=booking_id))

    conn.close()
    return render_template(
        'admin_book_seats.html',
        event=event,
        row_letters=row_letters,
        cols=cols,
        booked_seats=booked_seats,
        unavailable=unavailable
    )

def run():
    app.run(debug=True)

if __name__ == '__main__':
    run()



