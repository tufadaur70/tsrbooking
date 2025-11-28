#!/usr/bin/env python3
"""
Test delle nuove funzionalità di visibilità eventi
"""

from database import get_all_events, get_all_events_admin

def test_visibility_functions():
    """Test delle funzioni di visibilità degli eventi"""
    print("=== Test funzioni visibilità eventi ===\n")
    
    # Test get_all_events (solo visibili)
    print("1. Eventi visibili (per homepage):")
    visible_events = get_all_events()
    for event in visible_events:
        print(f"   - {event['title']} (ID: {event['id']}) - Visibile: {bool(event['visible'])}")
    
    # Test get_all_events_admin (tutti gli eventi)
    print("\n2. Tutti gli eventi (per admin dashboard):")
    all_events = get_all_events_admin()
    for event in all_events:
        visible_status = "✓ Visibile" if event['visible'] else "✗ Nascosto"
        print(f"   - {event['title']} (ID: {event['id']}) - {visible_status}")
    
    print(f"\nRiepilogo:")
    print(f"- Eventi visibili nella homepage: {len(visible_events)}")
    print(f"- Eventi totali nel database: {len(all_events)}")
    print(f"- Eventi nascosti: {len(all_events) - len(visible_events)}")

if __name__ == "__main__":
    test_visibility_functions()