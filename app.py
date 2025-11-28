import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import stripe
from werkzeug.utils import secure_filename
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Import moduli locali
from config import *
from database import *
from email_service import send_booking_email_html
from auth import login_required, check_admin_credentials
from booking_service import *

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configurazione Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Context processor per template
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Scheduler per reset transazioni scadute
scheduler = BackgroundScheduler()
scheduler.add_job(reset_transazioni_scadute, 'interval', seconds=300)
scheduler.start()

# ---------- ROUTE PRINCIPALI ----------

@app.route('/')
def index():
    """Homepage con lista eventi"""
    events = get_all_events()
    return render_template('index.html', events=events)

@app.route('/admin', methods=['GET','POST'])
def admin():
    """Login admin"""
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_admin_credentials(username, password):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Credenziali non valide'
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    """Logout admin"""
    session['logged_in'] = False
    return redirect(url_for('admin'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard admin con statistiche eventi"""
    events = get_all_events_admin()
    event_list = []
    
    for event in events:
        stats = get_event_stats(event['id'])
        event_list.append({
            'id': event['id'],
            'title': event['title'],
            'date': event['date'],
            'sold': stats['sold'],
            'validated': stats['validated'],
            'visible': event['visible'],
        })
    
    return render_template('dashboard.html', events=event_list)

# ---------- GESTIONE EVENTI ----------

@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    """Aggiungi nuovo evento"""
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        poster_url = None
        
        # Gestione upload poster
        poster = request.files.get('poster')
        if poster and allowed_file(poster.filename):
            filename = secure_filename(poster.filename)
            poster.save(os.path.join(UPLOAD_FOLDER, filename))
            poster_url = f'/static/posters/{filename}'
        
        # Formatta data
        dt = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        create_event(title, dt, time, price, poster_url)
        flash('Evento aggiunto con successo!')
        return redirect(url_for('dashboard'))

    return render_template('add_event.html')

@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """Modifica evento esistente"""
    event = get_event_by_id(event_id)
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        poster_url = event['poster_url']
        
        # Gestione upload nuovo poster
        poster = request.files.get('poster')
        if poster and allowed_file(poster.filename):
            filename = secure_filename(poster.filename)
            poster.save(os.path.join(UPLOAD_FOLDER, filename))
            poster_url = f'/static/posters/{filename}'
        
        # Formatta data
        dt = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        update_event(event_id, title, dt, time, price, poster_url, event['visible'])
        flash('Evento modificato con successo!')
        return redirect(url_for('dashboard'))

    return render_template('edit_event.html', event=event)

@app.route('/event/<int:event_id>/hide', methods=['POST'])
@login_required
def hide_event_route(event_id):
    """Nasconde evento dalla vista pubblica"""
    from database import hide_event
    hide_event(event_id)
    flash('Evento nascosto con successo!')
    return redirect(url_for('dashboard'))

@app.route('/event/<int:event_id>/show', methods=['POST'])
@login_required
def show_event_route(event_id):
    """Rende visibile evento nella vista pubblica"""
    from database import show_event
    show_event(event_id)
    flash('Evento reso visibile con successo!')
    return redirect(url_for('dashboard'))

# ---------- PRENOTAZIONI UTENTE ----------

@app.route('/select_seats/<int:event_id>', methods=['GET', 'POST'])
def select_seats(event_id):
    """Selezione posti per prenotazione utente"""
    event = get_event_by_id(event_id)
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('index'))

    booked_seats = get_booked_seats(event_id)

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Validazione form
        is_valid, error_msg = validate_booking_form(
            name, email, selected_seats, booked_seats, UNAVAILABLE_SEATS
        )
        if not is_valid:
            flash(error_msg)
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=ROW_LETTERS,
                cols=COLS,
                booked_seats=booked_seats,
                unavailable=UNAVAILABLE_SEATS
            )
        
        # Verifica concorrenza finale
        if not check_seats_available(event_id, selected_seats):
            flash('Alcuni posti sono appena stati prenotati da un altro utente. Riprova!')
            return render_template(
                'select_seats.html',
                event=event,
                row_letters=ROW_LETTERS,
                cols=COLS,
                booked_seats=booked_seats,
                unavailable=UNAVAILABLE_SEATS
            )
        
        # Crea prenotazione
        seats_str = ','.join(selected_seats)
        booking_id = create_booking(event_id, name, email, seats_str, status=1)
        return redirect(url_for('createcheckoutsession', booking_id=booking_id))

    return render_template(
        'select_seats.html',
        event=event,
        row_letters=ROW_LETTERS,
        cols=COLS,
        booked_seats=booked_seats,
        unavailable=UNAVAILABLE_SEATS
    )

# ---------- PRENOTAZIONI ADMIN ----------

@app.route('/event/<int:event_id>/admin_book_seats', methods=['GET', 'POST'])
@login_required
def admin_book_seats(event_id):
    """Prenotazione admin (pagamento in contanti)"""
    event = get_event_by_id(event_id)
    if not event:
        flash("Evento non trovato.")
        return redirect(url_for('dashboard'))

    booked_seats = get_booked_seats(event_id)

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Validazione form
        is_valid, error_msg = validate_admin_booking_form(
            name, selected_seats, booked_seats, UNAVAILABLE_SEATS
        )
        if not is_valid:
            flash(error_msg)
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=ROW_LETTERS,
                cols=COLS,
                booked_seats=booked_seats,
                unavailable=UNAVAILABLE_SEATS
            )
        
        # Verifica concorrenza finale
        if not check_seats_available(event_id, selected_seats):
            flash('Alcuni posti sono appena stati prenotati da un altro utente. Riprova!')
            return render_template(
                'admin_book_seats.html',
                event=event,
                row_letters=ROW_LETTERS,
                cols=COLS,
                booked_seats=booked_seats,
                unavailable=UNAVAILABLE_SEATS
            )
        
        # Crea prenotazione con status 3 (cassa)
        seats_str = ','.join(selected_seats)
        booking_id = create_booking(event_id, name, email, seats_str, status=3)
        flash('Prenotazione registrata con successo!')
        return redirect(url_for('print_ticket', booking_id=booking_id))

    return render_template(
        'admin_book_seats.html',
        event=event,
        row_letters=ROW_LETTERS,
        cols=COLS,
        booked_seats=booked_seats,
        unavailable=UNAVAILABLE_SEATS
    )

# ---------- PAGAMENTI STRIPE ----------

@app.route('/createcheckoutsession', methods=['GET'])
def createcheckoutsession():
    """Crea sessione checkout Stripe"""
    booking_id = int(request.args['booking_id'])
    booking = get_booking_by_id(booking_id)
    event = get_event_by_id(booking['event_id'])

    # Prepara dati prodotto
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
        metadata={'booking_id': booking_id},
        success_url=STRIPE_SUCCESS_URL,
        cancel_url=STRIPE_CANCEL_URL
    )

    return redirect(session_stripe.url, code=303)

@app.route('/payment/success')
def payment_success():
    """Gestione pagamento riuscito"""
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Errore: sessione non trovata", "danger")
        return redirect(url_for('index'))

    session_stripe = stripe.checkout.Session.retrieve(session_id)
    booking_id = int(session_stripe.metadata['booking_id'])

    booking = get_booking_by_id(booking_id)
    event = get_event_by_id(booking['event_id'])
    
    if booking and booking['status'] == 1:
        update_booking_status(booking_id, 2)  # Status 2 = pagato
        send_booking_email_html(booking_id)
    else:
        flash("Prenotazione non trovata o già pagata", "danger")

    return render_template('payment_success.html', event=event, booking=booking)

@app.route('/payment/cancel')
def payment_cancel():
    """Gestione pagamento annullato"""
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Errore: sessione non trovata", "danger")
        return redirect(url_for('index'))

    session_stripe = stripe.checkout.Session.retrieve(session_id)
    booking_id = int(session_stripe.metadata['booking_id'])
    delete_booking(booking_id)
    
    return render_template('payment_cancel.html')

# ---------- GESTIONE TRANSAZIONI ----------

@app.route('/event/<int:event_id>/transactions')
@login_required
def event_transactions(event_id):
    """Lista transazioni per evento"""
    event = get_event_by_id(event_id)
    transactions = get_bookings_by_event(event_id)
    
    return render_template(
        'event_transactions.html',
        event_title=event['title'] if event else 'Evento sconosciuto',
        transactions=transactions
    )

@app.route('/resend_ticket/<int:booking_id>', methods=['POST'])
@login_required
def resend_ticket(booking_id):
    """Reinvia ticket via email"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        flash('Prenotazione non trovata.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    
    if booking['status'] not in (2, 3):
        flash('Solo le prenotazioni pagate o validate possono ricevere il biglietto.', 'warning')
        return redirect(request.referrer or url_for('dashboard'))
    
    send_booking_email_html(booking_id)
    flash('Biglietto inviato nuovamente a ' + booking['email'], 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/delete_transaction/<int:booking_id>', methods=['POST'])
@login_required
def delete_transaction(booking_id):
    """Elimina transazione e libera i posti"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        flash('Prenotazione non trovata.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Salva informazioni per il messaggio di conferma
    event = get_event_by_id(booking['event_id'])
    seats_info = booking['seats']
    customer_name = booking['name']
    
    # Elimina la prenotazione
    delete_booking(booking_id)
    
    flash(f'Prenotazione eliminata con successo. Posti {seats_info} liberati per {customer_name}.', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/print_ticket/<int:booking_id>')
@login_required
def print_ticket(booking_id):
    """Pagina per stampare ticket"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return 'Prenotazione non trovata', 404
    
    event = get_event_by_id(booking['event_id'])
    return render_template('print_ticket.html', booking=booking, event=event)

# ---------- AVVIO APPLICAZIONE ----------

def run():
    app.run(debug=True)

if __name__ == '__main__':
    run()
