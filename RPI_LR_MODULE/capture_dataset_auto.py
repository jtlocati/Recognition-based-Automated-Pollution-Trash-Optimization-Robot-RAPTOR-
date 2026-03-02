#pi-only install, must replace to test on computer
#from picamera2 import Picamera2
from math import cos as Picamera2
from datetime import datetime
from pathlib import Path
import csv
import cv2
import time
import numpy as np

"""
Install on Pi OS:
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv
"""

# ----------------------------
# Config
# ----------------------------
WINDOW_NAME = "Trash Dataset Capture (AUTO when object placed)  |  q=quit, r=recalibrate"
DATASET_DIR = Path("dataset")
IMG_DIR = DATASET_DIR / "images"
CSV_PATH = DATASET_DIR / "captures.csv"

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480

SAVE_WIDTH = 1280
SAVE_HEIGHT = 720

# ROI where food will appear (fractions of frame): (x1, y1, x2, y2)
ROI_FRAC = (0.20, 0.20, 0.80, 0.85)

# Pixels below this value count as black background.
BLACK_THRESH = 35

# Trigger conditions
MIN_BLACK_DROP = 0.15     # trigger when black% drops by >= 15% from baseline
DEBOUNCE_FRAMES = 4       # require the condition for this many consecutive frames
COOLDOWN_SECONDS = 2.0    # after capture, ignore triggers for this long

# Baseline calibration
CALIBRATION_FRAMES = 20   # average over N frames when scene is empty

# ignore very bright reflections by smoothing
BLUR_KERNEL = (5, 5)


# Setup folders
IMG_DIR.mkdir(parents=True, exist_ok=True)

def log_to_csv(filename: str, timestamp: str):
    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["filename", "timestamp"])
        writer.writerow([filename, timestamp])

def get_roi(frame_bgr):
    h, w = frame_bgr.shape[:2]
    x1 = int(ROI_FRAC[0] * w)
    y1 = int(ROI_FRAC[1] * h)
    x2 = int(ROI_FRAC[2] * w)
    y2 = int(ROI_FRAC[3] * h)
    return frame_bgr[y1:y2, x1:x2], (x1, y1, x2, y2)

def black_fraction(roi_bgr):
    # Convert ROI to grayscale and count pixels below threshold as "black"
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    if BLUR_KERNEL is not None:
        gray = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    black_mask = gray < BLACK_THRESH
    return float(np.mean(black_mask))

def calibrate_baseline(picam2):
    print("\nCalibration: make sure NOTHING is under the camera (only black background).")
    print(f"Calibrating using {CALIBRATION_FRAMES} frames...")
    vals = []
    for _ in range(CALIBRATION_FRAMES):
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        roi, _ = get_roi(frame)
        vals.append(black_fraction(roi))
        time.sleep(0.02)
    baseline = float(np.mean(vals))
    print(f"Baseline black% = {baseline*100:.1f}%")
    return baseline

def save_still(picam2, preview_config, still_config):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"trash_{ts}.jpg"
    filepath = IMG_DIR / filename

    # Switch to still config
    picam2.stop()
    picam2.configure(still_config)
    picam2.start()
    time.sleep(0.1)

    still = picam2.capture_array()
    still = cv2.cvtColor(still, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(filepath), still)
    log_to_csv(filename, ts)
    print(f"Saved: {filepath}")

    # Switch back to preview
    picam2.stop()
    picam2.configure(preview_config)
    picam2.start()
    time.sleep(0.05)

    return ts, filename, filepath


# Camera Initalization
picam2 = Picamera2()

preview_config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (PREVIEW_WIDTH, PREVIEW_HEIGHT)}
)
still_config = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (SAVE_WIDTH, SAVE_HEIGHT)}
)

picam2.configure(preview_config)
picam2.start()
time.sleep(1)

baseline_black = calibrate_baseline(picam2)

print("\nRunning. Place food under camera to auto-capture.")
print("Controls: q=quit, r=recalibrate baseline\n")


# ========================================== Main loop ==========================================

debounce_count = 0
last_capture_time = 0.0

try:
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        roi, (x1, y1, x2, y2) = get_roi(frame)
        bf = black_fraction(roi)

        # Visual overlay
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        drop = baseline_black - bf
        status = f"baseline={baseline_black*100:.1f}%  now={bf*100:.1f}%  drop={drop*100:.1f}%"
        cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        now = time.time()
        in_cooldown = (now - last_capture_time) < COOLDOWN_SECONDS

        # Trigger logic
        trigger_condition = (drop >= MIN_BLACK_DROP) and (not in_cooldown)

        if trigger_condition:
            debounce_count += 1
        else:
            debounce_count = max(0, debounce_count - 1)

        cv2.putText(
            frame,
            f"debounce={debounce_count}/{DEBOUNCE_FRAMES}  cooldown={'YES' if in_cooldown else 'NO'}",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF

        # Recalibrate baseline
        if key == ord('r'):
            baseline_black = calibrate_baseline(picam2)
            debounce_count = 0
            continue

        # Quit
        if key == ord('q'):
            print("Quitting...")
            break

        # Capture when debounced
        if debounce_count >= DEBOUNCE_FRAMES:
            # Take the picture
            save_still(picam2, preview_config, still_config)
            last_capture_time = time.time()
            debounce_count = 0

finally:
    cv2.destroyAllWindows()
    picam2.stop()