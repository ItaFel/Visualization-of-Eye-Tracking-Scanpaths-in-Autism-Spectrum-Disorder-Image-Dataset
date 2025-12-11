# Autism Diagnosis Eye-Tracking App

## Overview
This application provides a web interface for autism diagnosis via eye-tracking.
It includes:
- A FastAPI backend for video processing and inference.
- A simple Frontend for user interaction.
- Eye-tracking logic using MediaPipe.

## Installation

1.  **System Requirements**: Ubuntu/Debian Linux.
2.  **Model Setup**:
    - Download the model file from the provided link (https://drive.google.com/file/d/1-eVGpJrhwdCV_8dasjyXkg2yorbhR5bF/view?usp=drive_link).
    - Rename the file to `autism_classifier.pth`.
    - Place it in the `models/` directory:
      `autism_diagnosis_app/models/autism_classifier.pth`
3.  **Run Installer**:
    ```bash
    ./install.sh
    ```

## Running the App

1.  Execute:
    ```bash
    ./run.sh
    ```
2.  Open your browser at `http://localhost:8000`.

## Workflow
1.  Register/Login.
2.  "Buy" diagnosis (Mock).
3.  Start diagnosis -> Sign Consent -> View Instructions.
4.  Record video of the child watching the stimulus.
5.  Upload video.
6.  Wait for processing and see results.
