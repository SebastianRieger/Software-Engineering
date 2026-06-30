#!/usr/bin/env bash
# Downloads the German Vosk speech recognition model to Backend/models/
set -euo pipefail

MODEL_DIR="$(cd "$(dirname "$0")/.." && pwd)/models"
MODEL_NAME="vosk-model-de-0.21"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

# SHA256 of the official vosk-model-de-0.21.zip from alphacephei.com.
# To obtain: curl -L -o /tmp/vosk.zip "${MODEL_URL}" && sha256sum /tmp/vosk.zip
# Leave empty to skip integrity check (not recommended for production environments).
EXPECTED_SHA256=""

if [ -d "${MODEL_DIR}/${MODEL_NAME}" ]; then
    echo "Modell bereits vorhanden: ${MODEL_DIR}/${MODEL_NAME}"
    echo "Um neu zu laden, zuerst loeschen: rm -rf ${MODEL_DIR}/${MODEL_NAME}"
    exit 0
fi

if ! command -v curl &>/dev/null; then
    echo "Fehler: curl ist nicht installiert." >&2
    exit 1
fi

if ! command -v unzip &>/dev/null; then
    echo "Fehler: unzip ist nicht installiert." >&2
    exit 1
fi

mkdir -p "${MODEL_DIR}"
echo "Lade Vosk-Modell herunter: ${MODEL_NAME} (~45 MB) ..."
curl -L --progress-bar -o "${MODEL_DIR}/${MODEL_NAME}.zip" "${MODEL_URL}"

if [ -n "${EXPECTED_SHA256}" ]; then
    echo "Prueffe SHA256 ..."
    ACTUAL_SHA256="$(sha256sum "${MODEL_DIR}/${MODEL_NAME}.zip" | awk '{print $1}')"
    if [ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]; then
        echo "FEHLER: SHA256-Pruefung fehlgeschlagen!" >&2
        echo "  Erwartet: ${EXPECTED_SHA256}" >&2
        echo "  Erhalten: ${ACTUAL_SHA256}" >&2
        rm -f "${MODEL_DIR}/${MODEL_NAME}.zip"
        exit 1
    fi
    echo "SHA256 OK."
else
    echo "Hinweis: SHA256-Pruefung uebersprungen (EXPECTED_SHA256 nicht gesetzt)."
    echo "  Fuer sichere Downloads: Hash ermitteln und in dieses Skript eintragen."
fi

echo "Entpacke ..."
unzip -q "${MODEL_DIR}/${MODEL_NAME}.zip" -d "${MODEL_DIR}"
rm "${MODEL_DIR}/${MODEL_NAME}.zip"

echo ""
echo "Fertig! Setze in Backend/.env:"
echo "  VOICE_MODEL_PATH=./models/${MODEL_NAME}"
