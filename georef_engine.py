import cv2
import pandas as pd
import numpy as np
import math
import os
import tempfile

R = 6378137.0

def process_mosaic(video_path, csv_path, output_path, progress_callback=None):
    """
    Processes a drone video and its telemetry CSV to generate a georeferenced orthomosaic.
    """
    print(f"Loading telemetry from {csv_path}...")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Selection logic: Use 'isVideo' column if available, otherwise use all points with lat/lon
    video_rows = df[df['isVideo'].astype(str) == '1'].copy()
    if len(video_rows) == 0:
        video_rows = df.dropna(subset=['latitude', 'longitude']).copy()
        
    if len(video_rows) == 0:
        raise ValueError("No valid telemetry data found in CSV.")

    print(f"Total telemetry points: {len(video_rows)}")

    # Calculate Geospatial Bounds
    min_lng = video_rows['longitude'].min()
    max_lng = video_rows['longitude'].max()
    min_lat = video_rows['latitude'].min()
    max_lat = video_rows['latitude'].max()
    
    mid_lat = (min_lat + max_lat) / 2.0
    span_x_m = math.radians(max_lng - min_lng) * R * math.cos(math.radians(mid_lat))
    span_y_m = math.radians(max_lat - min_lat) * R
    
    # Add Margin (200 meters padding)
    MARGIN = 200.0
    span_x_m += 2 * MARGIN
    span_y_m += 2 * MARGIN
    
    # Define Canvas Dimensions (respecting aspect ratio)
    MAX_DIM = 4096
    if span_x_m > span_y_m:
        w = MAX_DIM
        h = int(MAX_DIM * (span_y_m / span_x_m))
    else:
        h = MAX_DIM
        w = int(MAX_DIM * (span_x_m / span_y_m))
        
    print(f"Target Mosaic Canvas: {w}x{h}")
    mosaic = np.zeros((h, w, 3), dtype=np.uint8) 
    
    # Center of geometry for relative projection
    cg_lng = (min_lng + max_lng) / 2.0
    cg_lat = (min_lat + max_lat) / 2.0

    def gps_to_pixels(lng, lat):
        dx_m = math.radians(lng - cg_lng) * R * math.cos(math.radians(cg_lat))
        dy_m = math.radians(lat - cg_lat) * R
        px = (dx_m / span_x_m) * w + (w / 2.0)
        py = (h / 2.0) - (dy_m / span_y_m) * h
        return [px, py]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if math.isnan(fps) or fps == 0: fps = 30.0
    
    video_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Processing Step (Capture frame more frequently to fill gaps)
    # 6 means roughly 1 frame every 0.6 seconds (given 10Hz log)
    process_step = 6 
    total_points = len(video_rows)
    
    processed_count = 0
    for i in range(0, total_points, process_step):
        row = video_rows.iloc[i]
        
        # Calculate matching frame index (assuming 10Hz log)
        frame_time_sec = i / 10.0
        frame_idx = int(frame_time_sec * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret: break
            
        alt_ft = float(row.get('ascent(feet)', 100))
        alt_m = alt_ft * 0.3048
        
        # FOV (DJI Mavic 3 / Air 2S approx 60 deg)
        fov_rad = math.radians(60) 
        diagonal_dist = alt_m * math.tan(fov_rad / 2.0) * 2
        
        heading = float(row.get('compass_heading(degrees)', 0))
        lng = float(row['longitude'])
        lat = float(row['latitude'])
        
        # Perspective Corners Calculation
        # Aspect Ratio of frame determines corner angles
        aspect = video_w / video_h
        diag_angle = math.degrees(math.atan(aspect))
        
        # Corner Bearings
        angles = [
            (heading - diag_angle) % 360,     # TL
            (heading + diag_angle) % 360,     # TR
            (heading + 180 - diag_angle) % 360,# BR
            (heading + 180 + diag_angle) % 360 # BL
        ]
        
        dist = diagonal_dist / 2.0
        dst_px_pts = []
        
        for brng in angles:
            b_rad = math.radians(brng)
            d_lat = dist * math.cos(b_rad) / R
            d_lng = dist * math.sin(b_rad) / (R * math.cos(math.radians(lat)))
            c_lng, c_lat = lng + math.degrees(d_lng), lat + math.degrees(d_lat)
            dst_px_pts.append(gps_to_pixels(c_lng, c_lat))
            
        # Warp Perspective
        src_pts = np.float32([[0, 0], [video_w, 0], [video_w, video_h], [0, video_h]])
        dst_pts = np.float32(dst_px_pts)
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(frame, M, (w, h))
        
        # Create mask for overlay
        mask = cv2.warpPerspective(np.ones_like(frame)*255, M, (w, h))
        
        # Update mosaic (Overwrite logic)
        np.copyto(mosaic, warped, where=(mask > 0))
        
        processed_count += 1
        
        # Report progress
        if progress_callback:
            percent = int((i / total_points) * 100)
            progress_callback(percent)

        # Progress logging (every 10% or so)
        if (processed_count % max(1, (total_points // (process_step * 10)))) == 0:
            print(f"Stitching progress: {int((i/total_points)*100)}% (Frame at {frame_time_sec}s)...")

    cv2.imwrite(output_path, mosaic)
    cap.release()
    print(f"Completed! Processed {processed_count} frames. Output saved to {output_path}")
    return output_path
