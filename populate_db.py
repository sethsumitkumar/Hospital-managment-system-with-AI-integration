import sqlite3
import random
from datetime import datetime, timedelta

def populate():
    conn = sqlite3.connect('hospital.db')
    cur = conn.cursor()

    # Sample data for generation
    names = ["Aarav", "Priya", "Vikram", "Sanya", "Rahul", "Anjali", "Amit", "Neha", "Rohan", "Sneha"]
    surnames = ["Sharma", "Verma", "Gupta", "Mehta", "Singh", "Kumar", "Patel", "Joshi"]
    medicines = ["Paracetamol", "Dollo 650", "Ativan", "Amlodipine", "Metformin", "Azithromycin", "Ibuprofen"]
    diseases = ["Fever", "Hypertension", "Diabetes", "Infection", "Body Ache", "Anxiety"]
    doctors = [
        "Dr. A. Smith (Cardiology)", "Dr. B. Jones (Neurology)", "Dr. C. Williams (Orthopedics)",
        "Dr. D. Brown (Pediatrics)", "Dr. E. Davis (General Surgeon)"
    ]

    print("Inserting 50 records...")

    for i in range(1, 51):
        ref_no = f"REF{1000 + i}"
        p_name = f"{random.choice(names)} {random.choice(surnames)}"
        tablet = random.choice(medicines)
        disease = random.choice(diseases)
        doctor = random.choice(doctors)
        
        # Random dates
        dob = (datetime.now() - timedelta(days=random.randint(7000, 25000))).strftime("%d-%m-%Y")
        issue_date = datetime.now().strftime("%d-%m-%Y")
        exp_date = (datetime.now() + timedelta(days=365)).strftime("%d-%m-%Y")

        sql = """INSERT OR IGNORE INTO hospital 
                 (Reference_No, Nameoftablets, dose, Numbersoftablets, lot, issuedate, expdate, 
                  dailydose, storage, nhsnumber, patientname, DOB, patientaddress, doctor, Disease) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        
        values = (
            ref_no, tablet, "500mg", "30", "L999", issue_date, exp_date,
            "2", "Store in cool place", f"NHS{2000+i}", p_name, dob, 
            "Pune, Maharashtra", doctor, disease
        )

        cur.execute(sql, values)

    conn.commit()
    conn.close()
    print("✅ Successfully added 50 sample patients to hospital.db!")

if __name__ == "__main__":
    populate()