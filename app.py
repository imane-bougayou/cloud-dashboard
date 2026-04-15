from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import random
import time
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    manage_session=False
)

# =========================
# LOAD EXCEL (SOURCE UNIQUE)
# =========================
FILE = "./Healthcare_Dashboard_Full_Data.xlsx"

df_patients = pd.read_excel(FILE, sheet_name="Patients")
df_staff = pd.read_excel(FILE, sheet_name="Staff")
df_vehicles = pd.read_excel(FILE, sheet_name="Vehicles")

df_patients['Registration_Date'] = pd.to_datetime(df_patients['Registration_Date'])
df_patients['Discharge_Date'] = pd.to_datetime(df_patients['Discharge_Date'], errors='coerce')

today = df_patients['Registration_Date'].max()

# =========================
# YEARS
# =========================
years = sorted(df_patients['Registration_Date'].dt.year.unique().tolist())
years = ["Total"] + years

# =========================
# REAL-TIME STORAGE
# =========================
real_time_labels = []
real_time_in_data = []
real_time_out_data = []

client_sessions = {}

# =========================
# JITTER (ONLY FOR 2026)
# =========================
def jitter(values, percent=0.05):
    return [max(0, int(v + v * random.uniform(-percent, percent))) for v in values]

# =========================
# MAIN FUNCTION
# =========================
def compute_data_for_year(year):

    df = df_patients.copy()

    # =====================
    # 2025 → REAL DATA ONLY
    # =====================
    if year == 2025:
        df = df[df['Registration_Date'].dt.year == 2025]

    # =====================
    # 2026 → EXCEL + JITTER
    # =====================
    elif year == 2026:
        df = df[df['Registration_Date'].dt.year == 2025]  # base Excel

    # =====================
    # TOTAL
    # =====================
    elif year == "Total":
        pass

    # =====================
    # TREND
    # =====================
    df['Month'] = df['Registration_Date'].dt.to_period('M').astype(str)
    trend = df.groupby(['Month', 'Type']).size().unstack(fill_value=0)

    trend_in = trend.get('Inpatient', pd.Series()).tolist()
    trend_out = trend.get('Outpatient', pd.Series()).tolist()
    months = trend.index.tolist()

    # =====================
    # KPIs BASE
    # =====================
    total_patients = len(df)
    hospitalized = df['Discharge_Date'].isna().sum()

    admissions_week = df[df['Registration_Date'] >= today - timedelta(days=7)].shape[0]
    admissions_month = df[df['Registration_Date'] >= today - timedelta(days=30)].shape[0]

    # =====================
    # STAFF / VEHICLES
    # =====================
    dept_counts = df_staff['Role'].value_counts()

    dept_labels = dept_counts.index.tolist()
    dept_data = dept_counts.values.tolist()

    vehicles_data = df_vehicles['Status'].value_counts().reindex(
        ['Available', 'In Mission', 'Maintenance'],
        fill_value=0
    ).tolist()

    gender_data = df_patients['Gender'].value_counts().reindex(
        ['Female', 'Male'],
        fill_value=0
    ).tolist()

    # =====================
    # APPLY JITTER ONLY 2026
    # =====================
    if year == 2026:
        trend_in = jitter(trend_in)
        trend_out = jitter(trend_out)
        total_patients = max(0, total_patients + random.randint(-20, 20))
        hospitalized = max(0, hospitalized + random.randint(-10, 10))
        admissions_week = max(0, admissions_week + random.randint(-5, 5))
        admissions_month = max(0, admissions_month + random.randint(-10, 10))
    else:
        trend_in = trend_in
        trend_out = trend_out

    return {
        'trend_labels': months,
        'trend_in_data': trend_in,
        'trend_out_data': trend_out,

        'dept_labels': dept_labels,
        'dept_data': dept_data,

        'gender_data': gender_data,
        'vehicles_data': vehicles_data,

        'total_patients': total_patients,
        'hospitalized': hospitalized,
        'admissions_week': admissions_week,
        'admissions_month': admissions_month,

        'delta_total': 0,
        'delta_hospitalized': 0,
        'delta_week': 0,
        'delta_month': 0
    }

# =========================
# SOCKET EVENTS
# =========================
@socketio.on('connect')
def handle_connect():
    client_sessions[request.sid] = {'year': 'Total'}
    emit('update_data', compute_data_for_year("Total"))


@socketio.on('disconnect')
def handle_disconnect():
    client_sessions.pop(request.sid, None)


@socketio.on('change_year')
def handle_change_year(data):
    year = data['year']
    client_sessions[request.sid]['year'] = year
    emit('update_data', compute_data_for_year(year))


@socketio.on('refresh_data')
def handle_refresh():
    year = client_sessions[request.sid]['year']
    emit('update_data', compute_data_for_year(year))


# =========================
# REAL TIME LOOP (optional)
# =========================
def background_task():
    while True:
        time.sleep(5)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]['year']
            socketio.emit('update_data', compute_data_for_year(year), to=sid)


# =========================
# ROUTE
# =========================
@app.route('/')
def index():
    data = compute_data_for_year("Total")
    data['years'] = years
    data['default_year'] = "Total"
    data['staff_labels'] = list(df_staff['Role'].unique())
    return render_template("index.html", data=data)


# =========================
# START
# =========================
socketio.start_background_task(background_task)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)