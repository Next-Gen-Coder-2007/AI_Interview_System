from flask import Flask, jsonify, render_template
from deepface import DeepFace
import cv2
import threading

app = Flask(__name__)
camera = cv2.VideoCapture(0)

current_emotion = "Neutral"

def detect_emotion():
    global current_emotion
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        try:
            result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
            current_emotion = result[0]['dominant_emotion']
        except:
            current_emotion = "Unknown"
from flask import Response

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

threading.Thread(target=detect_emotion, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/emotion')
def get_emotion():
    return jsonify({'emotion': current_emotion})

if __name__ == '__main__':
    app.run(debug=True)