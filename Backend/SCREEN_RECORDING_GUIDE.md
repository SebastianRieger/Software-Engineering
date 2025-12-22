# 🎥 Screen Recording für die Präsentation

## Option 1: Automatisches Recording (Empfohlen)

Dieses Script startet automatisch die Screen-Aufnahme, führt die Demo aus, und stoppt die Aufnahme:

```bash
cd Backend
chmod +x RECORD_DEMO.sh
./RECORD_DEMO.sh
```

**Was passiert:**
1. ⏱️ Countdown (5 sec)
2. 🔴 ffmpeg startet Recording
3. 🎬 DEMO.sh läuft automatisch
4. ✅ Recording stoppt automatisch
5. 📹 Video wird gespeichert als `gesture_recognition_demo_YYYYMMDD_HHMMSS.mp4`

---

## Option 2: Manuell mit ffmpeg

Falls du mehr Kontrolle haben möchtest:

### Terminal 1: Backend starten
```bash
cd Backend/src
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Recording starten
```bash
ffmpeg -f x11grab -s 1920x1080 -framerate 30 -i :0.0 \
       -c:v libx264 -crf 23 -preset medium \
       demo_recording.mp4
```

### Terminal 3: Demo ausführen
```bash
cd Backend
bash DEMO.sh
```

### Recording stoppen
In Terminal 2: **Drücke `q`** um Recording zu stoppen

---

## Option 3: Mit OBS (GUI - Kostenlos)

**Installation (falls noch nicht installiert):**
```bash
sudo dnf install obs-studio
```

**Schritte:**
1. OBS öffnen
2. Scene erstellen mit "Display Capture"
3. **Start Recording** klicken
4. Demo laufen lassen
5. **Stop Recording** klicken

---

## Video abspielen

Nach dem Recording:

```bash
# Mit VLC
vlc gesture_recognition_demo_*.mp4

# Mit ffplay
ffplay gesture_recognition_demo_*.mp4

# Mit Firefox (einfach Datei öffnen)
firefox gesture_recognition_demo_*.mp4
```

---

## Tipps für besseres Video

✓ **Fenster-Arrangement vor Recording:**
- Terminal mit Demo deutlich sichtbar
- Backend Output sichtbar lassen (optional)
- Screen so anordnen dass alles lesbar ist (Font-Größe 😉)

✓ **Video-Qualität optimieren:**
- Resolution: 1920x1080 oder 1280x720 (Standard)
- FPS: 30 fps (Standard, gut für Präsentationen)
- Bitrate: Auto mit libx264 preset medium (gute Balance)

✓ **Nach dem Recording:**
- Video anschauen und testen
- Backup machen (USB-Stick)
- PowerPoint: Video einbetten oder externe Link

---

## Troubleshooting

**Problem: "ffmpeg: command not found"**
```bash
sudo dnf install ffmpeg
```

**Problem: Audio fehlt**
```bash
# Audio nicht aufgezeichnet? Kein Problem - für Demo nicht nötig
# Oder mit `-f pulse` für PulseAudio
```

**Problem: Video ist zu groß**
```bash
# Mit höherer Kompression
ffmpeg -f x11grab -s 1920x1080 -framerate 30 -i :0.0 \
       -c:v libx264 -crf 28 -preset slow \
       small_demo.mp4
```

---

## Was morgen passiert

### Vor Präsentation
1. Video-Datei auf USB-Stick oder Cloud
2. Auf Präsentations-Laptop testen (VLC/Browser)
3. Backup-Datei dabei haben

### Während Präsentation
1. Video abspielen (fullscreen empfohlen)
2. Fertig - keine Live-Demo-Probleme! 🎉

---

**Bereit? Los geht's! 🚀**
