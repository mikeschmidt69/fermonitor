fermonitor is configured with separate ini files associated with various Python files of the program. The program is made this way so it is easy to reuse blocks of code and the corresponding configuration. Logging can also be set at different levels for different files for debugging. As each file uses a different [section] name all of the sections could be put to one file. The CONFIGFILE variable of each file would need to be modified to reference this shared file.

Below is reference to each of the configuration files, their variables and short description. All configuration files except fermonitor.ini are repeatedly read so values can be changes while program is running.

Any text editor can be used to edit the configuration files. There is also a command line tool, ini_editor.py, that can be used.

###########################################################
fermonitor.ini

[Fermonitor]
TiltColor = 
ChamberControl = WIRE
MessageLevel = INFO

TiltColor inidicates the color of the Tilt hydrometer being used. If the value is empty then Tilt hydrometer will not be used. 

ChamberControl is either WIRE (default) or TILT and indicates which sensor should provide temperature to control behaviour of Chamber.

MessageLevel specifies the message level of logs that is output (ERROR, WARNING, INFO or DEBUG) from the fermonitor.py and settings.py files. If attribute does not exist or equals any other value it defaults to INFO level.

###########################################################
chamber.ini

[Chamber]
MessageLevel = INFO
Dates = 26/03/2019 12:00:00,28/09/2019 13:00:00,14/10/2019 14:00:00,20/04/2020 14:00:00
Temps = 18,21,0
BeerTemperatureBuffer = 0.2
ChamberScaleBuffer = 5.0

MessageLevel specifies the message level of logs that is output (ERROR, WARNING, INFO or DEBUG) from chamber.py. If attribute does not exist or equals any other value it defaults to INFO level.

Dates indicate the starting time for controlling the fermentation temperature, when target temperatures should change and an additional time when fermentation control should end. There should always be one more date (end time) than number of temperatures. Dates should be formated as DD/MM/YYYY HH:MM:SS and separated by a comma.

Temps are the target temperatures the controller is trying to reach after the corresponding date has passed.

BeerTemperatureBuffer is the temperature range +/- from the target that must be exceeded before the controller turns on heating or cooling to bring beer temperature closer to target.

ChamberScaleBuffer is the scale factor that the difference of the chamber temperature and target temperature must be within for the controller to turn on the heating or cooling. A larger value allows the chamber to more quickly change the temperature of the beer but also might trigger the temperature of the beero to overshoot the target. Having too small of a value may cause the beer temperture to remain offset above or below the target and requires more time for making a step in the beer temperature.

###########################################################
controller.ini

[Controller]
MessageLevel = INFO
OnDelay = 60
BeerTempAdjust = 0.0
ChamberTempAdjust = 0.0

MessageLevel specifies the message level of logs that is output (ERROR, WARNING, INFO or DEBUG) from controller.py. If attribute does not exist or equals any other value it defaults to INFO level.

OnDelay sets the duration in minutes the chamber's heating or cooling must remain off before it can be turned on again. This is to prevent cycling the compressor of refridgerator too often.

BeerTempAdjust is for adjusting (correcting) the wired beer sensor's temperature reading. 

ChamberTempAdjust is for adjusting (correcting) the wired chamber sensor's temperature reading. 

###########################################################
tilt.ini

[BLACK]
MessageLevel = INFO
BluetoothDeviceId = 0
UpdateIntervalSeconds = 120

The section [BLACK] should correspond with the color of the Tilt and that specified in fermonitor.ini

MessageLevel specifies the message level of logs that is output (ERROR, WARNING, INFO or DEBUG) from tilt.py. If attribute does not exist or equals any other value it defaults to INFO level.

BluetoothDeviceId is the Bluetooth device ID of Raspberry Pi that is used to receive the Bluetooth beacons from the Tilt

UpdateIntervalSeconds is the interval data is read from the Tilt. The minimum value is 60s

###########################################################
brewfather.ini

[BrewFather]
MessageLevel = INFO
UpdateURL = http://log.brewfather.net/stream?id=xxxxxxxxx
Device = test
UpdateIntervalSeconds = 900
Update = True

MessageLevel specifies the message level of logs that is output (ERROR, WARNING, INFO or DEBUG) from brewfather.py. If attribute does not exist or equals any other value it defaults to INFO level.

UpdateURL is the url specified in brewfather.app settings for sending data to the online application

Device is the name used when reporting values to brewfather.app

UpdateIntervalSeconds is the time interval for updating brewfather.app with most recent data. All data between intervals is not used. The interval must be 900s (15min) or larger otherwise brewfather.app will ignore the posted data

Update is a boolean (True or False) flag indicating if brewfather.app should be update with data or not
