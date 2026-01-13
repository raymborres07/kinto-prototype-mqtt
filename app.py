import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import pandas as pd
import plotly.graph_objects as go
import queue

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="KINTO Live Monitor", page_icon="📡", layout="wide")

st.title("📡 KINTO: Real-Time Patient Monitor")
st.markdown("Listening for live MQTT packets from **Topic: `kinto/wearable/v1/data`**")

# --- INITIALIZATION ---
# 1. Initialize Session State for the data history
if "data_log" not in st.session_state:
    st.session_state["data_log"] = []

# 2. Create a global Queue for thread-safe communication
# The callback (background thread) puts data here.
# The main loop (Streamlit thread) reads from here.
if "data_queue" not in st.session_state:
    st.session_state["data_queue"] = queue.Queue()

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("kinto/wearable/v1/data")

def on_message(client, userdata, msg):
    try:
        # Parse JSON
        payload = json.loads(msg.payload.decode())
        
        # Put the data into the Queue (Thread-Safe)
        userdata.put(payload)
        
    except Exception as e:
        print(f"Error parsing MQTT: {e}")

# --- START MQTT CLIENT ---
# We store the client in session_state to prevent re-connecting on every refresh
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(userdata=st.session_state["data_queue"]) # Pass queue as userdata
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect("broker.hivemq.com", 1883, 60)
        client.loop_start() # Start background thread
        st.session_state["mqtt_client"] = client
        st.success("✅ Connected to MQTT Broker!")
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")

# --- DASHBOARD UI LOOP ---
placeholder = st.empty()

# This loop updates the UI independently of the MQTT thread
while True:
    # 1. EMPTY THE QUEUE INTO SESSION STATE
    # We check if the background thread dropped off any new packages
    while not st.session_state["data_queue"].empty():
        new_data = st.session_state["data_queue"].get()
        st.session_state["data_log"].append(new_data)
        
        # Keep log short (last 100 entries)
        if len(st.session_state["data_log"]) > 100:
            st.session_state["data_log"].pop(0)

    # 2. RENDER UI
    with placeholder.container():
        if len(st.session_state["data_log"]) > 0:
            latest = st.session_state["data_log"][-1]
            
            # Unique ID for chart keys to prevent DuplicateElementId error
            unique_id = time.time()
            
            # ALERT BANNER
            if latest["fall_detected"] or latest["svm"] > 3.0:
                st.error(f"🚨 FALL DETECTED! Impact Force: {latest['svm']} G")
            else:
                st.success("✅ Patient Status: Stable")

            # METRICS
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("❤️ Heart Rate", f"{latest['hr']} BPM", f"{latest['hr']-75}")
            m2.metric("💧 SpO2", f"{latest['spo2']} %")
            m3.metric("🌡️ Temp", f"{latest['temp']} °C")
            m4.metric("📉 Impact (SVM)", f"{latest['svm']} G")

            # CHARTS
            df = pd.DataFrame(st.session_state["data_log"])
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Heart Rate & SpO2")
                fig_vitals = go.Figure()
                fig_vitals.add_trace(go.Scatter(y=df["hr"], mode='lines', name='Heart Rate', line=dict(color='#FF4B4B')))
                fig_vitals.add_trace(go.Scatter(y=df["spo2"], mode='lines', name='SpO2', line=dict(color='#00CC96')))
                fig_vitals.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10), template="plotly_dark")
                
                # KEY FIX IS HERE:
                st.plotly_chart(fig_vitals, use_container_width=True, key=f"vitals_{unique_id}")
                
            with c2:
                st.subheader("Accelerometer (SVM)")
                fig_acc = go.Figure()
                fig_acc.add_trace(go.Scatter(y=df["svm"], mode='lines', name='Force (G)', line=dict(color='#FFA15A', width=2)))
                fig_acc.add_hline(y=3.0, line_dash="dash", line_color="red")
                fig_acc.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10), template="plotly_dark")
                
                # KEY FIX IS HERE:
                st.plotly_chart(fig_acc, use_container_width=True, key=f"acc_{unique_id}")
        else:
            st.info("⏳ Waiting for data stream... Check if device.py is running!")
            
    # Short sleep to prevent CPU spiking
    time.sleep(0.5)