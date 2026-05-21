import cv2
import time
import json
import os
from typing import List, Dict, Any
import numpy as np

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class VLMEventLogger:
    def __init__(self, output_dir: str = "logs"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[VLM Logger] Initialized. Output directory set to: {self.output_dir}")

    def extract_keyframes(self, video_path: str, interval_sec: float = 2.0) -> List[Dict[str, Any]]:
        """
        Extract frames from a video at regular intervals and save them as temporary images.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        print(f"[VLM Logger] Video details: {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration.")

        frame_interval = int(fps * interval_sec)
        keyframes = []
        
        frame_idx = 0
        success = True
        
        while success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, frame = cap.read()
            if not success:
                break
                
            timestamp = frame_idx / fps
            img_filename = f"frame_{timestamp:.2f}s.jpg"
            img_path = os.path.join(self.output_dir, img_filename)
            cv2.imwrite(img_path, frame)
            
            keyframes.append({
                "timestamp_sec": timestamp,
                "frame_idx": frame_idx,
                "image_path": img_path
            })
            
            frame_idx += frame_interval
            
        cap.release()
        print(f"[VLM Logger] Extracted {len(keyframes)} keyframes at {interval_sec}s intervals.")
        return keyframes

    def analyze_frame_with_mock_vlm(self, image_path: str, timestamp: float) -> str:
        """
        Fallback VLM analysis function generating detailed semantic descriptions
        for drone-surveillance contexts, simulating VLM predictions.
        """
        # Simulated responses based on typical aerial telemetry scenarios to ensure demo works
        time_int = int(timestamp)
        if time_int % 10 == 0:
            return f"Aerial surveillance view showing a red multirotor drone taking off from the launchpad. The runway markers are clearly visible, and weather conditions appear clear and sunny."
        elif time_int % 10 == 2:
            return f"Drone flight log at {timestamp:.1f}s. The drone is ascending over a parking lot. A silver SUV is seen turning right near the security gate."
        elif time_int % 10 == 4:
            return f"Drone camera view showing high-altitude scouting of an industrial complex. Large silos and storage containers are visible below. No anomalous heat signatures detected."
        elif time_int % 10 == 6:
            return f"Aerial frame captured at {timestamp:.1f}s. Monitoring a perimeter fence line. The terrain is semi-arid with sparse vegetation. A security vehicle is parked near checkpoint 3."
        else:
            return f"Drone hovering at steady altitude. Ground telemetry shows open agricultural fields with grid patterns. The solar panel array is visible in the upper-right corner."

    def process_video(self, video_path: str, interval_sec: float = 2.0) -> List[Dict[str, Any]]:
        """
        Processes a video file, extracting frames and describing them.
        """
        keyframes = self.extract_keyframes(video_path, interval_sec)
        video_logs = []

        print("[VLM Logger] Starting VLM frame analysis...")
        for frame_data in keyframes:
            timestamp = frame_data["timestamp_sec"]
            image_path = frame_data["image_path"]
            
            # In a real environment, you would call a VLM API or local Ollama:
            # description = self.call_local_vlm(image_path)
            description = self.analyze_frame_with_mock_vlm(image_path, timestamp)
            
            log_entry = {
                "timestamp_sec": timestamp,
                "frame_idx": frame_data["frame_idx"],
                "image_path": image_path,
                "description": description
            }
            video_logs.append(log_entry)
            print(f"  - [{timestamp:.2f}s]: {description[:70]}...")
            
        # Save structured log to disk
        log_json_path = os.path.join(self.output_dir, "vlm_event_log.json")
        with open(log_json_path, "w") as f:
            json.dump(video_logs, f, indent=4)
            
        print(f"[VLM Logger] Saved complete event log to: {log_json_path}")
        return video_logs

if __name__ == "__main__":
    # Create a dummy video file if none exists to test the pipeline
    dummy_video = "dummy_flight.mp4"
    if not os.path.exists(dummy_video):
        print("[Setup] Generating a dummy video for testing...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(dummy_video, fourcc, 10.0, (640, 480))
        for i in range(100):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add moving circle to simulate motion
            cv2.circle(frame, (100 + i * 4, 240), 30, (0, 0, 255), -1)
            cv2.putText(frame, f"Time: {i/10.0:.1f}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            out.write(frame)
        out.release()
        
    logger = VLMEventLogger()
    logger.process_video(dummy_video, interval_sec=2.0)
