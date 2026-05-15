from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from flask import request
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    manage_session=False
)

# =========================
# LOAD EXCEL DATA
# =========================
df_patients = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")

# Convert dates once
df_patients['Registration_Date'] = pd.to_datetime(df_patients['Registration_Date'])
df_patients['Discharge_Date'] = pd.to_datetime(df_patients['Discharge_Date'], errors='coerce')

today = datetime(2026, 4, 14)

# Add year column
df_patients['Year'] = df_patients['Registration_Date'].dt.year

years = sorted(df_patients['Year'].dropna().unique().tolist())
years = ["Total"] + [int(y) for y in years]

client_sessions = {}

# =========================
# CORE LOGIC (EXCEL ONLY)
# =========================
def compute_data_for_year(year):

    # FILTER DATA
    if year == "Total":
        df = df_patients
    else:
        df = df_patients[df_patients['Year'] == int(year)]

    # =========================
    # BASIC STATS
    # =========================
    total_patients = len(df)
    hospitalized = df['Discharge_Date'].isna().sum()

    admissions_week = len(df[df['Registration_Date'] >= today - timedelta(days=7)])
    admissions_month = len(df[df['Registration_Date'] >= today - timedelta(days=30)])

    # =========================
    # TREND (MONTHLY REAL DATA)
    # =========================
    df['Month'] = df['Registration_Date'].dt.to_period('M')

    monthly = df.groupby('Month').size().reset_index(name='count')

    trend_labels = monthly['Month'].astype(str).tolist()
    trend_in_data = monthly['count'].tolist()

    # Split inpatient/outpatient
    monthly_type = df.groupby(['Month', 'Type']).size().unstack(fill_value=0)

    trend_inpatients = monthly_type.get('Inpatient', pd.Series(0)).reindex(monthly['Month'], fill_value=0).tolist()
    trend_outpatients = monthly_type.get('Outpatient', pd.Series(0)).reindex(monthly['Month'], fill_value=0).tolist()

    # =========================
    # DEPARTMENTS (REAL IF EXISTS)
    # =========================
    dept_labels = ["Cardiology", "Neurology", "Surgery", "Pediatrics", "Oncology"]

    if 'Department' in df.columns:
        dept_data = df['Department'].value_counts().reindex(dept_labels, fill_value=0).tolist()
    else:
        dept_data = [0] * len(dept_labels)

    # =========================
    # STAFF (REAL)
    # =========================
    staff_counts = df_staff['Role'].value_counts()
    staff_labels = staff_counts.index.tolist()
    staff_data = staff_counts.values.tolist()

    # =========================
    # VEHICLES (REAL)
    # =========================
    vehicle_counts = df_vehicles['Status'].value_counts()

    vehicles_data = [
        int(vehicle_counts.get('Available', 0)),
        int(vehicle_counts.get('In Mission', 0)),
        int(vehicle_counts.get('Maintenance', 0))
    ]

    # =========================
    # GENDER (IF EXISTS)
    # =========================
    if 'Gender' in df.columns:
        gender_data = df['Gender'].value_counts().tolist()
    else:
        gender_data = [0, 0]

    return {
        "trend_labels": trend_labels,
        "trend_in_data": trend_inpatients,
        "trend_out_data": trend_outpatients,

        "dept_labels": dept_labels,
        "dept_data": dept_data,

        "staff_labels": staff_labels,
        "staff_data": staff_data,

        "vehicles_data": vehicles_data,

        "gender_data": gender_data,

        "total_patients": total_patients,
        "hospitalized": hospitalized,
        "admissions_week": admissions_week,
        "admissions_month": admissions_month
    }

# =========================
# SOCKET EVENTS
# =========================
@socketio.on('connect')
def handle_connect():
    client_sessions[request.sid] = {"year": "Total"}
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
def handle_refresh_data():
    year = client_sessions[request.sid]['year']
    emit('update_data', compute_data_for_year(year))

# =========================
# REAL-TIME BACKGROUND TASK
# (NO FAKE DATA, JUST REFRESH)
# =========================
def background_task():
    while True:
        socketio.sleep(5)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]['year']
            socketio.emit(
                'update_data',
                compute_data_for_year(year),
                to=sid
            )

# =========================
# ROUTE
# =========================
@app.route('/')
def index():
    data = compute_data_for_year("Total")
    data['years'] = years
    data['default_year'] = "Total"
    data['staff_labels'] = data['staff_labels']
    return render_template("index.html", data=data)

# =========================
# START
# =========================
socketio.start_background_task(background_task)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)