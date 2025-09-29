import smtplib
from email.message import EmailMessage
from config import EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT
from database import get_booking_by_id, get_event_by_id

def send_booking_email_html(booking_id):
    """Invia email di conferma prenotazione"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return "Prenotazione non trovata"
    
    event = get_event_by_id(booking['event_id'])
    if not event:
        return "Evento non trovato"
    
    event_title = event['title']
    event_date = event['date']
    event_time = event['time']
    seats = booking['seats']
    to_email = booking['email']
    name = booking['name']

    subject = f'ACQUISTO CONFERMATO {event_title}'

    # Percorsi immagini
    logo_url = 'https://booking.tfnmusic.it/static/img/logo.png'
    poster_url = ''
    if event['poster_url']:
        if event['poster_url'].startswith('http'):
            poster_url = event['poster_url']
        else:
            poster_url = f"https://booking.tfnmusic.it{event['poster_url']}"
    
    poster_img_html = (
        f"<img src='{poster_url}' alt='Locandina evento' "
        f"style='max-width:220px;border-radius:8px;box-shadow:0 1px 6px #0002;"
        f"margin:0 auto 10px auto;display:block;'>" 
        if poster_url else ''
    )

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
                Nominativo: <b>{name}</b><br>
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
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    msg.set_content("Conferma di acquisto")
    msg.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return "Message sent!"
    except Exception as e:
        return f"Errore invio email: {e}"