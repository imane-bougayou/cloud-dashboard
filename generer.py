import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)

# PARAMÈTRES
n_patients = 1000
n_staff = 200
n_treatments = 1500
n_vehicles = 50

start_date = datetime(2025, 12, 1)
end_date = datetime(2026, 4, 9)
date_range = (end_date - start_date).days

departments = ["Cardiology", "Neurology", "Surgery", "Pediatrics", "Oncology"]
genders = ["Male", "Female"]
types = ["Inpatient", "Outpatient"]
staff_roles = ["Doctor", "Nurse", "Admin"]
staff_status = ["Available", "Busy", "On Leave"]
vehicle_types = ["Ambulance", "Car"]
vehicle_status = ["Available", "On Mission"]
locations = ["Zone A", "Zone B", "Zone C", "Zone D"]

# ======================
# 1. PATIENTS
# ======================
patients = []

today = datetime(2026, 4, 9)  # date actuelle (fixe pour cohérence)

for i in range(n_patients):
    
    dob = datetime(1940,1,1) + timedelta(days=np.random.randint(0, 25000))
    admission_date = start_date + timedelta(days=np.random.randint(0, date_range))
    
    patient_type = np.random.choice(types)

    # LOGIQUE COMPLÈTE
    if patient_type == "Inpatient":
        
        # 25% restent encore hospitalisés
        if np.random.rand() < 0.25:
            discharge_date = None
        else:
            stay_days = np.random.randint(1, 15)
            discharge_date = admission_date + timedelta(days=stay_days)
            
            # sécurité : éviter une date future
            if discharge_date > today:
                discharge_date = None

    else:
        discharge_date = None  # outpatient

    patients.append({
        "Patient_ID": i+1,
        "Name": f"Patient_{i+1}",
        "Gender": np.random.choice(genders),
        "Date_of_Birth": dob,
        "Registration_Date": admission_date,
        "Discharge_Date": discharge_date,
        "Type": patient_type,
        "Department": np.random.choice(departments)
    })

df_patients = pd.DataFrame(patients)# ======================
# 2. STAFF
# ======================
staff = []
for i in range(n_staff):
    staff.append({
        "Staff_ID": i+1,
        "Name": f"Staff_{i+1}",
        "Role": np.random.choice(staff_roles),
        "Department": np.random.choice(departments),
        "Status": np.random.choice(staff_status)
    })

df_staff = pd.DataFrame(staff)

# ======================
# 3. TREATMENTS
# ======================
treatments = []
for i in range(n_treatments):
    treatments.append({
        "Treatment_ID": i+1,
        "Patient_ID": np.random.randint(1, n_patients+1),
        "Treatment_Type": random.choice(["Surgery", "Consultation", "Therapy"]),
        "Cost": round(np.random.uniform(100, 5000), 2),
        "Date": start_date + timedelta(days=np.random.randint(0, date_range))
    })

df_treatments = pd.DataFrame(treatments)

# ======================
# 4. VEHICLES
# ======================
vehicles = []
for i in range(n_vehicles):
    vehicles.append({
        "Vehicle_ID": i+1,
        "Type": np.random.choice(vehicle_types),
        "Status": np.random.choice(vehicle_status),
        "Location": np.random.choice(locations)
    })

df_vehicles = pd.DataFrame(vehicles)

# ======================
# EXPORT EXCEL
# ======================
with pd.ExcelWriter("Healthcare_Dashboard_Full_Data.xlsx") as writer:
    df_patients.to_excel(writer, sheet_name="Patients", index=False)
    df_staff.to_excel(writer, sheet_name="Staff", index=False)
    df_treatments.to_excel(writer, sheet_name="Treatments", index=False)
    df_vehicles.to_excel(writer, sheet_name="Vehicles", index=False)

print("✅ Fichier Excel COMPLET généré !")