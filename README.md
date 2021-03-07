# fermonitor
Homebrew Fermentation Controller

Setup includes Raspberry Pi with 2 1-wire temperature sensor probes (beer, chamber), 2 relays switches for powering cooling device (fridge) and heating device (heating pad), 2 LED, 2x16 LCD and motion sensor for turning on/off display. Look at architecture.pdf for overview.

fermonitor.py is the main app and starts the various support threads (chamber, tilt, brewfather and interface). Implementation is responsible for collecting data from various chamber and passing to brewfather class for updating remote service and to interface for displaying to LCD. Implementation also provides web interface using Flask (xxx.xxx.xxx.xxx:5000)

tilt.py has code for reading data temperature and specific gravity from Tilt Hydrometer (https://tilthydrometer.com/). The tilt class runs in own thread and reads own section of configuration file, fermonitor.ini. Code is based on tiltV1.py code found at following URL and utilizes blescan.py found on the same page
https://www.instructables.com/id/Reading-a-Tilt-Hydrometer-With-a-Raspberry-Pi/. I followed instructions on this page: https://kvurd.com/blog/tilt-hydrometer-ibeacon-data-format/ Ran "sudo systemctl daemon-reload" followed by "sudo systemctl restart bluetooth" to get "sudo hcitool lescan" to run. I found Tilt from list by first running the command and then tilting the Tilt to see what device is added to the list. It did not have label "Tilt" for easy identification.

brewfather.py contains code for updating JSON data to https://brewfather.app/. The brewfather class runs in own thread and reads own section of configuration file, fermonitor.ini.

interface.py controls LCD to show temperatures and specific gravity and a motion sensor for turning on LCD when motion is detected. 

I run the app by "sudo python3 fermonitor.py &" or including similar line to /etc/rc.local to start at boot-up of RPi. I then monitor the fermonitor.log

I can monitor the fermentation on BrewFather but I also use port-forwarding on home router to provide remote access to the Flask web interface that provides more insight on current state of controller. Port-forwarding also allows SSH access to the RPi for editing .ini files or in worse case rebooting RPi.

Most of the files are configured with their own .ini
fermonitor.py -> fermonitor.ini
- message level
- if chamber is controlled by wired temperature or from Tilt
- color of Tilt

chamber.py -> chamber.ini
- message level
- temperatures to maintain
- dates the various temperature targets are active
- buffers, scale factors and adjuments to control the chamber
- delay heating / cooling devices can be turned on

brewfather.py -> brewfather.ini
- message level
- update URL to sending data to your BrewFather account
- update interval
- device name used in BrewFather
- boolean determining if remote service is updated

tilt.py -> tilt.py
- message level
- update interval
- Bluetooth ID
