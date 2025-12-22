#!/bin/bash
# Record screen while running the demo

OUTPUT_FILE="gesture_recognition_demo_$(date +%Y%m%d_%H%M%S).mp4"

echo "=================================================="
echo "  RECORDING SETUP"
echo "=================================================="
echo ""
echo "Output file: $OUTPUT_FILE"
echo ""
echo "WICHTIG: Stelle sicher, dass:"
echo "  1. Backend läuft: Backend/src$ uvicorn main:app ..."
echo "  2. Deine Fenster so angeordnet sind, wie du sie zeigen möchtest"
echo "  3. Terminal mit Demo-Script sichtbar ist"
echo ""
echo "Starte Recording in 5 Sekunden..."
echo ""

# Count down
for i in 5 4 3 2 1; do
    echo "  $i..."
    sleep 1
done

echo ""
echo "🔴 RECORDING STARTED"
echo ""

# Get screen resolution
RESOLUTION=$(xrandr | grep " connected primary" | awk '{print $4}' | cut -d'+' -f1)
if [ -z "$RESOLUTION" ]; then
    # Fallback if no primary display
    RESOLUTION="1920x1080"
fi

echo "Screen resolution: $RESOLUTION"
echo ""

# Start recording (will record until Ctrl+C)
# Using x11grab for X11 display, with audio
ffmpeg -f x11grab -s "$RESOLUTION" -framerate 30 -i :0.0 \
       -f pulse -i default \
       -c:v libx264 -crf 23 -preset medium \
       -c:a aac -q:a 9 \
       "$OUTPUT_FILE" &

FFMPEG_PID=$!

# Run demo
echo ""
echo "🎬 Running demo..."
echo ""
sleep 2

# Make sure we're in the right directory
cd "$(dirname "$0")"

cd Backend
./RECORD_DEMO.sh  # Takes ~10 sec total

DEMO_EXIT=$?

echo ""
echo ""
echo "Demo finished. Stopping recording in 3 seconds..."
sleep 3

# Stop ffmpeg
kill $FFMPEG_PID 2>/dev/null
wait $FFMPEG_PID 2>/dev/null

echo ""
echo "=================================================="
echo "  RECORDING COMPLETE"
echo "=================================================="
echo ""
echo "Datei: $OUTPUT_FILE"
echo "Größe: $(ls -lh "$OUTPUT_FILE" | awk '{print $5}')"
echo ""
echo "✓ Video ready for presentation tomorrow!"
echo ""
echo "Du kannst es jetzt abspielen mit:"
echo "  vlc $OUTPUT_FILE"
echo "  oder"
echo "  ffplay $OUTPUT_FILE"
