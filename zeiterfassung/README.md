# Zeitkonto — persönliche Zeiterfassung

Eigenständiges Django-Projekt für Stefan Zeiler. Deutsche, responsive Oberfläche mit Monatskalender, Tagesformular, Jahresübersicht und persönlichem Benutzerkonto.

## Enthalten

- Vier Stempelzeiten: Beginn, Mittagspause von/bis, Feierabend; Berechnung minutengenau ohne Rundung der Stempelzeiten.
- Standard Donnerstag/Freitag mit je **8:40 Stunden (520 Minuten)**. Das entspricht **17:20 Stunden pro Woche / 40 % einer 5-Tage-Woche**.
- Arbeitstage einzeln verschieben; dabei wandert das Soll mit. Alternativ Tagessoll im Tagesformular überschreiben (0 = frei).
- Historisierte Arbeitspläne mit Gültigkeitsdatum. Neue Pläne verändern frühere Zeiträume nicht; bewusstes Ersetzen eines Plans mit gleichem Datum berechnet den Zeitraum neu.
- Tages-, Wochen-, Monats-, Jahres- und Gesamtsaldo inklusive konfigurierbarem Anfangssaldo.
- Ferienanspruch pro Jahr, manueller Vorjahresübertrag, bezogene/geplante/restliche Tage, halbe Tage und Ferienzeiträume.
- Krankheit, Feiertage, Überstundenabbau und unbezahlte Abwesenheit.
- Offene/unvollständige Tage sichtbar, Notizen, monatlicher CSV-Export, persönliche JSON-Sicherung und Wiederherstellung.
- Login und benutzergetrennte Daten, CSRF-Schutz, automatische Tests und GitHub Actions.

## Schnellstart unter Windows (PowerShell)

Python 3.11 oder neuer installieren. ZIP entpacken, Terminal im Ordner mit `manage.py` öffnen:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Falls Python in einer anderen Version installiert ist, `py -3.11` durch `py` ersetzen. Benutzername und Passwort beim Anlegen selbst wählen. Es gibt kein fest eingebautes Passwort.

Dann **http://127.0.0.1:8000** öffnen und anmelden. Später genügt ein Doppelklick auf **start.bat**. Zum Beenden im Serverfenster Strg+C drücken. Der Server muss laufen, solange du die Anwendung nutzt.

## Erster Start

1. Unter **Einstellungen** Erfassungsbeginn und vorhandenen Anfangssaldo in Minuten setzen (z. B. 150 = +2:30 h).
2. Arbeitsplan prüfen: Donnerstag und Freitag, 520 Minuten. Ein neuer Plan gilt ab dem gewählten Datum. Für ein einzelnes Tauschen die Funktion **Arbeitstag verschieben** nutzen.
3. Ferienanspruch für das Jahr in **deinen tatsächlichen Arbeitstagen** eintragen. Beispiel: fünf Ferienwochen × zwei Arbeitstage = zehn Tage. Nicht nochmals mit 40 % multiplizieren. Der Anspruch ist bewusst nicht vorbelegt.
4. Kalender öffnen, Tag auswählen und Stempelzeiten eintragen.

## Berechnungsregeln

`Arbeitszeit = (Pause beginnt − Arbeitsbeginn) + (Feierabend − Pause endet)`

`Tagesbilanz = Arbeitszeit + Abwesenheitsgutschrift − Tagessoll`

Beispiel: 07:00–12:00 und 13:00–16:50 ergeben 8:50 h, bei 8:40 h Soll also +0:10 h.

- Vier vollständige Stempelzeiten schliessen den Tag automatisch ab. Ein einzelnes vollständiges Zeitpaar kann über **Tag abschliessen** abgeschlossen werden.
- Ein nicht erfasster oder unvollständiger Tag ist **offen** und geht noch nicht in den Saldo ein. Die Zahl offener Tage wird angezeigt; der Saldo ist bis zur Vervollständigung vorläufig. Ein bewusst abgeschlossener Arbeitstag ohne Zeiten erzeugt das volle Minus.
- Zukünftige Tage sind Planung und erzeugen weder Plus noch Minus. Zukünftige Ferien reservieren aber bereits Ferientage.
- Wochen gehen von Montag bis Sonntag. Eine Woche an der Monatsgrenze enthält auch die Tage des angrenzenden Monats; die Monatsbilanz enthält nur den gewählten Monat.
- Verschiebungen über eine Wochen-/Monatsgrenze verschieben auch das Soll zwischen diesen Perioden.
- Ferien, Krankheit und Feiertage schreiben das geplante Tagessoll anteilig gut. Ferien verbrauchen nur an geplanten Arbeitstagen Urlaub. Bei ½ Ferien wird ½ Tag abgezogen, der Rest des Tages kann mit Zeiten erfasst werden.
- Überstundenabbau schreibt keine Zeit gut: ein voller Tag verbraucht das Tagessoll. Unbezahlte Abwesenheit reduziert das Soll anteilig. Diese Regeln sind Anwendungseinstellungen im Code, keine Prüfung eines Arbeitsvertrags.
- Restferien = Jahresanspruch + manueller Übertrag − bezogene − geplante Ferien. Ein negatives Ferienkonto bleibt sichtbar; Eingaben werden nicht versteckt oder still angepasst.
- Feiertage werden manuell erfasst, da der Arbeitsort/Feiertagskalender nicht festgelegt ist. Ein vorhandener Ferieneintrag kann am Feiertag auf „Feiertag“ geändert werden.
- Datum und Uhrzeit werden lokal für Europe/Zurich betrachtet. Nur Schichten innerhalb eines Kalendertags sind vorgesehen; Nachtschichten auf zwei Tage aufteilen.
- Tagessoll in ganzen Minuten. Bei halben Abwesenheiten und ungeradem Minutensoll wird die Gutschrift auf eine Minute gerundet (Python-Rundung); der Standard 520 Minuten ist exakt halbierbar.

## Auf GitHub hochladen

Dieses Paket ist vollständig vorbereitet, aber noch keinem GitHub-Repository zugeordnet. Auf https://github.com/new ein **privates** Repository `zeiterfassung` erstellen, ohne README, Lizenz oder .gitignore. Dann im Projektordner:

```powershell
git init -b main
git add .
git commit -m "Initiale Version der Zeiterfassung"
git remote add origin https://github.com/SZeiler2002/zeiterfassung.git
git push -u origin main
```

Wenn ein anderer Repository-Name gewählt wurde, die Remote-URL entsprechend anpassen. GitHub-Anmeldung erfolgt über deine normale Git-Einrichtung, keine Zugangsdaten in Dateien eintragen.

**GitHub speichert den Code, nicht deine Stunden.** GitHub Pages kann diese Django-Anwendung nicht ausführen. Zum Zugriff von mehreren Geräten einen gemeinsamen Django-Server mit gemeinsamer Datenbank betreiben. Zwei lokale Installationen haben getrennte Datenbestände; `git pull` synchronisiert keine Arbeitszeiten.

## Speicherung und Sicherung

Der einfache Start verwendet SQLite (`db.sqlite3`) im Projektordner. Die Datei, die lokale geheime Schlüsseldatei und virtuelle Umgebung sind in `.gitignore` ausgeschlossen.

- Persönliche Sicherung: **Einstellungen → Persönliche Sicherung herunterladen**. Enthält alle eigenen Einträge, Arbeitspläne und Ansprüche, aber keine Passwörter.
- Vollständige lokale Sicherung: Server stoppen und `db.sqlite3` an einen sicheren Ort kopieren; zum Zurückspielen ebenfalls Server stoppen.
- Persönliche JSON-Sicherung wiederherstellen (Benutzer muss existieren):

```powershell
.\.venv\Scripts\python.exe manage.py restore_timebackup C:\Pfad\zeiterfassung-backup.json --username stefan
```

Falls der Benutzer bereits Zeiterfassungsdaten hat, verweigert der Befehl das Überschreiben. Nach aktueller Sicherung kann `--replace` bewusst ergänzt werden. Die Wiederherstellung ersetzt nur die Zeiterfassungsdaten dieses Benutzers und ist transaktional: ungültige Eingaben werden vollständig zurückgerollt.

## Optional PostgreSQL

```powershell
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]"
$env:POSTGRES_DB="zeiterfassung"
$env:POSTGRES_USER="zeiterfassung"
$env:POSTGRES_PASSWORD="DEIN_PASSWORT"
$env:POSTGRES_HOST="localhost"
.\.venv\Scripts\python.exe manage.py migrate
```

Die Datenbank und der Datenbankbenutzer müssen vorher angelegt werden. Der Datenbankwechsel kopiert keine bestehenden SQLite-Daten. Persönliche Daten bei Bedarf über JSON sichern und wiederherstellen.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Die Tests prüfen unter anderem Pausenberechnung, Salden, offene Tage, halbe Ferien, Planwechsel, Verschiebungen, Monats-/Jahresgrenzen, Fremdzugriff, CSRF, CSV und Sicherungswiederherstellung. GitHub Actions führt sie bei Push und Pull Request aus.

## Betrieb auf einem Server

Die Standardeinstellungen und `runserver` sind für den lokalen Start. Für Hosting: WSGI-Server verwenden, HTTPS und statische Dateien bereitstellen (`collectstatic`), `DJANGO_DEBUG=0`, einen eigenen `DJANGO_SECRET_KEY` und `DJANGO_ALLOWED_HOSTS` setzen. Bei TLS-Terminierung am Reverse-Proxy dessen sichere Weiterleitung passend konfigurieren. Keine lokale Entwicklungsinstanz ungeschützt ins Internet freigeben. Das Repository enthält keine fertige Hosting-Konfiguration.

Django 5.2 wird als Abhängigkeit innerhalb seiner Wartungsreihe verwendet; Quelle: https://docs.djangoproject.com/en/5.2/releases/5.2/ . Regelmässig mit `pip install --upgrade -r requirements.txt` aktualisieren und Tests ausführen.
