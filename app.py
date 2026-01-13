import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import pandas as pd
import plotly.graph_objects as go
import queue
import threading
import random
import numpy as np

# FIX: Import this to silence the "missing ScriptRunContext" warning
from streamlit.runtime.scriptrunner import add_script_run_ctx

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="KINTO Live Monitor", page_icon="📡", layout="wide")

st.title("📡 KINTO: Real-Time Patient Monitor")

# --- SIDEBAR: CLOUD SIMULATOR ---
st.sidebar.header("🔧 Debug / Demo")
use_simulator = st.sidebar.checkbox("☁️ Enable Cloud Simulator", value=False, help="Generate dummy data from this server so the dashboard works without a physical device.")

# --- SESSION STATE INITIALIZATION ---
if "data_log" not in st.session_state:
    st.session_state["data_log"] = []

if "data_queue" not in st.session_state:
    st.session_state["data_queue"] = queue.Queue()

# --- MQTT SETUP ---
BROKER = "broker.hivemq.com"
TOPIC = "kinto/wearable/v1/data"

# 1. RECEIVER CALLBACKS (The Dashboard Logic)
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        userdata.put(payload)
    except Exception as e:
        print(f"Error parsing MQTT: {e}")

# 2. SENDER LOGIC (The "Device" Simulation)
def run_simulation():
    # FIX: Explicitly use VERSION1 to handle the DeprecationWarning
    sim_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    try:
        sim_client.connect(BROKER, 1883, 60)
    except:
        return
        
    t_step = 0
    while True:
        # Check if user turned off simulation
        if not st.session_state.get("sim_active", False):
            break
            
        t_step += 0.1
        
        # Generate Data (Same logic as device.py)
        hr = int(75 + 5 * np.sin(t_step * 0.5) + random.uniform(-2, 2))
        spo2 = round(98 + random.uniform(-1, 1), 1)
        if spo2 > 100: spo2 = 100
        temp = round(36.8 + 0.2 * np.sin(t_step * 0.1) + random.uniform(-0.1, 0.1), 2)
        
        # Random Fall Trigger
        is_fall = False
        acc_svm = 1.0 + random.uniform(-0.1, 0.1)
        if random.random() < 0.02: # 2% chance
            acc_svm = 4.5
            is_fall = True
            
        payload = {
            "timestamp": time.time(),
            "hr": hr, "spo2": spo2, "temp": temp,
            "svm": round(acc_svm, 2), "fall_detected": is_fall
        }
        
        sim_client.publish(TOPIC, json.dumps(payload))
        time.sleep(0.5)

# --- START/STOP SIMULATOR THREAD ---
if use_simulator:
    if not st.session_state.get("sim_active"):
        st.session_state["sim_active"] = True
        
        # Start the thread
        t = threading.Thread(target=run_simulation, daemon=True)
        
        # FIX: Attach the Streamlit context to the thread
        add_script_run_ctx(t)
        
        t.start()
        st.sidebar.success("✅ Simulation Running")
else:
    st.session_state["sim_active"] = False

# --- START MQTT LISTENER (ONCE) ---
if "mqtt_client" not in st.session_state:
    # FIX: Explicitly use VERSION1 to handle the DeprecationWarning
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, userdata=st.session_state["data_queue"])
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_start()
        st.session_state["mqtt_client"] = client
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")

# --- DASHBOARD UI LOOP ---
placeholder = st.empty()

while True:
    while not st.session_state["data_queue"].empty():
        new_data = st.session_state["data_queue"].get()
        st.session_state["data_log"].append(new_data)
        if len(st.session_state["data_log"]) > 100:
            st.session_state["data_log"].pop(0)

    with placeholder.container():
        if len(st.session_state["data_log"]) > 0:
            latest = st.session_state["data_log"][-1]
            unique_id = time.time()
            
            # Status Banner
            if latest["fall_detected"] or latest["svm"] > 3.0:
                st.error(f"🚨 FALL DETECTED! Impact Force: {latest['svm']} G")
            else:
                st.success(f"✅ Patient Status: Stable | Source: {'Simulated' if use_simulator else 'Live Device'}")

            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("❤️ Heart Rate", f"{latest['hr']} BPM", f"{latest['hr']-75}")
            m2.metric("💧 SpO2", f"{latest['spo2']} %")
            m3.metric("🌡️ Temp", f"{latest['temp']} °C")
            m4.metric("📉 Impact", f"{latest['svm']} G")

            # Charts
            df = pd.DataFrame(st.session_state["data_log"])
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Vitals")
                fig_v = go.Figure()
                fig_v.add_trace(go.Scatter(y=df["hr"], name='HR', line=dict(color='#FF4B4B')))
                fig_v.add_trace(go.Scatter(y=df["spo2"], name='SpO2', line=dict(color='#00CC96')))
                fig_v.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10), template="plotly_dark")
                st.plotly_chart(fig_v, use_container_width=True, key=f"vitals_{unique_id}")

            with c2:
                st.subheader("Motion (SVM)")
                fig_a = go.Figure()
                fig_a.add_trace(go.Scatter(y=df["svm"], name='G-Force', line=dict(color='#FFA15A')))
                fig_a.add_hline(y=3.0, line_dash="dash", line_color="red")
                fig_a.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10), template="plotly_dark")
                st.plotly_chart(fig_a, use_container_width=True, key=f"acc_{unique_id}")

        else:
            st.info("⏳ Waiting for data... Turn on 'Cloud Simulator' in the sidebar to demo!")
            
    time.sleep(0.5)