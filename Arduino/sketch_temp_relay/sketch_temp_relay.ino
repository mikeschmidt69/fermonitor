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
const int RESET = 4;
const int COOL_LED = 7; // pin for LED showing Relay is on
const int HEAT_LED = 8; // pin for LED showing Relay is on
const int HEAT_RELAY = 11; // pin used for heating relay switch
const int COOL_RELAY = 12; // pin used for heating relay switch
const int ARDUINO_LED = 13; // In-build LED pin on the Arduino 

// analogue pins
const int INTERNAL_TEMP = A6; // Assigning analog pin A5 to variable 'sensor'

// other constants
const int SAFE_INTERNAL_TEMP = 60; // safe internal operating temperature
const int NUM_TEMP_AVG = 100;  // number of temperature readings to average 
const int COMM_INTERVAL = 60; // client watchdog interval of one minute, if no input is received for interval it is assumed there is no control and heating/cooling should stop

/********************************************************************/
// global variables
bool bHeat = false; // inidcates if system should heat
bool bCool = false; // indicates if system should cool
bool bSafe = false; // indicates if system has overheated

unsigned long secLastSerialUpdate = 0UL; // last time serial was updated

float fInternalTemp; // internal temperature in C
float fBeerTemp; // beer temperature in C
float fFridgeTemp; // beer temp in C

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
  digitalWrite(RESET, HIGH);
  digitalWrite (HEAT_RELAY, HIGH); 
  digitalWrite (COOL_RELAY, HIGH); 
  
   // start serial port 
  Serial.begin(19200);
  Serial.println("I:Starting");

  // initialize pins as OUTPUT
  pinMode (ARDUINO_LED, OUTPUT); 
  pinMode (HEAT_RELAY, OUTPUT); 
  pinMode (HEAT_LED, OUTPUT); 
  pinMode (COOL_RELAY, OUTPUT); 
  pinMode (COOL_LED, OUTPUT); 
  pinMode (RESET, OUTPUT);
  
  pinMode (INTERNAL_TEMP, INPUT); // Configuring sensor pin as input 
    
  // Start up the library 
  sensors.begin(); 
  delay(5000);
}

// loops through reading the sensor and reports data to user through serial connection
// turns on LCD based on motion sensor and updates connected LCD with latest results
void loop() {

   
  float fTemp = 0.0f;
  for (int i=0; i < NUM_TEMP_AVG; i++) {
    fTemp += analogRead(INTERNAL_TEMP) * 0.48828125;
  }
  fInternalTemp = fTemp/NUM_TEMP_AVG;


  fTemp = 0.0f;
  for (int i=0; i < NUM_TEMP_AVG; i++) {
    sensors.requestTemperatures(); // Send the command to get temperature readings
    fTemp += sensors.getTempCByIndex(0);
  }
  fBeerTemp = fTemp/NUM_TEMP_AVG;
  
  fTemp = 0.0f;
  for (int i=0; i < NUM_TEMP_AVG; i++) {
    sensors.requestTemperatures(); // Send the command to get temperature readings
    fTemp += sensors.getTempCByIndex(1);
  }
  fFridgeTemp = fTemp/NUM_TEMP_AVG;

  // Check if safe to operate; if not, reset
  bSafe = true;

  // Check serial connection is availalbe
  if (!Serial) {                                                
    bSafe = false;    
  }
  // if serial is available check additional failure modes for logging
  else {
    // Check safe internal temperature
    if (fInternalTemp > SAFE_INTERNAL_TEMP) {
      bSafe = false;
      Serial.println("W:Excessive Internal Temp +"+String((SAFE_INTERNAL_TEMP - fInternalTemp),1)+"C");
      Serial.flush();
    }
  
    // Check that client has communicated within COMM_INTERVAL interval
    if (millis()/1000 - secLastSerialUpdate > COMM_INTERVAL) {
      bSafe = false;         
      Serial.println("W:Excessive delay in client response");
      Serial.flush();
    }
  
    // Check that more than 24 hours has not passed
    if (millis()/1000/60/60 >= 24) {
      bSafe = false;
      Serial.println("W:One day operation exceeded");
      Serial.flush();
    }
  }
  
  // If not safe, turn off heat/cooling and reset
  if (!bSafe) {
    heat(false);
    cool(false);
    digitalWrite(RESET, LOW); // reset Arduino
  }
   
  // read and process commands from serial interface
  handleSerial();

  // turn on in-build LED to show operation is bing done
  digitalWrite (ARDUINO_LED,HIGH); // Turn ON the LED on pin 13
  delay (90); //Wait for so internal LED is off a short pause
  digitalWrite (ARDUINO_LED, LOW); //Turn OFF the in-build LED
}


// read commands from (USB) serial connection and set appropriate flag/variables influencing how the system works
void handleSerial() {
  int iCmdCharNum = 0; // tracks # of characters read over serial during this method call

  while (Serial.available() > 0) {
    char incomingCharacter = Serial.read();
    iCmdCharNum++;
//    Serial.println("I:"+String(incomingCharacter));
    
    switch (incomingCharacter) {

      // user requests heating to be turned on; if cooling is on, it will also be turned off
      case 'h':
      case 'H':
        if (iCmdCharNum == 1) {
          incomingCharacter = Serial.read();
          iCmdCharNum++;
          if (incomingCharacter == '\r' || incomingCharacter == '\n') {
            secLastSerialUpdate = millis()/1000;
            iCmdCharNum = 0;
            heat(true);
          }
        }
        break;

      // user requests cooling to be turned on; if heating is on, it will also be turned off
      case 'c':
      case 'C':
        if (iCmdCharNum == 1) {
          incomingCharacter = Serial.read();
          iCmdCharNum++;
          if (incomingCharacter == '\r' || incomingCharacter == '\n') {
            secLastSerialUpdate = millis()/1000;
            iCmdCharNum = 0;
            cool(true);
          }
        }
        break;

      // user requests both heating and cooling to be turned off
      case 'o':
      case 'O':
        if (iCmdCharNum == 1) {
          incomingCharacter = Serial.read();
          iCmdCharNum++;
          if (incomingCharacter == '\r' || incomingCharacter == '\n') {
            secLastSerialUpdate = millis()/1000;
            iCmdCharNum = 0;
            heat(false);
            cool(false);
          }
        }
        break;

      // user requests status
      case '?':
        if (iCmdCharNum == 1) {
          incomingCharacter = Serial.read();
          iCmdCharNum++;
          if (incomingCharacter == '\r' || incomingCharacter == '\n') {
            secLastSerialUpdate = millis()/1000;
            iCmdCharNum = 0;
            Serial.println("S:"+String((SAFE_INTERNAL_TEMP - fInternalTemp),1));
            Serial.println("B:"+String(fBeerTemp,1));
            Serial.println("F:"+String(fFridgeTemp,1));

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
          }
        }
        break;
      case '\n':
        iCmdCharNum = 0;
        break;
        
      // unknown input, turn off heating/cooling
      default:
        heat(false);
        cool(false);
//        Serial.println("W:Invalid input");    
      break;
    }
  }
}

void heat(bool _on) {
  if (_on && bSafe) {
    bHeat = true;
    digitalWrite (HEAT_RELAY,LOW);
    digitalWrite (HEAT_LED,HIGH);              
    cool(false);
    Serial.println("H:+");
  }
  else {
    bHeat = false;
    digitalWrite (HEAT_RELAY,HIGH);
    digitalWrite (HEAT_LED,LOW);        
    Serial.println("H:-");
  }
}

void cool(bool _on) {
  if (_on && bSafe) {
    bCool = true;
    digitalWrite (COOL_RELAY,LOW);
    digitalWrite (COOL_LED,HIGH);    
    heat(false);
    Serial.println("C:+");
  }
  else {
    bCool = false;
    digitalWrite (COOL_RELAY,HIGH);
    digitalWrite (COOL_LED,LOW);        
    Serial.println("C:-");
  }
}
