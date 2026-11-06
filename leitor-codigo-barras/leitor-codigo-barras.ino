const byte SENSOR = 2;
const byte LED = 8;
const byte BUZZER = 9;

bool ultimoEstado = HIGH;

void setup() {
  pinMode(SENSOR, INPUT);
  pinMode(LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  Serial.begin(9600);
}

void loop() {
  bool estado = digitalRead(SENSOR);

  // Dispara apenas quando um objeto aparece
  if (ultimoEstado == HIGH && estado == LOW) {
    Serial.println("1");

    efeitoScanner();
  }
  ultimoEstado = estado;
}

void efeitoScanner() {

  // Primeiro bipe
  digitalWrite(LED, HIGH);
  tone(BUZZER, 2200);  // 2200 Hz
  delay(55);

  digitalWrite(LED, LOW);
  noTone(BUZZER);
  delay(35);

  // Segundo bipe (ligeiramente mais agudo)
  digitalWrite(LED, HIGH);
  tone(BUZZER, 2700);
  delay(45);

  digitalWrite(LED, LOW);
  noTone(BUZZER);
  delay(40);

  // Pisca mais uma vez
  digitalWrite(LED, HIGH);
  delay(50);
  digitalWrite(LED, LOW);
}