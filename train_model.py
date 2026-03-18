import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# --- STEP 1: LOAD DATA ---
print("📊 Step 1: Loading data from health_data.csv...")
try:
    df = pd.read_csv('health_data.csv')
    # Features: Age, Dose, Is it an Antibiotic?, Is it a Painkiller?
    X = df[['Age', 'Daily_Dose', 'Is_Antibiotic', 'Is_Painkiller']]
    y = df['Risk_Label']
except FileNotFoundError:
    print("❌ Error: health_data.csv not found. Please create the file with headers: Age,Daily_Dose,Is_Antibiotic,Is_Painkiller,Risk_Label")
    exit()

# --- STEP 2: TRAIN-TEST SPLIT ---
# We split 80% for training and 20% for testing to validate the AI on unseen data
print("🧪 Step 2: Splitting data into Training (80%) and Testing (20%) sets...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- STEP 3: ALGORITHM TOURNAMENT (The Comparison) ---
print("🤖 Step 3: Comparing AI Algorithms to find the most accurate model...")

models = {
    "Logistic Regression": LogisticRegression(),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42)
}

best_model = None
highest_acc = 0

# Loop through each model to see which one performs best
for name, model in models.items():
    # Train the model
    model.fit(X_train, y_train)
    
    # Test the model on the 20% test data
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"✅ {name} Accuracy: {acc * 100:.2f}%")
    
    # Selection logic for the winner
    if acc > highest_acc:
        highest_acc = acc
        best_model = model

# --- STEP 4: SAVE THE WINNER ---
# This saves the best performing model so your Flask app can use it 
model_filename = 'risk_model.pkl'
joblib.dump(best_model, model_filename) 
print(f"\n🏆 Winner: {type(best_model).__name__} saved to '{model_filename}'")

# --- STEP 5: FINAL EVALUATION (For Project Documentation) ---
print("\n--- 📈 Final Model Performance Stats ---")
final_pred = best_model.predict(X_test)

print("1. Confusion Matrix (Shows Correct vs Incorrect predictions):")
print(confusion_matrix(y_test, final_pred))

print("\n2. Detailed Classification Report:")
print(classification_report(y_test, final_pred))