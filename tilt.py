#
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

# tilt.py code is based on tiltV1.py code found at following URL and utilizes 
# blescan.py found on the same page 
# https://www.instructables.com/id/Reading-a-Tilt-Hydrometer-With-a-Raspberry-Pi/

import blescan
from datetime import datetime, timedelta
import time
import os
import bluetooth._bluetooth as bluez
import threading

import logging

import configparser
from distutils.util import strtobool

logger = logging.getLogger('FERMONITOR.TILT')
logger.setLevel(logging.INFO)

COLOR = "COLOR"
TEMP = "TEMP"
SG = "SG"
TIME = "TIME"

RED = "RED"
GREEN = "GREEN"
BLACK = "BLACK"
PURPLE = "PURPLE"
ORANGE = "ORANGE"
BLUE = "BLUE"
YELLOW = "YELLOW"
PINK = "PINK"

DEFAULT_BT_DEVICE_ID = 0
MINIMUM_INTERVAL = 10
CONFIGFILE = "tilt.ini"
CONFIGSECTION = "TILT"

DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

def validColor(color):
    if color in {RED,GREEN,BLACK,PURPLE,ORANGE,BLUE,YELLOW,PINK}:
        return True
    return False

# Class for reading temperature and sepcific gravity form Tilt Hydrometer. Class uses a separate thread to collect data from the connected
# Tilt at a defined interval
class Tilt (threading.Thread):

    #Assign uuid's of various colour tilt hydrometers. BLE devices like the tilt work primarily using advertisements. 
    #The first section of any advertisement is the universally unique identifier. Tilt uses a particular identifier based on the colour of the device
    color = {
        'a495bb10c5b14b44b5121370f02d74de' : RED,
        'a495bb20c5b14b44b5121370f02d74de' : GREEN,
        'a495bb30c5b14b44b5121370f02d74de' : BLACK,
        'a495bb40c5b14b44b5121370f02d74de' : PURPLE,
        'a495bb50c5b14b44b5121370f02d74de' : ORANGE,
        'a495bb60c5b14b44b5121370f02d74de' : BLUE,
        'a495bb70c5b14b44b5121370f02d74de' : YELLOW,
        'a495bb80c5b14b44b5121370f02d74de' : PINK
    }


    # Constructor for class
    def __init__(self):
        threading.Thread.__init__(self)
    
        self.bluetoothDeviceId = DEFAULT_BT_DEVICE_ID
        self.interval = MINIMUM_INTERVAL

        self.lastUpdateTime = datetime.now()  - timedelta(seconds=self.interval) # last time the tilt was read
     
        self.data = {}
        self.stopThread = True
        self._readConf()


    # Starts background thread that updates the data from Tilt hydrometer (temp, specific gravity) on regular basis.
    # This is not a realtime operation so thread sleeps for 5s after each iteration
    def run(self):
        logger.info("Starting Tilt Monitoring")
        self.stopThread = False
        while self.stopThread != True:
            self._readConf()
            self._update()    # calls method that updates data from Tilt if update time interval has lapsed
            time.sleep(MINIMUM_INTERVAL)
        logger.info("Tilt Monitoring Stopped.")


    # stops the background thread updating data coming from configured Tilt
    def stop(self):
        self.stopThread = True
   
    
    # return a copy of the data to be used outside module
    def getAllData(self):
        return self.data.copy()


    # return a copy of the data for a specific color tilt
    def getData(self, _color):
        if self.data.get(_color) != None and len(self.data[_color]) > 0:
            return self.data[_color].copy()
        else:
            return None

 
    # Internal method for checking if the update time interval has lapsed and new data should be read from Tilt
    def _update(self):
        updateTime = self.lastUpdateTime + timedelta(seconds=self.interval)
        if datetime.now() > updateTime:
            logger.debug("Update data")
            self._readdata()
            self.lastUpdateTime = datetime.now()
        else:
            logger.debug("Update interval not reached:"+datetime.now().strftime(DATETIME_FORMAT) +" / "+ updateTime.strftime(DATETIME_FORMAT)) 


    # Method for scan BLE advertisements until one matching tilt uuid is found and data (temperature, specific gravity) is read and stored
    def _readdata(self):

        curTime = datetime.now()
        timeout = curTime + timedelta(minutes=1) # scan for 1 minute looking for data from tilt

        logger.debug("Connecting to Bluetooth...")
        try:
            sock = bluez.hci_open_dev(self.bluetoothDeviceId)

        except:
            logger.exception("Error accessing bluetooth device...")
            return False

        blescan.hci_le_set_scan_parameters(sock)
        blescan.hci_enable_le_scan(sock)

        _data = {}
    
        while (curTime < timeout):
            returnedList = blescan.parse_events(sock, 10)

            for beacon in returnedList:  # returnedList is a list datatype of string datatypes seperated by commas (,)
 
                output = beacon.split(',') # split the list into individual strings in an array
                uuid = output[1]

                if uuid in Tilt.color.keys():
                    logger.debug("Found Tilt hydrometer:" + uuid)

                    foundColor = Tilt.color.get(uuid)
                    foundTemp = float(int(output[2],16)-32)*5/9
                    foundSG = float(int(output[3],16)/1000)

                    logger.debug("Found "+foundColor+" Tilt: T/"+str(foundTemp)+", SG/"+str(foundSG))
                    
                    if  foundTemp > 200:  # first reading always showed temperature of 537.2C and SG 1.0
                        logger.debug("Skipping initial datasets as temp and SG are always wrong")
                    else:
                        _data[foundColor] = {COLOR: foundColor, TEMP: round(float(foundTemp),1), SG: round(float(foundSG),3), TIME:curTime}
                        logger.debug(foundColor+" - "+curTime.strftime(DATETIME_FORMAT)+" - T:"+str(round(float(foundTemp),1))+" - SG:"+"{:5.3f}".format(round(float(foundSG),3)))

            curTime = datetime.now()

        # Did not collect data before timeout; set data as invalid
        if len(_data) == 0:
            logger.debug("Timed out collecting data from Tilt")
        
        self.data = _data

        blescan.hci_disable_le_scan(sock)
        return True
        

    def _readConf(self):
    
        bDefaultInterval = True
        bDefaultBtDeviceId = True
        
        if os.path.isfile(CONFIGFILE) == False:
            logger.error("Tilt configuration file is not valid: "+CONFIGFILE)
        else:
            ini = configparser.ConfigParser()
            try:
                logger.debug("Reading Tilt config: " + CONFIGFILE)
                ini.read(CONFIGFILE)

                if CONFIGSECTION in ini:
                    config = ini[CONFIGSECTION]

                    try:
                        if config["UpdateIntervalSeconds"] != "" and int(config["UpdateIntervalSeconds"]) >= MINIMUM_INTERVAL:
                            self.interval = int(config.get("UpdateIntervalSeconds"))
                            bDefaultInterval = False
                        else:
                            self.interval = MINIMUM_INTERVAL
                    except KeyError:
                        pass

                    try:
                        if config["BluetoothDeviceId"] != "" and int(config["BluetoothDeviceId"]) >= 0:
                            self.bluetoothDeviceId = int(config.get("BluetoothDeviceId"))
                            bDefaultBtDeviceId = False
                        else:
                            self.bluetoothDeviceId = 0
                    except KeyError:
                        pass

                    try:
                        if config["MessageLevel"] == "DEBUG":
                            logger.setLevel(logging.DEBUG)
                        elif config["MessageLevel"] == "WARNING":
                            logger.setLevel(logging.WARNING)
                        elif config["MessageLevel"] == "ERROR":
                            logger.setLevel(logging.ERROR)
                        elif config["MessageLevel"] == "INFO":
                            logger.setLevel(logging.INFO)
                        else:
                            logger.setLevel(logging.INFO)
                    except KeyError:
                        logger.setLevel(logging.INFO)
                else:
                    logger.error("["+CONFIGSECTION+"] section not found in ini file: " + CONFIGFILE)
            except:
                pass
    
        if bDefaultInterval or bDefaultBtDeviceId:
            logger.warning("Problem read from configuration file: \""+CONFIGFILE+ \
                "\". Using some default values[**] for Tilt configuration. It could take a minute for updated values in config file to be used.")
            sConf = "UpdateIntervalSeconds = "+str(self.interval)
            if bDefaultInterval:
                sConf = sConf + "**"
            sConf = sConf + "\nBluetoothDeviceId = "+str(self.bluetoothDeviceId)
            if bDefaultBtDeviceId:
                sConf = sConf + "**"
            print(sConf)

