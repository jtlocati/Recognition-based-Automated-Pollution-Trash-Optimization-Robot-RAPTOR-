# Pi-only import — comment out and use a mock to test on a regular computer
from picamera2 import Picamera2
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


# ======================== Configuration ========================

WINDOW_NAME = "Trash Dataset Capture (AUTO when object placed)  |  q=quit, r=recalibrate"
DATASET_DIR = Path("dataset")
IMG_DIR = DATASET_DIR / "images"
CSV_PATH = DATASET_DIR / "captures.csv"

PREVIEW_WIDTH = 1280
PREVIEW_HEIGHT = 1280

SAVE_WIDTH = 1280
SAVE_HEIGHT = 720

# ROI where trash will appear (fractions of frame): (x1, y1, x2, y2)
ROI_FRAC = (0.20, 0.20, 0.80, 0.85)

# Trigger via mean absolute pixel difference from baseline
# When the average per-pixel brightness change in the ROI exceeds this
# value (0–255 scale), we consider an object present.
CHANGE_THRESH = 18 # tune this: lower = more sensitive

DEBOUNCE_FRAMES = 10 # require condition for N consecutive frames
COOLDOWN_SECONDS = 10.0 # ignore triggers for this long after a capture

# Baseline calibration
CALIBRATION_FRAMES = 20 # average over N frames when scene is empty

# Smooth out sensor noise before comparison
BLUR_KERNEL = (7, 7)


# ======================== Setup ========================

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


def to_gray_blurred(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, BLUR_KERNEL, 0)


def mean_abs_diff(roi_bgr, baseline_gray):
    gray = to_gray_blurred(roi_bgr)
    diff = cv2.absdiff(gray, baseline_gray)
    return float(np.mean(diff))


def calibrate_baseline(picam2):
    print("\nCalibration: make sure NOTHING is under the camera (only the background).")
    print(f"Calibrating using {CALIBRATION_FRAMES} frames ...")
    accum = None
    for _ in range(CALIBRATION_FRAMES):
        frame = picam2.capture_array("lores")
        frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2BGR)
        roi, _ = get_roi(frame)
        gray = to_gray_blurred(roi)
        if accum is None:
            accum = gray.astype(np.float64)
        else:
            accum += gray.astype(np.float64)
        time.sleep(0.02)
    baseline_gray = (accum / CALIBRATION_FRAMES).astype(np.uint8)
    avg_brightness = float(np.mean(baseline_gray))
    print(f"Baseline average brightness = {avg_brightness:.1f} / 255")
    return baseline_gray


def save_still(picam2):
    #Capture a high-res still from the main stream.
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"trash_{ts}.jpg"
    filepath = IMG_DIR / filename

    still = picam2.capture_array("main")
    still = cv2.cvtColor(still, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(filepath), still)
    log_to_csv(filename, ts)
    print(f"  >>> Saved: {filepath}")

    return ts, filename, filepath


# ======================== Camera Initialisation ========================

picam2 = Picamera2()

# Single config: high-res main (for stills) + low-res lores (for preview).
# No need to stop/reconfigure when capturing.
config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (SAVE_WIDTH, SAVE_HEIGHT)},
    lores={"format": "YUV420", "size": (PREVIEW_WIDTH, PREVIEW_HEIGHT)},
    display="lores",
)

picam2.configure(config)
picam2.start()
time.sleep(1)

baseline_gray = calibrate_baseline(picam2)

print("\nRunning.  Place trash under camera to auto-capture.")
print("Controls:  q = quit,  r = recalibrate baseline\n")


# ============================== Main loop ==============================

debounce_count = 0
last_capture_time = 0.0

try:
    while True:
        # Grab the low-res stream for live preview / detection
        frame = picam2.capture_array("lores")
        frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2BGR)

        roi, (x1, y1, x2, y2) = get_roi(frame)
        diff = mean_abs_diff(roi, baseline_gray)

        # Visual overlay
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

        now = time.time()
        in_cooldown = (now - last_capture_time) < COOLDOWN_SECONDS

        # Cooldown/status text only
        if in_cooldown:
            remaining = COOLDOWN_SECONDS - (now - last_capture_time)
            text = f"Cooldown: {remaining:.1f}s"
            text_color = (0, 0, 255) # Red
        else:
            text = "Cooldown: 0.0s"
            text_color = (0, 255, 0) # Green

        cv2.putText(
            frame,
            text,
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,#font
            text_color,
            4,
            cv2.LINE_AA
        )

        # Trigger logic
        trigger_condition = (diff >= CHANGE_THRESH) and (not in_cooldown)

        if trigger_condition:
            debounce_count += 1
        else:
            debounce_count = 0

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("r"):
            baseline_gray = calibrate_baseline(picam2)
            debounce_count = 0
            continue

        if key == ord("q"):
            print("Quitting...")
            break

        # Capture when debounced
        if debounce_count >= DEBOUNCE_FRAMES:
            save_still(picam2)
            last_capture_time = time.time()
            debounce_count = 0

finally:
    cv2.destroyAllWindows()
    picam2.stop()
