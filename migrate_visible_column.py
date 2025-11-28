#!/usr/bin/env python3
"""
Script per aggiungere la colonna 'visible' alla tabella events esistente
Questo script deve essere eseguito una sola volta per aggiornare il database esistente.
"""

import sqlite3
from config import DB_PATH

def migrate_database():
    """Aggiunge la colonna visible alla tabella events se non esiste"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verifica se la colonna visible esiste già
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'visible' not in columns:
            print("Aggiungendo colonna 'visible' alla tabella events...")
            cursor.execute("ALTER TABLE events ADD COLUMN visible INTEGER DEFAULT 1")
            
            # Imposta tutti gli eventi esistenti come visibili
            cursor.execute("UPDATE events SET visible = 1 WHERE visible IS NULL")
            
            conn.commit()
            print("✓ Migrazione completata con successo!")
            print("✓ Tutti gli eventi esistenti sono ora visibili per default")
        else:
            print("✓ La colonna 'visible' esiste già nel database")
            
    except Exception as e:
        print(f"❌ Errore durante la migrazione: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()