# fermonitor
Homebrew Fermentation Controller 

Python3 code to read temperature and specific gravity from Tilt Hydrometer (https://tilthydrometer.com/) and temperature from 1-wire sensor; log the data to local CSV and to https://brewfather.app/ and will control relay switch for powering refridgerator for mainatining consistent fermentation temperature.

Functionality is configured using fermonitor.ini

tilt.py code is based on tiltV1.py code found at following URL and utilizes blescan.py found on the same page
https://www.instructables.com/id/Reading-a-Tilt-Hydrometer-With-a-Raspberry-Pi/

1-wire temperature sensor code is based on worksheet 3 of https://github.com/CamJam-EduKit/EduKit2. Changed /boot/config.txt to include "dtoverlay=w1-gpio" then ran the 2 modprobe commands found in onewiretemp.py

I followed instructions on this page: https://kvurd.com/blog/tilt-hydrometer-ibeacon-data-format/
Ran "sudo systemctl daemon-reload" followed by "sudo systemctl restart bluetooth" to get "sudo hcitool lescan" to run. I found Tilt from list by first running the command and then tilting the Tilt to see what device is added to the list. It did not have label "Tilt" for easy identification.
