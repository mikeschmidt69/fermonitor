# Copyright (c) 2019 Michael Schmidt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import threading
import time
import glob
import datetime
import logging
import RPi.GPIO as GPIO
import I2C_LCD_driver
from setup_logger import logger

logger = logging.getLogger('INTERFACE')
logger.setLevel(logging.INFO)

# Set a variable to hold the GPIO Pin identity
PIN_PIR = 17 # motion pin

LCD_ON_SEC = 30
DISPLAY_ON_SEC = 5
NUM_DISPLAYS = 3


# Handles communication with Arduino over serial interface to read wired temperaturess and turn on/off heating and cooling devices
class Interface (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self, _sWelcome):
        threading.Thread.__init__(self)
        
        # variables to hold pir current and last states
        self.pir_state = 0
        self.bStopRequest = False

        self.iDisplay = 1
        
        self.sScreen1Row1 = _sWelcome
        self.sScreen1Row2 = " Target:        "
        self.sScreen2Row1 = "     SG:        "
        self.sScreen2Row2 = "   Beer:        "
        self.sScreen3Row1 = "(W)Beer:        "
        self.sScreen3Row2 = "Chamber:        "
        self.lcdOffTime = datetime.datetime.now() 
        self.displaySwitchTime = datetime.datetime.now() + datetime.timedelta(seconds=DISPLAY_ON_SEC)

        # Initialize the GPIO Pins
        os.system('modprobe w1-gpio') # Turns on the GPIO module

        # Set the GPIO naming conventions
        GPIO.setmode (GPIO.BCM)
        GPIO.setwarnings(False)

        # Set the three GPIO pins for Output
        GPIO.setup(PIN_PIR, GPIO.IN)

        # Create LCD, passing in MCP GPIO adapter.
        self.lcd = I2C_LCD_driver.lcd()
        time.sleep(5)
        self.lcd.backlight(0)
        self.bLcdOn = False

        if _sWelcome != None:
            self.lcd.backlight(1)
            self.bLcdOn = True
            self.lcd.lcd_display_string(_sWelcome,1)
            self.lcdOffTime = datetime.datetime.now() + datetime.timedelta(seconds=LCD_ON_SEC)
            logger.debug("1 - LCD is on to show welcome")

        else:
            self.lcd.backlight(0)
            self.bLcdOn = False
        

        # Loop until PIR output is 0
        while GPIO.input(PIN_PIR) == 1:
            self.pir_state = 0
        
    # Starts the background thread
    def run(self):
        while not self.bStopRequest:
            curTime = datetime.datetime.now()

            # Set which of the 2 displays should be shown
            if curTime > self.displaySwitchTime:
                self.iDisplay = self.iDisplay + 1
                if self.iDisplay > NUM_DISPLAYS:
                    self.iDisplay = 1

                self.displaySwitchTime = curTime + datetime.timedelta(seconds=DISPLAY_ON_SEC)
                self.lcd.lcd_clear()

            self.pir_state = GPIO.input(PIN_PIR)

            # Motion detected
            if self.pir_state == 1:

                # Display should be turned on if not already on
                self.lcd.backlight(1)
                self.bLcdOn = True
               
                # Reset timeout of display when motion is detected
                self.lcdOffTime = curTime + datetime.timedelta(seconds=LCD_ON_SEC)

                logger.debug("LCD ON due to detected motion, timeout reset -> PIR_STATE: " + str(self.pir_state) + " bLcdOn: " + str(self.bLcdOn) + " curTime: " + curTime.strftime("%d.%m.%Y %H:%M:%S") + " lcdOffTime: " + self.lcdOffTime.strftime("%d.%m.%Y %H:%M:%S") )

            # Motion not detected
            else:

                # display is on
                if self.bLcdOn:

                    # Display should be turned off as timeout has expired
                    if curTime > self.lcdOffTime:
                        self.lcd.lcd_clear()
                        self.lcd.backlight(0)                
                        self.bLcdOn = False

                        logger.debug("Turning LCD OFF -> PIR_STATE: " + str(self.pir_state) + " bLcdOn: " + str(self.bLcdOn) + " curTime: " + curTime.strftime("%d.%m.%Y %H:%M:%S") + " lcdOffTime: " + self.lcdOffTime.strftime("%d.%m.%Y %H:%M:%S") )

                    # Display on until timeout expires
                    else:
                        logger.debug("LCD ON without motion until timeout -> PIR_STATE: " + str(self.pir_state) + " bLcdOn: " + str(self.bLcdOn) + " curTime: " + curTime.strftime("%d.%m.%Y %H:%M:%S") + " lcdOffTime: " + self.lcdOffTime.strftime("%d.%m.%Y %H:%M:%S") )

                # Normal state for LCD to be off when no motion detected
                else:             
                    self.lcd.backlight(0)                
                    self.bLcdOn = False
                    logger.debug("LCD remains OFF -> PIR_STATE: " + str(self.pir_state) + " bLcdOn: " + str(self.bLcdOn))

            try:

                # If display is ON show latest values
                if self.bLcdOn:
                    if self.iDisplay == 1:
                        logger.debug("Displaying screen 1")
                        self.lcd.lcd_display_string(self.sScreen1Row1,1)
                        self.lcd.lcd_display_string(self.sScreen1Row2,2)
                    elif self.iDisplay == 2:
                        logger.debug("Displaying screen 2")
                        self.lcd.lcd_display_string(self.sScreen2Row1,1)
                        self.lcd.lcd_display_string(self.sScreen2Row2,2)
                    elif self.iDisplay == 3:
                        logger.debug("Displaying screen 3")
                        self.lcd.lcd_display_string(self.sScreen3Row1,1)
                        self.lcd.lcd_display_string(self.sScreen3Row2,2)
                    else:
                        self.iDisplay = 1;
                        logger.debug("Display increment messed up; resetting to 1")


            except:
                logger.error("*** PROBLEM WRITING TO LCD ***")
                logger.error("Error:", sys.exc_info()[0])
                        
                # Recreate LCD
                self.lcd = I2C_LCD_driver.lcd()
                time.sleep(5)
        
                self.lcd.lcd_clear()
                self.lcdOffTime = curTime
                self.lcd.backlight(0)                
                self.bLcdOn = False

                logger.debug(self.sScreen1Row1)
                logger.debug(self.sScreen1Row2)
                logger.debug(self.sScreen2Row1)
                logger.debug(self.sScreen2Row2)
                logger.debug(self.sScreen3Row1)
                logger.debug(self.sScreen3Row2)
            
            time.sleep(0.5)



    def __del__(self):
        self.lcd.lcd_clear()
        self.lcd.backlight(0)                
        logger.debug("Delete interface class")

    # stops the background thread and requests heating and cooling to be stopped
    def stop(self):
        self.lcd.lcd_clear()
        self.lcd.backlight(0)
        self.bLcdOn = False
        self.bStopRequest = True

    # set logging level
    def setLogLevel(self, level):
        if level == logging.DEBUG:
            logger.setLevel(logging.DEBUG)
        elif level == logging.WARNING:
            logger.setLevel(logging.WARNING)
        elif level == logging.ERROR:
            logger.setLevel(logging.ERROR)
        elif level == logging.INFO:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.INFO)

    def setData(self, _target, _beerT, _sg, _beerWireT, _chamberT):

        if _target is not None:
            self.sScreen1Row2 = None
            self.sScreen1Row2 = " Target:{:5.1f}C  ".format(round(float(_target),1))
        if _sg is not None:
            self.sScreen2Row1 = None
            self.sScreen2Row1 = "     SG:  {:5.3f} ".format(round(float(_sg),3))
        if _beerT is not None:
            self.sScreen2Row2 = None
            self.sScreen2Row2 = "   Beer:{:5.1f}C  ".format(round(float(_beerT),1))
        if _beerWireT is not None:
            self.sScreen3Row1 = None
            self.sScreen3Row1 = "(W)Beer:{:5.1f}C  ".format(round(float(_beerWireT),1))
        if _chamberT is not None:
            self.sScreen3Row2 = None
            self.sScreen3Row2 = "Chamber:{:5.1f}C  ".format(round(float(_chamberT),1))


