# 🚑 KINTO: IoT Fall Detection & Vitals Monitor

A real-time IoT prototype for elderly care. This system uses an MQTT architecture to transmit simulated sensor data (Heart Rate, SpO2, Accelerometer) from a wearable device to a cloud dashboard.

## 🏗️ Architecture
- **Device (`device.py`):** Simulates a smart band. Generates sensor data and detects falls using a Signal Vector Magnitude (SVM) algorithm. Publishes JSON packets to MQTT.
- **Dashboard (`app.py`):** A Streamlit web app that subscribes to the MQTT topic, visualizes live vitals, and triggers Red Alerts when a fall is detected.
- **Protocol:** MQTT (via HiveMQ public broker).

## 🚀 How to Run

### 1. Start the Dashboard (The Nurse Station)
pip install -r requirements.txt
streamlit run app.py

### 2. Start the Wearable Device (The Patient)
Open a new terminal and run:

python device.py

You will see data being transmitted in the terminal, and the Dashboard will update in real-time.

🛠️ Tech Stack
Python 3.x

Paho-MQTT (IoT Communication)

Streamlit (Real-time Dashboard)

Plotly (Live Charting)