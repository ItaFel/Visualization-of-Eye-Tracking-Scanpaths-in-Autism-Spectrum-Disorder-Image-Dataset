import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def process_video_to_scanpath(video_path: str):
    """
    Processes a video file and extracts the scanpath (sequence of gaze points).
    Returns a list of (x, y) coordinates normalized to [0, 1].
    """
    cap = cv2.VideoCapture(video_path)
    scanpath = []

    # Iris landmarks indices in MediaPipe Face Mesh
    LEFT_IRIS = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]
    
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        # Convert the BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image_rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # Get iris centers
                # Simplified: average of iris landmarks
                
                h, w = image.shape[:2]
                
                left_iris_pts = np.array([(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) for i in LEFT_IRIS])
                right_iris_pts = np.array([(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) for i in RIGHT_IRIS])
                
                left_center = np.mean(left_iris_pts, axis=0)
                right_center = np.mean(right_iris_pts, axis=0)
                
                # Average both eyes for a single gaze point estimate
                gaze_point = (left_center + right_center) / 2.0
                
                # In a real app, we would map this relative to head pose and calibration
                # Here we just return the raw normalized coordinate relative to the frame
                scanpath.append(gaze_point.tolist())
                
    cap.release()
    return scanpath
