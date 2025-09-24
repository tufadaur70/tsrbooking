import os, sqlite3, io, json, secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session
import qrcode
import stripe
from flask_mail import Mail, Message
from io import BytesIO
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.secret_key = 'supersecretkey'   


# ---------- CARICA FILE DI CONFIG ----------
with open('config.json') as f:
    CONFIG = json.load(f)

# ---------- STRIPE CONFIGURAZIONE ----------
stripe.api_key = CONFIG['stripe']['secret_key']

# ---------- FLASK MAIL CONFIGURAZIONE----------
app.config['MAIL_SERVER'] = 'smtp.tim.it'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True  # Abilita StartTLS
app.config['MAIL_USERNAME'] = 'a.tufanari@tim.it'
app.config['MAIL_PASSWORD'] = 'caWdyw-qurqo4-zorbex'
app.config['MAIL_DEFAULT_SENDER'] = 'a.tufanari@tim.it'

mail = Mail(app) # Inizializza l'oggetto Mail con l'applicazione Flask

# ---------- CONFIGURAZIONE UPLOAD FILE POSTER ----------

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'posters')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect('data/cinema.db')
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
    print(f"Reset transazioni scadute prima di {limite}")
    # Aggiorno tutte le transazioni scadute
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

def genera_qrcode(token):
    # Crea l'URL di validazione con il token
    url = f"http://127.0.0.1:5000/validate_qrcode?token={token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return byte_io


def send_booking_email_html(to_email, token, seats, event_id , name, booking_id ):
    qr_mio = genera_qrcode(token)
    
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    conn.close()
    event_title = event['title']
    event_date = event['date']
    event_time = event['time']
    poster_url = event['poster_url'] or '/static/img/default_poster.png'  # Immagine di default se manca
    logo_url = '/static/img/logo.png'  # Percorso del logo del teatro

    msg = Message(
        subject=f'PRENOTAZIONE CONFERMATA {event_title}',
        sender='a.tufanari@tim.it',
        recipients=[to_email]
    )

    msg.html = f"""
    <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:14px;box-shadow:0 2px 12px #0001;padding:24px 18px 18px 18px;font-family:'Roboto',Arial,sans-serif;">
      <div style="text-align:center;margin-bottom:18px;">
        <h2 style="text-align:center;color:#e53935;margin-bottom:18px;">Teatro San Raffaele</h2>
     
      </div>
      <h2 style="text-align:center;color:#e53935;margin-bottom:18px;">Prenotazione confermata!</h2>
      <div style="text-align:center;margin-bottom:18px;">
        </div>
      <div style="font-size:1.08em;color:#222;margin-bottom:18px;text-align:center;">
        <b>{event_title}</b><br>
        Data: {event_date} &nbsp;|&nbsp; Ora: {event_time}<br>
        Nominativo: <b>{name}</b><br>
        Posti: <b>{seats}</br>
        Prenotazione Numero: <b>{booking_id}</b>
      </div>
      <div style="text-align:center;margin-bottom:18px;">
        <img src="cid:qrcode_image" alt="QR Code biglietto" style="width:140px;height:140px;border-radius:12px;box-shadow:0 1px 8px #0001;">
        <div style="font-size:0.95em;color:#888;margin-top:6px;">Mostra questo QR code all'ingresso</div>
      </div>
      <div style="text-align:center;color:#555;font-size:0.98em;margin-top:18px;">
        <br>
        Grazie per la prenotazione!
      </div>
    </div>
    """

    msg.body = "Prenotazione confermata. In allegato il QR code."
    msg.attach(
        filename="qrcode.png",
        content_type="image/png",
        data=qr_mio.read(),
        disposition='inline',
        headers={'Content-ID': '<qrcode_image>'}
    )
    mail.send(msg)
    return "Message sent!"
    
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

@app.route('/select_seats/<int:event_id>', methods=['GET', 'POST'])
def select_seats(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    rows = 18
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
        # Verifica che i posti selezionati siano ancora disponibili
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
        seats_str = ','.join(selected_seats)
        now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        # Inserisci la prenotazione (status 1 = in attesa)
        qrcode_token = secrets.token_urlsafe(16)  # genera token univoco
        conn.execute(
            'INSERT INTO bookings (event_id, name, email, seats, status, qrcode_token , created_at) VALUES (?, ?, ?, ?, ?, ?,?)',
            (event_id, name, email, seats_str, 1,qrcode_token , now)
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

@app.route('/validate_qrcode')
@login_required
def validate_qrcode():
    result = None
    token = str(request.args['token'])
        # Usa la stessa logica della API
    conn = get_db()
    booking = conn.execute(
            "SELECT * FROM bookings WHERE qrcode_token=?",
            (token,)
        ).fetchone()
    if not booking:
            result = {"success": False, "error": "Prenotazione non trovata"}
    elif booking['status'] == 1:
            result = {"success": False, "error": "Transazione non pagata"}
    elif booking['status'] == 3:
            result = {"success": False, "error": "Transazione già validata"}
    else:
            conn.execute(
                "UPDATE bookings SET status=3 WHERE id=?",
                (booking['id'],)
            )
            conn.commit()
            result = {"success": True, "message": "Prenotazione validata"}
    conn.close()
    return render_template('validate_qrcode_result.html', result=result)

@app.route('/createcheckoutsession', methods=['GET'])
def createcheckoutsession():
    booking_id = int(request.args['booking_id'])

    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    event = conn.execute('SELECT * FROM events WHERE id=?', (booking['event_id'],)).fetchone()
    conn.close()

    seats = booking['seats']
    email = booking['email']

    # Stripe Checkout
    session_stripe = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        customer_email=email,
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'unit_amount': int(event['price'] * 100),
                'product_data': {
                    'name': f"{event['title']} ({seats})"
                }
            },
            'quantity': len(seats.split(','))
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

        # invia la mail con il QR code
        send_booking_email_html(booking['email'],  booking['qrcode_token'],booking['seats'], booking['event_id'], booking['name'],booking['id'])
        
        
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

@app.route('/event/<int:event_id>/seatmap')
@login_required
def event_seatmap(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
   
    rows = 18
    cols = 27
    unavailable = set(CONFIG['unavailable_seats'])
    row_letters = CONFIG['row_letters']
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))
    # Recupera i posti venduti per l'evento
    bookings = conn.execute('SELECT seats FROM bookings WHERE event_id=? AND status = 2', (event_id,)).fetchall()
    validation = conn.execute('SELECT seats FROM bookings WHERE event_id=? AND status = 3', (event_id,)).fetchall()
    print(validation)
    
    sold_seats = set()  
    for b in bookings:
        sold_seats.update(b['seats'].split(','))
    validati = set()
    for v in validation:
        validati.update(v['seats'].split(','))
    conn.close()
      
    return render_template(
        'event_seatmap.html',
        event_title=event['title'],
        row_letters=row_letters,
        cols=cols,
        sold_seats=sold_seats,
        validation=validati,
        unavailable=unavailable
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
def qrcode_image(token):
    img_io = genera_qrcode(token)
    return app.response_class(img_io, mimetype='image/png')

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

if __name__ == '__main__':
    app.run(debug=True)

