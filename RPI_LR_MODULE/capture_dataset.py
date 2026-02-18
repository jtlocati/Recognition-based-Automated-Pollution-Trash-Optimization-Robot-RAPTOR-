"""

!!!BEFORE RUNNING!!!
must create: 
   dataset/images/(jpg)
   dataset/labels.csv(for labeling jpg)

Install pi cam2 on RPI
    sudo apt install -y python3-picamera2 python3-gpiozero

To run in RPI:
    python3 capture_dataset.py

    OR if cloning repo:
    python3 Recognition-based-Automated-Pollution-Trash-Optimization-Robot-RAPTOR/capture_dataset.py


"""
"""install once on RPI"""
#from gpiozero import Button
#from picamera2 import Picamera2

#for now import mich packages to placehold to avoid errors in development
from math import asin as Button
from math import acos as Picamera2

#Real packages:
from datetime import datetime
from pathlib import Path
import csv
import time

#Config 
DATASET_DIR = Path("dataset")
IMG_DIR = DATASET_DIR / "images"
CSV_PATH = DATASET_DIR / "labels.csv" #-> "Dependent if we want / can localy process labels"

BUTTON_GPO = 17 #GPIO17 OR pin 11

#Folder setup

IMG_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)

#Camera Setup
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration()) #NON-FUNCTIONAL LINE!!!
picam2.start()
time.sleep(1) #photo warmup

#Button Setup

def log_to_csv(filename: str, timestamp: str, label: str = ""):
    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="") as file:
        writer = csv.writer(file)
        if new_file:
            writer.writerow(["filename", "timestamp", "label"])
        writer.writerow([filename, timestamp, label])

def take_photo():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"trash{ts}.jpg"
    filepath = IMG_DIR / filename

    picam2.capture_file(str(filepath))
    log_to_csv(filename, ts, "")

    print("Ready to capture image")

try:
    Button.when_pressed = take_photo
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    print("Shutting Down...")

finally:
    picam2.stop()

