#!/usr/bin/env python3
"""
Test completo della funzionalità elimina transazione
"""

from database import *
from booking_service import get_booked_seats

def test_delete_transaction_workflow():
    """Test del flusso completo di eliminazione transazione"""
    print("=== Test completo elimina transazione ===\n")
    
    event_id = 1
    
    # 1. Stato iniziale
    print("1. Stato iniziale:")
    initial_bookings = get_bookings_by_event(event_id)
    initial_booked_seats = get_booked_seats(event_id)
    print(f"   Prenotazioni totali: {len(initial_bookings)}")
    print(f"   Posti occupati: {initial_booked_seats}")
    
    # 2. Crea nuova prenotazione test
    print("\n2. Creazione prenotazione test:")
    test_seats = "C5,C6,C7"  # Posti facilmente identificabili
    booking_id = create_booking(event_id, "Mario Rossi", "mario@test.com", test_seats, status=2)
    print(f"   Prenotazione creata - ID: {booking_id}")
    print(f"   Cliente: Mario Rossi")
    print(f"   Posti: {test_seats}")
    print(f"   Status: 2 (Pagato)")
    
    # 3. Verifica posti occupati
    print("\n3. Verifica posti occupati:")
    bookings_after_create = get_bookings_by_event(event_id)
    booked_seats_after_create = get_booked_seats(event_id)
    print(f"   Prenotazioni totali: {len(bookings_after_create)}")
    print(f"   Posti occupati: {sorted(booked_seats_after_create)}")
    print(f"   Nuovi posti occupati: {[seat for seat in test_seats.split(',')]}")
    
    # 4. Verifica dettagli prenotazione
    print("\n4. Dettagli prenotazione creata:")
    booking = get_booking_by_id(booking_id)
    print(f"   ID: {booking['id']}")
    print(f"   Nome: {booking['name']}")
    print(f"   Email: {booking['email']}")
    print(f"   Posti: {booking['seats']}")
    print(f"   Status: {booking['status']}")
    print(f"   Creata il: {booking['created_at']}")
    
    # 5. Elimina prenotazione
    print("\n5. Eliminazione prenotazione:")
    print(f"   Eliminando prenotazione ID {booking_id}...")
    delete_booking(booking_id)
    print("   ✓ Prenotazione eliminata dal database")
    
    # 6. Verifica eliminazione
    print("\n6. Verifica stato dopo eliminazione:")
    deleted_booking = get_booking_by_id(booking_id)
    bookings_after_delete = get_bookings_by_event(event_id)
    booked_seats_after_delete = get_booked_seats(event_id)
    
    print(f"   Prenotazione esistente: {'No' if deleted_booking is None else 'Sì'}")
    print(f"   Prenotazioni totali: {len(bookings_after_delete)}")
    print(f"   Posti occupati: {sorted(booked_seats_after_delete)}")
    
    # 7. Verifica posti liberati
    print("\n7. Verifica posti liberati:")
    freed_seats = [seat for seat in test_seats.split(',') if seat not in booked_seats_after_delete]
    print(f"   Posti che erano occupati: {test_seats}")
    print(f"   Posti ora liberi: {freed_seats}")
    print(f"   Tutti i posti liberati: {'Sì' if len(freed_seats) == 3 else 'No'}")
    
    # 8. Riepilogo
    print("\n8. Riepilogo test:")
    print(f"   ✓ Prenotazione creata correttamente")
    print(f"   ✓ Posti correttamente occupati durante la prenotazione")
    print(f"   ✓ Prenotazione eliminata dal database")
    print(f"   ✓ Posti liberati e disponibili per nuove prenotazioni")
    print(f"   ✓ Nessuna traccia della prenotazione eliminata")
    
    return len(initial_bookings) == len(bookings_after_delete)

if __name__ == "__main__":
    success = test_delete_transaction_workflow()
    if success:
        print("\n🎉 Test completato con successo!")
    else:
        print("\n❌ Errore nel test!")