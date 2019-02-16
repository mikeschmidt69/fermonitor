# CamJam EduKit 2 - Sensors
# Worksheet 3 - Temperature

# Import Libraries
import os
import glob
import time
import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD

STATE_OK = 0
STATE_HOT = 1
STATE_HOT_ALARM = 2
STATE_COLD = 3
STATE_COLD_ALARM = 4

STATE = ["OK         ", "HOT        ", "ALARM: HOT ", "COLD       ", "ALARM: COLD"]

ALARM_STATE_ARMED = True

current_state = STATE_OK
previous_state = STATE_OK

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module
os.system('modprobe w1-therm') # Truns on the Temperature module

# Set the GPIO naming conventions
GPIO.setmode (GPIO.BCM)
GPIO.setwarnings(False)

# Set a variable to hold the GPIO Pin identity
pinpir = 17 # motion pin
pinblue = 23 # blue LED
pinred = 24 # red LED
pingreen = 25 # red LED
pinbuzz = 22 # buzzer
pinrelay = 20 # relay switch

# Set the three GPIO pins for Output
GPIO.setup(pinbuzz, GPIO.OUT)
GPIO.setup(pinred, GPIO.OUT)
GPIO.setup(pingreen, GPIO.OUT)
GPIO.setup(pinblue, GPIO.OUT)
GPIO.setup(pinpir, GPIO.IN)
GPIO.setup(pinrelay, GPIO.OUT)

GPIO.output(pinred, GPIO.HIGH)
GPIO.output(pingreen, GPIO.HIGH)
GPIO.output(pinblue, GPIO.HIGH)
GPIO.output(pinbuzz, GPIO.LOW)
GPIO.output(pinrelay, GPIO.LOW)

global p_R, p_G, p_B

p_R = GPIO.PWM(pinred, 2000)
p_G = GPIO.PWM(pingreen, 2000)
p_B = GPIO.PWM(pinblue, 2000)

p_R.start(0)
p_G.start(0)
p_B.start(0)

# Finds the correct device file that holds the temperature data
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# Set color of RGB LED
def setColor(r_val, g_val, b_val):
    p_R.ChangeDutyCycle(r_val)
    p_G.ChangeDutyCycle(g_val)
    p_B.ChangeDutyCycle(b_val)

# A function that reads the sensors data
def read_temp_raw():
    f = open(device_file, 'r') # Opens the temperature device file
    lines = f.readlines() # Returns the text
    f.close()
    return lines

# convert the value of the sensor into temperature
def read_temp():
    lines = read_temp_raw() # read the temperature device file

    # while the first line does not contain 'YES', wait for 0.2s
    # and then read the device file again.
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw

    # Look for th eposition of the '=' in the second line of the
    # device file
    equals_pos = lines[1].find('t=')

    # If the '=' is found, convert the rest of th eline after the
    # '=' into degrees Celsius, then degrees Fahrenheit
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

temp_target = float(20.0)
temp_tol = float(1.0)
temp_alarm = float(2.0)

# variables to hold pir current and last states
current_pir_state = 0
previous_pir_state = 0


PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
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
    
    setColor(100,100,100)
    time.sleep(1)
    setColor(0,100,0)
    
    mcp.output(3,1)     # turn on LCD backlight
    lcd.begin(16,2)     # set number of LCD lines and columns

    while True:
                   
        temp_c = read_temp()

        if temp_c > temp_target+temp_alarm:
            current_state = STATE_HOT_ALARM
        elif temp_c > temp_target + temp_tol and temp_c <= temp_target + temp_alarm:
            current_state = STATE_HOT
        elif temp_c <= temp_target + temp_tol and temp_c >= temp_target - temp_tol:        
            current_state = STATE_OK
        elif temp_c < temp_target - temp_tol and temp_c >= temp_target - temp_alarm:
            current_state = STATE_COLD
        elif temp_c < temp_target - temp_alarm:
            current_state = STATE_COLD_ALARM

        # Read PIR state
        current_pir_state = GPIO.input(pinpir)

        # If the PIR is triggered
        if current_pir_state == 1 and previous_pir_state == 0:
            # Record previous state
            previous_pir_state = 1
            if (current_state == STATE_HOT_ALARM or current_state == STATE_COLD_ALARM) and ALARM_STATE_ARMED == True:
                ALARM_STATE_ARMED = False
                print("Motion detected: alarm cancelled")

        # If the PIR has returned to ready state
        elif current_pir_state == 0 and previous_pir_state == 1:
            previous_pir_state = 0

        if current_state != previous_state:
            ALARM_STATE_ARMED = True
            
            # Set LED color
            if current_state == STATE_HOT or current_state == STATE_HOT_ALARM:
                setColor(100,0,0)
            elif current_state == STATE_COLD or current_state == STATE_COLD_ALARM:
                setColor(0,0,100)
            elif current_state == STATE_OK:
                setColor(0,100,0)
 
        # Handle Alarm
        if (current_state == STATE_HOT_ALARM or current_state == STATE_COLD_ALARM) and ALARM_STATE_ARMED == True:
            GPIO.output(pinbuzz, GPIO.HIGH)
        else:
            GPIO.output(pinbuzz, GPIO.LOW)


        # Turn on relay if cold
        if current_state == STATE_HOT or current_state == STATE_HOT_ALARM:
            GPIO.output(pinrelay, GPIO.HIGH)
        else:
            GPIO.output(pinrelay, GPIO.LOW)
                        
        print("Temp: ",temp_c)
        lcd.setCursor(0,0)  # set cursor position
        lcd.message( 'Temp: %.2f\n' % temp_c )
        lcd.message( STATE[current_state] ) 

        time.sleep(0.2)
        
        previous_state = current_state
        
except KeyboardInterrupt:
    print("...Stopped")
    
    # Reset GPIO settings
    p_R.stop()
    p_G.stop()
    p_B.stop()
    lcd.clear()
    GPIO.cleanup()
