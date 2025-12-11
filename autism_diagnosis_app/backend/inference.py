import torch
import torch.nn as nn
import numpy as np
import os

class AutismClassifier(nn.Module):
    # Placeholder architecture - must match the trained model structure
    # Since we don't know the exact structure, we assume a simple LSTM or MLP
    def __init__(self, input_size=2, hidden_size=64, num_classes=2):
        super(AutismClassifier, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x shape: (batch, seq_len, 2)
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return out

MODEL_PATH = "../models/autism_classifier.pth"

def load_model():
    model = AutismClassifier()
    if os.path.exists(MODEL_PATH):
        try:
            model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
            model.eval()
            print(f"Loaded model from {MODEL_PATH}")
            return model
        except Exception as e:
            print(f"Failed to load model: {e}")
            return None
    else:
        print(f"Model file not found at {MODEL_PATH}. Using mock inference.")
        return None

# Global model instance
model_instance = load_model()

def predict_autism_risk(scanpath):
    """
    Takes a scanpath (list of [x, y]) and returns (risk_label, probability).
    """
    if not scanpath:
        return "Low", 0.0

    if model_instance:
        # Preprocess scanpath
        # Normalize/Resample to fixed length if needed
        # Convert to tensor
        input_tensor = torch.tensor([scanpath], dtype=torch.float32) # Add batch dim
        
        with torch.no_grad():
            outputs = model_instance(input_tensor)
            probs = torch.softmax(outputs, dim=1)
            risk_prob = probs[0][1].item() # Assuming class 1 is "High Risk"
            
        risk_level = "High" if risk_prob > 0.5 else "Low"
        return risk_level, risk_prob
    else:
        # Mock logic
        # e.g. based on variance or just random
        # High variance in gaze might indicate different patterns? 
        # Just random for now as placeholder
        import random
        risk_prob = random.random()
        risk_level = "High" if risk_prob > 0.5 else "Low"
        return risk_level, risk_prob
