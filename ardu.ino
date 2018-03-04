int sensorValue = 0; // value read from the pot
byte lb;
byte hb;

void setup()
{
    // initialize serial communications at 115200 bps:
    Serial.begin(115200);
}

void loop()
{
    // read A0:
    sensorValue = analogRead(A0);
    // shift sample by 3 bits, and select higher byte
    hb = highByte(sensorValue << 3);
    // set 3 most significant bits and send out
    Serial.write(hb | 0b11100000);
    // select lower byte and clear 3 most significant bits
    lb = (lowByte(sensorValue)) & 0b00011111;
    // set bits 5 and 6 and send out
    Serial.write(lb | 0b01100000);
    delay(12);
}