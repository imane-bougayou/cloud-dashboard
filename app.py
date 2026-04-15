from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from flask import request
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

client_sessions = {}

# =========================
# DATA LOAD
# =========================
df_patients = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")

today = datetime(2026, 4, 14)

# Ensure datetime format
df_patients['Registration_Date'] = pd.to_datetime(df_patients['Registration_Date'])

# =========================
# MONTHLY TREND FROM EXCEL
# =========================
df_patients['Month'] = df_patients['Registration_Date'].dt.to_period('M')
monthly_counts = df_patients.groupby(['Month', 'Type']).size().unstack(fill_value=0)

inpatient_counts = monthly_counts.get('Inpatient', pd.Series()).values.tolist()
outpatient_counts = monthly_counts.get('Outpatient', pd.Series()).values.tolist()

# =========================
# REAL TIME DATA STORAGE
# =========================
real_time_labels = []
real_time_in_data = []
real_time_out_data = []
counter = 0


def generate_real_time_patient_values():
    inpatients = random.choice(inpatient_counts) if inpatient_counts else random.randint(100, 200)
    outpatients = random.choice(outpatient_counts) if outpatient_counts else random.randint(200, 400)
    return inpatients, outpatients


# init real-time graph
for i in range(10):
    in_val, out_val = generate_real_time_patient_values()
    current_time = (datetime.now() - timedelta(seconds=(10 - i) * 10)).strftime('%H:%M:%S')
    real_time_labels.append(current_time)
    real_time_in_data.append(in_val)
    real_time_out_data.append(out_val)

# =========================
# YEARS LIST
# =========================
df_patients['Year'] = df_patients['Registration_Date'].dt.year
years = sorted(df_patients['Year'].unique().tolist())
years = ["Total"] + years

staff_counts = df_staff['Role'].value_counts().to_dict()
staff_labels = list(staff_counts.keys())

vehicle_counts = df_vehicles['Status'].value_counts()

# =========================
# CORE FUNCTION
# =========================
def compute_data_for_year(year):

    # ================= TOTAL (FIXED VERSION) =================
    if year == "Total":

        total_patients = int(len(df_patients))

        hospitalized = int(df_patients['Discharge_Date'].isna().sum())

        admissions_week = int(df_patients[
            df_patients['Registration_Date'] >= today - timedelta(days=7)
        ].shape[0])

        admissions_month = int(df_patients[
            df_patients['Registration_Date'] >= today - timedelta(days=30)
        ].shape[0])

        months = real_time_labels

        trend_in_data = real_time_in_data
        trend_out_data = real_time_out_data

        delta_total = 0
        delta_hospitalized = 0
        delta_week = 0
        delta_month = 0

        dept_data = [0, 0, 0, 0, 0]
        dept_status = ["Stable"] * 5
        gender_data = [0, 0]
        staff_data = [0] * len(staff_labels)
        vehicles_data = [
            int(vehicle_counts.get('Available', 0)),
            int(vehicle_counts.get('In Mission', 0)),
            int(vehicle_counts.get('Maintenance', 0))
        ]

    # ================= YEAR 2025 (STATIC DEMO) =================
    elif year == 2025:
        total_patients = 1200
        hospitalized = 350
        admissions_week = 23
        admissions_month = 100

        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, 13)]

        trend_in_data = [120, 135, 110, 145, 160, 130, 140, 155, 125, 170, 180, 165]
        trend_out_data = [300, 320, 280, 350, 380, 310, 340, 370, 290, 400, 420, 390]

        dept_data = [100, 80, 120, 90, 110]
        dept_status = ['Increasing', 'Stable', 'Decreasing', 'Increasing', 'Stable']

        gender_data = [660, 540]
        staff_data = [50, 60, 55]

        vehicles_data = [10, 5, 3]

        delta_total = 5.2
        delta_hospitalized = -2.1
        delta_week = 10.5
        delta_month = 8.3

    # ================= YEAR 2026 (REAL + LIVE FEEL) =================
    else:

        df_y = df_patients[df_patients['Year'] == int(year)]

        total_patients = len(df_y)
        hospitalized = df_y['Discharge_Date'].isna().sum()

        admissions_week = df_y[
            df_y['Registration_Date'] >= today - timedelta(days=7)
        ].shape[0]

        admissions_month = df_y[
            df_y['Registration_Date'] >= today - timedelta(days=30)
        ].shape[0]

        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, today.month + 1)]

        trend_in_data = inpatient_counts[:len(months)]
        trend_out_data = outpatient_counts[:len(months)]

        dept_data = [138, 52, 58, 126, 83]
        dept_status = ['Decreasing', 'Decreasing', 'Increasing', 'Decreasing', 'Stable']

        gender_data = [729, 621]

        staff_data = [67, 59, 51]

        vehicles_data = [
            int(vehicle_counts.get('Available', 0)),
            int(vehicle_counts.get('In Mission', 0)),
            int(vehicle_counts.get('Maintenance', 0))
        ]

        delta_total = -1.8
        delta_hospitalized = 4.5
        delta_week = 12.3
        delta_month = -3.2

    dept_labels = ["Cardiology", "Neurology", "Surgery", "Pediatrics", "Oncology"]

    return {
        'trend_labels': months,
        'trend_out_data': trend_out_data,
        'trend_in_data': trend_in_data,

        'dept_labels': dept_labels,
        'dept_data': dept_data,
        'dept_status': dept_status,

        'gender_data': gender_data,
        'staff_data': staff_data,
        'vehicles_data': vehicles_data,

        'total_patients': total_patients,
        'hospitalized': hospitalized,
        'admissions_week': admissions_week,
        'admissions_month': admissions_month,

        'delta_total': delta_total,
        'delta_hospitalized': delta_hospitalized,
        'delta_week': delta_week,
        'delta_month': delta_month
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
def handle_refresh_data():
    year = client_sessions[request.sid]['year']
    emit('update_data', compute_data_for_year(year))


# =========================
# BACKGROUND REAL TIME
# =========================
def background_task():
    global counter

    while True:
        time.sleep(1)
        counter += 1

        if counter % 10 == 0:
            in_val, out_val = generate_real_time_patient_values()
            current_time = datetime.now().strftime('%H:%M:%S')

            real_time_labels.append(current_time)
            real_time_in_data.append(in_val)
            real_time_out_data.append(out_val)

            if len(real_time_labels) > 20:
                real_time_labels.pop(0)
                real_time_in_data.pop(0)
                real_time_out_data.pop(0)

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
    data['staff_labels'] = staff_labels
    return render_template("index.html", data=data)


socketio.start_background_task(background_task)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)