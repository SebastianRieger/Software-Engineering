import threading
import time
import base64
from typing import Optional, Dict, List, Tuple

try:
    import cv2
    import mediapipe as mp
    import numpy as np
    HAS_MEDIAPIPE = True
except Exception:
    cv2 = None
    mp = None
    np = None
    HAS_MEDIAPIPE = False

from services import ws_manager


class GestureService:
    """Gesture recognition using MediaPipe Pose and OpenCV.

    Features:
    - Background camera capture and pose detection
    - Exponential moving average smoothing of body center
    - Trajectory-based gesture detection (swipe_left/right/down, circle)
    - WebSocket event broadcasting
    - Configurable thresholds and parameters

    Detected gestures:
    - swipe_right: rightward movement
    - swipe_left: leftward movement
    - swipe_down: downward movement
    - circle: circular motion

    Thread-safe state access via locks.
    """

    def __init__(self, camera_index: int = 0,
                 alpha: float = 0.6,
                 max_traj: int = 64,
                 gesture_cooldown: float = 1.0,
                 swipe_thresh: float = 0.12,
                 down_thresh: float = 0.12,
                 circle_sweep_min: float = 4.5,
                 circle_cv_max: float = 0.5):
        """
        Initialize GestureService.

        Args:
            camera_index: Camera device index (default 0)
            alpha: EMA smoothing factor [0, 1]; higher = more responsive
            max_traj: Trajectory buffer size (frames)
            gesture_cooldown: Minimum seconds between same gesture events
            swipe_thresh: Min displacement for horizontal swipe (normalized coords)
            down_thresh: Min displacement for downward swipe
            circle_sweep_min: Min angular sweep for circle (radians)
            circle_cv_max: Max coefficient of variation for circle radius
        """
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()

        self.latest_frame = None
        self.latest_jpeg_b64: Optional[str] = None
        self.prev_center = None
        self.smoothed_center: Optional[Tuple[float, float]] = None
        self.alpha = alpha

        # Trajectory (normalized coordinates)
        self.trajectory: List[Tuple[float, float]] = []
        self.max_traj = max_traj

        # Movement state
        self.movement: Dict[str, float] = {"dx": 0.0, "dy": 0.0}
        self.flags: Dict[str, bool] = {"down": False, "left": False, "right": False}

        # Gesture detection parameters
        self.gesture_cooldown = gesture_cooldown
        self.last_gesture_time: Dict[str, float] = {}
        self.swipe_thresh = swipe_thresh
        self.down_thresh = down_thresh
        self.circle_sweep_min = circle_sweep_min
        self.circle_cv_max = circle_cv_max

        # MediaPipe Pose (set when available)
        if HAS_MEDIAPIPE:
            self.mp_pose = mp.solutions.pose
        else:
            self.mp_pose = None
        self.pose = None

    def start(self):
        with self.lock:
            if self.running:
                return
            if not HAS_MEDIAPIPE or cv2 is None:
                raise RuntimeError("Mediapipe/OpenCV nicht verfügbar in dieser Umgebung")
            self.cap = cv2.VideoCapture(self.camera_index)
            if not (self.cap and self.cap.isOpened()):
                # Try to release if failed
                if self.cap:
                    self.cap.release()
                self.cap = None
                raise RuntimeError("Kamera konnte nicht geöffnet werden")

            self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.pose:
            self.pose.close()
            self.pose = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _run(self):
        while True:
            with self.lock:
                if not self.running:
                    break
            if self.cap is None:
                time.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Process frame with MediaPipe (convert BGR -> RGB)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            center = None
            if results.pose_landmarks:
                # Use nose (0) and shoulders (11,12) if available to compute a stable center
                lm = results.pose_landmarks.landmark
                indices = [0, 11, 12]
                points = [lm[i] for i in indices if i < len(lm)]
                xs = [p.x for p in points if p.visibility > 0.2]
                ys = [p.y for p in points if p.visibility > 0.2]
                if xs and ys:
                    cx = float(np.mean(xs))
                    cy = float(np.mean(ys))
                    center = (cx, cy)

            # Update smoothing and trajectory
            if center:
                if self.smoothed_center is None:
                    self.smoothed_center = center
                else:
                    sx = self.alpha * center[0] + (1 - self.alpha) * self.smoothed_center[0]
                    sy = self.alpha * center[1] + (1 - self.alpha) * self.smoothed_center[1]
                    self.smoothed_center = (sx, sy)
                self.trajectory.append(self.smoothed_center)
                if len(self.trajectory) > self.max_traj:
                    self.trajectory.pop(0)
            else:
                # when no detection, slowly decay
                self.smoothed_center = None
                self.trajectory.clear()

            # Compute simple motion deltas using smoothed center
            if self.smoothed_center and self.prev_center:
                dx = self.smoothed_center[0] - self.prev_center[0]
                dy = self.smoothed_center[1] - self.prev_center[1]
            else:
                dx = 0.0
                dy = 0.0

            self.prev_center = self.smoothed_center

            # Thresholds tuned for normalized coords; adjust if needed
            thr_side = 0.02
            thr_down = 0.02

            self.movement["dx"] = dx
            self.movement["dy"] = dy
            self.flags["down"] = dy > thr_down
            self.flags["left"] = dx < -thr_side
            self.flags["right"] = dx > thr_side

            # Detect discrete gestures from trajectory
            gesture = self._detect_gesture()
            if gesture:
                now = time.time()
                last = self.last_gesture_time.get(gesture, 0)
                if now - last > self.gesture_cooldown:
                    self.last_gesture_time[gesture] = now
                    # Broadcast event to websocket clients (non-blocking)
                    try:
                        import asyncio

                        asyncio.create_task(ws_manager.manager.broadcast({"type": "gesture", "gesture": gesture, "movement": {"dx": dx, "dy": dy}}))
                    except Exception:
                        pass

            # Encode a small preview frame
            try:
                _, jpeg = cv2.imencode('.jpg', frame)
                b64 = base64.b64encode(jpeg.tobytes()).decode('ascii')
                self.latest_jpeg_b64 = f"data:image/jpeg;base64,{b64}"
            except Exception:
                self.latest_jpeg_b64 = None

            # A small sleep to avoid pegging CPU
            time.sleep(0.02)

    def get_status(self) -> Dict:
        return {
            "running": bool(self.running),
            "movement": self.movement.copy(),
            "flags": self.flags.copy(),
            "frame": self.latest_jpeg_b64,
        }

    def _detect_gesture(self) -> Optional[str]:
        """Detect gesture from trajectory.

        Returns:
            Gesture name or None if no gesture detected.
        """
        traj = self.trajectory
        if not traj or len(traj) < 6:
            return None

        xs = [p[0] for p in traj]
        ys = [p[1] for p in traj]

        # Displacement and span
        dx_total = xs[-1] - xs[0]
        dy_total = ys[-1] - ys[0]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)

        # Horizontal swipes
        if (abs(dx_total) > self.swipe_thresh and
            abs(dx_total) > abs(dy_total) * 1.5 and
            span_x > 0.06):
            return "swipe_right" if dx_total > 0 else "swipe_left"

        # Downward swipe
        if (dy_total > self.down_thresh and
            dy_total > abs(dx_total) * 1.2 and
            span_y > 0.06):
            return "swipe_down"

        # Circle detection
        cx = float(np.mean(xs))
        cy = float(np.mean(ys))

        if cx == 0 and cy == 0:
            return None

        vecs = [(x - cx, y - cy) for x, y in traj]
        radii = [np.hypot(v[0], v[1]) for v in vecs]

        if not radii or np.mean(radii) < 0.01:
            return None

        angles = [np.arctan2(v[1], v[0]) for v in vecs]
        ang_unwrap = np.unwrap(angles)
        total_sweep = abs(ang_unwrap[-1] - ang_unwrap[0])
        radius_cv = np.std(radii) / (np.mean(radii) + 1e-6)

        if total_sweep > self.circle_sweep_min and radius_cv < self.circle_cv_max:
            return "circle"

        return None

    def capture_image(self, path: Optional[str] = None) -> Optional[str]:
        """Return latest frame as base64 string and optionally save to disk."""
        if self.latest_jpeg_b64 is None:
            return None
        if path:
            # strip header
            header, _, data = self.latest_jpeg_b64.partition(',')
            if data:
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(data))
        return self.latest_jpeg_b64


# Module-level singleton convenient for endpoints
gesture_service = GestureService()
