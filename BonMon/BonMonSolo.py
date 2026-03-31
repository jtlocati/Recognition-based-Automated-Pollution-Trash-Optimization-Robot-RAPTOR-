#Use this code to test the functionality of the motors without being dependent on imageing software

#import RPi.GPIO as GPIO -> RPI native install "sudo apt install python3-gpiozero"

#for now import random stuff to void errors
from math import comb as GPIO #DELETE BEFORE RUNNING
import time

STEP = 18
DIR = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(STEP, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)

GPIO.output(DIR, GPIO.HIGH)  # Set direction

for _ in range(50):  # 200 steps = 1 rotation for most -> 90 degerees 
    GPIO.output(STEP, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(STEP, GPIO.LOW)
    time.sleep(0.001)
    
GPIO.cleanup()