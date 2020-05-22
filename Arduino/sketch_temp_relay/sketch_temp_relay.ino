/********************************************************************/
// Sketch to read temperature from 3 wired temperature sensors (beer, fridge and internal controller temp).
// Based on the temperature readings and outside control from a host the sketch can turn on/off electrical relays.
// Relays are meant to be connected to a heating source and cooling source. When the related heating/cooling
// relays are closed a corresponding colored LED (BLUE-cooling; RED-heating) is illuminated. 
//
// The sketch has default values and can function independently with the exception of controlling the electrical
// relays. The sketch is controlled over a serial (USB) interface with single character commands (documented later
// in sketch. The sktech then reports the status to a connected host over the same serial interface.
/********************************************************************/
// Included the libraries
#include <OneWire.h> 
#include <DallasTemperature.h>
#include <Wire.h>



/*********************************************************************/
// Constants

// digital pins
const int ONE_WIRE_BUS = 2;
const int COOL_LED = 7; // pin for LED showing Relay is on
const int HEAT_LED = 8; // pin for LED showing Relay is on
const int HEAT_RELAY = 10; // pin used for heating relay switch
const int COOL_RELAY = 9; // pin used for heating relay switch
const int ARDUINO_LED = 13; // In-build LED pin on the Arduino 

// analogue pins
const int INTERNAL_TEMP = A6; // Assigning analog pin A5 to variable 'sensor'

// other constants
const int SAFE_INTERNAL_TEMP = 60; // safe internal operating temperature
const int NUM_TEMP_AVG = 10;  // number of temperature readings to average 
const unsigned long WD_TIME = (60UL); // watchdog interval 10min
/********************************************************************/
// global variables
bool bHeat = false; // inidcates if system should heat
bool bCool = false; // indicates if system should cool
bool bSafe = false; // indicates if system has overheated

unsigned long secLastSerialUpdate = 0UL; // last time serial was updated

float fInternalTemp[NUM_TEMP_AVG]; // internal temperature in C
float fBeerTemp[NUM_TEMP_AVG]; // beer temperature in C
float fFridgeTemp[NUM_TEMP_AVG]; // beer temp in C

int iTempNum = 0; // position in all of the temp arrays

/********************************************************************/
// Setup a oneWire instance to communicate with any OneWire devices  
// (not just Maxim/Dallas temperature ICs) 
OneWire oneWire(ONE_WIRE_BUS); 
/********************************************************************/
// Pass our oneWire reference to Dallas Temperature. 
DallasTemperature sensors(&oneWire);
/********************************************************************/

// Sets up Arduino logic
void setup() {
   // start serial port 
  Serial.begin(19200);

  // initialize pins as OUTPUT
  pinMode (ARDUINO_LED, OUTPUT); 
  pinMode (HEAT_RELAY, OUTPUT); 
  pinMode (HEAT_LED, OUTPUT); 
  pinMode (COOL_RELAY, OUTPUT); 
  pinMode (COOL_LED, OUTPUT); 
  
  pinMode (INTERNAL_TEMP, INPUT); // Configuring sensor pin as input 
    
  // Start up the library 
  sensors.begin(); 
  delay(5000);
}

// loops through reading the sensor and reports data to user through serial connection
// turns on LCD based on motion sensor and updates connected LCD with latest results
void loop() {

  float fTemp = 0.0f;
  
  // read temperatures and place to array for averaging
  
  fTemp = analogRead(INTERNAL_TEMP);
  fInternalTemp[iTempNum] = fTemp * 0.48828125;

  sensors.requestTemperatures(); // Send the command to get temperature readings
  fTemp = sensors.getTempCByIndex(0);
  if (fTemp > -55 and fTemp < 125) {
    fBeerTemp[iTempNum] = fTemp;
  }
  
  fTemp = sensors.getTempCByIndex(1);
  if (fTemp > -55 and fTemp < 125) {
    fFridgeTemp[iTempNum] = fTemp;
  }
  iTempNum += 1;
  if (iTempNum >= NUM_TEMP_AVG){
    iTempNum = 0;
  }

  // Check safe internal temperature and Watchdog  
  if ((getTemp(fInternalTemp) > SAFE_INTERNAL_TEMP) || (millis()/1000 - secLastSerialUpdate > WD_TIME )) {
    bSafe = false;
    heat(false);
    cool(false);
  }
  else {
    bSafe = true;
  }

  // read and process commands from serial interface a§§§§§§§§§§§§§§§§§§11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111                                                                                                                                                                                                                                                                                                                         
  handleSerial();

  // turn on in-build LED to show operation is bing done
  digitalWrite (ARDUINO_LED,HIGH); // Turn ON the LED on pin 13
  delay (90); //Wait for so internal LED is off a short pause
  digitalWrite (ARDUINO_LED, LOW); //Turn OFF the in-build LED
}


// read commands from (USB) serial connection and set appropriate flag/variables influencing how the system works
void handleSerial() {
  while (Serial.available() > 0) {
    char incomingCharacter = Serial.read();
    
    switch (incomingCharacter) {

      // user requests heating to be turned on; if cooling is on, it will also be turned off
      case 'h':
      case 'H':
        secLastSerialUpdate = millis()/1000;
        heat(true);
        break;

      // user requests cooling to be turned on; if heating is on, it will also be turned off
      case 'c':
      case 'C':
        secLastSerialUpdate = millis()/1000;
        cool(true);
        break;

      // user requests both heating and cooling to be turned off
      case 'o':
      case 'O':
        secLastSerialUpdate = millis()/1000;
        heat(false);
        cool(false);
        break;

      case '?':
        secLastSerialUpdate = millis()/1000;
        Serial.println("S:"+String((SAFE_INTERNAL_TEMP - getTemp(fInternalTemp)),1));
        Serial.println("B:"+String(getTemp(fBeerTemp),1));
        Serial.println("F:"+String(getTemp(fFridgeTemp),1));

        if (bHeat) {
          Serial.println("H:+");
        }
        else {
          Serial.println("H:-");
        }
        if (bCool) {
          Serial.println("C:+");
        }
        else {
          Serial.println("C:-");
        }
        break;
        
      default:
        break;
    }
  }
}

void heat(bool _on) {
  if (_on && bSafe) {
    bHeat = true;
    digitalWrite (HEAT_RELAY,HIGH);
    digitalWrite (HEAT_LED,HIGH);              
    cool(false);
  }
  else {
    bHeat = false;
    digitalWrite (HEAT_RELAY,LOW);
    digitalWrite (HEAT_LED,LOW);        
  }
}

void cool(bool _on) {
  if (_on & bSafe) {
    bCool = true;
    digitalWrite (COOL_RELAY,HIGH);
    digitalWrite (COOL_LED,HIGH);    
    heat(false);
  }
  else {
    bCool = false;
    digitalWrite (COOL_RELAY,LOW);
    digitalWrite (COOL_LED,LOW);        
  }
}

// returns average temperature of values stored in array
float getTemp( float tempArray[] ) {
  float temp = 0.0f;
  
  for (int i=0; i < NUM_TEMP_AVG; i++) {
    temp += tempArray[i];
  }
  return temp/NUM_TEMP_AVG;
}
