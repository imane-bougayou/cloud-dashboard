from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import random
import time
import os

# =====================================================
# APP CONFIG
# =====================================================
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    manage_session=False
)

# =====================================================
# GLOBAL VARIABLES
# =====================================================
client_sessions = {}

EXCEL_FILE = "./Healthcare_Dashboard_Full_Data.xlsx"

# =====================================================
# LOAD EXCEL DATA
# =====================================================
df_patients = pd.read_excel(EXCEL_FILE, sheet_name="Patients")
df_staff = pd.read_excel(EXCEL_FILE, sheet_name="Staff")
df_vehicles = pd.read_excel(EXCEL_FILE, sheet_name="Vehicles")

# Safe dates conversion
df_patients["Registration_Date"] = pd.to_datetime(
    df_patients["Registration_Date"],
    errors="coerce"
)

if "Discharge_Date" in df_patients.columns:
    df_patients["Discharge_Date"] = pd.to_datetime(
        df_patients["Discharge_Date"],
        errors="coerce"
    )

today = datetime.now()
current_year = today.year

# =====================================================
# PREPARE HISTORICAL DATA
# =====================================================
df_patients["Month"] = df_patients["Registration_Date"].dt.to_period("M")
df_patients["Year"] = df_patients["Registration_Date"].dt.year

monthly_counts = df_patients.groupby(
    ["Month", "Type"]
).size().unstack(fill_value=0)

inpatient_counts = (
    monthly_counts["Inpatient"].tolist()
    if "Inpatient" in monthly_counts.columns
    else [120, 140, 160]
)

outpatient_counts = (
    monthly_counts["Outpatient"].tolist()
    if "Outpatient" in monthly_counts.columns
    else [300, 320, 350]
)

# =====================================================
# YEARS FILTER
# =====================================================
years = sorted(
    df_patients["Year"].dropna().unique().astype(int).tolist()
)

years = ["Total"] + years

# =====================================================
# STAFF DATA
# =====================================================
staff_counts = df_staff["Role"].value_counts().to_dict()
staff_labels = list(staff_counts.keys())
staff_base_data = [int(v) for v in staff_counts.values()]

# =====================================================
# VEHICLE DATA
# =====================================================
vehicle_counts = df_vehicles["Status"].value_counts()

vehicle_base_data = [
    int(vehicle_counts.get("Available", 0)),
    int(vehicle_counts.get("In Mission", 0)),
    int(vehicle_counts.get("Maintenance", 0))
]

# =====================================================
# REAL TIME DATA
# =====================================================
real_time_labels = []
real_time_in_data = []
real_time_out_data = []

counter = 0

# =====================================================
# HELPERS
# =====================================================
def safe_variation(value, percent=0.08):
    change = int(value * percent)
    return max(0, value + random.randint(-change, change))


def generate_real_time_patient_values():
    inpatients = random.choice(inpatient_counts)
    outpatients = random.choice(outpatient_counts)
    return inpatients, outpatients


def init_real_time_data():
    for i in range(10):
        in_val, out_val = generate_real_time_patient_values()

        current_time = (
            datetime.now() - timedelta(seconds=(10 - i) * 10)
        ).strftime("%H:%M:%S")

        real_time_labels.append(current_time)
        real_time_in_data.append(in_val)
        real_time_out_data.append(out_val)


init_real_time_data()

# =====================================================
# MAIN DATA FUNCTION
# =====================================================
def compute_data_for_year(year):

    # ======================================
    # TOTAL = REAL TIME LIVE
    # ======================================
    if year == "Total":

        total_patients = safe_variation(len(df_patients), 0.05)

        hospitalized = safe_variation(
            int(df_patients["Discharge_Date"].isna().sum()), 0.05
        )

        admissions_week = random.randint(20, 40)
        admissions_month = random.randint(90, 140)

        delta_total = round(random.uniform(-5, 5), 1)
        delta_hospitalized = round(random.uniform(-5, 5), 1)
        delta_week = round(random.uniform(-5, 5), 1)
        delta_month = round(random.uniform(-5, 5), 1)

        months = real_time_labels
        trend_in_data = real_time_in_data
        trend_out_data = real_time_out_data

    # ======================================
    # CURRENT YEAR = RANDOM DYNAMIC
    # ======================================
    elif str(year) == str(current_year):

        base_patients = 1350
        base_hospitalized = 380

        total_patients = base_patients + random.randint(-50, 50)
        hospitalized = base_hospitalized + random.randint(-20, 20)

        admissions_week = 26 + random.randint(-5, 5)
        admissions_month = 113 + random.randint(-10, 10)

        delta_total = round(random.uniform(-3, 3), 1)
        delta_hospitalized = round(random.uniform(-3, 3), 1)
        delta_week = round(random.uniform(-3, 3), 1)
        delta_month = round(random.uniform(-3, 3), 1)

        months = [
            f"{year}-{str(i).zfill(2)}"
            for i in range(1, today.month + 1)
        ]

        trend_in_data = [
            130 + random.randint(-10, 10),
            145 + random.randint(-10, 10),
            120 + random.randint(-10, 10),
            155 + random.randint(-10, 10)
        ][:len(months)]

        trend_out_data = [
            310 + random.randint(-20, 20),
            330 + random.randint(-20, 20),
            290 + random.randint(-20, 20),
            360 + random.randint(-20, 20)
        ][:len(months)]

    # ======================================
    # OLD YEARS = FIXED
    # ======================================
    else:

        year = int(year)

        total_patients = 1200
        hospitalized = 350
        admissions_week = 23
        admissions_month = 100

        delta_total = 5.2
        delta_hospitalized = -2.1
        delta_week = 10.5
        delta_month = 8.3

        months = [
            f"{year}-{str(i).zfill(2)}"
            for i in range(1, 13)
        ]

        trend_in_data = [
            120,135,110,145,160,130,
            140,155,125,170,180,165
        ]

        trend_out_data = [
            300,320,280,350,380,310,
            340,370,290,400,420,390
        ]

    # ======================================
    # COMMON DATA
    # ======================================
    dept_labels = [
        "Cardiology",
        "Neurology",
        "Surgery",
        "Pediatrics",
        "Oncology"
    ]

    dept_data = [random.randint(40, 160) for _ in range(5)]

    dept_status = random.choices(
        ["Stable", "Increasing", "Decreasing"],
        k=5
    )

    female = int(total_patients * random.uniform(0.48, 0.55))
    male = total_patients - female

    gender_data = [female, male]

    staff_data = [
        safe_variation(x, 0.05)
        for x in staff_base_data
    ]

    vehicles_data = [
        safe_variation(x, 0.10)
        for x in vehicle_base_data
    ]

    return {
        "trend_labels": months,
        "trend_out_data": trend_out_data,
        "trend_in_data": trend_in_data,
        "dept_labels": dept_labels,
        "dept_data": dept_data,
        "dept_status": dept_status,
        "gender_data": gender_data,
        "staff_data": staff_data,
        "vehicles_data": vehicles_data,
        "total_patients": total_patients,
        "hospitalized": hospitalized,
        "admissions_week": admissions_week,
        "admissions_month": admissions_month,
        "delta_total": delta_total,
        "delta_hospitalized": delta_hospitalized,
        "delta_week": delta_week,
        "delta_month": delta_month
    }

# =====================================================
# SOCKET EVENTS
# =====================================================
@socketio.on("connect")
def handle_connect():
    client_sessions[request.sid] = {"year": "Total"}
    emit("update_data", compute_data_for_year("Total"))


@socketio.on("disconnect")
def handle_disconnect():
    client_sessions.pop(request.sid, None)


@socketio.on("change_year")
def handle_change_year(data):
    year = data.get("year", "Total")
    client_sessions[request.sid]["year"] = year
    emit("update_data", compute_data_for_year(year))


@socketio.on("refresh_data")
def handle_refresh_data():
    year = client_sessions.get(
        request.sid, {}
    ).get("year", "Total")

    emit("update_data", compute_data_for_year(year))

# =====================================================
# BACKGROUND TASK
# =====================================================
def background_task():
    global counter

    while True:
        time.sleep(1)
        counter += 1

        # update live graph every 10 sec
        if counter % 10 == 0:

            in_val, out_val = generate_real_time_patient_values()

            current_time = datetime.now().strftime("%H:%M:%S")

            real_time_labels.append(current_time)
            real_time_in_data.append(in_val)
            real_time_out_data.append(out_val)

            if len(real_time_labels) > 20:
                real_time_labels.pop(0)
                real_time_in_data.pop(0)
                real_time_out_data.pop(0)

        # send updates to all users
        for sid in list(client_sessions.keys()):
            try:
                year = client_sessions[sid]["year"]

                socketio.emit(
                    "update_data",
                    compute_data_for_year(year),
                    to=sid
                )
            except:
                pass

# =====================================================
# ROUTE
# =====================================================
@app.route("/")
def index():

    data = compute_data_for_year("Total")

    data["years"] = years
    data["default_year"] = "Total"
    data["staff_labels"] = staff_labels

    return render_template(
        "index.html",
        data=data
    )

# =====================================================
# START BACKGROUND
# =====================================================
socketio.start_background_task(background_task)

# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False
    )