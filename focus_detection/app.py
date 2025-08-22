from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import mediapipe as mp
import math

app = Flask(__name__)
mp_face_mesh = mp.solutions.face_mesh
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [263, 387, 385, 362, 380, 373]

def calculate_ear(landmarks, eye_indices, image_width, image_height):
    def dist(a, b):
        return math.hypot((a.x - b.x) * image_width, (a.y - b.y) * image_height)

    p1 = landmarks[eye_indices[1]]
    p2 = landmarks[eye_indices[2]]
    p3 = landmarks[eye_indices[5]]
    p4 = landmarks[eye_indices[4]]
    p0 = landmarks[eye_indices[0]]
    p5 = landmarks[eye_indices[3]]

    vertical1 = dist(p1, p4)
    vertical2 = dist(p2, p3)
    horizontal = dist(p0, p5)

    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear

def analyze_attention(image):
    h, w = image.shape[:2]
    with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return "away"

        face = results.multi_face_landmarks[0]
        landmarks = face.landmark

        left_ear = calculate_ear(landmarks, LEFT_EYE, w, h)
        right_ear = calculate_ear(landmarks, RIGHT_EYE, w, h)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < 0.2:
            return "eyes_closed"

        nose_tip = landmarks[1]
        if nose_tip.x < 0.3 or nose_tip.x > 0.7:
            return "away"

        return "watching"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():
    file = request.data
    npimg = np.frombuffer(file, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    status = analyze_attention(img)
    return jsonify({'status': status})

if __name__ == '__main__':
    app.run(debug=True)
