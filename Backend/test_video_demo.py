#!/usr/bin/env python3
"""
Quick demo: Create a synthetic circle video and test gesture detection.
"""
import cv2
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.gestures import process_video_file

def create_demo_circle_video(output_path: str, duration_frames: int = 120):
    """
    Create a synthetic video showing body (shoulder/nose) drawing a circle.
    MediaPipe needs visible body landmarks to work.
    
    Args:
        output_path: Output video file path
        duration_frames: Number of frames
    """
    # Video properties
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 30
    frame_size = (640, 480)
    
    out = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
    
    # Generate frames
    for frame_idx in range(duration_frames):
        frame = np.ones((*frame_size[::-1], 3), dtype=np.uint8) * 220  # Light background
        
        # Simulate body (shoulders/torso area) - this helps MediaPipe detect pose
        body_x, body_y = 320, 350
        
        # Draw shoulders (stable reference)
        cv2.circle(frame, (body_x - 30, body_y), 8, (100, 100, 100), -1)  # Left shoulder
        cv2.circle(frame, (body_x + 30, body_y), 8, (100, 100, 100), -1)  # Right shoulder
        
        # Draw body/torso
        cv2.rectangle(frame, (body_x - 40, body_y), (body_x + 40, body_y + 60),
                      (100, 100, 100), 2)
        
        # Draw moving hand/arm making circle
        center_x, center_y = 320, 200
        radius = 60
        angle = (frame_idx / duration_frames) * 2 * np.pi * 1.5  # 1.5 circles
        
        hand_x = int(center_x + radius * np.cos(angle))
        hand_y = int(center_y + radius * np.sin(angle))
        
        # Draw circle path and hand
        cv2.circle(frame, (center_x, center_y), radius, (200, 200, 0), 1)  # Faint path
        cv2.circle(frame, (hand_x, hand_y), 12, (0, 100, 255), -1)  # Hand (orange)
        
        # Draw arm connection
        cv2.line(frame, (body_x, body_y - 20), (hand_x, hand_y), (100, 100, 100), 3)
        
        # Add label
        cv2.putText(frame, f"Circle Motion {frame_idx+1}/{duration_frames}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        out.write(frame)
    
    out.release()
    print(f"✓ Demo video created: {output_path}")

if __name__ == "__main__":
    video_path = "/tmp/demo_circle.mp4"
    
    # Step 1: Create synthetic video
    print("[1] Creating demo circle video...")
    create_demo_circle_video(video_path)
    
    # Step 2: Process with gesture detection
    print(f"\n[2] Processing video with gesture detection...")
    try:
        result = process_video_file(video_path)
        print(f"✓ Result: {result}")
        print(f"  - Gestures detected: {result['gestures']}")
        print(f"  - Frames processed: {result['frames_processed']}")
        print(f"  - Trajectory points: {result['trajectory_points']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
