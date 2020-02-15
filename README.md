# fermonitor
Homebrew Fermentation Controller 

Setup includes Arduino with 3 sensor probes (beer, fridge, internal controller), 2 relays switchs for powering cooling device (fridge) and heating device (heating pad), 2 LED in addition to in-build Arduino's LED.  The Arduino sketch is located in subdiretory of project.

The Arduino with sketch can be controlled over serial USB by sending following commands:

"h" or "H" -> turn on heating<p>
"c" or "C" -> turn on cooling<p>
"o" or "O" -> turn off heating and cooling<p>
"?" -> request state and temperatures<p>

Arduino is connected RaspberryPi via USB and communication between the two is over this serial interface. RaspberryPi receives the following updates from the Arduino which are handled by controller.py. The enclosed class runs in own thread reading the data.

"C:-" -> Cooling turned off<p>
"C:+" -> Cooling turned on<p>
"H:-" -> Heating turned off<p>
"H:+" -> Heating turned on<p>
"B:N" -> Reporting temperature of beer, N, in celcius<p>
"F:N" -> Reporting temperature of fridge, N, in celcius<p>
"S:N" -> Reporting gap to safe temperture limit inside the control box, N, in celcius<p>
   
tilt.py has code for reading data temperature and specific gravity from Tilt Hydrometer (https://tilthydrometer.com/). The tilt class runs in own thread and reads own section of configuration file, fermonitor.ini. Code is based on tiltV1.py code found at following URL and utilizes blescan.py found on the same page
https://www.instructables.com/id/Reading-a-Tilt-Hydrometer-With-a-Raspberry-Pi/. I followed instructions on this page: https://kvurd.com/blog/tilt-hydrometer-ibeacon-data-format/ Ran "sudo systemctl daemon-reload" followed by "sudo systemctl restart bluetooth" to get "sudo hcitool lescan" to run. I found Tilt from list by first running the command and then tilting the Tilt to see what device is added to the list. It did not have label "Tilt" for easy identification.

brewfather.py contains code for updating JSON data to https://brewfather.app/. The brewfather class runs in own thread and reads own section of configuration file, fermonitor.ini.

fermonitor.py is the main app and starts the various support threads (controller, chamber, tilt, brewfather). file is responsible for collecting data from various sources pass to brewfather class for updating remote service.

interface.py controls LCD to show temperatures and specific gravity and a motion sensor for turning on LCD when motion is detected. 

I run the app by "sudo python3 fermonitor.py &> output.log &" and then monitor the log using "tail -f output.log". CSV can be copied locally at any time to use and the settings in fermonitor.ini can be updated as needed while program is running.  
