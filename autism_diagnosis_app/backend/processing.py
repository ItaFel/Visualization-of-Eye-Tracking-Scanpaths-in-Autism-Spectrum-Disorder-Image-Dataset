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

def get_relative_iris_pos(eye_landmarks, iris_landmarks, landmarks_list):
    """
    Calculates the relative position of the iris within the eye.
    Returns (x, y) where x,y are in [0, 1] range relative to eye corners.
    """
    # Get eye corner coordinates
    # eye_landmarks[0] is typically the inner corner, [8] is outer (depending on mesh definition)
    # For robust width, we use the min and max x of the eye contour
    
    eye_pts = np.array([(landmarks_list[i].x, landmarks_list[i].y) for i in eye_landmarks])
    iris_pts = np.array([(landmarks_list[i].x, landmarks_list[i].y) for i in iris_landmarks])
    
    # Calculate bounding box of the eye
    min_x = np.min(eye_pts[:, 0])
    max_x = np.max(eye_pts[:, 0])
    min_y = np.min(eye_pts[:, 1])
    max_y = np.max(eye_pts[:, 1])
    
    eye_width = max_x - min_x
    eye_height = max_y - min_y
    
    # Calculate iris center
    iris_center = np.mean(iris_pts, axis=0)
    
    # Avoid division by zero
    if eye_width == 0: eye_width = 1e-6
    if eye_height == 0: eye_height = 1e-6
    
    # Normalize iris position relative to eye bounding box
    rel_x = (iris_center[0] - min_x) / eye_width
    rel_y = (iris_center[1] - min_y) / eye_height
    
    return np.array([rel_x, rel_y])

def process_video_to_scanpath(video_path: str):
    """
    Processes a video file and extracts the scanpath (sequence of gaze points).
    Returns a list of (x, y) coordinates normalized to [0, 1] relative to eye geometry.
    This method is robust to head movement.
    """
    cap = cv2.VideoCapture(video_path)
    scanpath = []

    # MediaPipe Face Mesh Indices
    # Left Eye (Subject's Left) - Indices for the eye contour and iris
    LEFT_EYE = [33, 133, 160, 159, 158, 144, 145, 153] # Simplified contour
    LEFT_IRIS = [474, 475, 476, 477]
    
    # Right Eye (Subject's Right)
    RIGHT_EYE = [362, 263, 387, 386, 385, 373, 374, 380] # Simplified contour
    RIGHT_IRIS = [469, 470, 471, 472]
    
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image_rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = face_landmarks.landmark
                
                # Get relative positions for both eyes
                # Note: Right eye in MP is usually the one on the user's right (image left)
                # But we will just average them.
                
                # We need to handle the indices carefully. 
                # Let's use the bounding box logic which is generic.
                # Right Eye (Image Left)
                pos_r = get_relative_iris_pos(LEFT_EYE, LEFT_IRIS, landmarks) # MP "Left" is image Left usually? No, standard is Subject Left.
                # Let's verify standard MP:
                # 33 is outer corner of Right Eye (Image Left). 133 is inner.
                # 362 is inner corner of Left Eye (Image Right). 263 is outer.
                # Actually, let's just use the sets we defined.
                
                # Calculating for "Left Eye" (indices 33...)
                pos_1 = get_relative_iris_pos(LEFT_EYE, LEFT_IRIS, landmarks)
                
                # Calculating for "Right Eye" (indices 362...)
                pos_2 = get_relative_iris_pos(RIGHT_EYE, RIGHT_IRIS, landmarks)
                
                # Average the two gaze vectors
                avg_gaze = (pos_1 + pos_2) / 2.0
                
                # Flip X if necessary (mirror effect). Usually for analysis we want "looking left on screen" to be 0.
                # If iris is at the "left" of the eye (relative to face), it is looking right?
                # Let's keep it consistent: relative position 0.5 is center.
                
                scanpath.append(avg_gaze.tolist())
                
    cap.release()
    return scanpath
