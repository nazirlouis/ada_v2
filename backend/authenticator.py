import face_recognition
import cv2
import asyncio
import os
import base64
import PIL.Image
import io

class FaceAuthenticator:
    def __init__(self, reference_image_path="reference.jpg", on_status_change=None, on_frame=None):
        """
        :param reference_image_path: Path to the user's reference photo.
        :param on_status_change: Async callback(is_authenticated: bool).
        :param on_frame: Async callback(frame_data_b64: str) to send frames to frontend.
        """
        self.reference_image_path = reference_image_path
        self.on_status_change = on_status_change
        self.on_frame = on_frame
        
        self.authenticated = False
        self.running = False
        self.reference_encoding = None

        self._load_reference()

    def _load_reference(self):
        if not os.path.exists(self.reference_image_path):
            print(f"[AUTH] [WARN] Reference file not found at {self.reference_image_path}. Authentication will fail.")
            return

        try:
            print("[AUTH] Loading reference image...")
            # Workaround for numpy 2.x / dlib compatibility issue
            # face_recognition.load_image_file uses PIL, which dlib now rejects due to array layout checks
            import numpy as np
            img_bgr = cv2.imread(self.reference_image_path)
            if img_bgr is None:
                print(f"[AUTH] [ERR] Failed to read image file: {self.reference_image_path}")
                return
            
            # Convert to RGB and enforce contiguous uint8 array
            image = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            image = np.ascontiguousarray(image, dtype=np.uint8)
            
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                self.reference_encoding = encodings[0]
                print("[AUTH] [OK] Reference face encoded successfully.")
            else:
                print("[AUTH] [ERR] No face found in reference image.")
        except Exception as e:
            print(f"[AUTH] [ERR] Error loading reference: {e}")

    async def start_authentication_loop(self):
        if self.authenticated:
            print("[AUTH] Already authenticated.")
            if self.on_status_change:
                await self.on_status_change(True)
            return

        if self.reference_encoding is None:
             print("[AUTH] [ERR] Cannot start auth loop: No reference encoding.")
             # Optionally trigger a failure state here
             return

        self.running = True
        print("[AUTH] Starting camera for authentication...")
        
        # Capture the current (main) event loop
        loop = asyncio.get_running_loop()
        
        # Use a separate thread for blocking camera/CV operations to avoid blocking asyncio loop
        await asyncio.to_thread(self._run_cv_loop, loop)

        print("[AUTH] Authentication loop finished.")
    
    def stop(self):
        print("[AUTH] Stopping authentication loop...")
        self.running = False

    def _run_cv_loop(self, loop):
        # Helper to try opening and reading a frame
        def try_open_camera(index):
            print(f"[AUTH] Trying to open camera with index {index}...")
            cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
            if not cap.isOpened():
                print(f"[AUTH] [ERR] Could not open video device {index}.")
                return None
            
            # Read one frame to verify
            # Some cameras open but fail to read if permissions are missing or device is busy
            ret, frame = cap.read()
            if not ret:
                 print(f"[AUTH] [ERR] Opened device {index} but failed to read first frame.")
                 cap.release()
                 return None
            
            print(f"[AUTH] [OK] Successfully opened and read from device {index}.")
            return cap

        video_capture = try_open_camera(0)
        
        if video_capture is None:
             print("[AUTH] Device 0 failed. Trying device 1...")
             video_capture = try_open_camera(1)

        if video_capture is None:
             print("[AUTH] [ERR] All camera attempts failed. Authentication cannot proceed.")
             self.running = False
             return

        process_this_frame = True
        
        while self.running and not self.authenticated:
            ret, frame = video_capture.read()
            if not ret:
                print("[AUTH] [ERR] Failed to read frame from camera loop.")
                break
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Optimization: Process every other frame
            if process_this_frame:
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                for face_encoding in face_encodings:
                    # See if the face is a match for the known face(s)
                    matches = face_recognition.compare_faces([self.reference_encoding], face_encoding, tolerance=0.6)
                    
                    if True in matches:
                        self.authenticated = True
                        print("[AUTH] [OPEN] FACE RECOGNIZED! Access Granted.")
                        if self.on_status_change:
                            # Run async callback safely from thread using the passed loop
                            asyncio.run_coroutine_threadsafe(self.on_status_change(True), loop)
                        self.running = False # Stop loop
                        break # Exit for loop

            process_this_frame = not process_this_frame

            # Send frame to frontend if callback exists
            if self.on_frame:
                 # Resize for performance sending over socket
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', small_frame)
                b64_str = base64.b64encode(buffer).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(self.on_frame(b64_str), loop)

        video_capture.release()
