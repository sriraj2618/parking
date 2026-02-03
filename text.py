import streamlit as st
import uuid
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# ================= FIREBASE INIT (SAFE) =================
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= CONFIG =================
TOTAL_CAR_SLOTS = 5
TOTAL_BIKE_SLOTS = 5

SECURITY_USER = "security"
SECURITY_PASS = "admin123"

# ================= UI =================
st.set_page_config(page_title="Digital Valet", layout="wide")
st.title("🚗 Digital Valet Parking System")
st.caption("Real-Time Field Project | Firebase Powered")
st.divider()

role = st.sidebar.selectbox("Select Role", ["Home", "User", "Security"])

# ================= HOME =================
if role == "Home":
    st.info("""
### Workflow
1. User creates account & logs in  
2. User books → UID generated (pending only)  
3. Security verifies UID → parking record created  
4. Return car → record deleted  

✔ Global  
✔ Multi-device  
✔ Fraud-safe  
""")
    st.stop()

# ================= USER =================
if role == "User":
    mode = st.sidebar.radio("User Access", ["Login", "Create Account"])

    # -------- CREATE ACCOUNT --------
    if mode == "Create Account":
        u = st.sidebar.text_input("Create Username")
        p = st.sidebar.text_input("Create Password", type="password")

        if st.sidebar.button("Register"):
            if db.collection("users").document(u).get().exists:
                st.error("Username already exists")
            else:
                db.collection("users").document(u).set({"password": p})
                st.success("Account created! Please login.")
        st.stop()

    # -------- LOGIN --------
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")

    doc = db.collection("users").document(u).get()
    if not doc.exists or doc.to_dict()["password"] != p:
        st.warning("Invalid login")
        st.stop()

    st.success(f"Welcome {u}")
    option = st.radio("Service", ["Book Slot", "Get My Car"])

    # -------- BOOK SLOT (PENDING ONLY) --------
    if option == "Book Slot":
        name = st.text_input("Name")
        vtype = st.selectbox("Vehicle Type", ["Car", "Bike"])

        if st.button("Generate UID"):
            uid = str(uuid.uuid4())[:8]

            db.collection("pending").document(uid).set({
                "username": u,
                "name": name,
                "vehicletype": vtype
            })

            st.success("Booking Created")
            st.code(uid)
            st.info("Show this UID to security at entry gate")

    # -------- GET CAR --------
    if option == "Get My Car":
        uid = st.text_input("Enter UID")

        if st.button("Request Return"):
            park_doc = db.collection("parking").document(uid).get()
            if park_doc.exists:
                db.collection("parking").document(uid).update({
                    "status": "Requested"
                })
                st.success("Return request sent")
            else:
                st.error("Vehicle not currently parked")

# ================= SECURITY =================
if role == "Security":
    su = st.sidebar.text_input("Security Username")
    sp = st.sidebar.text_input("Security Password", type="password")

    if su != SECURITY_USER or sp != SECURITY_PASS:
        st.warning("Invalid security login")
        st.stop()

    st.success("Security Dashboard")

    # -------- VERIFY & PARK --------
    st.subheader("Verify UID (Entry)")
    uid = st.text_input("Enter UID from user")

    if st.button("Verify & Park"):
        doc = db.collection("pending").document(uid).get()

        if not doc.exists:
            st.error("Invalid / Fake UID")
        else:
            data = doc.to_dict()
            vtype = data["vehicletype"]

            # get used slots
            used = [d.to_dict()["slot"] for d in db.collection("parking").stream()]

            slots = (
                [f"C{i}" for i in range(1, TOTAL_CAR_SLOTS + 1)]
                if vtype == "Car"
                else [f"B{i}" for i in range(1, TOTAL_BIKE_SLOTS + 1)]
            )

            free = list(set(slots) - set(used))
            if not free:
                st.error("Parking Full")
                st.stop()

            slot = free[0]

            db.collection("parking").document(uid).set({
                "username": data["username"],
                "name": data["name"],
                "vehicletype": vtype,
                "slot": slot,
                "status": "Parked"
            })

            db.collection("pending").document(uid).delete()
            st.success(f"Vehicle Parked → Slot {slot}")

    # -------- ACTIVE TABLE --------
    st.subheader("Active Parking Records")
    records = [
        d.to_dict() | {"UID": d.id}
        for d in db.collection("parking").stream()
    ]

    if records:
        st.dataframe(pd.DataFrame(records), use_container_width=True)
    else:
        st.info("No vehicles parked")

    # -------- RETURN CAR --------
    st.subheader("Return Vehicle")
    ruid = st.text_input("Enter UID to return")

    if st.button("Return Car"):
        if db.collection("parking").document(ruid).get().exists:
            db.collection("parking").document(ruid).delete()
            st.success("Vehicle returned & record deleted")
            st.experimental_rerun()
        else:
            st.error("UID not found")
