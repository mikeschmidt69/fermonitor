# CamJam EduKit 2 - Sensors
# Worksheet 3 - Temperature

# Import Libraries
import os
import glob
import time
import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module

# Set the GPIO naming conventions
GPIO.setmode (GPIO.BCM)
GPIO.setwarnings(False)

# Set a variable to hold the GPIO Pin identity
pinpir = 17 # motion pin

# Set the three GPIO pins for Output
GPIO.setup(pinpir, GPIO.IN)

# variables to hold pir current and last states
current_pir_state = 0
previous_pir_state = 0

PCF8574A_address = 0x27  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
try:
    mcp = PCF8574_GPIO(PCF8574A_address)
except:
    print ('I2C Address Error !')
    exit(1)

# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp) 

# Print out the temperture until the program is stopped with Ctrl-C

try:
    
    print("Waiting for PIR to settle ...")
    # Loop until PIR output is 0
    while GPIO.input(pinpir) == 1:
        current_pir_state = 0
    print("PIR is ready")
    
    time.sleep(1)
    
    mcp.output(3,1)     # turn on LCD backlight
    lcd.begin(16,2)     # set number of LCD lines and columns

    while True:
                   
        # Read PIR state
        current_pir_state = GPIO.input(pinpir)

        lcd.setCursor(0,0)  # set cursor position
        if current_pir_state == 1:
            lcd.message('PIR = 1')
        else:
            lcd.message('PIR = 0')

        time.sleep(0.2)
        
        
except KeyboardInterrupt:
    print("...Stopped")
    
    # Reset GPIO settings
    lcd.clear()
    GPIO.cleanup()
