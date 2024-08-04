import sys
import cv2
import numpy as np
import queue
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QSpacerItem, QSizePolicy, QDialog, QDialogButtonBox
from PyQt5.QtGui import QPixmap, QImage, QDesktopServices
from PyQt5.QtCore import Qt, QTimer, QUrl
from gestures import GestureRecognizerThread

class PrivacyDialog(QDialog):
    # Dialog for displaying the privacy policy
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Privacy Policy")
        self.setGeometry(200, 200, 400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #c9d1d9;
            }
            QLabel {
                font-size: 14px;
                color: #c9d1d9;
            }
            QDialogButtonBox {
                button-layout: QDialogButtonBox::Center;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Add privacy policy text
        privacy_label = QLabel("This application respects your privacy. It does not store or transmit any video data. "
                               "All processing is done locally on your device. For more information, visit our GitHub page.")
        privacy_label.setWordWrap(True)
        layout.addWidget(privacy_label)
        
        # Add OK button to close the dialog
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

class WebcamWidget(QWidget):
    # Main window for displaying video and recognizing gestures
    def __init__(self):
        super().__init__()
        
        self.video_size = (800, 600)  # Size of video display
        self.activated = 0  # State of the activation switch
        self.last_frame = None
        self.cap = None  # Video capture object
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.gesture_recognizer_thread = GestureRecognizerThread(self.frame_queue, self.result_queue)
        self.gesture_recognizer_thread.start()
        self.initUI()

        self.last_update_time = 0  # Time of the last update
        self.update_cooldown = 2  # Cooldown period in seconds
        self.detected_text = ""  # Text for recognized gestures
        self.last_gesture = None  # Last recognized gesture
        self.gesture_print_cooldown = 2  # Cooldown for printing same gesture

    def initUI(self):
        # Initialize the UI components and layout
        self.setWindowTitle('ASL AI Interpreter')
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117; 
                color: #c9d1d9;
                border-radius: 15px;
            }
            QLabel {
                border-radius: 15px;
            }
            QTextEdit {
                background-color: #161b22; 
                color: #c9d1d9; 
                font-family: Arial; 
                font-size: 14px; 
                border-radius: 15px; 
                border: 2px solid #30363d;
            }
            QPushButton {  
                border-radius: 15px;
                font-size: 14px;
                padding: 10px;
                border: 2px solid #30363d;
                min-width: 80px;
            }
        """)

        # Create video display label
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(*self.video_size)
        self.video_label.setStyleSheet("border: 2px solid #30363d; border-radius: 15px;")
        
        # Create console for displaying recognized gestures
        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setMaximumWidth(400)  # Width of the console

        # Create activation switch button
        self.switch_button = QPushButton('Off', self)
        self.switch_button.setStyleSheet("background-color: #ff6b6b; color: #fff;")
        self.switch_button.clicked.connect(self.toggle_switch)

        # Create privacy button to show privacy policy
        self.privacy_button = QPushButton('Privacy', self)
        self.privacy_button.setStyleSheet("background-color: #161b22; color: #c9d1d9;")
        self.privacy_button.clicked.connect(self.show_privacy_dialog)

        # Create GitHub button to open repository
        self.github_button = QPushButton('GitHub', self)
        self.github_button.setStyleSheet("background-color: #161b22; color: #c9d1d9;")
        self.github_button.clicked.connect(self.open_github)

        # Create button to clear console text
        self.clear_console_button = QPushButton('Clear Console', self)
        self.clear_console_button.setStyleSheet("background-color: #ffcc00; color: #000;")
        self.clear_console_button.clicked.connect(self.clear_console)

        # Layout configuration
        top_left_layout = QHBoxLayout()
        top_left_layout.addWidget(self.privacy_button)
        top_left_layout.addWidget(self.github_button)

        top_right_layout = QHBoxLayout()
        top_right_layout.addWidget(self.clear_console_button)
        top_right_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_right_layout.addWidget(self.switch_button)
        top_right_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        top_layout = QHBoxLayout()
        top_layout.addLayout(top_left_layout)
        top_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_layout.addLayout(top_right_layout)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)

        hbox = QHBoxLayout()
        hbox.addWidget(self.video_label)
        hbox.addWidget(self.console)

        main_layout.addLayout(hbox)

        self.setLayout(main_layout)

        # Set up video capture and timer
        self.cap = cv2.VideoCapture(0)  # Initialize video capture
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)  # Update every 50 milliseconds (20 fps)

    def toggle_switch(self):
        # Toggle the activation switch between 'On' and 'Off'
        if self.activated:
            self.activated = 0
            self.switch_button.setText('Off')
            self.switch_button.setStyleSheet("background-color: #ff6b6b; color: #fff;")
        else:
            self.activated = 1
            self.switch_button.setText('On')
            self.switch_button.setStyleSheet("background-color: #63c76a; color: #fff;")

    def update_frame(self):
        # Capture and update video frame, and process if activated
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                self.last_frame = frame.copy()
                if self.activated:  # Only process the frame if activated
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, self.video_size)
                    h, w, ch = frame.shape
                    bytes_per_line = ch * w
                    convert_to_qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    p = convert_to_qt_format.scaled(self.video_size[0], self.video_size[1], Qt.KeepAspectRatio)
                    self.video_label.setPixmap(QPixmap.fromImage(p))
                    
                    # Send frame to gesture recognizer thread
                    if not self.frame_queue.full():
                        self.frame_queue.put_nowait(frame)

                    # Update gesture display if results are available
                    if not self.result_queue.empty():
                        annotated_image, gesture_categories, predictions = self.result_queue.get_nowait()
                        self.update_gesture_display(annotated_image, gesture_categories)
                else:
                    self.show_blurred_frame()

    def update_gesture_display(self, annotated_image, gesture_categories):
        # Update the display with recognized gestures
        current_time = time.time()
        h, w, ch = annotated_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(annotated_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_qt_format.scaled(self.video_size[0], self.video_size[1], Qt.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(p))

        # Print the current detected gesture every 2 seconds
        if current_time - self.last_update_time >= self.gesture_print_cooldown:
            if gesture_categories:
                for i, (gesture_category, certainty) in enumerate(gesture_categories):
                    self.detected_text += gesture_category
                    self.console.append(f"Gesture {i + 1}: {gesture_category} ({certainty:.2f})")
                    self.last_gesture = gesture_category
            else:
                self.detected_text += " "
                self.last_gesture = None

            self.last_update_time = current_time

        # Clear and update the console text
        self.console.clear()
        self.console.setPlainText(self.detected_text)

    def show_blurred_frame(self):
        # Display a blurred version of the last frame
        if self.last_frame is not None:
            frame = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
            frame = cv2.GaussianBlur(frame, (99, 99), 0)
            frame = cv2.resize(frame, self.video_size)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            convert_to_qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            p = QPixmap.fromImage(convert_to_qt_format)
            self.video_label.setPixmap(p)

    def closeEvent(self, event):
        # Handle closing the application
        self.gesture_recognizer_thread.stop()
        self.cap.release()
        cv2.destroyAllWindows()
        event.accept()

    def show_privacy_dialog(self):
        # Show the privacy policy dialog
        dialog = PrivacyDialog()
        dialog.exec_()

    def open_github(self):
        # Open the GitHub repository in the web browser
        url = QUrl("https://github.com/Caadabra/Signn")  # GitHub URL
        QDesktopServices.openUrl(url)

    def clear_console(self):
        # Clear the console text and reset detected text
        self.console.clear()
        self.detected_text = ""  # Clear detected text as well

if __name__ == '__main__':
    # Run the application
    app = QApplication(sys.argv)
    webcam_widget = WebcamWidget()
    webcam_widget.show()
    sys.exit(app.exec_())
