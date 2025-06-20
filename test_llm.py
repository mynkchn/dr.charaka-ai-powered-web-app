import pickle
import numpy as np

# Load model
model_path = r"D:\project_ai_hackathon\ml_models\liver_disease_predictor\liver_prediction_xgb_model.pkl"
with open(model_path, "rb") as f:
    model = pickle.load(f)

# Healthy test case
test_data = np.array([
    [
        30,  # Age
        1,   # Gender
        0.5, # Total_Bilirubin
        0.1, # Direct_Bilirubin
        85,  # Alkaline_Phosphotase
        20,  # Alamine_Aminotransferase (ALT)
        22,  # Aspartate_Aminotransferase (AST)
        7.0, # Total_Protiens
        4.5, # Albumin
        1.5  # Albumin_and_Globulin_Ratio
    ]
])

# Predict
prediction = model.predict(test_data)
result = 'Liver Disease Detected' if prediction[0] == 1 else 'Disease NOT Detected'
print("Prediction:", result)

# If you want probability
if hasattr(model, 'predict_proba'):
    proba = model.predict_proba(test_data)
    print("Probabilities:", proba)
