from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import tempfile
import time
import json
from fpdf import FPDF
from georef_engine import process_mosaic, extract_detection_crops

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for the Web UI

# Global state to track progress
STITCH_PROGRESS = {"status": "idle", "percent": 0}

@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify(STITCH_PROGRESS)

@app.route('/stitch', methods=['POST'])
def stitch():
    """
    Endpoint to receive video and CSV files and return the stitched orthomosaic.
    """
    global STITCH_PROGRESS
    STITCH_PROGRESS = {"status": "starting", "percent": 0}

    if 'video' not in request.files or 'csv' not in request.files:
        return jsonify({"error": "Missing video or csv file"}), 400

    video_file = request.files['video']
    csv_file = request.files['csv']

    tmpdir = tempfile.mkdtemp()
    video_path = os.path.join(tmpdir, "input_video.mp4")
    csv_path = os.path.join(tmpdir, "input_telemetry.csv")
    output_path = os.path.join(tmpdir, "mosaic_result.jpg")

    video_file.save(video_path)
    csv_file.save(csv_path)

    try:
        def update_progress(p):
            STITCH_PROGRESS["percent"] = p
            STITCH_PROGRESS["status"] = "processing"

        process_mosaic(video_path, csv_path, output_path, progress_callback=update_progress)
        
        STITCH_PROGRESS["status"] = "completed"
        STITCH_PROGRESS["percent"] = 100
        
        return send_file(output_path, mimetype='image/jpeg', as_attachment=True, download_name="orthomosaic.jpg")
    except Exception as e:
        STITCH_PROGRESS["status"] = "error"
        return jsonify({"error": str(e)}), 500

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """
    Endpoint to generate a PDF mission report.
    """
    if 'video' not in request.files or 'csv' not in request.files or 'detections' not in request.form:
        return jsonify({"error": "Missing required data (video, csv, or detections)"}), 400

    video_file = request.files['video']
    csv_file = request.files['csv']
    detections = json.loads(request.form['detections'])
    
    tmpdir = tempfile.mkdtemp()
    video_path = os.path.join(tmpdir, "input_video.mp4")
    csv_path = os.path.join(tmpdir, "input_telemetry.csv")
    mosaic_path = os.path.join(tmpdir, "mosaic.jpg")
    pdf_path = os.path.join(tmpdir, "mission_report.pdf")
    crops_dir = os.path.join(tmpdir, "crops")

    video_file.save(video_path)
    csv_file.save(csv_path)

    try:
        # 1. Generate Mosaic for the cover
        process_mosaic(video_path, csv_path, mosaic_path)
        
        # 2. Extract Detection Crops
        saved_crops = extract_detection_crops(video_path, detections, crops_dir)
        
        # 3. Build PDF
        pdf = FPDF()
        pdf.add_page()
        
        # -- Title --
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 20, "Mission Analysis Report", ln=True, align="C")
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        pdf.ln(10)
        
        # -- Orthomosaic Cover --
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Aerial Orthomosaic View", ln=True)
        pdf.image(mosaic_path, x=10, w=190)
        pdf.ln(5)
        
        # -- Detection Summary Table --
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 15, "Detection Inventory", ln=True)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(40, 10, "Target ID", 1)
        pdf.cell(60, 10, "GPS Location", 1)
        pdf.cell(40, 10, "Timestamp", 1)
        pdf.cell(50, 10, "Thumbnail", 1)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for idx, det in enumerate(detections):
            # Row settings
            row_height = 25
            
            # ID
            pdf.cell(40, row_height, f"#{idx+1}", 1)
            
            # GPS
            gps_str = f"{det.get('lat', 0):.6f},\n{det.get('lng', 0):.6f}"
            pdf.multi_cell(60, row_height/2, gps_str, 1)
            
            # Time
            pdf.set_xy(110, pdf.get_y() - row_height)
            pdf.cell(40, row_height, f"{det.get('frame_time_sec', 0):.1f}s", 1)
            
            # Image Crop
            if idx < len(saved_crops):
                curr_x = 155
                curr_y = pdf.get_y() + 2
                pdf.image(saved_crops[idx], x=curr_x, y=curr_y, h=row_height-4)
                pdf.set_xy(150, pdf.get_y())
                pdf.cell(50, row_height, "", 1)
            else:
                pdf.cell(50, row_height, "No Crop", 1)
            
            pdf.ln()

        pdf.output(pdf_path)
        return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name="DJI_Mission_Report.pdf")

    except Exception as e:
        print(f"Report Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "DJI Orthomosaic Engine"})

if __name__ == '__main__':
    print("Starting DJI Georeferencing Bridge on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
