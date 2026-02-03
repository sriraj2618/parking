import streamlit as st
import pandas as pd
import sqlite3
import uuid

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

# Tables
c.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS parking(
    uid TEXT PRIMARY KEY,
    username TEXT,
    name TEXT,
    vehicletype TEXT,
    slot TEXT,
    status TEXT
)
""")
conn.commit()

# ================= CONFIG =================
TOTAL_CAR_SLOTS = 5
TOTAL_BIKE_SLOTS = 5

SECURITY_USER = "security"
SECURITY_PASS = "admin123"

# ================= SLOTS =================
if "car_slots" not in st.session_state:
    st.session_state.car_slots = [f"C{i}" for i in range(1, TOTAL_CAR_SLOTS+1)]

if "bike_slots" not in st.session_state:
    st.session_state.bike_slots = [f"B{i}" for i in range(1, TOTAL_BIKE_SLOTS+1)]

if "pending" not in st.session_state:
    st.session_state.pending = {}

# ================= UI =================
st.set_page_config("Digital Valet", layout="wide")
st.title("🚗 Digital Valet Parking System")
st.subheader("Hi, welcome to our smart parking platform")
st.divider()

role = st.sidebar.selectbox("Select Role", ["Home", "User", "Security"])

# ================= HOME =================
if role == "Home":
    st.info("""
Real-Time Digital Valet System

Workflow:
1. User books slot → gets UID.
2. Security verifies UID → record created.
3. Return → record deleted & slot freed.

This prevents illegal/fake parking entries.
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
            try:
                c.execute("INSERT INTO users VALUES (?,?)", (u, p))
                conn.commit()
                st.success("Account created! Now login.")
            except:
                st.error("Username already exists")
        st.stop()

    # -------- LOGIN --------
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")

    c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    if not c.fetchone():
        st.warning("Invalid login")
        st.stop()

    st.success(f"Welcome {u}")
    option = st.radio("Service", ["Book Slot", "Get My Car"])

    # -------- BOOK SLOT --------
    if option == "Book Slot":
        name = st.text_input("Name")
        vtype = st.selectbox("Vehicle Type", ["Car", "Bike"])

        if st.button("Generate UID"):
            if vtype == "Car" and not st.session_state.car_slots:
                st.error("Car Parking Full")
                st.stop()

            if vtype == "Bike" and not st.session_state.bike_slots:
                st.error("Bike Parking Full")
                st.stop()

            uid = str(uuid.uuid4())[:8]
            st.session_state.pending[uid] = {
                "username": u,
                "name": name,
                "vehicletype": vtype
            }

            st.success("Booking created")
            st.code(f"Your UID: {uid}")
            st.info("Show this UID to security at parking gate")

    # -------- GET CAR --------
    if option == "Get My Car":
        uid = st.text_input("Enter UID")

        if st.button("Request Return"):
            c.execute("UPDATE parking SET status='Requested' WHERE uid=?", (uid,))
            conn.commit()
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
        if uid in st.session_state.pending:
            data = st.session_state.pending[uid]
            vtype = data["vehicletype"]

            if vtype == "Car":
                slot = st.session_state.car_slots.pop(0)
            else:
                slot = st.session_state.bike_slots.pop(0)

            c.execute("INSERT INTO parking VALUES (?,?,?,?,?,?)",
                      (uid, data["username"], data["name"], vtype, slot, "Parked"))
            conn.commit()

            del st.session_state.pending[uid]
            st.success("Vehicle parked successfully")
            st.code(f"Slot: {slot}")
        else:
            st.error("Invalid / Fake UID")

    # -------- LIVE TABLE --------
    st.subheader("Active Parking Records")
    df = pd.read_sql("SELECT * FROM parking", conn)
    st.dataframe(df, use_container_width=True)

    # -------- RETURN CAR --------
    st.subheader("Return Vehicle")
    ruid = st.text_input("Enter UID to return")

    if st.button("Return Car"):
        c.execute("DELETE FROM parking WHERE uid=?", (ruid,))
        conn.commit()
        st.success("Vehicle returned & record deleted")
        st.experimental_rerun()
