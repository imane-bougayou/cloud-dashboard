from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request
import pandas as pd
from datetime import datetime, timedelta
import random
import time
import os
import numpy as np

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ✅ IMPORTANT: threading = ZERO dependency (pas eventlet, pas gevent)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    manage_session=False
)

client_sessions = {}

# =========================
# LOAD EXCEL (ONLY SOURCE)
# =========================
df_patients = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")

today = datetime(2026, 4, 14)

# =========================
# CLEAN DATA (FIX CRASH)
# =========================
df_patients["Registration_Date"] = pd.to_datetime(df_patients["Registration_Date"], errors="coerce")
df_patients["Discharge_Date"] = pd.to_datetime(df_patients["Discharge_Date"], errors="coerce")

# =========================
# SAFE JSON CONVERTER
# =========================
def safe(v):
    if isinstance(v, (np.integer, np.int64)):
        return int(v)
    if isinstance(v, (np.floating, np.float64)):
        return float(v)
    return v

# =========================
# REAL BASE DATA (FROM EXCEL ONLY)
# =========================
total_patients_base = len(df_patients)
hospitalized_base = df_patients["Discharge_Date"].isna().sum()

admissions_week_base = df_patients[
    df_patients["Registration_Date"] >= today - timedelta(days=7)
].shape[0]

admissions_month_base = df_patients[
    df_patients["Registration_Date"] >= today - timedelta(days=30)
].shape[0]

# =========================
# MONTHLY TREND FROM EXCEL
# =========================
df_patients["Month"] = df_patients["Registration_Date"].dt.to_period("M")

monthly = df_patients.groupby(["Month", "Type"]).size().unstack(fill_value=0)

inpatient_counts = monthly.get("Inpatient", pd.Series()).tolist()
outpatient_counts = monthly.get("Outpatient", pd.Series()).tolist()

# =========================
# REAL TIME DATA (CLEAN)
# =========================
real_time_labels = []
real_time_in = []
real_time_out = []

for i in range(min(10, len(inpatient_counts))):
    real_time_labels.append(f"T-{10-i}")
    real_time_in.append(int(inpatient_counts[i]))
    real_time_out.append(int(outpatient_counts[i]) if i < len(outpatient_counts) else 0)

# =========================
# YEARS
# =========================
years = sorted(df_patients["Registration_Date"].dt.year.dropna().unique().tolist())
years = ["Total"] + years

staff_counts = df_staff["Role"].value_counts().to_dict()
vehicle_counts = df_vehicles["Status"].value_counts().to_dict()

# =========================
# CORE FUNCTION (LOGIC ONLY)
# =========================
def compute_data_for_year(year):

    if year == "Total":
        total_patients = int(total_patients_base)
        hospitalized = int(hospitalized_base)
        admissions_week = int(admissions_week_base)
        admissions_month = int(admissions_month_base)

        trend_in = [int(x) for x in real_time_in]
        trend_out = [int(x) for x in real_time_out]
        labels = real_time_labels

    else:
        year = int(year)

        df_y = df_patients[df_patients["Registration_Date"].dt.year == year]

        total_patients = int(len(df_y))
        hospitalized = int(df_y["Discharge_Date"].isna().sum())

        admissions_week = int(df_y[df_y["Registration_Date"] >= today - timedelta(days=7)].shape[0])
        admissions_month = int(df_y[df_y["Registration_Date"] >= today - timedelta(days=30)].shape[0])

        monthly_y = df_y.groupby(df_y["Registration_Date"].dt.month).size()

        trend_in = monthly_y.tolist() if len(monthly_y) > 0 else [0]
        trend_out = monthly_y.tolist() if len(monthly_y) > 0 else [0]
        labels = [f"{year}-{i}" for i in range(1, len(trend_in) + 1)]

    return {
        "total_patients": safe(total_patients),
        "hospitalized": safe(hospitalized),
        "admissions_week": safe(admissions_week),
        "admissions_month": safe(admissions_month),

        "trend_labels": labels,
        "trend_in_data": [safe(x) for x in trend_in],
        "trend_out_data": [safe(x) for x in trend_out],

        "staff_labels": list(staff_counts.keys()),
        "staff_data": [safe(v) for v in staff_counts.values()],

        "vehicles_data": [
            safe(vehicle_counts.get("Available", 0)),
            safe(vehicle_counts.get("In Mission", 0))
        ]
    }

# =========================
# SOCKET EVENTS
# =========================
@socketio.on("connect")
def connect():
    client_sessions[request.sid] = {"year": "Total"}
    emit("update_data", compute_data_for_year("Total"))

@socketio.on("change_year")
def change_year(data):
    year = data.get("year", "Total")
    client_sessions[request.sid]["year"] = year
    emit("update_data", compute_data_for_year(year))

@socketio.on("disconnect")
def disconnect():
    client_sessions.pop(request.sid, None)

# =========================
# BACKGROUND REALTIME LOOP
# =========================
def background_task():
    while True:
        time.sleep(5)

        if len(real_time_labels) > 0:
            new_val = int(random.choice(inpatient_counts)) if inpatient_counts else 0
            real_time_in.append(new_val)
            real_time_out.append(int(new_val * random.uniform(1.2, 1.8)))

            real_time_labels.append(datetime.now().strftime("%H:%M:%S"))

            if len(real_time_labels) > 20:
                real_time_labels.pop(0)
                real_time_in.pop(0)
                real_time_out.pop(0)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]["year"]
            socketio.emit("update_data", compute_data_for_year(year), to=sid)

# =========================
# ROUTE
# =========================
@app.route("/")
def index():
    data = compute_data_for_year("Total")
    data["years"] = years
    data["default_year"] = "Total"
    return render_template("index.html", data=data)

socketio.start_background_task(background_task)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)