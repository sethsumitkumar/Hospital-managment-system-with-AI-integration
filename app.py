from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from db_config import db_config
import datetime
import re
import joblib           # For AI Risk Model
import numpy as np      # For Data Handling
import os               # For File Paths
import platform         # To detect Windows vs Linux
import pytesseract      # For OCR (Vision)
from PIL import Image   # For Image Processing
import google.generativeai as genai  # For Interactive Chat
import random           # For random appointment times

app = Flask(__name__)

# --- A. SECURITY & API SETUP ---
app.secret_key = "hospital_management_secret_key_2026"

ADMIN_USER = "admin"
ADMIN_PASS = "hospital123"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    print("⚠️ WARNING: GEMINI_API_KEY not found.")
    model = None

# --- B. OCR / VISION SETUP ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# --- C. RISK MODEL SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'risk_model.pkl')

try:
    risk_model = joblib.load(MODEL_PATH)
    print(f"✅ SUCCESS: AI Risk Model loaded.")
except Exception as e:
    risk_model = None
    print(f"⚠️ WARNING: Could not load AI model: {e}")

DOCTORS_NAMES = [
    "Dr. A. Smith (Cardiology)", "Dr. B. Jones (Neurology)", "Dr. C. Williams (Orthopedics)",
    "Dr. D. Brown (Pediatrics)", "Dr. E. Davis (General Surgeon)", "Dr. F. Miller (ENT)",
    "Dr. G. Wilson (Dermatology)", "Dr. H. Moore (Gynecology)", "Dr. I. Taylor (Oncology)",
    "Dr. J. Anderson (Psychiatry)"
]

# --- D. DATABASE UTILITIES ---
def get_db_connection():
    try:
        conn = sqlite3.connect(db_config['database'])
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as err:
        print(f"❌ Error: {err}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS hospital (
            Reference_No TEXT PRIMARY KEY, Nameoftablets TEXT, dose TEXT, 
            Numbersoftablets TEXT, lot TEXT, issuedate TEXT, expdate TEXT, 
            dailydose TEXT, storage TEXT, reg_date TEXT, patientname TEXT, 
            DOB TEXT, patientaddress TEXT, doctor TEXT, Disease TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT, dob TEXT, doctor TEXT, time TEXT,
            ref_no TEXT, status TEXT DEFAULT 'Confirmed')''')
            
        conn.commit()
        conn.close()

def calculate_age(dob_str):
    try:
        for fmt in ["%d-%m-%Y", "%d-%m-%y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                birth_date = datetime.datetime.strptime(str(dob_str), fmt).date()
                today = datetime.date.today()
                return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            except: continue
        return 30
    except: return 30

# --- E. OFFLINE HEALTH ADVICE LOGIC ---
def get_health_advice(row):
    advice_list = []
    tablet = row.get('Nameoftablets', '').lower() if row.get('Nameoftablets') else ''
    daily_dose_str = row.get('dailydose', '0')
    dob = row.get('DOB', '')
    expdate = row.get('expdate', '')
    
    exp_date_obj = None
    for fmt in ["%d-%m-%Y", "%d-%m-%y", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            exp_date_obj = datetime.datetime.strptime(str(expdate), fmt).date()
            break
        except: pass
    
    if exp_date_obj and (exp_date_obj - datetime.date.today()).days < 0:
        advice_list.append("🔴 <b>CRITICAL:</b> Medicine EXPIRED!")

    if "paracetamol" in tablet or "dollo" in tablet:
        advice_list.append("🌡️ <b>Fever:</b> Monitor temp. 6hr gap between doses.")
    elif "ativan" in tablet:
        advice_list.append("💤 <b>Anxiety:</b> May cause drowsiness. Do not drive.")

    if risk_model:
        try:
            dose_val = int(re.search(r'\d+', str(daily_dose_str)).group()) if re.search(r'\d+', str(daily_dose_str)) else 1
            prediction = risk_model.predict([[calculate_age(dob), dose_val, 0, 0]])
            if prediction[0] == 1: advice_list.append("🤖 <b>AI RISK ALERT:</b> High-risk dosage.")
        except: pass

    return advice_list

# --- F. ACCESS CONTROL ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- G. MAIN VIEWS ---

@app.route('/patient')
def patient_view():
    return render_template('patient.html')

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        rows = conn.execute("SELECT * FROM hospital").fetchall()
        patients = [dict(row) for row in rows]
        conn.close()
        return render_template('index.html', patients=patients, doctors=DOCTORS_NAMES)
    return "Database Connection Failed."

# --- NEW: DEDICATED DASHBOARD ROUTE ---
@app.route('/dashboard')
def dashboard_view():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    count = 0
    if conn:
        count = conn.execute("SELECT COUNT(*) FROM hospital").fetchone()[0]
        conn.close()
    
    return render_template('dashboard.html', patients_count=count)

# --- H. ACTION & ANALYTICS ROUTES ---

@app.route('/scan_prescription', methods=['POST'])
def scan_prescription():
    if 'file' not in request.files: return jsonify({"error": "No file"})
    file = request.files['file']
    try:
        img = Image.open(file)
        text = pytesseract.image_to_string(img)
        pname = re.search(r"Name:\s*([A-Za-z\s]+)", text)
        tablet = re.search(r"Rx:\s*([A-Za-z\s]+)", text)
        return jsonify({
            "pname": pname.group(1).strip() if pname else "",
            "name": tablet.group(1).strip() if tablet else ""
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/monthly-data')
def monthly_data():
    conn = get_db_connection()
    query = "SELECT strftime('%m', reg_date) as month, COUNT(*) as count FROM hospital WHERE reg_date >= date('now', '-6 months') GROUP BY month ORDER BY month ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    month_map = {'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}
    return jsonify({
        "labels": [month_map.get(r['month'], r['month']) for r in rows], 
        "values": [r['count'] for r in rows]
    })

@app.route('/analytics-data')
def analytics_data():
    conn = get_db_connection()
    rows = conn.execute("SELECT Disease, COUNT(*) as count FROM hospital GROUP BY Disease").fetchall()
    conn.close()
    return jsonify({
        "labels": [r['Disease'] for r in rows], 
        "values": [r['count'] for r in rows]
    })

@app.route('/get-appointments')
def get_appointments():
    if not session.get('logged_in'): return jsonify([])
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM appointments ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/chat', methods=['POST'])
def chat():
    try:
        req = request.json
        user_text = req.get('message', '').strip()
        user_text_lower = user_text.lower()
        
        match = re.search(r"(REF\d+|ref\d+)", user_text, re.IGNORECASE)
        ref_to_use = match.group(0).upper() if match else req.get('context_ref', '')

        conn = get_db_connection()
        patient_row = None
        if ref_to_use:
            patient_row = conn.execute("SELECT * FROM hospital WHERE Reference_No=?", (ref_to_use,)).fetchone()

        # 1. TRIGGER APPOINTMENT FLOW
        if "book" in user_text_lower or "appointment" in user_text_lower:
            res = "Welcome! Are you a <b>New Patient</b> or an <b>Old Patient</b>?"
            conn.close()
            return jsonify({"response": res})

        # 2. SELECTION MODE (NEW/OLD)
        if user_text_lower == "new patient" or user_text_lower == "new":
            docs = "<br>".join([f"- {d}" for d in DOCTORS_NAMES])
            res = f"Provide details: <b>Full Name, DD-MM-YYYY, Doctor Name</b><br><br><b>Doctors:</b><br>{docs}"
            conn.close()
            return jsonify({"response": res})

        if user_text_lower == "old patient" or user_text_lower == "old":
            docs = "<br>".join([f"- {d}" for d in DOCTORS_NAMES])
            res = f"Provide details: <b>Reference No, Doctor Name</b><br><br><b>Doctors:</b><br>{docs}"
            conn.close()
            return jsonify({"response": res})

        # 3. AI ADVICE & RISK (PRIORITIZED)
        if patient_row:
            p = dict(patient_row)
            advice_items = get_health_advice(p)
            if "advice" in user_text_lower or "recommend" in user_text_lower:
                tips = [a for a in advice_items if "RISK" not in a and "CRITICAL" not in a]
                res = f"💡 <b>Advice for {p['patientname']}:</b><br>" + ("<br>".join(tips) if tips else "Follow your doctor's orders.")
                conn.close()
                return jsonify({"response": res, "ref": ref_to_use})
            if "risk" in user_text_lower:
                risks = [a for a in advice_items if "RISK" in a or "CRITICAL" in a]
                res = f"⚠️ <b>Risk Analysis:</b><br>" + ("<br>".join(risks) if risks else "No dosage risks detected.")
                conn.close()
                return jsonify({"response": res, "ref": ref_to_use})
            if "supply" in user_text_lower:
                stock = p.get('Numbersoftablets', '0')
                res = f"📦 <b>Inventory Check for {p['patientname']}:</b><br>Remaining: <b>{stock} Tablets</b>"
                conn.close()
                return jsonify({"response": res, "ref": ref_to_use})

        # 4. DATA RETRIEVAL (Full Record)
        if match and patient_row:
            p = dict(patient_row)
            res = (f"📋 <b>Complete Record: {ref_to_use}</b><br>👤 <b>Name:</b> {p['patientname']}<br>"
                   f"🩺 <b>Condition:</b> {p['Disease']}<br>💊 <b>Tablet:</b> {p['Nameoftablets']}<br>"
                   f"👨‍⚕️ <b>Doctor:</b> {p['doctor']}<br>📦 <b>Storage:</b> {p['storage']}<br>"
                   f"🎂 <b>DOB:</b> {p['DOB']}<br>📍 <b>Address:</b> {p['patientaddress']}")
            conn.close()
            return jsonify({"response": res, "ref": ref_to_use})

        # 5. PROCESS BOOKING
        if "," in user_text:
            parts = [p.strip() for p in user_text.split(',')]
            appt_time = random.choice(["10:00 AM", "11:30 AM", "02:15 PM", "04:45 PM"])
            if "REF" in parts[0].upper():
                ref_id = parts[0].upper()
                row = conn.execute("SELECT patientname, DOB FROM hospital WHERE Reference_No=?", (ref_id,)).fetchone()
                if row:
                    p_name, p_dob, chosen_doc = row['patientname'], row['DOB'], parts[1]
                else:
                    conn.close(); return jsonify({"response": "❌ Error: Ref Not Found."})
            else:
                p_name, p_dob, chosen_doc = parts[0].title(), parts[1], parts[2]
                count = conn.execute("SELECT COUNT(*) FROM hospital").fetchone()[0]
                ref_id = f"REF{1201 + count + 1}"

            conn.execute("INSERT INTO appointments (patient_name, dob, doctor, time, ref_no) VALUES (?, ?, ?, ?, ?)",
                         (p_name, p_dob, chosen_doc, appt_time, ref_id))
            conn.commit()
            res = f"✅ <b>Appointment Confirmed!</b><br>👤 Patient: {p_name}<br>⏰ Time: <b>{appt_time}</b><br>👨‍⚕️ Doctor: {chosen_doc}<br>🆔 Ref: <b>{ref_id}</b>"
            conn.close()
            return jsonify({"response": res, "ref": ref_id})

        # FALLBACK: GEMINI
        if model:
            ai_res = model.generate_content(f"Answer briefly as a hospital assistant: {user_text}").text
            conn.close(); return jsonify({"response": ai_res.replace("\n", "<br>")})
            
        conn.close()
        return jsonify({"response": "I'm not sure how to help. Enter a Ref ID or select 'Book Appointment'."})
    except Exception as e:
        return jsonify({"response": f"System Error: {str(e)}"})

@app.route('/add', methods=['POST'])
def add_patient():
    if not session.get('logged_in'): return redirect(url_for('login'))
    data = request.form
    conn = get_db_connection()
    if conn:
        sql = """INSERT INTO hospital (Nameoftablets, Reference_No, dose, Numbersoftablets, lot, issuedate, expdate, dailydose, storage, reg_date, patientname, DOB, patientaddress, doctor, Disease) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        conn.execute(sql, (data['name'], data['ref'], data['dose'], data['no_of_tablets'], data['lot'], data['issue_date'], data['exp_date'], data['daily_dose'], data['storage'], data['reg_date'], data['pname'], data['dob'], data['address'], data['doctor'], data.get('disease', '')))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<ref>', methods=['GET'])
def delete_patient(ref):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    if conn:
        conn.execute("DELETE FROM hospital WHERE Reference_No=?", (ref,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)