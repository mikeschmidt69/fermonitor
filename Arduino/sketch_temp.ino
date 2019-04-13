/********************************************************************/
// First we include the libraries
#include <OneWire.h> 
#include <DallasTemperature.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define SECS_PER_MIN  (60UL)
#define MILLIS_PER_SEC  (1000UL)
#define numberOfSeconds(_time_) ((_time_ / MILLIS_PER_SEC) % SECS_PER_MIN)  
#define numberOfMinutes(_time_) (((_time_ / MILLIS_PER_SEC) / SECS_PER_MIN) % SECS_PER_MIN) 

/*********************************************************************/
// Constants

// digital pins
const int ONE_WIRE_BUS = 2;
const int MOTION = 3;
const int COOL_LED = 7; // pin for LED showing Relay is on
const int HEAT_LED = 8; // pin for LED showing Relay is on
const int HEAT_RELAY = 10; // pin used for heating relay switch
const int COOL_RELAY = 9; // pin used for heating relay switch
const int ARDUINO_LED = 13; // In-build LED pin on the Arduino 

// analogue pins
const int INTERNAL_TEMP = A6; // Assigning analog pin A5 to variable 'sensor'

// other constants
const int SAFE_INTERNAL_TEMP = 60; // safe internal operating temperature
const int DISPLAY_ON_SECONDS = 60; // number of seconds display stays on due to motion sensor
const int SCREEN_ON_SECONDS = 3; // number of seconds each display screen of data is shown
const int SERIAL_UPDATE_RATE_SECONDS = 5;
const int NUM_TEMP_AVG = 10;

/********************************************************************/
// global variables
bool bHeat = false; // inidcates if system should heat
bool bCool = false; // indicates if system should cool
bool bHeatOn = false; // indicates if system is heating
bool bCoolOn = false; // indicates if system is cooling
bool bDebug = false; // indicates if extra output should be sent to serial (E.g., echoing recieved requests)

unsigned long minHeatOff = 0; // when heating was turned off, minutes since Arduino was started defaults to delay so heat can be immediately turned on
unsigned long minCoolOff = 0; // when cooling was turned off, minutes since Arduino was started defaults to delay so cooling can be immediately turned on
unsigned long minHeatOn = 0; // when heating was turned on, minutes since Arduino was started
unsigned long minCoolOn = 0; // when cooling was turned on, minutes since Arduino was started

unsigned long secDisplayOn = 0; // when display was turned on
unsigned long secLastSerialUpdate = 0; // last time serial was updated
unsigned long secLastLcdUpdate = 0; // last time scrren was updated

float fInternalTemp[NUM_TEMP_AVG]; // internal temperature in C
float fBeerTemp[NUM_TEMP_AVG]; // beer temperature in C
float fFridgeTemp[NUM_TEMP_AVG]; // beer temp in C

int onDelay = 10; // minimum delay in minutes between powering on/off sockets (default 10min)
int motion_state = LOW;
int iLCD_Screen = 0; // controls which screen to show on LCD
int iTempNum = 0; // position in temp array

/********************************************************************/
// Setup a oneWire instance to communicate with any OneWire devices  
// (not just Maxim/Dallas temperature ICs) 
OneWire oneWire(ONE_WIRE_BUS); 
/********************************************************************/
// Pass our oneWire reference to Dallas Temperature. 
DallasTemperature sensors(&oneWire);
/********************************************************************/

// I2C pin declaration
LiquidCrystal_I2C lcd(0x27, 2, 1, 0, 4, 5, 6, 7, 3, POSITIVE);


// Sets up Arduino logic
void setup() {
   // start serial port 
  Serial.begin(9600);

  // initialize pins as OUTPUT
  pinMode (ARDUINO_LED, OUTPUT); 
  pinMode (HEAT_RELAY, OUTPUT); 
  pinMode (HEAT_LED, OUTPUT); 
  pinMode (COOL_RELAY, OUTPUT); 
  pinMode (COOL_LED, OUTPUT); 
  
  pinMode (INTERNAL_TEMP, INPUT); // Configuring sensor pin as input 
  pinMode(MOTION, INPUT);    // initialize sensor as an input
  
  lcd.begin(16,2); // Defining 16 columns and 2 rows of LCD display
    
  // Start up the library 
  sensors.begin(); 

  minHeatOff = numberOfMinutes(millis()) - onDelay;
  minCoolOff = numberOfMinutes(millis()) - onDelay;
  secLastLcdUpdate = numberOfSeconds(millis());
  secLastSerialUpdate = numberOfSeconds(millis()) - SERIAL_UPDATE_RATE_SECONDS;
}

// loops through reading the sensor and reports data to user through serial connection
// turns on LCD based on motion sensor and updates connected LCD with latest results
void loop() {

  // turn on in-build LED to show operation is bing done
  digitalWrite (ARDUINO_LED,HIGH); // Turn ON the LED on pin 13

  unsigned long curSecond = numberOfSeconds(millis());

  // read commands from serial interface
  handleSerial();

  float fTemp = 0.0f;
  
  // read temperatures
  
  fTemp = analogRead(INTERNAL_TEMP);
  fInternalTemp[iTempNum] = fTemp * 0.48828125;

  sensors.requestTemperatures(); // Send the command to get temperature readings
  fTemp = sensors.getTempCByIndex(0);
  if (fTemp > -100 and fTemp < 100) {
    fBeerTemp[iTempNum] = fTemp;
  }
  
  fTemp = sensors.getTempCByIndex(1);
  if (fTemp > -100 and fTemp < 100) {
    fFridgeTemp[iTempNum] = fTemp;
  }
  iTempNum += 1;
  if (iTempNum >= NUM_TEMP_AVG){
    iTempNum = 0;
  }

  // If safe internal temperature exceeded, override all commands and turn off all relays, LEDs. LCD will timeout after a minute
  
  if (getTemp(fInternalTemp) > SAFE_INTERNAL_TEMP) {
    bCool = false;
    bHeat = false;
  }

  // turn on/off heating cooling as needed
  handleHeatingCooling();   

  // Turn ON LCD if motion is detected and start displayON time
  motion_state = digitalRead(MOTION);   // read sensor value
  if (motion_state == HIGH) {           // check if the sensor is HIGH to turn on LCD
    lcd.backlight();
    secDisplayOn = curSecond;
  }

  // check if display ON timeout expired and update LCD or turn OFF LCD backlight 
  if ((curSecond - secDisplayOn) < DISPLAY_ON_SECONDS) {
    updateLCD();
  }
  else {
    lcd.clear();
    lcd.noBacklight();
  }

  // handle updating serial interface
  if ((curSecond - secLastSerialUpdate) > SERIAL_UPDATE_RATE_SECONDS) {
   outputSerial();
   secLastSerialUpdate = curSecond;
  }

  delay (100); //Wait for so internal LED is on a short pause
  digitalWrite (ARDUINO_LED, LOW); //Turn OFF the in-build LED
  delay (100); //Wait for so internal LED is on a short pause
}

// Based on current state of flags and forced delays determine if heating or cooling should be turned ON/OFF and changes state of related pins
void handleHeatingCooling() {

  unsigned long curTimeMin = numberOfMinutes(millis());

  // heat is off and requested on
  if (!bHeatOn and bHeat) {
    
    // need to check if heat off more than delay    
    if ( (curTimeMin - minHeatOff) >= onDelay ) {
      digitalWrite (HEAT_RELAY,HIGH);
      digitalWrite (HEAT_LED,HIGH);
      bHeatOn = true;
      minHeatOn = curTimeMin;
    }
  }
  // heat on and requested to be turned off
  else if (bHeatOn and !bHeat) {
    digitalWrite (HEAT_RELAY,LOW);
    digitalWrite (HEAT_LED,LOW);
    bHeatOn = false;
    minHeatOff = curTimeMin;
  }
  
  // cooling is off and requested on
  if (!bCoolOn and bCool) {
    
    // need to check if cooling off more than delay    
    if ( (curTimeMin - minCoolOff) >= onDelay ) {
      digitalWrite (COOL_RELAY,HIGH);
      digitalWrite (COOL_LED,HIGH);
      bCoolOn = true;
      minCoolOn = curTimeMin;
    }
  }
  // cooling on and requested to be turned off
  else if (bCoolOn and !bCool) {
    digitalWrite (COOL_RELAY,LOW);
    digitalWrite (COOL_LED,LOW);
    bCoolOn = false;
    minCoolOff = curTimeMin;
  }
}

// Reports the current state back to user over serial connection
// D:# Minimum delay used for turning on heating/cooling after it has been turned off
// I:# Intenral temperature of control box
// B:# Temperature of beer
// F:# Temperature of fridge
// h:# Heating requested but time remains (# = milliseconds) before it can be turned ON
// H:# Heating has been on for # milliseconds
// c:# Cooling requested but time remains (# = milliseconds) before it can be turned ON
// C:# Cooling has been on for # milliseconds
// O:# Neither heating or cooling is ON
// ?:aaa Debugging information
void outputSerial() {
  unsigned long coolOffDuration = 0; // used to calculate how much longer before on delay has expired
  unsigned long heatOffDuration = 0; // used to calculate how much longer before on delay has expired

  unsigned long curTime = numberOfMinutes(millis());

  if(bDebug) {
    Serial.println("?:Time/"+String(curTime)+"min");
  }
  
  Serial.println("D:"+String(onDelay));

  Serial.println("I:"+String(getTemp(fInternalTemp),1));
  Serial.println("B:"+String(getTemp(fBeerTemp),1));
  Serial.println("F:"+String(getTemp(fFridgeTemp),1));

  if (bHeat) {
    if (bHeatOn) {
      Serial.println("H:"+String(curTime - minHeatOn));

      if(bDebug) {
        Serial.println("?:Heat ON Time/"+String(minHeatOn)+"min");
      }    
    }
    else {
      heatOffDuration = curTime - minHeatOff;

      Serial.println("h:"+String(onDelay - heatOffDuration));
      if(bDebug) {
        Serial.println("?:Heat OFF Time/"+String(minHeatOff)+"min");
      }    
    }
  }  
  if (bCool) {
    if (bCoolOn) {
      Serial.println("C:"+String(curTime - minCoolOn));
      if(bDebug) {
        Serial.println("?:Cool ON Time/"+String(minCoolOn)+"min");
      }    
    }
    else {
      coolOffDuration = curTime - minCoolOff;
      
      Serial.println("c:"+String(onDelay - coolOffDuration));
      if(bDebug) {
        Serial.println("?:Cool OFF Time/"+String(minCoolOff)+"min");
      }    
    }
  }

  if (!bHeatOn and !bCoolOn) {
    if(bDebug) {
      Serial.println("?:Cool OFF Time/"+String(minCoolOff)+"min");
      Serial.println("?:Heat OFF Time/"+String(minHeatOff)+"min");
    }    
    if ((curTime-minCoolOff) < (curTime-minHeatOff)) {
      Serial.println("O:"+String(curTime - minCoolOff));
    }
    else {
      Serial.println("O:"+String(curTime - minHeatOff));
    }
  }
}

// Reports the current state to LCD screen
// I:# Intenral temperature of control box
// B:# Temperature of beer
// F:# Temperature of fridge
// h:# Heating requested but time remains (# = milliseconds) before it can be turned ON
// H:# Heating has been on for # milliseconds
// c:# Cooling requested but time remains (# = milliseconds) before it can be turned ON
// C:# Cooling has been on for # milliseconds
// O:# Neither heating or cooling is ON
void updateLCD() {
  unsigned long coolOffDuration = 0; // used to calculate how much longer before on delay has expired
  unsigned long heatOffDuration = 0; // used to calculate how much longer before on delay has expired

  unsigned long curTime = numberOfMinutes(millis());
  unsigned long curTimeSec = numberOfSeconds(millis());

  // determine which screen to show
  if (curTimeSec - secLastLcdUpdate > SCREEN_ON_SECONDS) {
    iLCD_Screen += 1;
    if (iLCD_Screen > 2) {
      iLCD_Screen = 0;
    }
    secLastLcdUpdate = curTimeSec;
  }

  String sTemp = "";
  if (iLCD_Screen == 0) {
    sTemp = "I:"+String(getTemp(fInternalTemp),1)+"C";
  }
  else if (iLCD_Screen == 1) {
    sTemp = "B:" + String(getTemp(fBeerTemp),1)+"C";
  }
  else if (iLCD_Screen == 2) {
    sTemp = "F:" + String(getTemp(fFridgeTemp),1)+"C";    
  }


  String sFridgeState = "";

  if (bHeat and !bHeatOn) {
    
    // need to check ok with delay
    if (minHeatOff == 0) {
      heatOffDuration = onDelay;
    }
    else {
      heatOffDuration = curTime - minHeatOff;
    }
    
    if (heatOffDuration < onDelay) {
      sFridgeState = "h:" + String(onDelay-heatOffDuration)+"min";
    }
  }
  else if (bHeat and bHeatOn) {
    sFridgeState = "H:" + String(curTime - minHeatOn)+"min";
  }
  
  if(bCool and !bCoolOn) {
    // need to check ok with delay
    
    if (minCoolOff == 0) {
      coolOffDuration = onDelay;
    }
    else {
      coolOffDuration = curTime - minCoolOff;
    }
    
    if (coolOffDuration < onDelay) {
      sFridgeState = "c:" + String(onDelay-coolOffDuration)+"min";
    }
  }
  else if (bCool and bCoolOn) {
    sFridgeState = "C:" + String(curTime - minCoolOn)+"min";
  }

  if ((!bHeatOn and !bHeat) and (!bCoolOn and !bCool)) {
    sFridgeState = "O:";
    if ( (curTime-minCoolOff) < (curTime-minHeatOff) ) {
      sFridgeState = sFridgeState + String(curTime - minCoolOff)+"min";
    }
    else {
      sFridgeState = sFridgeState + String(curTime - minHeatOff)+"min";
    }
  }

  lcd.clear();
  
  lcd.setCursor(0,0);
  lcd.print(sTemp);  
  
  lcd.setCursor(0,1);
  if (getTemp(fInternalTemp) > SAFE_INTERNAL_TEMP) {
    lcd.print("INT TEMP TOO HOT");  
  }
  else {
    lcd.print(sFridgeState);  
  }

}

// read commands from (USB) serial connection and set appropriate flag/variables influencing how the system works
void handleSerial() {
  while (Serial.available() > 0) {
    char incomingCharacter = Serial.read();
    switch (incomingCharacter) {

      // user requests heating to be turned on; if cooling is on, it will also be turned off
      case 'h':
      case 'H':
        if (!bHeat) {
          bHeat = true;
          if (bDebug) {
            Serial.println("h:+");            
          }
        }
        if (bCool){
          bCool = false;
          if (bDebug) {
            Serial.println("c:-");            
          }
        }
        break;

      // user requests cooling to be turned on; if heating is on, it will also be turned off
      case 'c':
      case 'C':
        if (!bCool){
          bCool = true;
          if (bDebug) {
            Serial.println("c:+");            
          }
        }
        if (bHeat){
          bHeat = false;
          if (bDebug) {
            Serial.println("h:-");            
          }
        }
        break;

      // user requests both heating and cooling to be turned off
      case 'o':
      case 'O':
        if (bHeat){
          bHeat = false;
          if (bDebug) {
            Serial.println("h:-");            
          }
        }
        if (bCool) {
          bCool = false;
          if (bDebug) {
            Serial.println("c:-");            
          }
        }
        break;

       // user requestesf the delay for turning on a device after turning off to be increased by 1 minute
      case '+':
        onDelay += 1;
        if (bDebug) {
          Serial.println("D:"+String(onDelay));
        }
        break;

      // user requestesf the delay for turning on a device after turning off to be decreased by 1 minute
      case '-':
        if (onDelay >= 1){
          onDelay -= 1;
        }
        if (bDebug) {
          Serial.println("D:"+String(onDelay));
        }
        break;
        
      // user requested current delay for turning on a device (heating or cooling) once it has been turned off
      case '=':               
          Serial.println("D:"+String(onDelay));
        break;

      // turn on/off verbose messages
      case '?':  
        bDebug = !bDebug;             
        if (bDebug){
          Serial.println("?:+");        
        }
        else {
          Serial.println("?:-");        
        }
        break;
    }
  }
}

float getTemp( float tempArray[] ) {
  float temp = 0.0f;
  
  for (int i=0; i < NUM_TEMP_AVG; i++) {
    temp += tempArray[i];
  }
  return temp/NUM_TEMP_AVG;
}
