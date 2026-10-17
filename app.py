import cv2

# Connect to your webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Could not open camera!")
    exit()

print("Camera connected successfully!")

while True:
    # Capture the current camera frame
    success, frame = camera.read()

    if not success:
        print("Failed to capture image.")
        break

    # Print information about the captured image
    height, width, channels = frame.shape
    print(f"Capturing image: {width}x{height} pixels", end="\r")

    # Display what the camera sees
    cv2.imshow("Math Scanner Camera", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
print("\nCamera closed.")
