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

from urllib import request, parse
import json
import sys
import requests
import datetime
import time
import os
import threading
import logging
from setup_logger import logger
import configparser
from distutils.util import strtobool

logger = logging.getLogger('BREWFATHER')
logger.setLevel(logging.INFO)

MINIMUM_INTERVAL = 900 # minimum number of seconds the BrewFather.app can be updated (i.e. 15min)
CONFIGFILE = "brewfather.ini"

# Brewfather class used for passing brew related logging data to BrewFather.app so it can be displayed for batch connected in the app.
class BrewFather (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self):
        threading.Thread.__init__(self)
    
        if os.path.isfile(CONFIGFILE) == False:
            raise IOError("BrewFather configuration file is not valid: "+CONFIGFILE)
        self.bUpdate = False                # flag indicating if BrewFather should be updated with data or not; useful for debugging
        self.sURL = ""                      # custom URL provided in the BrewFather app where data should be sent in JSON format
        self.interval = MINIMUM_INTERVAL    # interval in seconds for updating BrewFather; BrewFather rejects updates more often than 15min
        self.stopThread = True              # flag used for stopping the background thread that updates BrewFather
        self.bNewData = False

        # Data accepted by BrewFather; OK if some values are ""; not sure what happens if fields are missing.
        self.postdata = {
            "name": "Fermonitor",
            "temp": "",
            "aux_temp": "", # Fridge Temp
            "ext_temp": "", # Room Temp
            "temp_unit": "C", # C, F, K
            "gravity": "",
            "gravity_unit": "G", # G, P
            "pressure": "",
            "pressure_unit": "BAR", # PSI, BAR, KPA
            "ph": "",
            "comment": "",
            "beer": ""
        }
        self.jsondump = ""

        # Keeps track of last time BrewFather was updated to know when it can be updated again
        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=self.interval) # last time the tilt was read
     
    # Starts the background thread for updating BrewFather with lastest data. First re-reads configuration file to check
    # if any of the settings have changed
    def run(self):
        logger.info("Starting BrewFather Logging")
        self.stopThread = False
        while self.stopThread != True:
            self._readConf()
            self._update() 
            time.sleep(60)
        logger.info("BrewFather Monitoring Stopped")


    # stops the background thread updating data coming from configured Tilt
    def stop(self):
        self.stopThread = True

    # sets the data currently supported by my system, will expand with system
    def setData(self, _beer_temp, _aux_temp, _gravity):
        if _beer_temp != None:
            self.postdata["temp"] = str(round(float(_beer_temp),1))
        else:
            self.postdata["temp"] = ""

        if _aux_temp != None:
            self.postdata["aux_temp"] = str(round(float(_aux_temp),1))
        else: 
            self.postdata["aux_temp"] = ""

        if _gravity != None:
            self.postdata["gravity"] = "{:5.3f}".format(round(float(_gravity),3))
        else:
            self.postdata["gravity"] = ""

        if _beer_temp != None or _aux_temp != None or _gravity != None:
            self.bNewData = True
            
    def getLastJSON(self):
        return self.jsondump

    def getLastRequestTime(self):
        return self.lastUpdateTime

    # method for connecting and updating BrewFather.app
    def _update(self):
        updateTime = self.lastUpdateTime + datetime.timedelta(seconds=self.interval)

        # check update flag is enabled
        # check Brewfather URL is defined
        # check the updated interval has elapsed since last update
        # check relevant data for the system is valid
        # check the data has been updated since last update
        if self.bUpdate and self.sURL != "" and datetime.datetime.now() > updateTime and \
            self.postdata["name"] != "" and \
            self.bNewData:
            
            try:
                self.jsondump = json.dumps(self.postdata).encode('utf8')
                req = request.Request(self.sURL, data=self.jsondump, headers={'content-type': 'application/json'})
                response = request.urlopen(req)
                self.bNewData = False
                self.lastUpdateTime = datetime.datetime.now()
                logger.info("BrewFather: " + self.postdata["temp"] +"C, " + self.postdata["gravity"] + "SG, " + self.postdata["aux_temp"] +"C, " + self.lastUpdateTime.strftime("%d.%m.%Y %H:%M:%S"))
            except:
                logger.error("Exception posting to Brewfather: "+str(self.getLastJSON()))
        else:
            logger.debug("Update parameters:\nbUpdate = "+str(self.bUpdate)+"\nsUrl = "+self.sURL+"\npostdata.Name = "+self.postdata["name"] + \
                "\npostdata.temp = "+self.postdata["temp"]+"\npostdata.gravity = "+self.postdata["gravity"] + "\npostdata.aux_temp = "+self.postdata["aux_temp"] + \
                        "\nupdateTime = "+updateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                            "\nlastUpdateTime = "+self.lastUpdateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                               "\nCurrent Time = "+datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))


    # Read class parameters from configuration ini file.
    # Format:
    # [BrewFather]
    # Update = False
    # UpdateURL = http://log.brewfather.net/stream?id=xxxxxxxx
    # UpdateIntervalSeconds = 1800
    def _readConf(self):

        try:
            if os.path.isfile(CONFIGFILE) == False:
                logger.error("BrewFather configuration file is not valid: "+CONFIGFILE)

            ini = configparser.ConfigParser()
            ini.read(CONFIGFILE)

            if 'BrewFather' in ini:
                logger.debug("Reading BrewFather config")
        
                config = ini['BrewFather']
                
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
                
                if config["Update"] != "":
                    self.bUpdate = strtobool(config.get("Update"))
                else:
                    raise Excpetion
                if config["UpdateURL"] != "":
                    self.sURL = config.get("UpdateURL")
                else:
                    raise Exception

                try:
                    if config["UpdateIntervalSeconds"] != "":
                        if int(config["UpdateIntervalSeconds"]) >= MINIMUM_INTERVAL:
                            self.interval = int(config.get("UpdateIntervalSeconds"))
                        else:
                            logger.warning("Brewfather update interval cannot be less than 15min; using 900s")
                            self.interval = MINIMUM_INTERVAL
                    else:
                        raise Exception
                except:
                    logger.warning("Error reading Brewfather update interval; using 900s")
                    self.interval = MINIMUM_INTERVAL

                try:
                    if config["Device"] != "":
                        self.postdata["name"] = config["Device"]
                    else:
                        raise Exception
                except:
                    self.postdata["name"] = "Fermonitor"
                    

        except:
            self.bUpdate = False
            logger.warning("Problem read from configuration file: "+CONFIGFILE+". Updating BrewFather.app is disabled until configuration fixed. It could take a minute for updated values in config file to be used.")
            print("[BrewFather]\nUpdate = "+str(self.bUpdate)+"\nUpdateURL = "+self.sURL+"\nUpdateIntervalSeconds = "+str(self.interval))
            
        logger.debug("BrewFather config:\n[BrewFather]\nUpdate = "+str(self.bUpdate)+"\nUpdateURL = "+self.sURL+"\nUpdateIntervalSeconds = "+str(self.interval))
