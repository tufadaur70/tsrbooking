import sqlite3

# Connessione al database
conn = sqlite3.connect('cinema.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Tabella Eventi
c.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    price REAL NOT NULL,
    poster_url TEXT,
    visible INTEGER DEFAULT 1
)
""")

# Tabella Prenotazioni
c.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    seats TEXT NOT NULL,          -- posti separati da , 
    status REAL DEFAULT 0 , -- 0=libero, 1=pending ,2 = acquistato , 3 = validato
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id)
)
""")

conn.commit()
conn.close()

print("Database inizializzato con successo!")
