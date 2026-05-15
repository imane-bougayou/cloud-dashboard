from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request
import pandas as pd
from datetime import datetime, timedelta
import random
import os
import numpy as np

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ✅ SAFE MODE (no eventlet, no gevent)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    manage_session=False
)

client_sessions = {}

# =========================
# PATH SAFE (RAILWAY FIX)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "Healthcare_Dashboard_Full_Data.xlsx")

# =========================
# LOAD EXCEL ONLY
# =========================
df_patients = pd.read_excel(file_path, sheet_name="Patients")
df_staff = pd.read_excel(file_path, sheet_name="Staff")
df_vehicles = pd.read_excel(file_path, sheet_name="Vehicles")

# =========================
# CLEAN DATA
# =========================
df_patients["Registration_Date"] = pd.to_datetime(df_patients["Registration_Date"], errors="coerce")
df_patients["Discharge_Date"] = pd.to_datetime(df_patients["Discharge_Date"], errors="coerce")

today = datetime(2026, 4, 14)

# =========================
# SAFE CONVERTER
# =========================
def clean(v):
    if isinstance(v, (np.integer, np.int64)):
        return int(v)
    if isinstance(v, (np.floating, np.float64)):
        return float(v)
    return v

# =========================
# BASE METRICS (EXCEL ONLY)
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
# TREND DATA FROM EXCEL
# =========================
df_patients["Month"] = df_patients["Registration_Date"].dt.to_period("M")
monthly = df_patients.groupby("Month").size()

trend_labels = [str(x) for x in monthly.index.astype(str)]
trend_values = monthly.tolist()

# =========================
# YEARS
# =========================
years = sorted(df_patients["Registration_Date"].dt.year.dropna().unique().tolist())
years = ["Total"] + years

staff_counts = df_staff["Role"].value_counts().to_dict()
vehicle_counts = df_vehicles["Status"].value_counts().to_dict()

# =========================
# COMPUTE FUNCTION
# =========================
def compute_data_for_year(year):

    if year == "Total":
        return {
            "total_patients": clean(total_patients_base),
            "hospitalized": clean(hospitalized_base),
            "admissions_week": clean(admissions_week_base),
            "admissions_month": clean(admissions_month_base),

            "trend_labels": trend_labels,
            "trend_in_data": trend_values,
            "trend_out_data": trend_values,

            "staff_labels": list(staff_counts.keys()),
            "staff_data": [clean(v) for v in staff_counts.values()],

            "vehicles_data": [
                clean(vehicle_counts.get("Available", 0)),
                clean(vehicle_counts.get("In Mission", 0))
            ]
        }

    year = int(year)
    df_y = df_patients[df_patients["Registration_Date"].dt.year == year]

    monthly_y = df_y.groupby(df_y["Registration_Date"].dt.month).size()

    return {
        "total_patients": clean(len(df_y)),
        "hospitalized": clean(df_y["Discharge_Date"].isna().sum()),
        "admissions_week": clean(df_y.shape[0]),
        "admissions_month": clean(df_y.shape[0]),

        "trend_labels": [f"{year}-{i}" for i in monthly_y.index],
        "trend_in_data": [clean(x) for x in monthly_y.tolist()],
        "trend_out_data": [clean(x) for x in monthly_y.tolist()],

        "staff_labels": list(staff_counts.keys()),
        "staff_data": [clean(v) for v in staff_counts.values()],

        "vehicles_data": [
            clean(vehicle_counts.get("Available", 0)),
            clean(vehicle_counts.get("In Mission", 0))
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
# BACKGROUND LOOP
# =========================
def background_task():
    while True:
        socketio.sleep(5)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]["year"]
            socketio.emit(
                "update_data",
                compute_data_for_year(year),
                to=sid
            )

socketio.start_background_task(background_task)

# =========================
# ROUTE SAFE (NO CRASH)
# =========================
@app.route("/")
def index():
    data = compute_data_for_year("Total")

    safe_data = {
        "years": years,
        "default_year": "Total",
        "staff_labels": data.get("staff_labels", []),
        "trend_labels": data.get("trend_labels", []),
        "trend_in_data": data.get("trend_in_data", []),
        "trend_out_data": data.get("trend_out_data", []),
        "total_patients": data.get("total_patients", 0),
        "hospitalized": data.get("hospitalized", 0),
        "admissions_week": data.get("admissions_week", 0),
        "admissions_month": data.get("admissions_month", 0),
        "staff_data": data.get("staff_data", []),
        "vehicles_data": data.get("vehicles_data", [])
    }

    return render_template("index.html", data=safe_data)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)