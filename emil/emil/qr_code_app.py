import base64
import io
import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import cv2
import segno
import datenbank





QR_CODE_ORDNER = Path("erstellte_qr_codes")
QR_HINTERGRUENDE = {
    "Weiß": "#FFFFFF",
    "Hellblau": "#DCEEFF",
    "Creme": "#FFF4CC",
    "Hellgrün": "#DDF5E1",
    "Rosa": "#FFE0E6",
    "Lavendel": "#E9DFFF",
    "Hellgrau": "#EEEEEE",
    "Mint": "#D8F3EA",
    "Apricot": "#FFE1C2",
    "Hellgelb": "#FFF9B0",
}


def aendereUeberschrift(neueUeberschrift):
    fenster.title(neueUeberschrift)


def menuleiste_pushdown(fensteraenderung):
    global anwendung
    stoppe_scanner()
    anwendung = fensteraenderung
    aktualisiere_inhalt()


def aktualisiere_inhalt():
    for widget in fenster.winfo_children():
        if widget is not menuleiste:
            widget.destroy()

    global eingabefeld1, eingabefeld2,eingabefeld3,eingabefeld4, qr_vorschau, farbauswahl

    if anwendung == "QR-Code-erstellen":
        tk.Label(fenster, text="Daten für den QR-Code:").grid(
            row=0, column=0, padx=10, pady=8, sticky="e"
        )
        eingabefeld1 = tk.Entry(
            fenster,
            width=60,
            validate="key",
            validatecommand=(fenster.register(qr_eingabe_gueltig), "%P"),
        )
        eingabefeld1.grid(row=0, column=1, padx=10, pady=(8, 0), sticky="w")
        tk.Label(fenster, text="Maximal 200 Zeichen").grid(
            row=1, column=1, padx=10, sticky="w"
        )

        tk.Label(fenster, text="Buchtitel:").grid(
            row=2, column=0, padx=10, pady=8, sticky="e"
        )
        eingabefeld2 = tk.Entry(fenster, width=40)
        eingabefeld2.grid(row=2, column=1, padx=10, pady=8)

        tk.Label(fenster, text="ISBN:").grid(
            row=3, column=0, padx=10, pady=8, sticky="e"
        )
        eingabefeld3 = tk.Entry(fenster, width=40)
        eingabefeld3.grid(row=3, column=1, padx=10, pady=8)

        tk.Label(fenster, text="Regal:").grid(
            row=4, column=0, padx=10, pady=8, sticky="e"
        )
        eingabefeld4 = tk.Entry(fenster, width=40)
        eingabefeld4.grid(row=4, column=1, padx=10, pady=8)

        tk.Label(fenster, text="Hintergrundfarbe:").grid(
            row=5, column=0, padx=10, pady=8, sticky="e"
        )

        farbauswahl = tk.OptionMenu(
            fenster,
            qr_hintergrund_var,
            *QR_HINTERGRUENDE.keys(),
        )
        farbauswahl.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        tk.Button(
            fenster, text="QR-Code erstellen", command=generieren_aktion
        ).grid(row=6, column=1, padx=10, pady=8, sticky="w")

        qr_vorschau = tk.Label(fenster)
        qr_vorschau.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

    elif anwendung == "QR-Code-auslesen":
        global scanner_result_label, scan_aktionsrahmen

        tk.Label(
            fenster,
            text="QR-Code scannen",
            font=("Arial", 16, "bold"),
        ).pack(padx=10, pady=(10, 5))
        scanner_result_label = tk.Label(
            fenster,
            text=(
                f"Gespeicherte Information: {letzter_scan}"
                if letzter_scan
                else "Noch kein QR-Code erkannt."
            ),
            wraplength=760,
            justify="left",
            font=("Arial", 12),
        )
        scanner_result_label.pack(fill="x", padx=20, pady=12)
        scan_aktionsrahmen = tk.Frame(fenster)
        scan_aktionsrahmen.pack(fill="x", padx=20, pady=8)
        if letzter_scan:
            zeige_scan_ergebnis(letzter_scan)

        starte_scanner()


def starte_scanner():
    global scanner_cap, scanner_detector

    scanner_cap = cv2.VideoCapture(0)
    if not scanner_cap.isOpened():
        scanner_cap.release()
        scanner_cap = None
        messagebox.showerror(
            "Kamerafehler",
            "Die Kamera konnte nicht geöffnet werden.",
        )
        return

    scanner_detector = cv2.QRCodeDetector()
    aktualisiere_scannerbild()


def aktualisiere_scannerbild():
    global scanner_after_id, letzter_scan

    scanner_after_id = None
    if scanner_cap is None:
        return

    ret, frame = scanner_cap.read()
    if not ret:
        stoppe_scanner()
        messagebox.showerror(
            "Kamerafehler",
            "Es konnten keine Bilddaten von der Kamera gelesen werden.",
        )
        return

    daten, punkte, _ = scanner_detector.detectAndDecode(frame)
    if daten:
        if daten != letzter_scan:
            letzter_scan = daten
            datenbank.qr_scan_speichern(letzter_scan)
            if qr_scan_fenster is not None and qr_scan_fenster.winfo_exists():
                lade_qr_scan_uebersicht()
            zeige_scan_ergebnis(letzter_scan)
        stoppe_scanner()
        return

    if punkte is not None:
        punkte = punkte.astype(int)
        cv2.polylines(frame, [punkte], isClosed=True, color=(0, 255, 0), thickness=2)

    cv2.imshow("Kamera - QR-Code Scanner", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        stoppe_scanner()
        return

    scanner_after_id = fenster.after(15, aktualisiere_scannerbild)


def stoppe_scanner():
    global scanner_cap, scanner_after_id

    if scanner_after_id is not None:
        fenster.after_cancel(scanner_after_id)
        scanner_after_id = None
    if scanner_cap is not None:
        scanner_cap.release()
        scanner_cap = None
        cv2.destroyAllWindows()


def zeige_scan_ergebnis(qr_inhalt):
    for widget in scan_aktionsrahmen.winfo_children():
        widget.destroy()

    if not qr_inhalt.isdigit():
        infos = datenbank.buch_suchen(qr_inhalt)
        scanner_result_label.configure(text=f"Gespeicherte Information: {infos}")
        return

    try:
        buch = datenbank.buch_nach_id_laden(int(qr_inhalt))
    except sqlite3.Error as fehler:
        messagebox.showerror(
            "Datenbankfehler",
            f"Die Buchdaten konnten nicht geladen werden:\n{fehler}",
        )
        return

    if buch is None:
        scanner_result_label.configure(
            text=f"Kein Buch mit der Exemplar-ID {qr_inhalt} gefunden."
        )
        return

    buch_id, isbn, titel, ausgeliehen, regal, ausleiher, rueckgabedatum = buch
    status = "Ausgeliehen" if ausgeliehen else "Vorhanden"
    details = (
        f"Exemplar-ID: {buch_id}\n"
        f"Titel: {titel}\n"
        f"ISBN: {isbn}\n"
        f"Regal: {regal or '-'}\n"
        f"Status: {status}"
    )
    if ausgeliehen:
        try:
            rueckgabedatum_anzeige = datetime.strptime(
                rueckgabedatum, "%Y-%m-%d"
            ).strftime("%d.%m.%Y")
        except (TypeError, ValueError):
            rueckgabedatum_anzeige = rueckgabedatum or "-"
        details += (
            f"\nAusleiher: {ausleiher or '-'}"
            f"\nRückgabedatum: {rueckgabedatum_anzeige}"
        )
    scanner_result_label.configure(text=details)

    if ausgeliehen:
        tk.Button(
            scan_aktionsrahmen,
            text="Zurückgeben",
            command=lambda: buch_zurueckgeben_aktion(buch_id),
        ).pack()
        return

    tk.Label(scan_aktionsrahmen, text="Ausleiher:").grid(
        row=0, column=0, padx=5, pady=5, sticky="e"
    )
    ausleiher_eingabe = tk.Entry(scan_aktionsrahmen, width=35)
    ausleiher_eingabe.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    tk.Label(scan_aktionsrahmen, text="Rückgabedatum (TT.MM.JJJJ):").grid(
        row=1, column=0, padx=5, pady=5, sticky="e"
    )
    rueckgabedatum_eingabe = tk.Entry(scan_aktionsrahmen, width=35)
    rueckgabedatum_eingabe.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    tk.Button(
        scan_aktionsrahmen,
        text="Ausleihen",
        command=lambda: buch_ausleihen_aktion(
            buch_id, ausleiher_eingabe, rueckgabedatum_eingabe
        ),
    ).grid(row=2, column=1, padx=5, pady=8, sticky="w")


def buch_ausleihen_aktion(buch_id, ausleiher_eingabe, rueckgabedatum_eingabe):
    ausleiher = ausleiher_eingabe.get().strip()
    rueckgabedatum_text = rueckgabedatum_eingabe.get().strip()
    if not ausleiher:
        messagebox.showwarning(
            "Angabe fehlt",
            "Bitte den Namen des Ausleihers eintragen.",
        )
        return

    try:
        rueckgabedatum = datetime.strptime(
            rueckgabedatum_text, "%d.%m.%Y"
        ).date().isoformat()
    except ValueError:
        messagebox.showwarning(
            "Ungültiges Datum",
            "Bitte das Rückgabedatum im Format TT.MM.JJJJ eintragen.",
        )
        return

    try:
        erfolgreich = datenbank.buch_ausleihen_mit_details(
            buch_id, ausleiher, rueckgabedatum
        )
    except sqlite3.Error as fehler:
        messagebox.showerror(
            "Datenbankfehler",
            f"Der Ausleihstatus konnte nicht gespeichert werden:\n{fehler}",
        )
        return

    if not erfolgreich:
        messagebox.showwarning(
            "Ausleihe nicht möglich",
            "Das Buch ist nicht mehr als vorhanden eingetragen.",
        )
        return

    zeige_scan_ergebnis(str(buch_id))
    if depot_fenster is not None and depot_fenster.winfo_exists():
        lade_bibliotheksdepot()


def buch_zurueckgeben_aktion(buch_id):
    try:
        erfolgreich = datenbank.buch_zurueckgeben_mit_id(buch_id)
    except sqlite3.Error as fehler:
        messagebox.showerror(
            "Datenbankfehler",
            f"Die Rückgabe konnte nicht gespeichert werden:\n{fehler}",
        )
        return

    if not erfolgreich:
        messagebox.showwarning(
            "Rückgabe nicht möglich",
            "Das Buch ist nicht mehr als ausgeliehen eingetragen.",
        )
        return

    zeige_scan_ergebnis(str(buch_id))
    if depot_fenster is not None and depot_fenster.winfo_exists():
        lade_bibliotheksdepot()


def naechster_dateiname(name):
    basis = Path(name).name
    if basis.lower().endswith(".png"):
        basis = basis[:-4]
    basis = basis.strip()
    if not basis:
        basis = "qr_code"

    ziel = QR_CODE_ORDNER / f"{basis}.png"
    nummer = 1
    while ziel.exists():
        ziel = QR_CODE_ORDNER / f"{basis}_{nummer}.png"
        nummer += 1
    return ziel


def zeige_qr_code(dateipfad, ziel):
    bild = tk.PhotoImage(file=str(dateipfad))
    ziel.configure(image=bild, text="")
    ziel.image = bild


def qr_eingabe_gueltig(text):
    return len(text) <= 200


def generieren_aktion():
    global letzter_qr_pfad
    titel = eingabefeld2.get().strip()
    isbn = eingabefeld3.get().strip()
    regal = eingabefeld4.get().strip()
    menge = 1

    daten = str(datenbank.buch_hinzufuegen(isbn, titel, regal, menge))

    try:
        QR_CODE_ORDNER.mkdir(parents=True, exist_ok=True)
        dateipfad = naechster_dateiname(titel)
        segno.make_qr(daten).save(
            str(dateipfad),
            scale=10,
            light=QR_HINTERGRUENDE[qr_hintergrund_var.get()],
            dark="black",
        )
        dateipfad.with_suffix(".txt").write_text(daten, encoding="utf-32")



    except (OSError, ValueError) as fehler:
        messagebox.showerror(
            "QR-Code konnte nicht erstellt werden",
            f"Der QR-Code konnte nicht gespeichert werden:\n{fehler}",
        )
        return

    letzter_qr_pfad = dateipfad
    if galerie_fenster is not None and galerie_fenster.winfo_exists():
        lade_qr_codes()
    if depot_fenster is not None and depot_fenster.winfo_exists():
        lade_bibliotheksdepot()
    try:
        zeige_qr_code(dateipfad, qr_vorschau)
    except tk.TclError as fehler:
        messagebox.showerror(
            "Anzeige fehlgeschlagen",
            f"Der QR-Code wurde gespeichert, konnte aber nicht angezeigt werden:\n{fehler}",
        )


def oeffne_bibliotheksdepot():
    global depot_fenster, depot_inhalt, depot_canvas

    if depot_fenster is not None and depot_fenster.winfo_exists():
        depot_fenster.lift()
        lade_bibliotheksdepot()
        return

    depot_fenster = tk.Toplevel(fenster)
    depot_fenster.title("Bibliotheksinternes Depot")
    depot_fenster.geometry("800x700")

    rahmen = tk.Frame(depot_fenster)
    rahmen.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(rahmen)
    scrollbar.pack(side="right", fill="y")

    depot_canvas = tk.Canvas(rahmen, yscrollcommand=scrollbar.set)
    depot_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=depot_canvas.yview)

    depot_inhalt = tk.Frame(depot_canvas)
    depot_canvas.create_window((0, 0), window=depot_inhalt, anchor="nw")
    depot_inhalt.bind(
        "<Configure>",
        lambda _event: depot_canvas.configure(
            scrollregion=depot_canvas.bbox("all")
        ),
    )

    depot_fenster.protocol("WM_DELETE_WINDOW", schliesse_bibliotheksdepot)
    lade_bibliotheksdepot()


def lade_bibliotheksdepot():
    for widget in depot_inhalt.winfo_children():
        widget.destroy()

    try:
        buecher = datenbank.alle_buecher_laden()
    except sqlite3.Error as fehler:
        messagebox.showerror(
            "Datenbankfehler",
            f"Der Bibliotheksbestand konnte nicht geladen werden:\n{fehler}",
            parent=depot_fenster,
        )
        return

    if not buecher:
        tk.Label(
            depot_inhalt,
            text="Im Depot sind noch keine Bücher vorhanden.",
            padx=20,
            pady=20,
        ).pack()
        return

    for buch_id, isbn, titel, ausgeliehen, regal, ausleiher, rueckgabedatum in buecher:
        kachel = tk.LabelFrame(
            depot_inhalt,
            text=f"{titel} (Exemplar-ID: {buch_id})",
            padx=10,
            pady=10,
        )
        kachel.pack(fill="x", padx=10, pady=8)

        try:
            qr_bild = io.BytesIO()
            segno.make_qr(str(buch_id)).save(qr_bild, kind="png", scale=7)
            qr_daten = base64.b64encode(qr_bild.getvalue())
            bild = tk.PhotoImage(data=qr_daten.decode("ascii"))
            bild_label = tk.Label(kachel, image=bild)
            bild_label.image = bild
            bild_label.pack(side="left", padx=(0, 12))
        except (tk.TclError, ValueError, OSError) as fehler:
            tk.Label(
                kachel,
                text=f"QR-Code konnte nicht angezeigt werden: {fehler}",
            ).pack(side="left", padx=(0, 12))

        status = "Ausgeliehen" if ausgeliehen else "Vorhanden"
        details = (
            f"ISBN: {isbn}\n"
            f"Regal: {regal or '-'}\n"
            f"Ausleihstatus: {status}"
        )
        if ausgeliehen:
            try:
                rueckgabedatum_anzeige = datetime.strptime(
                    rueckgabedatum, "%Y-%m-%d"
                ).strftime("%d.%m.%Y")
            except (TypeError, ValueError):
                rueckgabedatum_anzeige = rueckgabedatum or "-"
            details += (
                f"\nAusleiher: {ausleiher or '-'}"
                f"\nRückgabedatum: {rueckgabedatum_anzeige}"
            )
        tk.Label(
            kachel,
            text=details,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)


def schliesse_bibliotheksdepot():
    global depot_fenster, depot_inhalt, depot_canvas
    if depot_fenster is not None:
        depot_fenster.destroy()
    depot_fenster = None
    depot_inhalt = None
    depot_canvas = None


def oeffne_qr_code_galerie():
    global galerie_fenster, galerie_inhalt, galerie_canvas

    if galerie_fenster is not None and galerie_fenster.winfo_exists():
        galerie_fenster.lift()
        lade_qr_codes()
        return

    galerie_fenster = tk.Toplevel(fenster)
    galerie_fenster.title("Erstellte QR-Codes")
    galerie_fenster.geometry("600x700")

    rahmen = tk.Frame(galerie_fenster)
    rahmen.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(rahmen)
    scrollbar.pack(side="right", fill="y")

    galerie_canvas = tk.Canvas(rahmen, yscrollcommand=scrollbar.set)
    galerie_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=galerie_canvas.yview)

    galerie_inhalt = tk.Frame(galerie_canvas)
    galerie_canvas.create_window((0, 0), window=galerie_inhalt, anchor="nw")
    galerie_inhalt.bind(
        "<Configure>",
        lambda _event: galerie_canvas.configure(
            scrollregion=galerie_canvas.bbox("all")
        ),
    )

    galerie_fenster.protocol("WM_DELETE_WINDOW", schliesse_qr_code_galerie)
    lade_qr_codes()


def oeffne_qr_scan_uebersicht():
    global qr_scan_fenster, qr_scan_text

    if qr_scan_fenster is not None and qr_scan_fenster.winfo_exists():
        qr_scan_fenster.lift()
        lade_qr_scan_uebersicht()
        return

    qr_scan_fenster = tk.Toplevel(fenster)
    qr_scan_fenster.title("Gespeicherte QR-Scans")
    qr_scan_fenster.geometry("700x600")

    rahmen = tk.Frame(qr_scan_fenster)
    rahmen.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar = tk.Scrollbar(rahmen)
    scrollbar.pack(side="right", fill="y")

    qr_scan_text = tk.Text(
        rahmen,
        yscrollcommand=scrollbar.set,
        wrap="word",
        state="disabled",
        font=("Arial", 10),
    )
    qr_scan_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=qr_scan_text.yview)

    lade_qr_scan_uebersicht()


def lade_qr_scan_uebersicht():
    if qr_scan_text is None:
        return

    qr_scan_text.config(state="normal")
    qr_scan_text.delete("1.0", tk.END)

    scans = datenbank.qr_scans_anzeigen()
    if not scans:
        qr_scan_text.insert(tk.END, "Noch keine QR-Scans gespeichert.")
    else:
        for scan_id, qr_inhalt, isbn, titel, regalstandort, erfasst_am in scans:
            qr_scan_text.insert(
                tk.END,
                (
                    f"Scan-ID: {scan_id}\n"
                    f"QR-Inhalt: {qr_inhalt}\n"
                    f"ISBN: {isbn or '-'}\n"
                    f"Titel: {titel or '-'}\n"
                    f"Regal: {regalstandort or '-'}\n"
                    f"Erfasst: {erfasst_am}\n\n"
                ),
            )

    qr_scan_text.config(state="disabled")


def schliesse_qr_code_galerie():
    global galerie_fenster
    if galerie_fenster is not None:
        galerie_fenster.destroy()
    galerie_fenster = None


def schliesse_hauptfenster():
    stoppe_scanner()
    fenster.destroy()


def lade_qr_codes():
    for widget in galerie_inhalt.winfo_children():
        widget.destroy()

    dateien = sorted(
        QR_CODE_ORDNER.glob("*.png"),
        key=lambda datei: datei.stat().st_mtime,
        reverse=True,
    ) if QR_CODE_ORDNER.exists() else []

    if not dateien:
        tk.Label(
            galerie_inhalt,
            text="Noch keine QR-Codes erstellt.",
            padx=20,
            pady=20,
        ).pack()
        return

    for dateipfad in dateien:
        kachel = tk.LabelFrame(
            galerie_inhalt,
            text=dateipfad.stem,
            padx=10,
            pady=10,
        )
        kachel.pack(fill="x", padx=10, pady=8)
        kachel.bind(
            "<Button-3>",
            lambda ereignis, pfad=dateipfad: zeige_qr_kontextmenue(
                ereignis, pfad
            ),
        )
        try:
            bild = tk.PhotoImage(file=str(dateipfad))
            groesse = max(bild.width(), bild.height())
            faktor = max(1, (groesse + 179) // 180)
            if faktor > 1:
                bild = bild.subsample(faktor, faktor)
            bild_label = tk.Label(kachel, image=bild)
            bild_label.image = bild
            bild_label.pack()
            name_label = tk.Label(kachel, text=f"Name: {dateipfad.stem}")
            name_label.pack()
            info_label = tk.Label(
                kachel,
                text=f"Gespeicherte Information: {lese_qr_information(dateipfad)}",
                wraplength=520,
                justify="left",
            )
            info_label.pack()
            for widget in (bild_label, name_label, info_label):
                widget.bind(
                    "<Button-3>",
                    lambda ereignis, pfad=dateipfad: zeige_qr_kontextmenue(
                        ereignis, pfad
                    ),
                )
        except tk.TclError as fehler:
            tk.Label(
                kachel,
                text=f"Bild konnte nicht geladen werden: {fehler}",
            ).pack()


def lese_qr_information(dateipfad):
    infodatei = dateipfad.with_suffix(".txt")
    if infodatei.exists():
        try:
            return infodatei.read_text(encoding="utf-32")
        except OSError as fehler:
            return f"Information konnte nicht gelesen werden: {fehler}"

    bild = cv2.imread(str(dateipfad))
    if bild is not None:
        information, _, _ = cv2.QRCodeDetector().detectAndDecode(bild)
        if information:
            return information
    return "Information nicht verfügbar"


def zeige_qr_kontextmenue(ereignis, dateipfad):
    kontextmenue = tk.Menu(fenster, tearoff=0)
    kontextmenue.add_command(
        label="Löschen",
        command=lambda: loesche_qr_code(dateipfad),
    )
    try:
        kontextmenue.tk_popup(ereignis.x_root, ereignis.y_root)
    finally:
        kontextmenue.grab_release()


def loesche_qr_code(dateipfad):
    global letzter_qr_pfad
    try:
        dateipfad.unlink()
        dateipfad.with_suffix(".txt").unlink(missing_ok=True)
    except OSError as fehler:
        messagebox.showerror(
            "Löschen fehlgeschlagen",
            f"Der QR-Code konnte nicht gelöscht werden:\n{fehler}",
        )
        return

    if letzter_qr_pfad == dateipfad:
        letzter_qr_pfad = None
        if qr_vorschau is not None and qr_vorschau.winfo_exists():
            qr_vorschau.configure(image="", text="")
            qr_vorschau.image = None

    if galerie_fenster is not None and galerie_fenster.winfo_exists():
        lade_qr_codes()


fenster = tk.Tk()
fenster.title("QR-Code erstellen")
fenster.geometry("800x700")
anwendung = "QR-Code-erstellen"

eingabefeld1 = None
eingabefeld2 = None
qr_vorschau = None
qr_hintergrund_var = tk.StringVar(fenster, value="Weiß")
farbauswahl = None
galerie_fenster = None
galerie_inhalt = None
galerie_canvas = None
depot_fenster = None
depot_inhalt = None
depot_canvas = None
letzter_qr_pfad = None
letzter_scan = ""
scanner_cap = None
scanner_detector = None
scanner_after_id = None
scanner_result_label = None
scan_aktionsrahmen = None
qr_scan_fenster = None
qr_scan_text = None

menuleiste = tk.Menu(fenster)
menuleiste.add_command(
    label="QR-Code erstellen",
    command=lambda: menuleiste_pushdown("QR-Code-erstellen"),
)
menuleiste.add_command(
    label="QR-Code auslesen",
    command=lambda: menuleiste_pushdown("QR-Code-auslesen"),
)
menuleiste.add_command(
    label="Erstellte QR-Codes",
    command=oeffne_qr_code_galerie,
)
menuleiste.add_command(
    label="Gespeicherte QR-Scans",
    command=oeffne_qr_scan_uebersicht,
)
menuleiste.add_command(
    label="Bibliotheksinternes Depot",
    command=oeffne_bibliotheksdepot,
)
fenster.config(menu=menuleiste)
fenster.protocol("WM_DELETE_WINDOW", schliesse_hauptfenster)

aktualisiere_inhalt()
fenster.mainloop()
