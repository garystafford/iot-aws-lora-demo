/*
  Description: Transmits Arduino Nano 33 BLE Sense sensor telemetry over LoRaWAN,
               including temperature, humidity, barometric pressure, and color,
               using REYAX RYLR896 transceiver modules
               http://reyax.com/wp-content/uploads/2020/01/Lora-AT-Command-RYLR40x_RYLR89x_EN.pdf
  Author: Gary Stafford
*/

#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>
#include <Arduino_APDS9960.h>

const int UPDATE_FREQUENCY = 5000;     // update frequency in ms
const float CALIBRATION_FACTOR = -4.0; // temperature calibration factor (Celsius)
const int ADDRESS = 116;
const int NETWORK_ID = 6;
const String PASSWORD = "92A0ECEC9000DA0DCF0CAAB0ABA2E0EF";
const String DELIMITER = "|";

String uid = "";

void setup()
{
  Serial.begin(9600);

  Serial1.begin(115200); // default baud rate of module is 115200
  delay(1000);           // wait for LoRa module to be ready

  // get unique transceiver id to identify iot device on network
  Serial1.print((String)"AT+UID?\r\n");
  uid = Serial1.readString();
  uid.replace("+UID=", ""); // trim off '+UID=' at start of line
  uid.replace("\r\n", ""); // trim off CR/LF at end of line

  // needs all need to be same for receiver and transmitter
  Serial1.print((String)"AT+ADDRESS=" + ADDRESS + "\r\n");
  delay(200);
  Serial1.print((String)"AT+NETWORKID=" + NETWORK_ID + "\r\n");
  delay(200);
  Serial1.print("AT+CPIN=" + PASSWORD + "\r\n");
  delay(200);
  Serial1.print("AT+CPIN?\r\n"); // confirm password is set

  if (!HTS.begin())
  { // initialize HTS221 sensor
    Serial.println("Failed to initialize humidity temperature sensor!");
    while (1);
  }

  if (!BARO.begin())
  { // initialize LPS22HB sensor
    Serial.println("Failed to initialize pressure sensor!");
    while (1);
  }

  // avoid bad readings to start bug
  // https://forum.arduino.cc/index.php?topic=660360.0
  BARO.readPressure();
  delay(1000);

  if (!APDS.begin())
  { // initialize APDS9960 sensor
    Serial.println("Failed to initialize color sensor!");
    while (1);
  }
}

void loop()
{
  updateReadings();
  delay(UPDATE_FREQUENCY);
}

void updateReadings()
{
  float temperature = getTemperature(CALIBRATION_FACTOR);
  float humidity = getHumidity();
  float pressure = getPressure();
  int colors[4];
  getColor(colors);

  String payload = buildPayload(temperature, humidity, pressure, colors);
  Serial.println("Payload: " + payload); // display the payload for debugging

  Serial1.print(payload); // send the payload over LoRaWAN WiFi

  displayResults(temperature, humidity, pressure, colors); // display the results for debugging
}

float getTemperature(float calibration)
{
  return HTS.readTemperature() + calibration;
}

float getHumidity()
{
  return HTS.readHumidity();
}

float getPressure()
{
  return BARO.readPressure();
}

void getColor(int c[])
{
  // check if a color reading is available
  while (!APDS.colorAvailable())
  {
    delay(5);
  }

  int r, g, b, a;
  APDS.readColor(r, g, b, a);
  c[0] = r;
  c[1] = g;
  c[2] = b;
  c[3] = a;
}

void displayResults(float t, float h, float p, int c[])
{
  Serial.println((String)"UID: " + uid);
  Serial.print("Temperature: ");
  Serial.println(t);
  Serial.print("Humidity: ");
  Serial.println(h);
  Serial.print("Pressure: ");
  Serial.println(p);
  Serial.print("Color (r, g, b, a): ");
  Serial.print(c[0]);
  Serial.print(", ");
  Serial.print(c[1]);
  Serial.print(", ");
  Serial.print(c[2]);
  Serial.print(", ");
  Serial.println(c[3]);
  Serial.println("----------");
}

String buildPayload(float t, float h, float p, int c[])
{
  String readings = "";
  readings += uid;
  readings += DELIMITER;
  readings += t;
  readings += DELIMITER;
  readings += h;
  readings += DELIMITER;
  readings += p;
  readings += DELIMITER;
  readings += c[0];
  readings += DELIMITER;
  readings += c[1];
  readings += DELIMITER;
  readings += c[2];
  readings += DELIMITER;
  readings += c[3];

  String payload = "";
  payload += "AT+SEND=";
  payload += ADDRESS;
  payload += ",";
  payload += readings.length();
  payload += ",";
  payload += readings;
  payload += "\r\n";

  return payload;
}
