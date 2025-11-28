import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import stripe
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps

# Import moduli locali
from config import *
from database import *
from email_service import  send_booking_confirmation_with_pdf
from auth import login_required, check_admin_credentials
from booking_service import *
from pdf_generator import generate_email_ticket_pdf, generate_tickets_summary_pdf

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

# Configurazione Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(BadRequest)
def bad_request_error(error):
    flash('Richiesta non valida', 'error')
    return redirect(url_for('index'))

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
    """Homepage con lista eventi visibili"""
    try:
        events = get_all_events()
        logger.info(f"Caricati {len(events)} eventi visibili per homepage")
        return render_template('index.html', events=events)
    except Exception as e:
        logger.error(f"Errore nel caricamento eventi: {e}")
        flash('Errore nel caricamento degli eventi', 'error')
        return render_template('index.html', events=[])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Login admin con validazione migliorata"""
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username e password sono obbligatori', 'error')
            return render_template('login.html')
        
        if check_admin_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            logger.info(f"Login admin riuscito per {username}")
            flash('Login effettuato con successo', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Tentativo login fallito per {username}")
            flash('Credenziali non valide', 'error')
            return render_template('login.html')
    
    except Exception as e:
        logger.error(f"Errore durante login: {e}")
        flash('Errore interno durante il login', 'error')
        return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    """Logout admin sicuro"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"Logout effettuato per {username}")
    flash('Logout effettuato con successo', 'info')
    return redirect(url_for('admin'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard admin con statistiche eventi"""
    try:
        events = get_all_events_admin()
        event_list = []
        
        for event in events:
            try:
                stats = get_event_stats(event['id'])
                event_list.append({
                    'id': event['id'],
                    'title': event['title'],
                    'date': event['date'],
                    'time': event['time'],
                    'price': event['price'],
                    'sold': stats['sold'],
                    'validated': stats['validated'],
                    'pending': stats['pending'],
                    'visible': event['visible'],
                })
            except Exception as e:
                logger.error(f"Errore calcolo statistiche evento {event['id']}: {e}")
                # Aggiungi evento senza statistiche
                event_list.append({
                    'id': event['id'],
                    'title': event['title'],
                    'date': event['date'],
                    'time': event['time'],
                    'price': event['price'],
                    'sold': 0,
                    'validated': 0,
                    'pending': 0,
                    'visible': event['visible'],
                })
        
        logger.info(f"Dashboard caricata con {len(event_list)} eventi")
        return render_template('dashboard.html', events=event_list)
        
    except Exception as e:
        logger.error(f"Errore caricamento dashboard: {e}")
        flash('Errore nel caricamento della dashboard', 'error')
        return render_template('dashboard.html', events=[])

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
        flash('Prenotazione registrata con successo!', 'success')
        return redirect(url_for('dashboard'))

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
        send_booking_confirmation_with_pdf(booking_id)
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
        event_id=event_id,
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
    
    send_booking_confirmation_with_pdf(booking_id)
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

@app.route('/generate_ticket_pdf/<int:booking_id>')
@login_required
def generate_ticket_pdf_route(booking_id):
    """Genera PDF del biglietto per una prenotazione"""
    try:
        booking = get_booking_by_id(booking_id)
        if not booking:
            flash('Prenotazione non trovata.', 'error')
            return redirect(url_for('dashboard'))
        
        event = get_event_by_id(booking['event_id'])
        if not event:
            flash('Evento non trovato.', 'error')
            return redirect(url_for('dashboard'))
        
        # Genera PDF
        pdf_data = generate_email_ticket_pdf(booking, event)
        
        # Prepara nome file
        filename = f"biglietto_{event['title'].replace(' ', '_')}_{booking['id']}.pdf"
        
        # Ritorna PDF come download
        from flask import make_response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f'Errore generazione PDF: {str(e)}')
        flash('Errore durante la generazione del PDF.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/generate_event_summary_pdf/<int:event_id>')
@login_required
def generate_event_summary_pdf_route(event_id):
    """Genera PDF riassuntivo di tutte le prenotazioni di un evento"""
    try:
        event = get_event_by_id(event_id)
        if not event:
            flash('Evento non trovato.', 'error')
            return redirect(url_for('dashboard'))
        
        # Ottieni tutte le transazioni dell'evento
        bookings = get_event_transactions(event_id)
        
        if not bookings:
            flash('Nessuna prenotazione trovata per questo evento.', 'warning')
            return redirect(url_for('event_transactions', event_id=event_id))
        
        # Genera PDF riassuntivo
        pdf_data = generate_tickets_summary_pdf(bookings, event)
        
        # Prepara nome file
        filename = f"riepilogo_{event['title'].replace(' ', '_')}.pdf"
        
        # Ritorna PDF come download
        from flask import make_response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f'Errore generazione PDF riepilogo: {str(e)}')
        flash('Errore durante la generazione del PDF riepilogo.', 'error')
        return redirect(url_for('dashboard'))

# ---------- AVVIO APPLICAZIONE ----------

def run():
    app.run(debug=True)

if __name__ == '__main__':
    run()
