"""
Modulo per la generazione di PDF dei biglietti
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
import io
import requests
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from urllib.parse import urlparse

def generate_email_ticket_pdf(booking, event):
    """
    Genera un PDF del biglietto ottimizzato per email con logo e poster
    
    Args:
        booking: Dict con i dati della prenotazione
        event: Dict con i dati dell'evento
    
    Returns:
        bytes: Contenuto del PDF generato
    """
    
    buffer = io.BytesIO()
    
    # Crea documento PDF in formato biglietto
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.3*inch,
        leftMargin=0.3*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )
    
    # Stili
    styles = getSampleStyleSheet()
    
    # Stile personalizzato per il titolo
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_CENTER,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Stile per l'evento
    event_style = ParagraphStyle(
        'EventStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#744210'),
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Lista elementi del documento
    story = []
    
    # Header con logo se esiste
    try:
        if os.path.exists('static/img/logo.png'):
            logo = Image('static/img/logo.png', width=1*inch, height=1*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.1*inch))
    except:
        pass
    
    # Header con titolo teatro
    story.append(Paragraph("🎭 TEATRO SAN RAFFAELE", title_style))
    story.append(Paragraph("<b>BIGLIETTO D'INGRESSO</b>", event_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Titolo evento in evidenza
    story.append(Paragraph(f"<b>{event['title']}</b>", event_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Poster dell'evento se esiste
    if event['poster_url']:
        try:
            # Tenta di caricare il poster
            if event['poster_url'].startswith('http'):
                # URL esterno
                response = requests.get(event['poster_url'], timeout=5)
                if response.status_code == 200:
                    img_buffer = io.BytesIO(response.content)
                    poster = Image(img_buffer, width=1.5*inch, height=2*inch)
                    poster.hAlign = 'CENTER'
                    story.append(poster)
                    story.append(Spacer(1, 0.1*inch))
            else:
                # File locale
                poster_path = event['poster_url'].lstrip('/')
                if os.path.exists(poster_path):
                    poster = Image(poster_path, width=1.5*inch, height=2*inch)
                    poster.hAlign = 'CENTER'
                    story.append(poster)
                    story.append(Spacer(1, 0.1*inch))
        except:
            # Se il poster non è caricabile, continua senza
            pass
    
    # Tabella con dettagli biglietto
    seats_count = len(booking['seats'].split(','))
    total_price = event['price'] * seats_count
    
    # Dati per la tabella - layout migliorato
    data = [
        ['👤 Intestatario', booking['name']],
        ['📧 Contatto', booking['email']],
        ['📅 Data Spettacolo', event['date']],
        ['⏰ Orario', event['time']],
        ['🎫 Posti Riservati', booking['seats']],
        ['💰 Totale Pagato', f"€ {total_price:.2f}"],
        ['🎟️ Codice Biglietto', f"#{booking['id']:05d}"]
    ]
    
    # Crea tabella con stile compatto
    table = Table(data, colWidths=[2*inch, 3*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Prima colonna
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#744210')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.15*inch))
    
    # Note importanti compatte
    important_style = ParagraphStyle(
        'ImportantStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#744210'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("⚠️ Presentare questo biglietto all'ingresso • Arrivare 20 min prima", important_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Footer compatto
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    story.append(Paragraph("📍 Teatro San Raffaele • 📧 info@teatrosanraffaele.it", footer_style))
    story.append(Paragraph(f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}", footer_style))
    
    # Genera il PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_ticket_pdf(booking, event):
    """
    Genera un PDF del biglietto per una prenotazione
    
    Args:
        booking: Dict con i dati della prenotazione
        event: Dict con i dati dell'evento
    
    Returns:
        BytesIO: Buffer contenente il PDF generato
    """
    
    buffer = io.BytesIO()
    
    # Crea documento PDF in formato biglietto (landscape A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Stili
    styles = getSampleStyleSheet()
    
    # Stile personalizzato per il titolo
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    # Stile per l'evento
    event_style = ParagraphStyle(
        'EventStyle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#744210'),
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )
    
    # Stile per i dettagli
    detail_style = ParagraphStyle(
        'DetailStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    # Stile per info importanti
    important_style = ParagraphStyle(
        'ImportantStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#744210'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Lista elementi del documento
    story = []
    
    # Header con titolo teatro
    story.append(Paragraph("🎭 TEATRO SAN RAFFAELE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Titolo evento
    story.append(Paragraph(f"<b>{event['title']}</b>", event_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Tabella con dettagli biglietto
    seats_count = len(booking['seats'].split(','))
    total_price = event['price'] * seats_count
    
    # Dati per la tabella
    data = [
        ['👤 Intestatario:', booking['name']],
        ['📧 Email:', booking['email']],
        ['📅 Data Spettacolo:', event['date']],
        ['⏰ Orario:', event['time']],
        ['🎫 Posti:', booking['seats']],
        ['💰 Prezzo Totale:', f"€ {total_price:.2f}"],
        ['🎟️ ID Prenotazione:', f"#{booking['id']}"]
    ]
    
    # Crea tabella
    table = Table(data, colWidths=[3*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Prima colonna in grassetto
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#744210')),  # Prima colonna colorata
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2d3748')),  # Seconda colonna
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')),  # Sfondo prima colonna
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.4*inch))
    
    # Istruzioni importanti
    story.append(Paragraph("📋 ISTRUZIONI IMPORTANTI", important_style))
    story.append(Spacer(1, 0.1*inch))
    
    instructions = [
        "• Presentare questo biglietto all'ingresso del teatro",
        "• Arrivare almeno 15 minuti prima dell'orario di spettacolo",
        "• I posti sono numerati e riservati",
        "• Non è consentito fumare all'interno del teatro",
        "• Spegnere i cellulari durante lo spettacolo"
    ]
    
    for instruction in instructions:
        story.append(Paragraph(instruction, detail_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Footer con info teatro
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    
    story.append(Paragraph(f"Biglietto generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}", footer_style))
    
    # Genera il PDF
    doc.build(story)
    
    # Ritorna il buffer
    buffer.seek(0)
    return buffer.getvalue()


def generate_tickets_summary_pdf(bookings, event):
    """
    Genera un PDF riassuntivo con tutti i biglietti di un evento
    
    Args:
        bookings: Lista di prenotazioni
        event: Dict con i dati dell'evento
    
    Returns:
        BytesIO: Buffer contenente il PDF generato
    """
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # Header
    story.append(Paragraph("🎭 TEATRO SAN RAFFAELE", title_style))
    story.append(Paragraph(f"<b>Riepilogo Prenotazioni - {event['title']}</b>", title_style))
    story.append(Paragraph(f"Data: {event['date']} - Ore: {event['time']}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Tabella riassuntiva
    headers = ['ID', 'Nome', 'Email', 'Posti', 'Stato', 'Totale €']
    data = [headers]
    
    total_revenue = 0
    total_tickets = 0
    
    for booking in bookings:
        seats_count = len(booking['seats'].split(','))
        booking_total = event['price'] * seats_count
        total_revenue += booking_total
        total_tickets += seats_count
        
        status_map = {
            1: 'Pending',
            2: 'Pagato',
            3: 'Cassa'
        }
        
        data.append([
            str(booking['id']),
            booking['name'],
            booking['email'],
            booking['seats'],
            status_map.get(booking['status'], 'Sconosciuto'),
            f"€ {booking_total:.2f}"
        ])
    
    # Riga totale
    data.append(['', '', '', f'Tot. {total_tickets} posti', '', f'€ {total_revenue:.2f}'])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),     # Dati
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Totale
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f7fafc')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()