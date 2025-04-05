import os
import time
import threading
from fastapi import testclient
import requests
import fitbit
import streamlit as st
import sendgrid
import pandas as pd
import pyttsx3
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from phi.agent import Agent

load_dotenv()

## 1. Set up the environment
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_EMAIL = os.getenv("SENDGRID_EMAIL")
CAREGIVER_EMAIL = os.getenv("CAREGIVER_EMAIL")
FITBIT_REDIRECT_URI = os.getenv("FITBIT_REDIRECT_URI")
FITBIT_CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
FITBIT_CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
FITBIT_ACCESS_TOKEN = os.getenv("FITBIT_ACCESS_TOKEN")
FITBIT_REFRESH_TOKEN = os.getenv("FITBIT_REFRESH_TOKEN")

## GOBAL VARIABLES
health_data = {
    "Heartrate": [], "Blood pressure": [], "Glucose Levels": [], "Oxygen Saturation (SpO2%)": [], "Timestamp": [], "Device_id/User_id": []
}

safety_data = {
    "Movement Activity": [], "Impact Force Level": [], "Post Fall Inactivity Duration (Seconds)": [], "Location": [], "Timestamp": [], "Device_id/User_id": []
}

reminder_data = {
    "Reminder Type": [], "Scheduled Time": [], "Timestamp": [], "Device_id/User_id": []
}

alerts=[]
reminders=[]

# Initialize pyttsx3 engine
try:
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 150)  # Speed of speech
    tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
except Exception as e:
    print(f"Error initializing pyttsx3: {e}")
    tts_engine = None

# Initialize Fitbit client
fitbit_client = fitbit.Fitbit(
    FITBIT_CLIENT_ID,
    FITBIT_CLIENT_SECRET,
    redirect_uri=FITBIT_REDIRECT_URI
)

## LOAD DATASET
df = pd.read_csv("health_monitoring.csv")
df1 = pd.read_csv('safety_monitoring.csv')
df2= pd.read_csv('daily_reminder.csv')

## HEALTH TRACKER AGENT 

health_tracker = Agent(
    name="HealthCare Agent",
    role="Monitor health data from the dataset and send alerts to cargivers if thresholds are exceeded",
    instructions="""
    "Check Heart Rate (>100 bpm), Blood Pressure (>130/85 mmHg), Glucose (<70 or >140 mg/dL), SpO2 (<92%).",
    "Send email alerts for abnormalities.",
    "Update health_data for visualization.

    """
)

## SAFETY AGRNT 

safety_agent = Agent(
    name="Safety Agent",

    role="Simulate fall detection, unsual activities and send alerts to caregivers",
    instructions="""
    "Simulate fall detection every 10 seconds.",
    "Send email alerts if a fall is detected.",
    "Log alerts for visualization.

    """
)

## REMINDER AGENT 

reminder_agent = Agent(
    name = "Reminder Agent",
    role="Send reminders to the elderly individuals for medication, apointments, events, consultation etc.",
    instructions="""
    Generate voice reminders for the elderly individuals.
    "Send email reminders for appointments and medication schedules.",
    "Log reminders for visualization."
    """
)

## HEALTHCARE AGENT TASK
def healthcare_task():
    for i,row in df.iterrows():
        timestamp=row['Timestamp']
        device_id=row['Device_id/User_id']
        heart_rate=row['Heart Rate']
        blood_pressure=row['Blood pressure']
        glucose=row['Glucose Levels']
        spo2=row['Oxygen Saturation (SpO2%)']

        health_data.append({
            'Timestamp':timestamp,'Device_id/User_id':device_id,'Heart rate':heart_rate,'Blood pressure':blood_pressure,'Glucose Levels':glucose,'Oxygen Saturation (SpO2%)':spo2
        })

        alert_msg = ""
        if row['Heart Rate Below/Above Threshold (Yes/No)'] == 'Yes':
            alert_msg += f"Heart Rate Alert: {heart_rate}bpm at {timestamp} of {device_id}\n"
        if row['Blood Pressure Below/Above Threshold (Yes/No)'] == 'Yes':
            alert_msg += f"Blood Pressure Alert: {blood_pressure}mmHg at {timestamp} of {device_id}\n"
        if row['Glucose Below/Above Threshold (Yes/No)'] == 'Yes':
            alert_msg += f"Glucose Alert: {glucose}mg/dL at {timestamp} of {device_id}\n"
        if row['SpO2 Below/Above Threshold (Yes/No)'] == 'Yes':
            alert_msg += f"SpO2 Alert: {spo2}% at {timestamp} of {device_id}\n"

        if alert_msg:
            alert_msg= f"[{timestamp}] {alert_msg}"
            send_email_alert("Health Alert",alert_msg)
            alerts.append(alert_msg)
            st.session_state.alerts = alerts

        time.sleep(1)


## SAFETY AGENT TASK
def safety_task():
    for i,row in df1.iterrows():
        timestamp=row['Timestamp']
        device_id=row['Device_id/User_id']
        movement_activity=row['Movement Activity']
        impact_force_level=row['Impact Force Level']
        post_fall_inactivity_duration=row['Post-Fall Inactivity Duration (Seconds)']
        location=row['Location']

        safety_data.append({
            'Timestamp':timestamp,'Device_id/User_id':device_id,'Movement activity':movement_activity,'Impact force level':impact_force_level,'Post-Fall Inactivity Duration (Seconds)':post_fall_inactivity_duration,'location':location
        })

        safety_alert=[]
        if row['Fall Detected'] == 'Yes':
            safety_alert.append(f"Fall Detected: {movement_activity} on {location} at {timestamp} of {device_id}\n")
        if row['Alert Triggered'] == 'Yes':
            safety_alert.append(f"Alert Triggered: {location} at {timestamp} of {device_id}\n")
        if row['Caregiver Notified'] == 'No':
            safety_alert.append(f"Caregiver Notified: {location} at {timestamp} of {device_id}\n")

        if safety_alert:
            safety_alert=f"Fall detected on {location} at {timestamp} of {device_id}\n{safety_alert}"
            send_email_alert("Safety Alert",safety_alert)
            alerts.append(safety_alert)
            st.session_state.alerts = alerts

        time.sleep(10)

## REMINDER TASK    
def reminder_task():
    for i,row in df2.iterrows():
        timestamp=row['Timestamp']
        device_id=row['Device_id/User_id']
        reminder_type=row['Reminder Type']
        scheduled_time=row['Scheduled Time']

        reminder_data.append({
            'Timestamp':timestamp,'Device_id/User_id':device_id,'Reminder Type':reminder_type,'Scheduled Time':scheduled_time
        })

        reminder_alert=[]
        if row['Reminder Sent'] == 'No':
            reminder_alert.append(f"Reminder Sent: {reminder_type} at {scheduled_time} of {device_id}\n")

        if row['Acknowledged'] == 'No':
            reminder_alert.append(f"Acknowledged: {reminder_type} at {scheduled_time} of {device_id}\n")

        if reminder_alert:
            reminder_alert=f"[{timestamp}] {reminder_alert}"
            speak_reminder(reminder_alert)
            reminders.append(reminder_alert)
            st.session_state.reminders = reminders

        time.sleep(1)

## EMAIL ALERT FUNCTION
def send_email_alert(subject,message):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    email = Mail(
        from_email=SENDGRID_EMAIL,
        to_emails=CAREGIVER_EMAIL,
        subject=subject,
        plain_text_content=message
    )
    try:
        sg.send(email)
    except Exception as e:
        print(f"Error sending email: {e}")

# Speak reminders using pyttsx3
def speak_reminder(text):
    if tts_engine:
        tts_engine.say(text)
        tts_engine.runAndWait()
    else:
        print("TTS engine unavailable. Reminder not spoken.")


## STREAMLIT APP
def streamlit():
    st.title("Elderly Care Monitoring System")

# Initialize session state
    if "health_data" not in st.session_state:
        st.session_state.health_data = {
        "heart_rate": [], "blood_pressure": [], "glucose": [], "spo2": [], "timestamps": []
    }
    if "alerts" not in st.session_state:
        st.session_state.alerts = []
    if "reminders_log" not in st.session_state:
        st.session_state.reminders_log = []

    # Health Data Visualization
    st.subheader("Health Monitoring")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Heart Rate (bpm)")
        if st.session_state.health_data["heart_rate"]:
            st.line_chart(
            {"Heart Rate": st.session_state.health_data["heart_rate"]},
            x=st.session_state.health_data["timestamps"]
        )
        else:
            st.write("No data yet.")
            st.write("Glucose Levels (mg/dL)")
            if st.session_state.health_data["glucose"]:
                st.line_chart(
                {"Glucose": st.session_state.health_data["glucose"]},
                x=st.session_state.health_data["timestamps"]
            )
            else:
                st.write("No data yet.")
            with col2:
                st.write("Blood Pressure (mmHg)")
            if st.session_state.health_data["blood_pressure"]:
                st.line_chart(
                {"Blood Pressure": st.session_state.health_data["blood_pressure"]},
                x=st.session_state.health_data["timestamps"]
            )
            else:
                st.write("No data yet.")
                st.write("Oxygen Saturation (SpO2%)")
                if st.session_state.health_data["spo2"]:
                    st.line_chart(
                    {"SpO2": st.session_state.health_data["spo2"]},
                    x=st.session_state.health_data["timestamps"]
            )
                else:
                    st.write("No data yet.")
            with col2:
                st.write("Blood Pressure (mmHg)")
                if st.session_state.health_data["blood_pressure"]:
                    st.line_chart(
                    {"Blood Pressure": st.session_state.health_data["blood_pressure"]},
                    x=st.session_state.health_data["timestamps"]
            )
                else:
                    st.write("No data yet.")
                    st.write("Oxygen Saturation (SpO2%)")
                    if st.session_state.health_data["spo2"]:
                        st.line_chart(
                            {"SpO2": st.session_state.health_data["spo2"]},
                            x=st.session_state.health_data["timestamps"]
                        )
                    else:
                        st.write("No data yet.")        

    # Alerts Section
    st.subheader("Alerts")
    if st.session_state.alerts:
        st.write("Recent Alerts:")
        st.write(st.session_state.alerts[-10:])  # Show last 10 alerts
    else:
        st.write("No alerts yet.")

    # Reminders Section
    st.subheader("Reminders")
    if st.session_state.reminders_log:
        st.write("Recent Reminders:")
        st.write(st.session_state.reminders_log[-5:])  # Show last 5 reminders
    else:
        st.write("No reminders yet.")

# Main function
def main():
    # Start agent threads
    health_thread = threading.Thread(target=healthcare_task)
    safety_thread = threading.Thread(target=safety_task)
    reminder_thread = threading.Thread(target=reminder_task)

    health_thread.daemon = True
    safety_thread.daemon = True
    reminder_thread.daemon = True

    health_thread.start()
    safety_thread.start()
    reminder_thread.start()

    # Run Streamlit UI
    streamlit()

if __name__ == "__main__":
    print("Starting Elderly Care Multi-Agent System...")
    # Run with: `streamlit run this_script.py`
    main()

