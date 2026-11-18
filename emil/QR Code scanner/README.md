# QR-Bibliothek als Website

## Lokal starten

Im Projektordner:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Danach ist die Website unter `http://127.0.0.1:5000` erreichbar. Die App
verwendet standardmäßig `bibliothek_neu.db` und speichert QR-Bilder im Ordner
`erstellte_qr_codes`.

## Auf Render veröffentlichen

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT app:app`

Für dauerhafte Daten auf Render einen Persistent Disk einrichten und als
Umgebungsvariablen setzen:

- `DATABASE_PATH=/var/data/bibliothek_neu.db`
- `QR_CODE_DIR=/var/data/erstellte_qr_codes`
- `SECRET_KEY` auf einen langen, zufälligen Wert setzen

Die App hat absichtlich keinen Passwortschutz. Bei öffentlichem Zugriff können
alle Besucher Bücher, Ausleihen und Ausleihernamen sehen und ändern. Vor dem
Veröffentlichen deshalb keine privaten Bestandsdaten verwenden, wenn das nicht
gewünscht ist.
