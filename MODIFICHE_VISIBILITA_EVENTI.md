# Modifiche implementate: Sistema di visibilità eventi

## Descrizione
Invece di eliminare fisicamente gli eventi dal database, il sistema ora permette di nasconderli dalla vista pubblica mantenendo tutti i dati (incluse le prenotazioni) intatti nel database.

## Modifiche apportate

### 1. Database (`database.py`)
- ✅ **get_all_events()**: Ora restituisce solo eventi visibili (`visible = 1`) per la homepage
- ✅ **get_all_events_admin()**: Nuova funzione che restituisce tutti gli eventi (inclusi nascosti) per l'admin
- ✅ **create_event()**: Aggiunto campo `visible` con default a 1 (visibile)
- ✅ **update_event()**: Supporto per aggiornare il campo `visible`
- ✅ **hide_event()**: Nuova funzione per nascondere un evento (`visible = 0`)
- ✅ **show_event()**: Nuova funzione per rendere visibile un evento (`visible = 1`)
- ✅ **delete_event()**: Mantenuta per emergenze (eliminazione fisica completa)

### 2. Schema Database (`db_init.py`)
- ✅ Aggiunta colonna `visible INTEGER DEFAULT 1` alla tabella `events`

### 3. Migrazione Database
- ✅ **migrate_visible_column.py**: Script per aggiornare database esistenti
- ✅ Aggiunge colonna `visible` se non esiste
- ✅ Imposta tutti gli eventi esistenti come visibili (`visible = 1`)

### 4. Applicazione Web (`app.py`)
- ✅ **dashboard()**: Usa `get_all_events_admin()` per mostrare tutti gli eventi inclusi quelli nascosti
- ✅ **hide_event_route()**: Nuova route `/event/<id>/hide` per nascondere eventi
- ✅ **show_event_route()**: Nuova route `/event/<id>/show` per rendere visibili eventi
- ✅ Aggiornato `edit_event()` per gestire il campo `visible`

### 5. Template Dashboard (`dashboard.html`)
- ✅ Aggiunta colonna "Stato" per mostrare se evento è visibile o nascosto
- ✅ Sostituito pulsante "Elimina" con pulsanti dinamici "Nascondi"/"Mostra"
- ✅ Indicatori visivi colorati per lo stato (verde = visibile, rosso = nascosto)
- ✅ Conferme diverse per nascondere/mostrare eventi

## Funzionamento

### Homepage (Vista Pubblica)
- Mostra solo eventi con `visible = 1`
- Gli eventi nascosti non compaiono nella lista

### Dashboard Admin
- Mostra tutti gli eventi (visibili e nascosti)
- Colonna "Stato" indica chiaramente la visibilità
- Pulsanti per nascondere/mostrare eventi

### Sicurezza
- Solo gli admin possono nascondere/mostrare eventi
- Le prenotazioni esistenti rimangono intatte quando un evento viene nascosto
- Possibilità di ripristinare eventi nascosti senza perdita di dati

## Vantaggi
1. **Conservazione dati**: Prenotazioni e dati evento non vengono mai persi
2. **Reversibilità**: Eventi nascosti possono essere facilmente ripristinati
3. **Controllo**: Admin può gestire la visibilità degli eventi senza eliminazioni permanenti
4. **Storico**: Mantiene storico completo per analisi e report
5. **Sicurezza**: Riduce rischio di perdita accidentale di dati

## Test effettuati
- ✅ Migrazione database esistente
- ✅ Funzioni di visibilità (hide/show)
- ✅ Filtro eventi visibili per homepage
- ✅ Visualizzazione completa per admin
- ✅ Import e caricamento applicazione senza errori