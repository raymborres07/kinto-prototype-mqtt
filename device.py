import time
import json
import random
import numpy as np
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
BROKER = "broker.hivemq.com"  # Public test broker
PORT = 1883
TOPIC = "kinto/wearable/v1/data"

# --- SIMULATION STATE ---
# We keep track of "time" to create realistic wave patterns
t_step = 0

def generate_sensor_data():
    global t_step
    t_step += 0.1
    
    # 1. Heart Rate (BPM): Normal 60-100, oscillating slightly
    heart_rate = int(75 + 5 * np.sin(t_step * 0.5) + random.uniform(-2, 2))
    
    # 2. SpO2 (%): Oxygen saturation (usually stable 95-100%)
    spo2 = round(98 + random.uniform(-1, 1), 1)
    if spo2 > 100: spo2 = 100
    
    # 3. Body Temperature (Celsius): 36.5 - 37.5
    temp = round(36.8 + 0.2 * np.sin(t_step * 0.1) + random.uniform(-0.1, 0.1), 2)
    
    # 4. Fall Sensor (Accelerometer SVM)
    # Simulating a sudden spike if a random trigger happens
    is_fall = False
    acc_svm = 1.0 + random.uniform(-0.1, 0.1) # Normal 1G gravity
    
    # Randomly trigger a "Fall" event (1 in 100 chance per tick)
    if random.random() < 0.01:
        acc_svm = 4.5 # Massive 4.5G spike
        is_fall = True
        print("⚠️ FALL EVENT TRIGGERED!")

    # Payload Packet
    payload = {
        "timestamp": time.time(),
        "hr": heart_rate,
        "spo2": spo2,
        "temp": temp,
        "svm": round(acc_svm, 2),
        "fall_detected": is_fall
    }
    return payload

# --- MQTT SETUP ---
client = mqtt.Client()

print(f"Connecting to {BROKER}...")
try:
    client.connect(BROKER, PORT, 60)
    print("✅ Connected! Simulating KINTO Band...")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    exit()

# --- MAIN LOOP ---
while True:
    data = generate_sensor_data()
    
    # Convert dict to JSON string
    message = json.dumps(data)
    
    # Publish
    client.publish(TOPIC, message)
    
    print(f"[TX] HR:{data['hr']} | SpO2:{data['spo2']}% | Temp:{data['temp']}C | SVM:{data['svm']}G")
    
    # Send data every 0.5 seconds
    time.sleep(0.5)