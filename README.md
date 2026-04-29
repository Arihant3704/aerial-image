# Aerial Inference Studio 🛸
### Real-time Drone Georeferencing & Object Detection

![Aerial Inference Studio Demo](demo.gif)


Transform standard DJI drone videos and flight logs into a professional-grade intelligence dashboard. This studio automatically extracts the exact GPS coordinates of objects detected by AI and plots them on a real-time interactive map.

---

## 🌟 Advanced Studio Features

Compared to the original demonstration, this **Inference Studio** includes several high-end analysis tools:

*   **📊 Detection Dashboard**: A real-time sidebar listing every confirmed object with high-resolution thumbnail crops and precise GPS coordinates.
*   **👁️ Side-by-Side Validation**: A floating "Picture-in-Picture" raw video feed with live AI bounding boxes synchronized to the map view.
*   **🎞️ Playback Controls**: Full video controls including play/pause and an interactive scrubber to jump to any point in the flight.
*   **📍 Follow Drone Mode**: Lock the map camera to the drone's position for a smooth "first-person" analysis experience.
*   **🧩 Mosaic Stitching**: Create a persistent "trail" of ground imagery (Orthomosaic) as the drone flies across the map.
*   **📂 Geo-Tagged Export**: Download a full JSON report of all detections, including timestamps, confidence levels, and coordinate data.
*   **🧠 Intelligent Log Matching**: Automatically matches your video file to the correct segment of a multi-recording flight log based on duration.

## 🛠️ Getting Started

### 1. Requirements
*   **Node.js**: For the Web Dashboard.
*   **Python 3.8+**: For the High-Fidelity Georeferencing Engine.
*   **Dependencies**:
    ```bash
    pip install flask flask-cors opencv-python pandas numpy
    ```

### 2. Launch the Studio
Run the automated startup script to initialize both the Web Dashboard and the Python Bridge:
```bash
./start.sh
```

### 3. Analyze Your Mission
1.  **Drop Files**: Drag and drop your DJI video file and its corresponding CSV flight log.
2.  **Generate Orthomosaic**: Click the purple button to trigger the **Python Georeferencing Bridge**. This will process the video at high-resolution with OpenCV-powered perspective warping.
3.  **Filter**: Use the **Confidence Slider** to hide low-confidence detections and focus on confirmed targets.
4.  **Export**: Save your mission data as a JSON file or download the finalized orthomosaic map.

---

## Technical Architecture: The Python Bridge 🌉

To overcome browser limitations with large 4K video files and complex linear algebra, this studio uses a **Hybrid Architecture**:

*   **Frontend (JS/Mapbox)**: Handles the real-time interactive mapping, detection lists, and UI controls.
*   **Backend (Python/OpenCV)**: A local Flask bridge that performs heavy-duty georeferencing. It projects every frame into a Cartesian meter-space (UTM-like) and uses OpenCV's `warpPerspective` to create gap-free, high-fidelity orthomosaics.

## Run It Locally

* Clone this repo
* Run `npm install` in the main directory
* Run `npm run build:dev` to start a webpack build with livereload
* Open a new terminal window and run `npx serve dist`
* Open `http://localhost:3000` in your browser

## Customize It

This repo can easily be changed to run any custom model trained with [Roboflow](https://app.roboflow.com) including the thousands of [pre-trained models shared on Roboflow Universe](https://universe.roboflow.com/search?q=aerial%20imagery%20top%20down%20view%20trained%20model). Simply swap out your `publishable_key` and the `model` ID and `version` in the `ROBOFLOW_SETTINGS` at the top of [`main.js`](src/main.js).

There are also some additional configuration options available at the top of [`renderMap.js`](src/renderMap.js).

For example, changing the model to `swimming-pool-b6pz4` to use this [swimming pool computer vision model](https://universe.roboflow.com/hruthik-sivakumar/swimming-pool-b6pz4/model/2) from Roboflow Universe changes the functionality from plotting solar panels to plotting pools:

https://user-images.githubusercontent.com/870796/190296751-02b46989-7e18-4fcb-93c4-67e492cff401.mp4

Other ideas for how to use this repo:
* [Search & Rescue](https://universe.roboflow.com/lifesparrow/images-25-8/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* [Monitoring swimmer safety](https://universe.roboflow.com/yolo-training/man-over-board/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true) in triathlons
* Helping governments [identify zoning violations](https://universe.roboflow.com/hruthik-sivakumar/swimming-pool-b6pz4/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* Monitoring core infrastructure like pipelines for [potential hazards like excavators and construction equipment](https://universe.roboflow.com/project-ip0vc/final-75vvh/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true) nearby
* [Finding people with bonfires](https://universe.roboflow.com/srichandana055-gmail-com/fire-and-smoke-videoo/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true) in high risk fire areas
* [Tracking wildlife](https://universe.roboflow.com/elephantdetection-90mt9/newprojectelephant/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* Mapping [oil wells](https://universe.roboflow.com/haritha-r/oilwells/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* Monitoring [land use and tree cover](https://universe.roboflow.com/treedataset-clsqo/tree-top-view/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* [Finding boats](https://universe.roboflow.com/jacob-solawetz/aerial-maritime) fishing in restricted areas
* Counting [cars in parking lots](https://universe.roboflow.com/swee-xiao-qi/parking-lot-availability/browse?queryText=&pageSize=50&startingIndex=0&browseQuery=true)
* [Tracking human rights violations](https://blog.roboflow.com/computer-vision-for-human-rights/)
* [Other Aerial Datasets & Models](https://universe.roboflow.com/browse/aerial) to get your gears turning

### Getting Your Flight Log

You can get the detailed flight log from a DJI drone using [Airdata](https://airdata.com). The [sample video and flight log](https://drive.google.com/drive/folders/1m0lmYyLEQJiaykf821rYtyRvlO5Q_SAf) were taken from a DJI Mavic Air 2. Full details are [in the blog post](https://blog.roboflow.com/georeferencing-drone-videos/).

<img width="659" alt="flighlog" src="https://user-images.githubusercontent.com/870796/190518745-278df36e-1866-4e15-9359-667848598557.png">

### Training a Custom Model

If you can't find a pre-trained model that accurately detects your particular object of interest on [Roboflow Universe](https://universe.roboflow.com) you can create a dataset and train your own custom model using [Roboflow](https://roboflow.com).

Roboflow is an end-to-end computer vision platform that has helped over 100,000 developers use computer vision. The easiest way to get started is to [sign up for a free Roboflow account](https://app.roboflow.com) and follow [our quickstart guide](https://docs.roboflow.com/quick-start).

Once you've trained a custom model, update your publishable API Key, model ID, and version in the configuration at the top of [`main.js`](src/main.js).

## ✅ Recent Contributions

We have recently upgraded this studio with high-end features originally listed as roadmap items:
*   **📂 Data Export**: Professional-grade geo-tagged JSON export for all AI detections.
*   **📄 Professional PDF Reports**: Automated generation of mission analysis documents with cover orthomosaics and target inventories.
*   **🎨 Dynamic AI Switcher**: The ability to swap vision models (Solar, Pools, custom) directly from the UI settings.
*   **🎯 Precision Alignment**: Fixed the 90-degree georeferencing rotation bug for pinpoint marker accuracy.

## 🛠️ Future Roadmap (Contributing)

Pull requests are welcome! Current ideas for deeper analysis tools:

*   **🏔️ Terrain Compensation**: Integrate SRTM or digital elevation models to improve coordinate accuracy in hilly terrain.
*   **🔥 Detection 'Burning'**: Render AI detection markers directly onto the finalized high-res orthomosaic export.
*   **📈 Movement Smoothing**: Implement linear interpolation (LERP) between 10Hz data points for ultra-smooth drone movement.
*   **📦 CLI Processing**: A standalone CLI for processing large batches of missions without the browser.
