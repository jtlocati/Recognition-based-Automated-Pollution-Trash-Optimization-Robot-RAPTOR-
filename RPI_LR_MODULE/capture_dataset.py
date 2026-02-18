#from picamera2 import Picamera2
from datetime import datetime
from pathlib import Path
import csv
import cv2
import time

"""
!!! BEFORE RUNNING !!!

sudo apt install -y python3-picamera2 python3-opencv


"""


# Config
WINDOW_NAME = "Trash Dataset Capture (SPACE=Take picture)"
DATASET_DIR = Path("dataset")
IMG_DIR = DATASET_DIR / "images"
CSV_PATH = DATASET_DIR / "captures.csv"

# Optional: make preview smaller so it runs smoother on RPi 3
PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480

# Making image bigger will slow down RPI
SAVE_WIDTH = 1280
SAVE_HEIGHT = 720


# Setup folders
IMG_DIR.mkdir(parents=True, exist_ok=True)

def log_to_csv(filename: str, timestamp: str):
    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["filename", "timestamp"])
        writer.writerow([filename, timestamp])


# Setup camera
picam2 = Picamera2()

# Preview stream (fast, for live display)
preview_config = picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (PREVIEW_WIDTH, PREVIEW_HEIGHT)}
)

# Still capture config (for saved images)
still_config = picam2.create_still_configuration(
    main={"format": "BGR888", "size": (SAVE_WIDTH, SAVE_HEIGHT)}
)

picam2.configure(preview_config)
picam2.start()
time.sleep(1)  # warm-up

print("Running. Press SPACE to save an image. Press Q to quit.")


# Continul loop
try:
    while True:
        # Live preview frame
        frame = picam2.capture_array()
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF

        # SPACE -> capture
        if key == ord(' '):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"trash_{ts}.jpg"
            filepath = IMG_DIR / filename

            # Switch to still config to save a higher quality image
            picam2.stop()
            picam2.configure(still_config)
            picam2.start()
            time.sleep(0.1)  # short settle

            still = picam2.capture_array()
            cv2.imwrite(str(filepath), still)
            log_to_csv(filename, ts)
            print(f"Saved: {filepath}")

            # Switch back to preview config
            picam2.stop()
            picam2.configure(preview_config)
            picam2.start()
            time.sleep(0.1)

        # Q -> quit (mainly for testing)
        elif key == ord('q'):
            print("Quitting...")
            break

finally:
    cv2.destroyAllWindows()
    picam2.stop()
