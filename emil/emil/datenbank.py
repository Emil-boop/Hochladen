import sqlite3

# Datenbank verbinden
db = sqlite3.connect("bibliothek_neu.db")
cursor = db.cursor()

# Tabelle für einzelne Buchexemplare
cursor.execute("""
CREATE TABLE IF NOT EXISTS buecher (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT NOT NULL,
    titel TEXT NOT NULL,
    ausgeliehen INTEGER DEFAULT 0,
    regalstandort TEXT,
    ausleiher TEXT,
    rueckgabedatum TEXT
)
""")

cursor.execute("PRAGMA table_info(buecher)")
buecher_spalten = {spalte[1] for spalte in cursor.fetchall()}
if "ausleiher" not in buecher_spalten:
    cursor.execute("ALTER TABLE buecher ADD COLUMN ausleiher TEXT")
if "rueckgabedatum" not in buecher_spalten:
    cursor.execute("ALTER TABLE buecher ADD COLUMN rueckgabedatum TEXT")

cursor.execute("""
CREATE TABLE IF NOT EXISTS qr_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qr_inhalt TEXT NOT NULL,
    isbn TEXT,
    titel TEXT,
    regalstandort TEXT,
    erfasst_am TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


def linie():
    print("=" * 85)


def _buch_als_text(buch):
    buch_id, isbn, titel, ausgeliehen, regal = buch
    status = "Ausgeliehen" if ausgeliehen else "Verfügbar"
    return (
        f"ID: {buch_id}\n"
        f"ISBN: {isbn}\n"
        f"Titel: {titel}\n"
        f"Status: {status}\n"
        f"Regal: {regal}"
    )


def qr_scan_speichern(qr_inhalt):
    if qr_inhalt is None:
        return None

    qr_text = str(qr_inhalt).strip()
    if not qr_text:
        return None

    isbn = ""
    titel = ""
    regal = ""

    if qr_text.isdigit():
        cursor.execute(
            """
            SELECT id, isbn, titel, ausgeliehen, regalstandort
            FROM buecher
            WHERE id = ?
            """,
            (int(qr_text),),
        )
        buch = cursor.fetchone()
        if buch is not None:
            _, isbn, titel, _, regal = buch
    else:
        cursor.execute(
            """
            SELECT id, isbn, titel, ausgeliehen, regalstandort
            FROM buecher
            WHERE isbn = ? OR titel = ?
            LIMIT 1
            """,
            (qr_text, qr_text),
        )
        buch = cursor.fetchone()
        if buch is not None:
            _, isbn, titel, _, regal = buch

    cursor.execute(
        """
        INSERT INTO qr_scans (qr_inhalt, isbn, titel, regalstandort)
        VALUES (?, ?, ?, ?)
        """,
        (qr_text, isbn, titel, regal),
    )
    db.commit()
    return cursor.lastrowid


def qr_scans_anzeigen():
    cursor.execute("""
    SELECT id, qr_inhalt, isbn, titel, regalstandort, erfasst_am
    FROM qr_scans
    ORDER BY id DESC
    """)
    return cursor.fetchall()


# Buch hinzufügen
def buch_hinzufuegen(isbn,titel,regal,menge):
    print("\n--- BUCH HINZUFÜGEN ---")


    if not isbn or not titel or not regal:
        print("FEHLER: Alle Felder müssen ausgefüllt werden!")
        return

    try:

        if menge <= 0:
            print("Die Menge muss größer als 0 sein!")
            return

        print("\nFolgende Exemplare wurden hinzugefügt:")

        for _ in range(menge):
            cursor.execute("""
            INSERT INTO buecher
            (
            isbn, titel, ausgeliehen, regalstandort)
            VALUES (?, ?, 0, ?)
            """, (isbn, titel, regal))

            print(
                "Exemplar-ID:",
                cursor.lastrowid,
                "| Titel:",
                titel,
                "| Regal:",
                regal
            )

        db.commit()
        print("\n", menge, "Exemplar(e) erfolgreich hinzugefügt!")

    except ValueError:
        print("FEHLER: Bitte eine gültige Menge eingeben!")

    inserted_id = cursor.lastrowid
    return inserted_id


# Alle Bücher anzeigen
def buecher_anzeigen():
    print("\n--- GESAMTER BÜCHERBESTAND ---")
    linie()

    cursor.execute("""
    SELECT id, isbn, titel, ausgeliehen, regalstandort
    FROM buecher
    ORDER BY id
    """)

    buecher = cursor.fetchall()

    if not buecher:
        print("Keine Bücher vorhanden.")
        linie()
        return

    print(
        f"{'ID':<6} {'ISBN':<18} {'Titel':<25} "
        f"{'Status':<15} {'Regal'}"
    )

    linie()

    for buch in buecher:
        buch_id, isbn, titel, ausgeliehen, regal = buch

        status = "Ausgeliehen" if ausgeliehen else "Verfügbar"

        print(
            f"{buch_id:<6} {isbn:<18} {titel[:24]:<25} "
            f"{status:<15} {regal}"
        )

    linie()
    print("Gesamtzahl Exemplare:", len(buecher))
    print(
        "Ausgeliehen:",
        sum(b[3] for b in buecher)
    )
    print(
        "Verfügbar:",
        sum(1 for b in buecher if b[3] == 0)
    )
    linie()


def alle_buecher_laden():
    cursor.execute("""
    SELECT id, isbn, titel, ausgeliehen, regalstandort, ausleiher, rueckgabedatum
    FROM buecher
    ORDER BY id
    """)
    return cursor.fetchall()


def buch_nach_id_laden(buch_id):
    cursor.execute("""
    SELECT id, isbn, titel, ausgeliehen, regalstandort, ausleiher, rueckgabedatum
    FROM buecher
    WHERE id = ?
    """, (buch_id,))
    return cursor.fetchone()


def buch_ausleihen_mit_details(buch_id, ausleiher, rueckgabedatum):
    if not ausleiher or not rueckgabedatum:
        raise ValueError("Ausleiher und Rückgabedatum müssen angegeben werden.")

    cursor.execute("""
    UPDATE buecher
    SET ausgeliehen = 1, ausleiher = ?, rueckgabedatum = ?
    WHERE id = ? AND ausgeliehen = 0
    """, (ausleiher, rueckgabedatum, buch_id))
    db.commit()
    return cursor.rowcount == 1


def buch_zurueckgeben_mit_id(buch_id):
    cursor.execute("""
    UPDATE buecher
    SET ausgeliehen = 0, ausleiher = NULL, rueckgabedatum = NULL
    WHERE id = ? AND ausgeliehen = 1
    """, (buch_id,))
    db.commit()
    return cursor.rowcount == 1


# Buch suchen
def buch_suchen(suchbegriff):
    print("\n--- BUCH SUCHEN ---")

    suchbegriff = str(suchbegriff or "").strip()
    if not suchbegriff:
        return "Kein Suchbegriff angegeben."

    cursor.execute("""
    SELECT id, isbn, titel, ausgeliehen, regalstandort
    FROM buecher
    WHERE isbn LIKE ? OR titel LIKE ? OR CAST(id AS TEXT) LIKE ?
    ORDER BY id
    """, ('%' + suchbegriff + '%',
          '%' + suchbegriff + '%', '%' + suchbegriff + '%'))

    ergebnisse = cursor.fetchall()

    if not ergebnisse:
        print("Kein Buch gefunden.")
        return "Kein Buch gefunden."

    print("\nGefundene Exemplare:")
    result = []
    for buch in ergebnisse:
        status = "Ausgeliehen" if buch[3] else "Verfügbar"
        result.append(
            f"Exemplar-ID: {buch[0]}\n"
            f"ISBN: {buch[1]}\n"
            f"Titel: {buch[2]}\n"
            f"Status: {status}\n"
            f"Regalstandort: {buch[4]}"
        )
        print("-" * 50)
        print(result[-1])

    return "\n\n".join(result)


# Buch ausleihen
def buch_ausleihen(id):
    print("\n--- BUCH AUSLEIHEN ---")

    if not id.isdigit():
        print("FEHLER: Ungültige ID!")
        return

    cursor.execute("""
    SELECT id, isbn, titel, ausgeliehen, regalstandort
    FROM buecher
    WHERE id = ?
    """, (int(id),))

    buch = cursor.fetchone()

    if buch is None:
        print("FEHLER: Dieses Exemplar existiert nicht!")
        return

    if buch[3] == 1:
        print("Dieses Exemplar ist bereits ausgeliehen!")
        print("Titel:", buch[2])
        print("Exemplar-ID:", buch[0])
        return

    cursor.execute("""
    UPDATE buecher
    SET ausgeliehen = 1
    WHERE id = ?
    """, (buch[0],))

    db.commit()

    print("\nBUCH ERFOLGREICH AUSGELIEHEN!")
    print("Exemplar-ID:", buch[0])
    print("Titel:", buch[2])
    print("ISBN:", buch[1])
    print("Regalstandort:", buch[4])


# Buch zurückgeben
def buch_zurueckgeben():
    print("\n--- BUCH ZURÜCKGEBEN ---")

    buch_id = input("Exemplar-ID eingeben: ").strip()

    if not buch_id.isdigit():
        print("FEHLER: Ungültige ID!")
        return

    cursor.execute("""
    SELECT id, titel, ausgeliehen
    FROM buecher
    WHERE id = ?
    """, (int(buch_id),))

    buch = cursor.fetchone()

    if buch is None:
        print("Dieses Exemplar wurde nicht gefunden!")
        return

    if buch[2] == 0:
        print("Dieses Exemplar ist nicht ausgeliehen!")
        return

    cursor.execute("""
    UPDATE buecher
    SET ausgeliehen = 0, ausleiher = NULL, rueckgabedatum = NULL
    WHERE id = ?
    """, (buch[0],))

    db.commit()

    print("\nBUCH ERFOLGREICH ZURÜCKGEGEBEN!")
    print("Exemplar-ID:", buch[0])
    print("Titel:", buch[1])
    print("Status: Wieder verfügbar")


# Buch löschen
def buch_loeschen():
    print("\n--- BUCH LÖSCHEN ---")

    buch_id = input("Exemplar-ID eingeben: ").strip()

    if not buch_id.isdigit():
        print("FEHLER: Ungültige ID!")
        return

    cursor.execute("""
    SELECT id, titel, ausgeliehen
    FROM buecher
    WHERE id = ?
    """, (int(buch_id),))

    buch = cursor.fetchone()

    if buch is None:
        print("Dieses Exemplar wurde nicht gefunden!")
        return

    if buch[2] == 1:
        print("Dieses Exemplar ist noch ausgeliehen!")
        return

    bestaetigung = input(
        f"Soll '{buch[1]}' mit ID {buch[0]} gelöscht werden? (j/n): "
    ).lower()

    if bestaetigung == "j":
        cursor.execute(
            "DELETE FROM buecher WHERE id = ?",
            (buch[0],)
        )
        db.commit()

        print("Exemplar erfolgreich gelöscht!")
        print("Gelöschte ID:", buch[0])
        print("Titel:", buch[1])
    else:
        print("Löschen abgebrochen.")


# Hauptmenü
def menue():
    while True:
        print("\n")
        linie()
        print("          BIBLIOTHEKSVERWALTUNG")
        linie()

        print("1 - Buch hinzufügen")
        print("2 - Alle Bücher anzeigen")
        print("3 - Buch suchen")
        print("4 - Buch ausleihen")
        print("5 - Buch zurückgeben")
        print("6 - Buch löschen")
        print("7 - Programm beenden")

        linie()

        auswahl = input("Menüpunkt auswählen: ").strip()

        if auswahl == "1":
            buch_hinzufuegen()
        elif auswahl == "2":
            buecher_anzeigen()
        elif auswahl == "3":
            buch_suchen()
        elif auswahl == "4":
            buch_ausleihen()
        elif auswahl == "5":
            buch_zurueckgeben()
        elif auswahl == "6":
            buch_loeschen()
        elif auswahl == "7":
            print("Programm wird beendet.")
            break
        else:
            print("Ungültige Eingabe!")

        input("\nENTER drücken, um fortzufahren...")


if __name__ == "__main__":
    try:
        menue()
    except KeyboardInterrupt:
        print("\nProgramm abgebrochen.")
    finally:
        db.close()
        print("Datenbankverbindung geschlossen.")
