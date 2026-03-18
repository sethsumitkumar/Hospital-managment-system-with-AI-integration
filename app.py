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

app = Flask(__name__)

# --- A. SECURITY & API SETUP ---
app.secret_key = "hospital_management_secret_key_2026"

# Default Admin Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "hospital123"

# GEMINI API SETUP
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
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
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS hospital (
            Reference_No TEXT PRIMARY KEY, Nameoftablets TEXT, dose TEXT, 
            Numbersoftablets TEXT, lot TEXT, issuedate TEXT, expdate TEXT, 
            dailydose TEXT, storage TEXT, nhsnumber TEXT, patientname TEXT, 
            DOB TEXT, patientaddress TEXT, doctor TEXT, Disease TEXT)''')
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

# --- F. AUTHENTICATION ROUTES ---

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
    return redirect(url_for('patient_view'))

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

# --- H. ACTION ROUTES ---

@app.route('/scan_prescription', methods=['POST'])
def scan_prescription():
    if 'file' not in request.files: return jsonify({"error": "No file"})
    file = request.files['file']
    try:
        img = Image.open(file)
        text = pytesseract.image_to_string(img)
        # Simple extraction logic for Demo
        pname = re.search(r"Name:\s*([A-Za-z\s]+)", text)
        tablet = re.search(r"Rx:\s*([A-Za-z\s]+)", text)
        return jsonify({
            "pname": pname.group(1).strip() if pname else "",
            "name": tablet.group(1).strip() if tablet else ""
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        req = request.json
        user_text = req.get('message', '').strip()
        match = re.search(r"(REF\d+|ref\d+|\d{4})", user_text)
        ref_to_use = match.group(0).upper() if match else req.get('context_ref', '')

        patient_context = "No patient context provided."
        tips_html = ""

        if ref_to_use:
            conn = get_db_connection()
            db_row = conn.execute("SELECT * FROM hospital WHERE Reference_No=?", (ref_to_use,)).fetchone()
            conn.close()
            if db_row:
                row = dict(db_row)
                tips_html = "<br>".join(get_health_advice(row))
                patient_context = f"Patient: {row['patientname']}, Med: {row['Nameoftablets']}, Disease: {row['Disease']}"

        prompt = f"System Context: {patient_context}\nUser: {user_text}\nAnswer briefly as a hospital AI. Answer general questions too."
        if model:
            ai_response = model.generate_content(prompt)
            res = ai_response.text.replace("\n", "<br>")
            if tips_html: res += f"<br><br><b>💡 Safety Tips:</b><br>{tips_html}"
            return jsonify({"response": res, "ref": ref_to_use})
        return jsonify({"response": "AI Offline."})
    except Exception as e:
        return jsonify({"response": f"Error: {e}"})

@app.route('/add', methods=['POST'])
def add_patient():
    if not session.get('logged_in'): return redirect(url_for('login'))
    data = request.form
    conn = get_db_connection()
    if conn:
        sql = """INSERT INTO hospital (Nameoftablets, Reference_No, dose, Numbersoftablets, lot, issuedate, expdate, dailydose, storage, nhsnumber, patientname, DOB, patientaddress, doctor, Disease) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        conn.execute(sql, (data['name'], data['ref'], data['dose'], data['no_of_tablets'], data['lot'], data['issue_date'], data['exp_date'], data['daily_dose'], data['storage'], data['nhs'], data['pname'], data['dob'], data['address'], data['doctor'], data.get('disease', '')))
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