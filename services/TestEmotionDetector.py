import cv2
import numpy as np
from keras.models import model_from_json
import collections

# Emotion labels and mental state mapping
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}
mental_state_dict = {
    "Angry": "Stressed or Irritated",
    "Disgusted": "Uncomfortable or Repulsed",
    "Fearful": "Anxious or Scared",
    "Happy": "Positive or Joyful",
    "Neutral": "Calm or Composed",
    "Sad": "Down or Depressed",
    "Surprised": "Astonished or Shocked"
}

# Load the emotion detection model
json_file = open('emotion_model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
emotion_model = model_from_json(loaded_model_json)

# Load weights into the model
emotion_model.load_weights("emotion_model.weights.h5")
print("Loaded model from disk")

# Function to process the video and analyze emotions
def process_video(video_source):
    cap = cv2.VideoCapture(video_source)
    paused = False

    # Track frequency of each detected emotion
    emotion_counter = collections.Counter()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("End of video or unable to read frame.")
                break

            frame = cv2.resize(frame, (1280, 720))
            face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            num_faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

            # Process each face
            for (x, y, w, h) in num_faces:
                cv2.rectangle(frame, (x, y - 50), (x + w, y + h + 10), (0, 255, 0), 4)
                roi_gray_frame = gray_frame[y:y + h, x:x + w]
                cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray_frame, (48, 48)), -1), 0)

                # Predict emotion
                emotion_prediction = emotion_model.predict(cropped_img)
                maxindex = int(np.argmax(emotion_prediction))
                detected_emotion = emotion_dict[maxindex]

                # Update emotion frequency
                emotion_counter[detected_emotion] += 1

                # Display the detected emotion on the frame
                cv2.putText(frame, detected_emotion, (x + 5, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

            # Display the result
            cv2.imshow('Emotion Detection', frame)

        # Check if window was closed
        if cv2.getWindowProperty('Emotion Detection', cv2.WND_PROP_VISIBLE) < 1:
            print("Window closed by user.")
            break

        # Keyboard controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit
            break
        elif key == ord('p'):  # Pause/Resume
            paused = not paused
        elif key == ord('n'):  # Load new video
            cap.release()
            new_video = input("Enter path to new video: ")
            cap = cv2.VideoCapture(new_video)

    cap.release()
    cv2.destroyAllWindows()

    # Display the emotion summary and mental state conclusion
    if emotion_counter:
        print("\nEmotion Analysis Summary:")
        for emotion, count in emotion_counter.items():
            print(f"{emotion}: {count} times")

        # Determine the dominant emotion
        dominant_emotion = emotion_counter.most_common(1)[0][0]
        print(f"\nDominant Emotion: {dominant_emotion}")
        mental_state = mental_state_dict[dominant_emotion]
        print(f"Mental State Conclusion: The person appears to be {mental_state}.")

# Start video processing (default to webcam)
video_source = input("Enter video path or press Enter to use webcam: ") or 0
process_video(video_source)
