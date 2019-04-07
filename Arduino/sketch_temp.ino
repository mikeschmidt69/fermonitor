/********************************************************************/
// First we include the libraries
#include <OneWire.h> 
#include <DallasTemperature.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

/*********************************************************************/
// Constants

// digital pins
const int ONE_WIRE_BUS = 2;
const int MOTION = 3;
const int COOL_LED = 7; // pin for LED showing Relay is on
const int HEAT_LED = 8; // pin for LED showing Relay is on
const int HEAT_RELAY = 9; // pin used for heating relay switch
const int COOL_RELAY = 10; // pin used for heating relay switch
const int ARDUINO_LED = 13; // In-build LED pin on the Arduino 

// analogue pins
const int INTERNAL_TEMP = A6; // Assigning analog pin A5 to variable 'sensor'

// other constants
const int SAFE_INTERNAL_TEMP = 60; // safe internal operating temperature

/********************************************************************/
// global variables
bool bHeat = false; // inidcates if system should heat
bool bCool = false; // indicates if system should cool
bool bHeatOn = false; // indicates if system is heating
bool bCoolOn = false; // indicates if system is cooling

unsigned long onDelay = 600000; // minimum delay in milliseconds between powering on/off sockets (default 10min)
unsigned long millsHeatOff = 0; // when heating was turned off, milliseconds since Arduino was started
unsigned long millsCoolOff = 0; // when cooling was turned off, milliseconds since Arduino was started
unsigned long offDuration = 0; // used to calculate how much longer before on delay has expired

float fInternalTemp = 0; // internal temperature in C
float fBeerTemp = 0; // beer temperature in C
float fFridgeTemp = 0; // beer temp in C

int motion_state = LOW;

// Strings used to display information on LCD and over serial connection
String sBeerTemp;
String sFridgeTemp;
String sInternalTemp;
String sFridgeState;

//
int iLCD_TextCount = 0; // controls which temperature is displayed as UI cycles through
int iLCD_OnCount = 0; // counts how many loop cycles before display turns off

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
}

void loop() {
  // turn on in-build LED to show operation is bing done
  digitalWrite (ARDUINO_LED,HIGH); // Turn ON the LED on pin 13
  
  // read internal temperature and determine if safe to operate
  fInternalTemp = analogRead(INTERNAL_TEMP);
  fInternalTemp = fInternalTemp * 0.48828125;
  sInternalTemp = String("I:"+String(fInternalTemp)); //Reading the value from sensor
  Serial.print(sInternalTemp+"\n");

  sensors.requestTemperatures(); // Send the command to get temperature readings
  fBeerTemp = sensors.getTempCByIndex(0);
  if (fBeerTemp > -100 and fBeerTemp < 100) {
    sBeerTemp = String("B:" + String(fBeerTemp));
    Serial.print(sBeerTemp+"\n");
  }
  
  fFridgeTemp = sensors.getTempCByIndex(1);
  if (fFridgeTemp > -100 and fBeerTemp < 100) {
    sFridgeTemp = String("F:" + String(fFridgeTemp));
    Serial.print(sFridgeTemp+"\n");
  }

  motion_state = digitalRead(MOTION);   // read sensor value
  if (motion_state == HIGH) {           // check if the sensor is HIGH
    iLCD_OnCount = 0;
  }
  if (iLCD_OnCount < 6) {
    lcd.backlight();
    iLCD_OnCount += 1;
  }
  else {
    lcd.noBacklight();
  }

  handleSerial();           // read commands from serial interface

  // If safe internal temperature exceeded, override all commands and turn off all relays, LEDs. LCD will timeout after a minute
  if (fInternalTemp > SAFE_INTERNAL_TEMP) {
    bCool = false;
    bHeat = false;
  }

  lcd.clear();
  lcd.setCursor(0,0);

  if (iLCD_TextCount == 0) {
    lcd.print(sBeerTemp);
    iLCD_TextCount += 1;
  }
  else if (iLCD_TextCount == 1) {
    lcd.print(sFridgeTemp);    
    iLCD_TextCount += 1;
  }
  else {
    lcd.print(sInternalTemp);    
    iLCD_TextCount = 0;
  }

  handleHeatingCooling();   // control heating/cooling and report to serial interface

  if (fInternalTemp > SAFE_INTERNAL_TEMP) {
    lcd.setCursor(0,1);
    lcd.print("INT TEMP TOO HOT");  
  }

  delay (100); //Wait for 1sec
  digitalWrite (ARDUINO_LED, LOW); //Turn OFF the in-build LED
  delay(2000); // Wait a second so user has chance to read LCD
}

void handleHeatingCooling() {
  sFridgeState = "";
  if (bHeat == true and bHeatOn == false) {
    
    // need to check ok with delay
    if (millsHeatOff == 0) {
      offDuration = onDelay;
    }
    else {
      offDuration = millis() - millsHeatOff;
    }
    
    if (offDuration < onDelay) {
      Serial.print("h:");
      Serial.print(onDelay - offDuration);
      Serial.print("\n");
      sFridgeState = sFridgeState + "h:" + String(onDelay-offDuration) + " ";
    }
    else {
      digitalWrite (HEAT_RELAY, HIGH);
      digitalWrite (HEAT_LED,HIGH);
      bHeatOn = true;
      Serial.println("H:+");
      sFridgeState = sFridgeState + "H:+ ";
    }
  }
  else if (bHeat == false and bHeatOn == true) {
    digitalWrite (HEAT_RELAY, LOW);
    digitalWrite (HEAT_LED,LOW);
    bHeatOn = false;
    millsHeatOff = millis();
    Serial.println("H:-");
  }
  else if (bHeat == true and bHeatOn == true) {
      sFridgeState = sFridgeState + "H: ";
  }
  
  if(bCool == true and bCoolOn == false) {
    // need to check ok with delay
    
    if (millsCoolOff == 0) {
      offDuration = onDelay;
    }
    else {
      offDuration = millis() - millsCoolOff;
    }
    
    if (offDuration < onDelay) {
      Serial.print("c:");
      Serial.print(onDelay - offDuration);
      Serial.print("\n");
      sFridgeState = sFridgeState + "c:" + String(onDelay-offDuration) + " ";
    }
    else {
      digitalWrite (COOL_RELAY, HIGH);
      digitalWrite (COOL_LED,HIGH);
      bCoolOn = true;
      Serial.println("C:+");
      sFridgeState = sFridgeState + "C:+ ";
    }
  }
  else if (bCool == false and bCoolOn == true) {
    digitalWrite (COOL_RELAY, LOW);
    digitalWrite (COOL_LED,LOW);
    bCoolOn = false;
    millsCoolOff = millis();
    Serial.println("C:-");
  }
  else if (bCool == true and bCoolOn == true) {
      sFridgeState = sFridgeState + "C: ";
  }

  lcd.setCursor(0,1);
  lcd.print(sFridgeState);  
}

// read commands from serial connection
void handleSerial() {
  while (Serial.available() > 0) {
    char incomingCharacter = Serial.read();
    switch (incomingCharacter) {
      case 'h':
      case 'H':
        if (bHeat == false) {
          bHeat = true;
          Serial.println("h:+");
        }
        if (bCool == true){
          bCool = false;
          Serial.println("c:-");
        }
        break;
      case 'c':
      case 'C':
        if (bCool == false){
          bCool = true;
          Serial.println("c:+");
        }
        if (bHeat == true){
          bHeat = false;
          Serial.println("h:-");
        }
        break;
      case 'o':
      case 'O':
        if (bHeat == true){
          bHeat = false;
          Serial.println("h:-");
        }
        if (bCool == true) {
          bCool = false;
          Serial.println("c:-");
        }
        break;
      case '+':
        onDelay += 60000;
        Serial.print("D:");
        Serial.print(onDelay);
        Serial.print("\n");
        break;
      case '-':
        if (onDelay >= 60000){
          onDelay -= 60000;
        }
        Serial.print("D:");
        Serial.print(onDelay);
        Serial.print("\n");
        break;
      case '=':
        Serial.print("D:");
        Serial.print(onDelay);
        Serial.print("\n");
        break;
    }
  }
}
