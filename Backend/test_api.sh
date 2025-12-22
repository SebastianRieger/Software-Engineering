#!/bin/bash
# Quick curl test for video processing endpoint

echo "=== Gesture Recognition Video Processing API Test ==="
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "❌ Backend not running. Start it first:"
    echo "   cd Backend/src && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi

echo "✓ Backend is running"
echo ""

# Test 1: Process video by path
echo "[TEST 1] Process video by local path"
echo "Usage: curl -X POST \"http://localhost:8000/api/v1/gestures/process-video?video_path=/path/to/video.mkv\""
echo ""

# Example with the demo video (if it exists)
if [ -f "/tmp/demo_circle.mp4" ]; then
    echo "Testing with demo video..."
    curl -X POST "http://localhost:8000/api/v1/gestures/process-video?video_path=/tmp/demo_circle.mp4" 2>/dev/null | python3 -m json.tool
    echo ""
else
    echo "⚠️  No demo video found at /tmp/demo_circle.mp4"
fi

echo ""
echo "[TEST 2] Upload video file"
echo "Usage: curl -X POST -F \"file=@/path/to/video.mkv\" http://localhost:8000/api/v1/gestures/process-video"
echo ""
echo "Example:"
echo "  curl -X POST -F \"file=@circle.mkv\" http://localhost:8000/api/v1/gestures/process-video"
echo ""

echo "=== Expected Response Format ==="
cat << 'EOF'
{
  "gestures": ["circle"],
  "frames_processed": 150,
  "trajectory_points": 145
}
EOF
