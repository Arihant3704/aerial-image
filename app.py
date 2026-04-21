from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import tempfile
import time
from georef_engine import process_mosaic

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for the Web UI

@app.route('/stitch', methods=['POST'])
def stitch():
    """
    Endpoint to receive video and CSV files and return the stitched orthomosaic.
    """
    if 'video' not in request.files or 'csv' not in request.files:
        return jsonify({"error": "Missing video or csv file"}), 400

    video_file = request.files['video']
    csv_file = request.files['csv']

    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video.mp4")
        csv_path = os.path.join(tmpdir, "input_telemetry.csv")
        output_path = os.path.join(tmpdir, "mosaic_result.jpg")

        print(f"Saving temporary files to {tmpdir}...")
        video_file.save(video_path)
        csv_file.save(csv_path)

        try:
            # Run the heavy-lifting georeferencing engine
            start_time = time.time()
            process_mosaic(video_path, csv_path, output_path)
            duration = time.time() - start_time
            print(f"Processing completed in {duration:.2f} seconds.")

            # Return the resulting image directly to the browser
            return send_file(output_path, mimetype='image/jpeg', as_attachment=True, download_name="orthomosaic.jpg")
            
        except Exception as e:
            print(f"Error during stitching: {str(e)}")
            return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "DJI Orthomosaic Engine"})

if __name__ == '__main__':
    # Running on 5001 to avoid conflicts with common dev ports
    print("Starting DJI Georeferencing Bridge on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
