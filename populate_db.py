import sqlite3
import random
from datetime import datetime, timedelta

def populate_data():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    # Clear previous identical data
    cursor.execute("DELETE FROM hospital")

    # --- Realistic Data Pools ---
    first_names = ["Aarav", "Vihaan", "Aditya", "Arjun", "Sai", "Ishaan", "Aaryan", "Siddharth", "Krishna", "Saanvi", "Ananya", "Aadhya", "Pari", "Diya", "Anika", "Riya", "Kavya", "Ishani"]
    last_names = ["Sharma", "Verma", "Gupta", "Patil", "Deshmukh", "Kulkarni", "Joshi", "Mehta", "Shah", "Kumar", "Singh", "Yadav", "Chavan", "Gaekwad"]
    
    doctors = ["Dr. A. Smith (Cardiology)", "Dr. B. Jones (Neurology)", "Dr. C. Williams (Orthopedics)", "Dr. D. Brown (Pediatrics)", "Dr. E. Davis (General Surgeon)"]
    diseases = ["Infection", "Fever", "Diabetes", "Hypertension", "Body Ache", "Anxiety", "Migraine", "Asthma"]
    tablets = ["Ibuprofen", "Paracetamol", "Dollo 650", "Metformin", "Ativan", "Nice", "Azithromycin", "Amlodipine"]
    
    doses = ["250mg", "500mg", "650mg", "5mg", "10mg", "1g"]
    tablet_counts = ["10", "15", "20", "30", "60"]
    daily_doses = ["1", "2", "3"]
    storages = ["Store in cool place", "Room temperature", "Refrigerate", "Keep away from light"]
    
    pune_areas = ["Kothrud, Pune", "Katraj, Pune", "Baner, Pune", "Viman Nagar, Pune", "Hadapsar, Pune", "Hinjewadi, Pune", "Pimpri, Pune"]

    # Date range for Registration: Aug 2025 to Mar 2026
    start_reg = datetime(2025, 8, 1)
    end_reg = datetime(2026, 3, 15)
    reg_delta = (end_reg - start_reg).days

    for i in range(1, 101):
        ref_no = f"REF{1000 + i}"
        
        # 1. Unique Name
        pname = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # 2. Randomized Medicine Details
        doctor = random.choice(doctors)
        disease = random.choice(diseases)
        tablet = random.choice(tablets)
        dose = random.choice(doses)
        count = random.choice(tablet_counts)
        daily = random.choice(daily_doses)
        storage = random.choice(storages)
        
        # 3. Randomized Registration Date
        random_reg_days = random.randint(0, reg_delta)
        reg_date_obj = start_reg + timedelta(days=random_reg_days)
        reg_date = reg_date_obj.strftime('%Y-%m-%d')
        
        # 4. Randomized Expiry Date (Always in the future)
        exp_date = (reg_date_obj + timedelta(days=random.randint(365, 730))).strftime('%Y-%m-%d')
        
        # 5. Randomized Date of Birth (Age 5 to 80)
        dob = (datetime.now() - timedelta(days=random.randint(1825, 29200))).strftime('%Y-%m-%d')
        
        # 6. Randomized Address
        address = f"Flat {random.randint(101, 909)}, {random.choice(pune_areas)}"

        sql = """INSERT INTO hospital (Reference_No, Nameoftablets, dose, Numbersoftablets, 
                 lot, issuedate, expdate, dailydose, storage, reg_date, patientname, 
                 DOB, patientaddress, doctor, Disease) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        
        cursor.execute(sql, (ref_no, tablet, dose, count, f"BT{random.randint(1000, 9999)}", reg_date, 
                             exp_date, daily, storage, reg_date, pname, 
                             dob, address, doctor, disease))

    conn.commit()
    conn.close()
    print("✅ Successfully generated 100 UNIQUE patient profiles!")

if __name__ == "__main__":
    populate_data()