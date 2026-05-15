from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from flask import request
import os
import numpy as np

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    manage_session=False
)

# =========================
# LOAD DATA
# =========================
df_patients = pd.read_excel("Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")

df_patients['Registration_Date'] = pd.to_datetime(df_patients['Registration_Date'], errors='coerce')
df_patients['Discharge_Date'] = pd.to_datetime(df_patients['Discharge_Date'], errors='coerce')

today = datetime(2026, 4, 14)

df_patients['Year'] = df_patients['Registration_Date'].dt.year

years = sorted(df_patients['Year'].dropna().unique().tolist())
years = ["Total"] + [int(y) for y in years]

client_sessions = {}

# =========================
# SAFE JSON CLEANER
# =========================
def safe(v):
    if isinstance(v, (np.integer, np.int64)):
        return int(v)
    return v

def clean(data):
    return {
        k: [safe(x) for x in v] if isinstance(v, list) else safe(v)
        for k, v in data.items()
    }

# =========================
# CORE FUNCTION
# =========================
def compute_data_for_year(year):

    if year == "Total":
        df = df_patients.copy()
    else:
        df = df_patients[df_patients['Year'] == int(year)].copy()

    df = df.dropna(subset=['Registration_Date'])

    total_patients = int(len(df))
    hospitalized = int(df['Discharge_Date'].isna().sum())

    admissions_week = int(len(df[df['Registration_Date'] >= today - timedelta(days=7)]))
    admissions_month = int(len(df[df['Registration_Date'] >= today - timedelta(days=30)]))

    # TREND
    df['Month'] = df['Registration_Date'].dt.to_period('M')
    monthly = df.groupby('Month').size().reset_index(name='count')

    trend_labels = monthly['Month'].astype(str).tolist()
    trend_data = [int(x) for x in monthly['count'].tolist()]

    # STAFF
    staff_counts = df_staff['Role'].value_counts()
    staff_labels = staff_counts.index.tolist()
    staff_data = [int(x) for x in staff_counts.values.tolist()]

    # VEHICLES
    vehicle_counts = df_vehicles['Status'].value_counts()

    vehicles_data = [
        int(vehicle_counts.get('Available', 0)),
        int(vehicle_counts.get('In Mission', 0)),
        int(vehicle_counts.get('Maintenance', 0))
    ]

    return clean({
        "trend_labels": trend_labels,
        "trend_data": trend_data,

        "total_patients": total_patients,
        "hospitalized": hospitalized,
        "admissions_week": admissions_week,
        "admissions_month": admissions_month,

        "staff_labels": staff_labels,
        "staff_data": staff_data,

        "vehicles_data": vehicles_data,

        # 🔥 FIX CRASH JINJA
        "gender_data": [0, 0]
    })

# =========================
# SOCKET EVENTS
# =========================
@socketio.on('connect')
def connect(auth=None):
    client_sessions[request.sid] = {"year": "Total"}
    emit('update_data', compute_data_for_year("Total"))

@socketio.on('disconnect')
def disconnect():
    client_sessions.pop(request.sid, None)

@socketio.on('change_year')
def change_year(data):
    year = data.get('year', "Total")
    client_sessions[request.sid]['year'] = year
    emit('update_data', compute_data_for_year(year))

@socketio.on('refresh_data')
def refresh():
    year = client_sessions[request.sid]['year']
    emit('update_data', compute_data_for_year(year))

# =========================
# BACKGROUND TASK
# =========================
def background():
    while True:
        socketio.sleep(5)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]['year']
            socketio.emit(
                'update_data',
                compute_data_for_year(year),
                to=sid
            )

socketio.start_background_task(background)

# =========================
# ROUTE
# =========================
@app.route('/')
def index():
    data = compute_data_for_year("Total")
    data['years'] = years
    data['default_year'] = "Total"
    return render_template("index.html", data=data)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)