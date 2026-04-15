---
title: Integration Audio-Streaming (WebRTC-Variante 2) — Analyse
date: 2025-12-02
---

# Integration von Audiostreaming in die bestehende Architektur

Kurzfassung
- Empfohlen: dieselbe Architektur wie in "WebRTC Variante 2" für Video verwenden — also WebRTC für Media-Transport und WebSocket (bestehender Event-Bus) für Signalisierung und Events.
- Audio lässt sich größtenteils über die gleiche Pipeline abwickeln: Signalisierung über WebSocket, Media-Transport über WebRTC (Opus), serverseitige Entgegennahme mit `aiortc` oder Weiterleitung an ein SFU.

Kontext und Motivation
- Ihr habt bereits eine Event-/WebSocket-Infrastruktur im Backend (`/ws`), FastAPI für HTTP/Signaling ist vorhanden bzw. kann leicht ergänzt werden.
- Ziel: Mikrofon-Audio in Echtzeit übertragen, ggf. auf Server transkribieren (Speech-to-Text), Voice-Events (Wakeword, VAD) erzeugen oder einfache Audioanalyse durchführen.

Kann die Video-Architektur (WebRTC + FastAPI + aiortc / SFU) wiederverwendet werden?
- Ja. Wesentliche Gründe:
  - WebRTC transportiert sowohl Audio- als auch Videostreams über RTP/DTLS/SRTP. Die PeerConnection abstrahiert Tracks (Video/Audio) gleichermaßen.
  - Das Signaling bleibt identisch: SDP-Offer/Answer + ICE-Candidates über WebSocket.
  - Auf Server-Seite kann `aiortc` sowohl MediaStreamTrack für Video als auch für Audio liefern. Die Verarbeitungspipeline kann also dieselben Hooks/Handler wiederverwenden.

Unterschiede / Audio-spezifische Anforderungen
- Codec: Verwende `Opus` (standard, low-latency, breit unterstützt). Sample-rate üblicherweise 48 kHz intern; ASR-Engines wie Vosk erwarten oft 16 kHz — Resampling nötig.
- Latenz: Für Sprache reicht typ. 100–300 ms; für interaktive Sprachsteuerung so niedrig wie möglich.
- Framegrößen: WebRTC/Opus arbeitet mit kleinen RTP-Paketen (20ms frames üblich). Das beeinflusst buffering und VAD.
- Preprocessing: Noise suppression, AGC (gain control) und VAD sollten idealerweise clientseitig (WebRTC built-in) oder serverseitig via spezialisierte libs erfolgen.

Wie sieht eine wiederverwendbare Pipeline aus?

1) Signaling (WebSocket / FastAPI)
  - Verwende euren bestehenden WebSocket-Endpunkt für Signalisierung: Nachrichtentypen `webrtc-offer`, `webrtc-answer`, `ice-candidate`.
  - Client (Browser) erstellt `RTCPeerConnection`, fügt lokale `MediaStream` (Audio+Video optional) hinzu, erzeugt `offer` und sendet über WebSocket.

2) Media-Transport (WebRTC)
  - Transportiert Audio (Opus) effizient; erlaubt adaptive bitrate und NAT traversal.
  - Auf Server empfangen: `aiortc` (Python) akzeptiert die PeerConnection, bietet `AudioStreamTrack`/`MediaStreamTrack` zur Weiterverarbeitung.

3) Verarbeitungsschicht
  - Option A: Server-seitige Verarbeitung (z. B. ASR, VAD, Feature-Extraction)
    - `aiortc` liefert Audioframes; konvertiere und resample auf Sample-Rate der ASR (z.B. 16 kHz) und leite an Vosk/Whisper/DeepSpeech.
    - Resultate (Transkription, Intents, Wakeword) publizieren als Events über eure WebSocket/EventBus.
  - Option B: Weiterleitung an SFU / Recorder / Analytics-Service
    - Für Skalierung mehrere Clients: SFU (mediasoup / Janus) betreibt RTP-Mixing/Forwarding. Serverseitige worker können als subscribers attachen.

4) Events & Rückkanal
  - Erzeugte Events (Transkript, Aktivitätsstatus) über WebSocket zurück an Clients.
  - Für Steuerbefehle (z. B. „Starte Aufnahme“, „Stopp“) weiter WebSocket verwenden.

Empfohlene Implementierungsdetails (Praktisch)

Backend-Pakete (Python)
- `aiortc` — WebRTC PeerConnection / MediaTrack auf Python-Seite
- `fastapi` — HTTP endpoints / (optional) REST signaling hooks
- `uvicorn` — ASGI server
- `webrtcvad` — Voice Activity Detection (falls gewünscht serverseitig)
- `pydub` / `soundfile` / `numpy` — Resampling und PCM-Konversion
- `vosk` oder `openai-whisper` (lokal) — ASR (je nach Genauigkeit/Performance-Anforderung)

Frontend (Browser)
- WebRTC native API (getUserMedia + RTCPeerConnection)
- Signaling über bestehende WebSocket-Client (wiederverwenden)

Beispiel-Flow (Kurz)
1. Client greift auf Mikrofon zu: `navigator.mediaDevices.getUserMedia({ audio: true })`.
2. `pc.addTrack(stream.getAudioTracks()[0], stream)`.
3. `pc.createOffer()` → `setLocalDescription(offer)` → send via WebSocket `{type:'webrtc-offer', sdp: offer.sdp}`.
4. Server (aiortc) erstellt RTCPeerConnection, `setRemoteDescription(offer)`, `createAnswer()` → send zurück.
5. Nach Verbindungsaufbau erhält serverseitiger Track Audio-Frames.

Codebeispiel — Signaling-Nachrichten (JSON)
```
{ "type": "webrtc-offer", "clientId": "mirror-01", "sdp": "v=0..." }
{ "type": "webrtc-answer", "clientId": "mirror-01", "sdp": "v=0..." }
{ "type": "ice-candidate", "clientId": "mirror-01", "candidate": {...} }
```

Beispiel: Verarbeitung eines `aiortc` AudioTracks
```python
# vereinfachtes Beispiel: empfangen eines AudioTracks mit aiortc und Weitergabe an ASR
from aiortc import RTCPeerConnection, RTCSessionDescription
from vosk import Model, KaldiRecognizer
import asyncio, json

async def handle_offer(sdp_offer):
    pc = RTCPeerConnection()

    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            # track ist ein MediaStreamTrack; aiortc liefert PCM-Frames (bytes)
            asyncio.create_task(process_audio_track(track))

    await pc.setRemoteDescription(RTCSessionDescription(sdp_offer, "offer"))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return pc.localDescription.sdp

async def process_audio_track(track):
    model = Model("/path/to/vosk-model")
    rec = KaldiRecognizer(model, 16000)
    while True:
        frame = await track.recv()
        pcm = frame.to_bytes()  # exemplarisch; evtl. Resampling nötig
        if rec.AcceptWaveform(pcm):
            res = json.loads(rec.Result())
            # publish event via WebSocket: res['text']

```

Wichtige Implementierungs- und Performance-Hinweise
- Resampling: WebRTC/Opus liefert oft 48 kHz; viele ASR-Modelle arbeiten mit 16 kHz. Resample effizient mit `samplerate`/`librosa`/`sox`-Bindings in nativen C libs oder via `ffmpeg`-Pipes.
- CPU auf Raspberry Pi: `aiortc` + ASR kann CPU-intensiv sein. Optionen:
  - Leichte ASR-Modelle (Vosk-small) oder spracherkennungs-API remote verwenden.
  - Edge: Führe VAD / wakeword lokal, schicke nur relevante Clips für Transkription.
  - Offload: Dedizierten worker/instance (mehr CPU/RAM) betreiben.
- Echo Cancellation: Wenn Mirror zugleich Lautsprecher ist und Rückkopplung existiert, AEC/EC muss berücksichtigt werden (WebRTC bietet clientseitig meist AEC/AGC).

Test- und Validierungsstrategie
- POC 1 (lokal, 1 Client): Implementiere WebRTC offer/answer flow mit `aiortc`, empfange Audio, transkribiere lokal (low-end model). Metriken: end-to-end Latenz, CPU, memory.
- POC 2 (Edge/On-device): Wenn Zielgerät Raspberry Pi ist, teste direkt dort. Miss CPU-Last pro Sekunde und Latenz.
- Skalierungstest: Anzahl gleichzeitiger Clients (falls relevant) mit SFU-Setup messen.

Roadmap & Empfehlungen
1. POC WebRTC Audio (3–7 Tage): Implementiere Signaling über existierenden WebSocket und setze `aiortc`-Receiver auf. Test lokal.
2. Optimierung (1–2 Wochen): Resampling/ASR-Integration, VAD, AEC Tests. Falls aiortc zu schwer ist, evaluiere SFU plus separate ASR worker.
3. Produktion: Entscheide zwischen on-device processing (Datenschutz, Offline) vs. Cloud/Remote (bessere ASR, höhere Kosten).

Fazit
- Die WebRTC-Variante 2 (FastAPI Signaling + aiortc/SFU) lässt sich sehr gut wiederverwenden für Audio-Streaming. Die meiste Signalisierungs- und Event-Architektur bleibt gleich, die Unterschiede liegen in Resampling, ASR-Integration und Performance-Tuning auf Zielhardware.

---

Datei erstellt: IntegrationAudioStreaming.md
