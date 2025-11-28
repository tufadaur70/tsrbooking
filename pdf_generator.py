"""
Modulo per la generazione di PDF dei biglietti
"""

def debug_image_paths(image_path):
    """Debug function per controllare i percorsi delle immagini"""
    import os
    print(f"=== DEBUG PERCORSO IMMAGINE ===")
    print(f"Path richiesto: {image_path}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(__file__)}")
    
    possible_paths = [
        os.path.join(os.path.dirname(__file__), image_path.lstrip('/')),
        os.path.join(os.getcwd(), image_path.lstrip('/')),
        image_path.lstrip('/'),
        os.path.join('static', image_path.lstrip('/static/'))
    ]
    
    for i, path in enumerate(possible_paths):
        exists = os.path.exists(path)
        print(f"Percorso {i+1}: {path} - {'ESISTE' if exists else 'NON ESISTE'}")
    print("==============================")
    return possible_paths

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
    
    # Crea documento PDF in formato biglietto elegante
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.4*inch,
        leftMargin=0.4*inch,
        topMargin=0.4*inch,
        bottomMargin=0.4*inch
    )
    
    # Stili
    styles = getSampleStyleSheet()
    
    # Stili eleganti per biglietto teatrale - senza cornici
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.HexColor('#2B4C8C'),  # Blu elegante
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#F8F9FA'),  # Grigio molto chiaro
        borderWidth=0,  # Nessuna cornice
        borderPadding=10
    )
    
    # Stile per l'evento elegante - senza cornice
    event_style = ParagraphStyle(
        'EventTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#8B0000'),  # Rosso scuro teatrale
        alignment=TA_CENTER,
        spaceAfter=18,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#F0F0F0'),  # Grigio chiaro
        borderWidth=0,  # Nessuna cornice
        borderPadding=12
    )
    
    # Stile per dettagli eleganti - più grandi e senza cornici
    detail_style = ParagraphStyle(
        'TicketDetails',
        parent=styles['Normal'],
        fontSize=16,  # Aumentato da 12 a 16
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#FFFFFF'),  # Bianco pulito
        borderWidth=0,  # Nessuna cornice
        borderPadding=10
    )
    
    # Lista elementi del documento
    story = []
    
    # Header con logo se esiste
    try:
        import os
        # Prova diversi percorsi possibili per il logo
        base_dir = os.environ.get('APP_BASE_DIR', os.path.dirname(__file__))
        logo_paths = [
            os.path.join(base_dir, 'static', 'img', 'logo.png'),
            os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.png'),
            os.path.join(os.getcwd(), 'static', 'img', 'logo.png'),
            'static/img/logo.png',
            './static/img/logo.png'
        ]
        
        logo_loaded = False
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.2*inch, height=1.2*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.1*inch))
                logo_loaded = True
                break
        
        if not logo_loaded:
            # Fallback: aggiungi spazio per il logo mancante
            print("Warning: Logo non trovato in nessun percorso")
            story.append(Spacer(1, 0.3*inch))
            
    except Exception as e:
        # Log dell'errore ma continua
        print(f"Errore caricamento logo: {e}")
        story.append(Spacer(1, 0.3*inch))
    
    # Titolo principale del teatro
    story.append(Paragraph("🎭 BIGLIETTO D'INGRESSO 🎭", title_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Titolo evento in evidenza con bordo dorato
    story.append(Paragraph(f"<b>🎪 {event['title']} 🎪</b>", event_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Poster dell'evento (più piccolo ma elegante)
    if event['poster_url']:
        try:
            poster_added = False
            if event['poster_url'].startswith('http'):
                # URL esterno
                import requests
                response = requests.get(event['poster_url'], timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; TSR-PDF-Generator/1.0)'
                })
                if response.status_code == 200:
                    img_buffer = io.BytesIO(response.content)
                    poster = Image(img_buffer, width=1.8*inch, height=2.2*inch)
                    poster.hAlign = 'CENTER'
                    story.append(poster)
                    story.append(Spacer(1, 0.1*inch))
                    poster_added = True
            else:
                # File locale - prova diversi percorsi
                base_dir = os.environ.get('APP_BASE_DIR', os.path.dirname(__file__))
                poster_paths = [
                    os.path.join(base_dir, event['poster_url'].lstrip('/')),
                    os.path.join(os.path.dirname(__file__), event['poster_url'].lstrip('/')),
                    os.path.join(os.getcwd(), event['poster_url'].lstrip('/')),
                    event['poster_url'].lstrip('/'),
                    os.path.join('static', event['poster_url'].lstrip('/static/'))
                ]
                
                for poster_path in poster_paths:
                    if os.path.exists(poster_path):
                        poster = Image(poster_path, width=1.8*inch, height=2.2*inch)
                        poster.hAlign = 'CENTER'
                        story.append(poster)
                        story.append(Spacer(1, 0.1*inch))
                        poster_added = True
                        break
                        
            if not poster_added:
                # Fallback: placeholder testuale pulito
                placeholder_style = ParagraphStyle(
                    'PlaceholderStyle',
                    parent=styles['Normal'],
                    fontSize=16,
                    textColor=colors.HexColor('#2B4C8C'),
                    alignment=TA_CENTER,
                    backColor=colors.HexColor('#F8F9FA'),
                    borderWidth=0,  # Nessuna cornice
                    borderPadding=25
                )
                story.append(Paragraph("🎭<br/>POSTER<br/>NON DISPONIBILE", placeholder_style))
                story.append(Spacer(1, 0.1*inch))
                
        except Exception as e:
            print(f"Errore caricamento poster: {e}")
            # Aggiungi placeholder pulito in caso di errore
            placeholder_style = ParagraphStyle(
                'PlaceholderStyle',
                parent=styles['Normal'],
                fontSize=16,
                textColor=colors.HexColor('#8B0000'),
                alignment=TA_CENTER,
                backColor=colors.HexColor('#F8F9FA'),
                borderWidth=0,  # Nessuna cornice
                borderPadding=25
            )
            story.append(Paragraph("🎭<br/>ERRORE CARICAMENTO<br/>POSTER", placeholder_style))
            story.append(Spacer(1, 0.1*inch))
    
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
    
    # Crea tabella pulita senza cornici
    table = Table(data, colWidths=[2.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),  # Aumentato da 11 a 14
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Prima colonna
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),  # Anche i valori in bold
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2B4C8C')),  # Blu elegante
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#8B0000')),  # Rosso teatrale
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Nessuna griglia/cornice
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),  # Grigio chiaro per etichette
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FFFFFF')),  # Bianco per valori
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F0F0F0')]),
        ('PADDING', (0, 0), (-1, -1), 12),  # Aumentato padding
        ('LINEBELOW', (0, 0), (-1, -2), 1, colors.HexColor('#E0E0E0')),  # Solo linee sottili tra righe
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.2*inch))
    
    # Box istruzioni pulito - senza cornici
    important_style = ParagraphStyle(
        'ImportantBox',
        parent=styles['Normal'],
        fontSize=14,  # Più grande
        textColor=colors.HexColor('#8B0000'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#F8F9FA'),  # Grigio chiaro
        borderWidth=0,  # Nessuna cornice
        borderPadding=12
    )
    
    story.append(Paragraph("⚠️ ISTRUZIONI IMPORTANTI ⚠️<br/>Presentare questo biglietto all'ingresso • Arrivare 20 minuti prima", important_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Footer elegante - senza giallo
    footer_style = ParagraphStyle(
        'FooterElegant',
        parent=styles['Normal'],
        fontSize=11,  # Più grande
        textColor=colors.HexColor('#2B4C8C'),
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        backColor=colors.HexColor('#F8F9FA'),  # Grigio chiaro
        borderColor=colors.HexColor('#2B4C8C'),
        borderWidth=1,
        borderPadding=8
    )
    
    story.append(Paragraph("🏛️ TEATRO SAN RAFFAELE 🏛️<br/>📧 info@teatrosanraffaele.it", footer_style))
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph(f"Biglietto generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}", 
                          ParagraphStyle('FooterDate', parent=styles['Normal'], fontSize=8, 
                                       textColor=colors.HexColor('#718096'), alignment=TA_CENTER)))
    
    # Genera il PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()

#PEPPE
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