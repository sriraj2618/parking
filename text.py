import streamlit as st
import uuid
import json
import time
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# ================= FIREBASE (SECURE) =================
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
st.set_page_config("Digital Valet", layout="wide")
st.title("🚗 Digital Valet Parking System")
st.caption("Real-Time Field Project | Firebase Powered")
st.divider()

role = st.sidebar.selectbox("Select Role", ["Home", "User", "Security"])

# ================= HOME =================
if role == "Home":
    st.info("""
Welcome to the Digital Valet Parking System.

Workflow:
1. User books slot → gets UID.
2. Security verifies UID → vehicle officially parked.
3. Return → status updates + slot released.

This system works globally using Firebase.
""")
    st.stop()

# ================= USER =================
if role == "User":
    mode = st.sidebar.radio("User", ["Login", "Create Account"])

    # ---- CREATE ACCOUNT ----
    if mode == "Create Account":
        u = st.sidebar.text_input("Create Username")
        p = st.sidebar.text_input("Create Password", type="password")

        if st.sidebar.button("Register"):
            db.collection("users").document(u).set({
                "password": p
            })
            st.success("Account created! Now login.")
        st.stop()

    # ---- LOGIN ----
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")

    doc = db.collection("users").document(u).get()
    if not doc.exists or doc.to_dict()["password"] != p:
        st.warning("Invalid login")
        st.stop()

    st.success(f"Welcome {u}")
    option = st.radio("Service", ["Book Slot", "Get My Car"])

    # ---- BOOK SLOT (PENDING ONLY) ----
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

            st.success("Booking created successfully")
            st.code(f"Your UID: {uid}")
            st.info("Show this UID to security at the parking gate")

    # ---- GET CAR ----
    if option == "Get My Car":
        uid = st.text_input("Enter UID")

        if st.button("Request Return"):
            db.collection("parking").document(uid).update({
                "status": "Requested"
            })
            st.success("Return request sent to security")

# ================= SECURITY =================
if role == "Security":
    su = st.sidebar.text_input("Security Username")
    sp = st.sidebar.text_input("Security Password", type="password")

    if su != SECURITY_USER or sp != SECURITY_PASS:
        st.warning("Invalid security login")
        st.stop()

    st.success("Security Dashboard")

    # ---- VERIFY & PARK ----
    st.subheader("Verify UID (Entry)")
    uid = st.text_input("Enter UID from user")

    if st.button("Verify & Park"):
        doc = db.collection("pending").document(uid).get()

        if doc.exists:
            data = doc.to_dict()
            vtype = data["vehicletype"]

            # Get used slots
            parked = db.collection("parking").stream()
            used_slots = [d.to_dict()["slot"] for d in parked]

            # Slot pool
            if vtype == "Car":
                slots = [f"C{i}" for i in range(1, TOTAL_CAR_SLOTS+1)]
            else:
                slots = [f"B{i}" for i in range(1, TOTAL_BIKE_SLOTS+1)]

            free_slots = list(set(slots) - set(used_slots))
            if not free_slots:
                st.error("No slots available")
                st.stop()

            slot = free_slots[0]

            # Create real parking record
            db.collection("parking").document(uid).set({
                "username": data["username"],
                "name": data["name"],
                "vehicletype": vtype,
                "slot": slot,
                "status": "Parked"
            })

            # Remove from pending
            db.collection("pending").document(uid).delete()

            st.success("Vehicle parked successfully")
            st.code(f"Allocated Slot: {slot}")
        else:
            st.error("Invalid / Fake UID")

    # ---- LIVE TABLE ----
    st.subheader("Active Parking Records")
    docs = db.collection("parking").stream()
    rows = [d.to_dict() | {"UID": d.id} for d in docs]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # ---- RETURN CAR (FINAL WITH POPUP) ----
    st.subheader("Return Vehicle")
    ruid = st.text_input("Enter UID to return")

    if st.button("Return Car"):
        doc = db.collection("parking").document(ruid).get()

        if doc.exists:
            # Step 1: Update status
            db.collection("parking").document(ruid).update({
                "status": "Returning"
            })

            # Popup for security staff
            st.toast("🚘 Car is being brought to the gate...", icon="⏳")
            st.info("Please wait, the valet is on the way")

            time.sleep(2)  # simulate real delay

            # Step 2: Delete record (slot freed)
            db.collection("parking").document(ruid).delete()

            st.toast("✅ Car returned successfully!", icon="🎉")
            st.success("Vehicle returned and slot released")

            st.rerun()
        else:
            st.toast("❌ UID not found", icon="⚠️")
            st.error("Invalid UID")
