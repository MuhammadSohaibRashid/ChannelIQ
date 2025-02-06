from ultralytics import YOLO
from moviepy.editor import VideoFileClip
from multiprocessing import Manager, Pool, cpu_count
from collections import deque
import cv2
import numpy as np
import os
import webrtcvad
import torch
from tqdm import tqdm
import logging
import json


class EnhancedVideoProcessor:
    def __init__(self, yolo_model_path, cache_dir="cache"):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.face_detector = YOLO(yolo_model_path).to(self.device)
        self.vad = webrtcvad.Vad(3)
        self.cache_dir = cache_dir
        self.setup_logging()
        os.makedirs(cache_dir, exist_ok=True)

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('video_processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def cache_detections(self, video_path, detections):
        """Cache face detection results"""
        cache_path = os.path.join(self.cache_dir, f"{os.path.basename(video_path)}_detections.json")
        with open(cache_path, 'w') as f:
            json.dump(detections, f)

    def load_cached_detections(self, video_path):
        """Load cached face detection results"""
        cache_path = os.path.join(self.cache_dir, f"{os.path.basename(video_path)}_detections.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    def preprocess_frame(self, frame):
        """Enhance frame quality before processing"""
        # Denoise the frame
        if frame.shape[1] > 1920:  # Only denoise high-res videos
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

        # Enhance contrast using CLAHE
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced = cv2.merge((cl, a, b))
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    def adaptive_batch_size(self, frame_count, memory_threshold=0.8):
        """Dynamically adjust batch size based on available memory"""
        import psutil
        available_memory = psutil.virtual_memory().available
        total_memory = psutil.virtual_memory().total
        memory_ratio = available_memory / total_memory

        if memory_ratio > memory_threshold:
            return min(200, frame_count // 10)
        else:
            return min(100, frame_count // 20)

    def predict_movement(self, position_buffer):
        """Predict next likely face position using simple linear regression"""
        if len(position_buffer) < 3:
            return None

        x = np.arange(len(position_buffer))
        y = np.array(position_buffer)
        coeffs = np.polyfit(x, y, 1)
        return int(coeffs[0] * (len(position_buffer) + 1) + coeffs[1])

    def process_frame_batch(self, frames, current_positions, speaker_segments):
        """Process a batch of frames in parallel"""
        results = []
        predicted_pos = self.predict_movement(current_positions)

        for frame in frames:
            # Use predicted position to optimize face detection area
            if predicted_pos is not None:
                height, width = frame.shape[:2]
                margin = width // 4
                x1 = max(0, predicted_pos - margin)
                x2 = min(width, predicted_pos + margin)
                roi = frame[:, x1:x2]

                # Detect faces in ROI
                detections = self.face_detector(roi).xyxy[0]

                # Adjust coordinates back to full frame
                if len(detections):
                    detections[:, [0, 2]] += x1
            else:
                detections = self.face_detector(frame).xyxy[0]

            results.append(detections)

        return results

    def run(self, video_path, output_path, target_fps=30):
        """Enhanced video processing pipeline"""
        self.logger.info(f"Starting video processing: {video_path}")

        # Check for cached detections
        cached_detections = self.load_cached_detections(video_path)

        # Initialize video capture
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_fps = cap.get(cv2.CAP_PROP_FPS)

        # Calculate frame sampling for target FPS
        sampling_rate = max(1, round(original_fps / target_fps))

        # Initialize output video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            output_path,
            fourcc,
            target_fps,
            (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        )

        try:
            with Pool(processes=cpu_count()) as pool:
                frames_buffer = []
                positions_buffer = deque(maxlen=30)

                for frame_idx in tqdm(range(0, total_frames, sampling_rate)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frames_buffer.append(self.preprocess_frame(frame))

                    # Process in batches
                    if len(frames_buffer) >= self.adaptive_batch_size(total_frames):
                        batch_results = self.process_frame_batch(
                            frames_buffer,
                            positions_buffer,
                            None  # Add speaker segments if needed
                        )

                        # Process and write frames
                        for frame, detections in zip(frames_buffer, batch_results):
                            processed_frame = self.apply_final_processing(frame, detections)
                            out.write(processed_frame)

                        frames_buffer = []

                # Process remaining frames
                if frames_buffer:
                    batch_results = self.process_frame_batch(
                        frames_buffer,
                        positions_buffer,
                        None
                    )
                    for frame, detections in zip(frames_buffer, batch_results):
                        processed_frame = self.apply_final_processing(frame, detections)
                        out.write(processed_frame)

        except Exception as e:
            self.logger.error(f"Error during processing: {str(e)}")
            raise
        finally:
            cap.release()
            out.release()

        self.logger.info("Processing completed successfully")
        return target_fps

    def apply_final_processing(self, frame, detections):
        """Apply final enhancements and corrections"""
        # Convert detections to face boxes
        face_boxes = []
        if len(detections):
            for det in detections:
                if det[4] > 0.5:  # Confidence threshold
                    face_boxes.append(det[:4].tolist())

        # Apply stabilization and cropping
        result_frame = self.apply_stabilized_crop(frame, face_boxes)

        # Color correction and final touches
        result_frame = cv2.convertScaleAbs(result_frame, alpha=1.1, beta=5)
        return result_frame

    def apply_stabilized_crop(self, frame, face_boxes):
        """Apply stabilized cropping with improved smoothing"""
        height, width = frame.shape[:2]
        target_width = int(height * 9 / 16)

        if face_boxes:
            # Calculate optimal center based on face positions
            centers = [(box[0] + box[2]) / 2 for box in face_boxes]
            current_center = int(np.mean(centers))
        else:
            current_center = width // 2

        # Apply advanced stabilization
        smoothed_center = self.advanced_stabilization(current_center, width)

        # Calculate and apply crop
        x_start = max(0, min(width - target_width, smoothed_center - target_width // 2))
        return frame[:, int(x_start):int(x_start + target_width)]

    def advanced_stabilization(self, current_center, frame_width):
        """Advanced stabilization with motion prediction"""
        # Implementation details for advanced stabilization
        # This could include Kalman filtering or more sophisticated motion prediction
        return current_center  # Placeholder for actual implementation


if __name__ == "__main__":
    processor = EnhancedVideoProcessor(r"C:\Users\aqiba\Desktop\test3-main\test3-main\backend\backend\Clips-Generator\AI-Youtube-Shorts-Generator-main\models\yolov8n.pt")
    processor.run(r"C:\Users\aqiba\Desktop\test3-main\test3-main\backend\backend\Clips-Generator\AI-Youtube-Shorts-Generator-main\cropped_clip_1.mp4", "output_video.mp4")