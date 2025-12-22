#!/bin/bash
# Quick presentation demo script for circle gesture recognition

echo "=================================================="
echo "  GESTURE RECOGNITION - CIRCLE DETECTION DEMO"
echo "=================================================="
echo ""

# Check backend
echo "[1] Checking backend..."
if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "    ❌ Backend not running!"
    echo ""
    echo "    Start it with:"
    echo "    cd Backend/src && uvicorn main:app --host 0.0.0.0 --port 8000"
    exit 1
fi
echo "    ✓ Backend running on port 8000"
echo ""

# Paths
VIDEO_PATH="/home/user/Studium/Software Engineering Projekt/repo/Software-Engineering/Backend/video Kreisbewegung.mkv"
API_URL="http://localhost:8000/api/v1/gestures/process-video"

echo "[2] Processing circle video: 'video Kreisbewegung.mkv'"
echo "    Path: $VIDEO_PATH"
echo ""

# URL encode the path for the query parameter
ENCODED_PATH=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$VIDEO_PATH'))")

echo "[3] Sending HTTP POST request..."
echo "    Endpoint: POST /api/v1/gestures/process-video"
echo "    Video: $ENCODED_PATH"
echo ""

# Make request and parse response
RESPONSE=$(curl -s -X POST "$API_URL?video_path=$ENCODED_PATH")
GESTURE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('gestures', [])[0] if data.get('gestures') else 'NONE')")
FRAMES=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('frames_processed', 0))")
POINTS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('trajectory_points', 0))")

echo "=================================================="
echo "  RESULT"
echo "=================================================="
echo "  Gesture Detected:    $GESTURE"
echo "  Frames Processed:    $FRAMES"
echo "  Trajectory Points:   $POINTS"
echo "=================================================="
echo ""

if [ "$GESTURE" = "circle" ]; then
    echo "✓ SUCCESS! Circle gesture correctly detected!"
    exit 0
else
    echo "✗ No circle detected. Response:"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi
