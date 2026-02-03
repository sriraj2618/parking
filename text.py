import streamlit as st
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# ================= FIREBASE =================
cred = credentials.Certificate("firebase_key.json")
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
st.subheader("Hi, welcome to our smart parking platform")
st.divider()

role = st.sidebar.selectbox("Select Role", ["Home", "User", "Security"])

# ================= HOME =================
if role == "Home":
    st.info("""
Real-Time Digital Valet System (Firebase Backend)

Workflow:
1. User books slot → gets UID.
2. Security verifies UID → real parking record created.
3. Return → record deleted & slot freed.

This works globally using Firebase.
""")
    st.stop()

# ================= USER =================
if role == "User":
    mode = st.sidebar.radio("User", ["Login", "Create Account"])

    # -------- CREATE ACCOUNT --------
    if mode == "Create Account":
        u = st.sidebar.text_input("Create Username")
        p = st.sidebar.text_input("Create Password", type="password")

        if st.sidebar.button("Register"):
            db.collection("users").document(u).set({
                "password": p
            })
            st.success("Account created! Now login.")
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

            st.success("Booking created")
            st.code(f"Your UID: {uid}")
            st.info("Show this UID to security at parking gate")

    # -------- GET CAR --------
    if option == "Get My Car":
        uid = st.text_input("Enter UID")

        if st.button("Request Return"):
            db.collection("parking").document(uid).update({
                "status": "Requested"
            })
            st.success("Return request sent to security")

# ================= SECURITY =================
if role == "Security":
    su = st.sidebar.text_input("Username")
    sp = st.sidebar.text_input("Password", type="password")

    if su != SECURITY_USER or sp != SECURITY_PASS:
        st.warning("Invalid security login")
        st.stop()

    st.success("Security Dashboard")

    # -------- VERIFY & PARK --------
    st.subheader("Verify UID (Entry Gate)")
    uid = st.text_input("Enter UID from user")

    if st.button("Verify & Park"):
        doc = db.collection("pending").document(uid).get()

        if doc.exists:
            data = doc.to_dict()
            vtype = data["vehicletype"]

            # Get u
