#!/usr/bin/env python3
"""Debug trajectory from real video to understand why circle isn't detected."""
import sys
from pathlib import Path
sys.path.insert(0, 'src')

try:
    import cv2
    import mediapipe as mp
    import numpy as np
except Exception:
    print("Error: mediapipe/opencv not available")
    sys.exit(1)

video_path = 'video Kreisbewegung.mkv'

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(f"Error: Could not open {video_path}")
    sys.exit(1)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

trajectory = []
frame_count = 0
prev_center = None
smoothed_center = None
alpha = 0.6

print("[DEBUG] Analyzing video trajectory...")
print()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    
    center = None
    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        indices = [0, 11, 12]
        points = [lm[i] for i in indices if i < len(lm)]
        xs = [p.x for p in points if p.visibility > 0.2]
        ys = [p.y for p in points if p.visibility > 0.2]
        if xs and ys:
            cx = float(np.mean(xs))
            cy = float(np.mean(ys))
            center = (cx, cy)
    
    if center:
        if smoothed_center is None:
            smoothed_center = center
        else:
            sx = alpha * center[0] + (1 - alpha) * smoothed_center[0]
            sy = alpha * center[1] + (1 - alpha) * smoothed_center[1]
            smoothed_center = (sx, sy)
        trajectory.append(smoothed_center)

pose.close()
cap.release()

print(f"Frames: {frame_count}, Trajectory points: {len(trajectory)}")
print()

if trajectory:
    xs = [p[0] for p in trajectory]
    ys = [p[1] for p in trajectory]
    
    print(f"X range: {min(xs):.3f} to {max(xs):.3f} (span: {max(xs)-min(xs):.3f})")
    print(f"Y range: {min(ys):.3f} to {max(ys):.3f} (span: {max(ys)-min(ys):.3f})")
    print()
    
    # Analyze as circle
    cx = float(np.mean(xs))
    cy = float(np.mean(ys))
    vecs = [(x - cx, y - cy) for x, y in trajectory]
    radii = [np.hypot(v[0], v[1]) for v in vecs]
    
    print(f"Center: ({cx:.3f}, {cy:.3f})")
    print(f"Radii: min={min(radii):.3f}, max={max(radii):.3f}, mean={np.mean(radii):.3f}, std={np.std(radii):.3f}")
    print(f"Radius CV (std/mean): {np.std(radii) / (np.mean(radii) + 1e-6):.3f}")
    print()
    
    angles = [np.arctan2(v[1], v[0]) for v in vecs]
    ang_unwrap = np.unwrap(angles)
    total_sweep = abs(ang_unwrap[-1] - ang_unwrap[0])
    print(f"Angular sweep: {total_sweep:.3f} rad ({np.degrees(total_sweep):.1f}°)")
    print()
    
    print("[DETECTION CHECK]")
    print(f"  sweep > 3.5 rad? {total_sweep > 3.5}")
    print(f"  radius_cv < 0.6? {np.std(radii) / (np.mean(radii) + 1e-6) < 0.6}")
    print(f"  → Circle detected? {total_sweep > 3.5 and np.std(radii) / (np.mean(radii) + 1e-6) < 0.6}")
    print()
    
    # Try lower thresholds
    print("[LOWER THRESHOLD TEST]")
    print(f"  sweep > 2.5 rad? {total_sweep > 2.5}")
    print(f"  radius_cv < 0.8? {np.std(radii) / (np.mean(radii) + 1e-6) < 0.8}")
    print(f"  → Circle detected? {total_sweep > 2.5 and np.std(radii) / (np.mean(radii) + 1e-6) < 0.8}")
else:
    print("No trajectory detected!")
