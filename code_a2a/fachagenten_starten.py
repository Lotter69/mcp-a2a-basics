#!/usr/bin/env python3
"""
Startet alle drei Fachagenten in EINEM Fenster (für Lab 03 und die Laborübungen).

  Lager-Agent        Port 9999   (lager_agent.py)
  Bestell-Agent      Port 9998   (bestell_agent.py)
  Raumbuchungs-Agent Port 9997   (raum_agent.py)

Jede Ausgabezeile bekommt den Namen des Agenten vorangestellt, z. B. [Lager] ...
Beenden mit Strg+C (beendet alle drei).
"""
import os
import subprocess
import sys
import threading
from pathlib import Path

ORDNER = Path(__file__).parent
AGENTEN = [("Lager      ", "lager_agent.py"),
           ("Bestellung ", "bestell_agent.py"),
           ("Raum       ", "raum_agent.py")]


def ausgabe_weiterreichen(name, prozess):
    for zeile in prozess.stdout:
        print(f"[{name}] {zeile}", end="", flush=True)


# Kinder sollen UTF-8 ausgeben (sonst Umlautfehler in der Windows-Konsole)
umgebung = dict(os.environ, PYTHONIOENCODING="utf-8")

prozesse = []
for name, datei in AGENTEN:
    p = subprocess.Popen([sys.executable, "-u", str(ORDNER / datei)], cwd=ORDNER, env=umgebung,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    prozesse.append(p)
    threading.Thread(target=ausgabe_weiterreichen, args=(name.strip(), p), daemon=True).start()

try:
    for p in prozesse:
        p.wait()
except KeyboardInterrupt:
    print("\nBeende alle Fachagenten ...")
    for p in prozesse:
        p.terminate()
