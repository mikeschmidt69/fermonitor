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

logger = logging.getLogger('brewfather')
logger.setLevel(logging.INFO)

MINIMUM_INTERVAL = 900 # minimum number of seconds the BrewFather.app can be updated (i.e. 15min)

# Brewfather class used for passing brew related logging data to BrewFather.app so it can be displayed for batch connected in the app.
class BrewFather (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self, configFile):
        threading.Thread.__init__(self)
    
        if os.path.isfile(configFile) == False:
            raise IOError("BrewFather configuration file is not valid: "+configFile)
        self.configFile = configFile        # config file containing class properties
        self.bUpdate = False                # flag indicating if BrewFather should be updated with data or not; useful for debugging
        self.sURL = ""                      # custom URL provided in the BrewFather app where data should be sent in JSON format
        self.interval = MINIMUM_INTERVAL    # interval in seconds for updating BrewFather; BrewFather rejects updates more often than 15min
        self.stopThread = True              # flag used for stopping the background thread that updates BrewFather
        self.dataTime = datetime.datetime.now()

        # Data accepted by BrewFather; OK if some values are ""; not sure what happens if fields are missing.
        self.postdata = {
            "name": "",
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

        # Keeps track of last time BrewFather was updated to know when it can be updated again
        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=self.interval) # last time the tilt was read
     
    # Starts the background thread for updating BrewFather with lastest data. First re-reads configuration file to check
    # if any of the settings have changed
    def run(self):
        logger.info("Starting BrewFather Logging")
        self.stopThread = False
        while self.stopThread != True:
            self._readConf(self.configFile)
            self._update() 
            time.sleep(60)
        logger.info("BrewFather Monitoring Stopped")


    # stops the background thread updating data coming from configured Tilt
    def stop(self):
        self.stopThread = True

    # sets the data currently supported by my system, will expand with system
    def setData(self, name, temp, gravity, dataTime):
        self.postdata["name"] = str(name)
        self.postdata["temp"] = str(round(float(temp),1))
        self.postdata["gravity"] = "{:5.3f}".format(round(float(gravity),3))
        self.dataTime = dataTime

    # method for connecting and updating BrewFather.app
    def _update(self):
        updateTime = self.lastUpdateTime + datetime.timedelta(seconds=self.interval)

        # check update flag is enabled
        # check Brewfather URL is defined
        # check the updated interval has elapsed since last update
        # check relevant data for the system is valid
        # check the data has been updated since last update
        if self.bUpdate and self.sURL != "" and datetime.datetime.now() > updateTime and \
            self.postdata["name"] != "" and self.postdata["temp"] != "" and self.postdata["gravity"] != "" and \
            self.dataTime > self.lastUpdateTime:
            
            params = json.dumps(self.postdata).encode('utf8')
            req = request.Request(self.sURL, data=params, headers={'content-type': 'application/json'})
            response = request.urlopen(req)
            logger.debug("BrewFather: " + self.postdata["temp"] +" : " + self.postdata["gravity"])
            self.lastUpdateTime = datetime.datetime.now()

        else:
            logger.debug("Update paramters:\nbUpdate = "+str(self.bUpdate)+"\nsUrl = "+self.sURL+"\npostdata.Name = "+self.postdata["name"] + \
                "\npostdata.temp = "+self.postdata["temp"]+"\npostdata.gravity = "+self.postdata["gravity"] + \
                    "\ndataTime = "+self.dataTime.strftime("%d.%m.%Y %H:%M:%S") + \
                        "\nupdateTime = "+updateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                            "\nlastUpdateTime = "+self.lastUpdateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                               "\nCurrent Time = "+datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))


    # Read class parameters from passed configuration ini file.
    # Format:
    # [BrewFather]
    # Update = False
    # UpdateURL = http://log.brewfather.net/stream?id=CdetYZYm9XNP1R
    # UpdateIntervalSeconds = 1800
    def _readConf(self, configFile):

        try:
            if os.path.isfile(configFile) == False:
                logger.error("BrewFather configuration file is not valid: "+configFile)

            ini = configparser.ConfigParser()
            ini.read(configFile)

            if 'BrewFather' in ini:
                logger.debug("Reading BrewFather config")
        
                config = ini['BrewFather']
                
                try:
                    if config["MessageLevel"] == "DEBUG":
                        logger.setLevel(logging.DEBUG)
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
                if config["UpdateIntervalSeconds"] != "":
                    if int(config["UpdateIntervalSeconds"]) >= 900:
                        self.interval = int(config.get("UpdateIntervalSeconds"))
                    else:
                        logger.warning("Brewfather update interval cannot be less than 15min; using 900s")
                        self.interval = MINIMUM_INTERVAL
                else:
                    raise Exception

        except:
            self.bUpdate = False
            logger.warning("Problem read from configuration file: "+configFile+". Updating BrewFather.app is disabled until configuration fixed. \
                It could take a minute for updated values in config file to be used.")
            print("[BrewFather]\nUpdate = "+str(self.bUpdate)+"\nUpdateURL = "+self.sURL+"\nUpdateIntervalSeconds = "+str(self.interval))
            
        logger.debug("BrewFather config:\n[BrewFather]\nUpdate = "+str(self.bUpdate)+"\nUpdateURL = "+self.sURL+"\nUpdateIntervalSeconds = "+str(self.interval))
