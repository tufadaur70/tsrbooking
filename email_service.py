import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.message import EmailMessage
from config import EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT
from database import get_booking_by_id, get_event_by_id
from pdf_generator import generate_email_ticket_pdf

def send_booking_confirmation_with_pdf(booking_id):
    """Invia email di conferma con biglietto PDF allegato - testo essenziale"""
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

    subject = f'Biglietto - {event_title}'

   

    # HTML essenziale
    html_body = f"""
    <div style='font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;'>
        <h2 style='color:#2d3748;text-align:center;'>Teatro San Raffaele</h2>
        <p>Gentile <strong>{name}</strong>,</p>
        <p>Ecco il suo biglietto per:</p>
        <div style='background:#f8f9fa;padding:15px;border-radius:8px;margin:15px 0;'>
            <h3 style='color:#744210;margin:0 0 10px 0;'>{event_title}</h3>
            <p style='margin:5px 0;'><strong>Data:</strong> {event_date}</p>
            <p style='margin:5px 0;'><strong>Ora:</strong> {event_time}</p>
            <p style='margin:5px 0;'><strong>Posti:</strong> {seats}</p>
            <p style='margin:5px 0;'><strong>Codice prenotazione:</strong> {booking_id}</p>
        </div>
        <p>Il biglietto in PDF è allegato a questa email.</p>
        <p>NON OCCORRE STAMPARE IL BIGLIETTO</p>
        <p style='color:#666;'>Cordiali saluti,<br>Teatro San Raffaele</p>
    </div>
    """

    # Genera PDF del biglietto
    try:
        pdf_data = generate_email_ticket_pdf(booking, event)
        if not pdf_data:
            return "Errore nella generazione del PDF"
    except Exception as e:
        return f"Errore PDF: {e}"

    # Prepara email multipart
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email

    # Aggiungi testo
    
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Aggiungi PDF come allegato
    pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                             filename=f'biglietto_{booking_id}_{event_title.replace(" ", "_")}.pdf')
    msg.attach(pdf_attachment)

    # Invia email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return "Email con biglietto PDF inviata con successo!"
    except Exception as e:
        return f"Errore invio email: {e}"

   