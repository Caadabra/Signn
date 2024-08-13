import cv2
import mediapipe as mp
import threading
import queue
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class GestureRecognizerThread(threading.Thread):
    # Thread for recognizing gestures using MediaPipe
    def __init__(self, frame_queue, result_queue):
        threading.Thread.__init__(self)
        self.frame_queue = frame_queue  # Queue for incoming video frames
        self.result_queue = result_queue  # Queue for output results
        self.running = True  # Thread control flag
        self.frame_skip = 1  # Default number of frames to skip
        self.recognizer = None  # Gesture recognizer instance
        self.initialize_recognizer()  # Initialize the gesture recognizer

    def initialize_recognizer(self):
        # Initialize the gesture recognizer with the model
        base_options = python.BaseOptions(model_asset_path=r"C:\Users\BlueB\OneDrive\Desktop\School\12DDT\Sign Language Translator\GUI\gesture_recogniser.task")
        options = vision.GestureRecognizerOptions(base_options=base_options)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)

    def run(self):
        # Main loop to process frames from the queue
        frame_count = 0
        while self.running:
            try:
                if frame_count % self.frame_skip == 0:
                    # Process the frame if it's time to do so
                    frame = self.frame_queue.get(timeout=1)
                    annotated_image, gesture_categories, predictions = self.detect_hand_gesture(frame)
                    self.result_queue.put((annotated_image, gesture_categories, predictions))
                else:
                    # Skip the frame
                    self.frame_queue.get(timeout=1)

                frame_count += 1
            except queue.Empty:
                # Continue if the queue is empty
                continue

    def detect_hand_gesture(self, frame):
        # Convert frame to RGB and detect hand gestures
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        recognition_result = self.recognizer.recognize(image)
        
        annotated_image = frame.copy()  # Copy the frame for annotation
        gestures_detected = []  # List to store detected gestures
        predictions = []  # List to store gesture predictions

        # Process detected gestures
        if recognition_result.gestures:
            for i, hand_gestures in enumerate(recognition_result.gestures):
                top_gesture = hand_gestures[0]
                gesture_category = top_gesture.category_name
                certainty = top_gesture.score
                gestures_detected.append((gesture_category, certainty))
                predictions.append((gesture_category, certainty))
                hand_landmarks = recognition_result.hand_landmarks[i]
                
                # Draw landmarks on the frame
                for landmark in hand_landmarks:
                    x = int(landmark.x * annotated_image.shape[1])
                    y = int(landmark.y * annotated_image.shape[0])
                    cv2.circle(annotated_image, (x, y), 5, (255, 0, 0), -1)  # Draw landmarks
        
        return annotated_image, gestures_detected, predictions

    def stop(self):
        # Stop the thread
        self.running = False
