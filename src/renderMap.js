const CONFIG = {
    // use your own MapBox access token to access your custom maps & usage quota
    // get yours here: https://account.mapbox.com/access-tokens/create
    mapboxAccessToken: 'pk.eyJ1IjoieWVsZGFyYnkiLCJhIjoiY2w3czRlcG5qMGxvbDNxbnVoOTUzeW9nNCJ9.RKnzgCuuLaaFzcFsuZWdFQ',

    // if detections are closer than this constant, combine them into a single marker
    MIN_SEPARATION_OF_DETECTIONS_IN_METERS: 20,

    // wait until a detection is made on this number of distinct frames before showing the marker
    MIN_DETECTIONS_TO_MAKE_VISIBLE: 3
}

// Dependency for map rendering
const mapboxgl = require('mapbox-gl');
window.mapboxgl = mapboxgl;
require('mapbox-gl/dist/mapbox-gl.css');
mapboxgl.accessToken = CONFIG.mapboxAccessToken;

// Dependency for CSV parsing
const Papa = require('papaparse');

// Dependency for Geospatial calculations 
const turf = {
    point: require('@turf/helpers').point,
    rhumbDestination: require('@turf/rhumb-destination').default,
    distance: require('@turf/distance').default
};
window.turf = turf;

// run once to initialize map mode
var renderMap = async function(videoFile, flightLogFile) {
    // render the map UI
    var mapTemplate = require(__dirname + "/templates/map.hbs");
    $('body').html(mapTemplate());

    // parse the flight log from CSV to an array of objects (keyed by header column)
    const observations = await readCSVFile(flightLogFile);

    // Get video duration to match the correct flight log segment
    const videoDuration = await getVideoDuration(videoFile);
    const targetRowCount = Math.round(videoDuration * 10);

    // Filter the flight log for all continuous video segments
    var segments = [];
    var currentSegment = [];
    observations.forEach(o => {
        if (o.isVideo === "1") {
            currentSegment.push(o);
        } else if (currentSegment.length > 5) { // Minimum 0.5s segment
            segments.push(currentSegment);
            currentSegment = [];
        }
    });
    if (currentSegment.length > 5) segments.push(currentSegment);

    // Intelligently choose the best segment based on duration
    var videoObservations = segments[0] || [];
    if (segments.length > 1) {
        videoObservations = _.min(segments, (s) => Math.abs(s.length - targetRowCount));
        console.log(`Matched video (${videoDuration.toFixed(1)}s) to flight segment (${(videoObservations.length/10).toFixed(1)}s) out of ${segments.length} options.`);
    }

    // Calculate bounds of the chosen flight segment
    var top = -Infinity, bottom = Infinity, left = Infinity, right = -Infinity;
    videoObservations.forEach(o => {
        o.latitude = parseFloat(o.latitude);
        o.longitude = parseFloat(o.longitude);
        if(o.longitude > top) top = o.longitude;
        if(o.longitude < bottom) bottom = o.longitude;
        if(o.latitude < left) left = o.latitude;
        if(o.latitude > right) right = o.latitude;
    });
    
    // create a map view with the default streets styling zoomed out to the full world
    const map = new mapboxgl.Map({
        container: 'map',
        zoom: 1,
        style: 'mapbox://styles/mapbox/satellite-v9'
    });
    window.map = map;
    
    // wait until the map is initialized to add things to it
    map.on('load', function() {
        // GeoJSON representing the flight path
        var pathGeoJSON = {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [_.map(videoObservations, function(o) {
                        return [o.longitude, o.latitude];
                    })]
                }
            }
        };

        map.addSource("dronePath", pathGeoJSON);

        // draw a line around the flight path
        map.addLayer({
            'id': 'droneOutline',
            'type': 'line',
            'source': 'dronePath',
            'layout': {},
            'paint': {
                'line-color': '#6706CE',
                'line-width': 3
            }
        });

        // add the video to the map (we'll animate it according to the flight path)
        map.addSource('video', {
            'type': 'video',
            'urls': [URL.createObjectURL(videoFile)],
            'coordinates': [ // start with video in center of path; will get immediately overwritten but needs a default
                [(top+bottom)/2+0.0007, (left+right)/2 - 0.0007],
                [(top+bottom)/2+0.0007, (left+right)/2 + 0.0007],
                [(top+bottom)/2-0.0007, (left+right)/2 + 0.0007],
                [(top+bottom)/2-0.0007, (left+right)/2 - 0.0007]
            ]
        });

        map.addLayer({
            'id': 'video',
            'type': 'raster',
            'source': 'video'
        });

        // zoom the map to the flight path (with 50px of padding)
        map.fitBounds([
            [bottom, left],
            [top, right]
        ], {
            padding: 50
        });

        var videoSource = map.getSource('video');
        
        var fov = 59 * Math.PI / 180; // drone camera field of view in radians; via https://mavicpilots.com/threads/measured-field-of-view-for-mavic-air-59%C2%B0-video-69%C2%B0-photo.85228/
        var fovAtan = Math.tan(fov); // multiply by altitude to get distance across the video's diagonal

        // used to throttle the ML code so it doesn't make the display laggy
        var detectionInFlight = false;
        var lastDetection = 0;

        // keep track of where we've placed markers so we can smooth them out when the same panel is found across multiple frames
        var foundPoints = [];
        window.foundPoints = foundPoints;
        window.confidenceThreshold = 50;
        var isFollowing = false;
        var isPaused = true; 

        // Bind Confidence Slider
        $('#confidence-slider').on('input', function() {
            window.confidenceThreshold = parseInt($(this).val());
            $('#confidence-value').text(window.confidenceThreshold + "%");
            updateDashboardUI();
            updateMarkerVisibility();
        });

        $('#follow-drone-toggle').on('change', function() {
            isFollowing = $(this).is(':checked');
        });

        // setup validation video
        var validationVideo = document.getElementById('validation-video');
        var validationCanvas = document.getElementById('validation-canvas');
        var validationCtx = validationCanvas.getContext('2d');
        validationVideo.src = URL.createObjectURL(videoFile);

        // Global bounds for mosaic stitching
        var mosaicBounds = [
            [top, left],
            [bottom, left],
            [bottom, right],
            [top, right]
        ];

        // helper to initialize mosaic canvas on first use
        var initMosaicSource = function() {
            var mosaicCanvas = document.createElement('canvas');
            mosaicCanvas.width = 4096;
            mosaicCanvas.height = 4096;
            window.mosaicCanvas = mosaicCanvas;
            window.mosaicCtx = mosaicCanvas.getContext('2d');
            window.mosaicCtx.fillStyle = "white";
            window.mosaicCtx.fillRect(0, 0, 4096, 4096);
            
            map.addSource('mosaic', {
                'type': 'canvas',
                'canvas': mosaicCanvas,
                'animate': false,
                'coordinates': mosaicBounds
            });

            map.addLayer({
                'id': 'mosaic-layer',
                'type': 'raster',
                'source': 'mosaic',
                'paint': { 'raster-opacity': 0.8 }
            }, 'video'); // place behind live video
        };

        // helper to map GPS to Mosaic Canvas pixels
        var gpsToMosaicPixels = function(lng, lat) {
            var xPercent = (lng - top) / (bottom - top);
            var yPercent = (lat - left) / (right - left);
            return {
                x: xPercent * 4096,
                y: yPercent * 4096
            };
        };

        // helper to capture thumbnail from video
        var captureThumbnail = function(video, bbox) {
            var cropCanvas = document.createElement('canvas');
            cropCanvas.width = 100;
            cropCanvas.height = 100;
            var ctx = cropCanvas.getContext('2d');
            
            // pad the bbox slightly for context
            var pad = 20;
            ctx.drawImage(
                video, 
                bbox.x - bbox.width/2 - pad, bbox.y - bbox.height/2 - pad, 
                bbox.width + pad*2, bbox.height + pad*2,
                0, 0, 100, 100
            );
            return cropCanvas.toDataURL();
        };



        // helper to export results
        var exportResults = function() {
            var data = _.map(foundPoints, function(p) {
                var coords = p.location.geometry.coordinates;
                return {
                    class: p.class,
                    latitude: coords[1],
                    longitude: coords[0],
                    confidence: p.confidence,
                    observations: p.points.length,
                    thumbnail: p.thumbnail
                };
            });

            var blob = new Blob([JSON.stringify(data, null, 4)], {type: "application/json"});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = `drone_detections_${Date.now()}.json`;
            a.click();
        };

        // playback controls
        var $playBtn = $('#play-pause-btn');
        var $playIcon = $('#play-icon');
        var $scrubberContainer = $('#scrubber-container');
        var $scrubberProgress = $('#scrubber-progress');
        var $currentTimeLabel = $('#current-time');
        var $durationLabel = $('#total-duration');

        var formatTime = function(seconds) {
            var mins = Math.floor(seconds / 60);
            var secs = Math.floor(seconds % 60);
            return (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs;
        };

        $playBtn.click(function() {
            var video = videoSource.video;
            if (isPaused) {
                isPaused = false;
                video.play();
                $playIcon.removeClass('fa-play').addClass('fa-pause');
            } else {
                isPaused = true;
                video.pause();
                $playIcon.removeClass('fa-pause').addClass('fa-play');
            }
        });

        $scrubberContainer.click(function(e) {
            var video = videoSource.video;
            var percent = (e.pageX - $(this).offset().left) / $(this).width();
            video.currentTime = percent * video.duration;
            updateScrubber();
        });

        var updateScrubber = function() {
            var video = videoSource.video;
            if(!video.duration) return;
            var percent = (video.currentTime / video.duration) * 100;
            $scrubberProgress.css('width', percent + '%');
            $currentTimeLabel.text(formatTime(video.currentTime));
            $durationLabel.text(formatTime(video.duration));
        };

        // sync the video with the flight log & use it to update the video's orientation on the map,
        // look for solar panels using our computer vision model, and plot them on the map with markers
        var detectFrame = function() {
            // wait for the video to load
            var video = videoSource.video;
            if(!video || !video.videoWidth) {
                requestAnimationFrame(detectFrame);
                return;
            }

            // sync scrubber
            updateScrubber();

            // stop loop if video ended
            if(video.ended) {
                console.log("Video ended, stopping detection loop.");
                validationVideo.pause();
                $playIcon.removeClass('fa-pause').addClass('fa-play');
                return;
            }

            // run this function on every tick
            requestAnimationFrame(detectFrame);

            // speed the video up 4x so it's not so boring
            video.playbackRate = 4.0;

            // pull video vars into local scope
            var {
                videoWidth,
                videoHeight,
                currentTime
            } = video;
            
            // the flight log observations are recorded every 100ms; pull the one corresponding to the current video timestamp
            var frame = Math.floor(currentTime * 10);
            var observation = videoObservations[frame%videoObservations.length];

            // store the location of the drone
            var lon = parseFloat(observation.longitude);
            var lat = parseFloat(observation.latitude);
            var center = turf.point([lon, lat]);
            var altitude = parseFloat(observation["ascent(feet)"]) * 0.3048; // convert to meters

            // Update camera if following
            if(isFollowing) {
                map.easeTo({
                    center: [lon, lat],
                    duration: 0
                });
            }

            // calculate the ground distance shown (diagonal distance from top-left to bottom-right corner)
            var diagonalDistance = altitude * fovAtan;
            var distance = diagonalDistance/2; // distance (in meters) from center point to any of the 4 corners

            // the direction the drone is pointed
            var bearing = (parseFloat(observation["compass_heading(degrees)"]) - 90) % 360;
            // the number of degrees the top corners of the video are offset from the drone heading
            var offset = Math.atan(videoHeight / videoWidth) * 180 / Math.PI;

            // calculate the GPS coordinates of the video's four corners by starting at the drone's location and
            // traveling `distance` meters in the direction of that corner
            var options = {units: 'meters'};
            var topLeft = turf.rhumbDestination(center, distance, (bearing-offset+180)%360-180, options).geometry.coordinates;
            var topRight = turf.rhumbDestination(center, distance, (bearing+offset+180)%360-180, options).geometry.coordinates;
            var bottomRight = turf.rhumbDestination(center, distance, (bearing-offset)%360-180, options).geometry.coordinates;
            var bottomLeft = turf.rhumbDestination(center, distance, (bearing+offset)%360-180, options).geometry.coordinates;
            
            // orient the video on the map
            videoSource.setCoordinates([
                topRight,
                bottomRight,
                bottomLeft,
                topLeft
            ]);

            // sync validation video
            if(Math.abs(validationVideo.currentTime - currentTime) > 0.1) {
                validationVideo.currentTime = currentTime;
            }
            if(isPaused) validationVideo.pause();
            else validationVideo.play();

            // if the model has loaded, we're not already waiting for a prediction to return,
            // and it's been at least 200ms since we last ran a frame through the vision model,
            // and the mission is NOT paused,
            // run a video frame through our computer vision model to detect & plot solar panels
            if(window.model && !detectionInFlight && Date.now() - lastDetection >= 200 && !isPaused) {
                // pause the video so it doesn't get out of sync
                detectionInFlight = true;
                video.pause();

                // run the current frame through the model
                window.model.detect(video).then(function(predictions) {
                    // draw boxes on validation canvas
                    validationCanvas.width = videoWidth;
                    validationCanvas.height = videoHeight;
                    validationCtx.clearRect(0, 0, videoWidth, videoHeight);
                    validationCtx.strokeStyle = "#6706CE";
                    validationCtx.lineWidth = 4;
                    validationCtx.font = "bold 24px Inter";
                    validationCtx.fillStyle = "#6706CE";

                    _.each(predictions, function(p) {
                        validationCtx.strokeRect(p.bbox.x - p.bbox.width/2, p.bbox.y - p.bbox.height/2, p.bbox.width, p.bbox.height);
                        validationCtx.fillText(p.class + " " + Math.round(p.confidence*100) + "%", p.bbox.x - p.bbox.width/2, p.bbox.y - p.bbox.height/2 - 10);
                    });

                    // for each solar panel detected, convert its x/y position in the video frame to a GPS coordinate
                    _.each(predictions, function(p) {
                        // change coordinate system so the center point of the video is (0, 0) (instead of the top-left point)
                        // this means that (0, 0) is where our drone is and makes our math easier
                        var normalized = [p.bbox.y - videoHeight / 2, p.bbox.x - videoWidth / 2];

                        // calculate the distance and bearing of the solar panel relative to the center point
                        var distanceFromCenterInPixels = Math.sqrt((videoWidth/2-p.bbox.x)*(videoWidth/2-p.bbox.x)+(videoHeight/2-p.bbox.y)*(videoHeight/2-p.bbox.y));
                        var diagonalDistanceInPixels = Math.sqrt(videoWidth*videoWidth + videoHeight*videoHeight);
                        var percentOfDiagonal = distanceFromCenterInPixels / diagonalDistanceInPixels;
                        var distance = percentOfDiagonal * diagonalDistance; // in meters

                        var angle = Math.atan(normalized[0]/(normalized[1]||0.000001)) * 180 / Math.PI;
                        // if the detection is in the right half of the frame we need to rotate it 180 degrees
                        if(normalized[1] >= 0) angle += 180;

                        // use that distance and bearing to get the GPS location of the panel
                        var point = turf.rhumbDestination(center, distance, (bearing + angle)%360, options);

                        // combine detections that are close together so we end up with a single marker per panel
                        // instead of clusters when a panel is detected across multiple frames of the video
                        var duplicate = _.find(foundPoints, function(fp, i) {
                            var distanceFromPoint = turf.distance(point, fp.location, {units: 'kilometers'});
                            if(distanceFromPoint < CONFIG.MIN_SEPARATION_OF_DETECTIONS_IN_METERS/1000) {
                                // if we have already found this panel, average the position of the new observation with
                                // its existing position
                                fp.points.push(point.geometry.coordinates);
                                var location = [0, 0];
                                _.each(fp.points, function(point) {
                                    location[0] += point[0];
                                    location[1] += point[1];
                                });
                                location[0] = location[0]/fp.points.length;
                                location[1] = location[1]/fp.points.length;
                                fp.location = turf.point(location);

                                // update class and confidence if this new view is better
                                if(p.confidence > (fp.confidence || 0)) {
                                    fp.confidence = p.confidence;
                                    fp.class = p.class;
                                    fp.thumbnail = captureThumbnail(video, p.bbox);
                                }

                                // only show a panel if it has been detected at least twice
                                // (this prevents noisy predictions from clogging up the map)
                                if(!fp.marker && fp.points.length >= CONFIG.MIN_DETECTIONS_TO_MAKE_VISIBLE) {
                                    var marker = new mapboxgl.Marker()
                                        .setLngLat(location)
                                        .addTo(map);

                                    fp.marker = marker;
                                } else if(fp.marker) {
                                    // if the marker is already shown, update its position to the new average
                                    fp.marker.setLngLat(location);
                                }

                                // ensure visibility is correct
                                updateMarkerVisibility();

                                return true;
                            }
                        });

                        // if this is a new point, save it
                        if(!duplicate) {
                            foundPoints.push({
                                location: point,
                                points: [point.geometry.coordinates],
                                marker: null,
                                thumbnail: captureThumbnail(video, p.bbox),
                                confidence: p.confidence,
                                class: p.class
                            });
                        }
                    });

                    updateDashboardUI();
                }).finally(function() {
                    // then start the video playing again ONLY if the user hasn't paused
                    detectionInFlight = false;
                    lastDetection = Date.now();
                    if(!isPaused) video.play();
                });
            }
        };

        // start animating & detecting frames
        detectFrame();

        // --- Utility Functions (Inside Scope) ---
        function updateMarkerVisibility() {
            foundPoints.forEach(function(fp) {
                if(fp.marker) {
                    var visible = fp.confidence * 100 >= window.confidenceThreshold;
                    fp.marker.getElement().style.display = visible ? 'block' : 'none';
                }
            });
        }

        function updateDashboardUI() {
            var $list = $('#detections-list');
            var html = "";

            _.sortBy(foundPoints, p => -p.confidence).forEach(function(p) {
                if(p.points.length < CONFIG.MIN_DETECTIONS_TO_MAKE_VISIBLE) return;
                if(p.confidence * 100 < window.confidenceThreshold) return;
                
                var coords = p.location.geometry.coordinates;
                html += `
                    <div class="bg-gray-50 rounded-lg p-3 border border-gray-100 flex items-center space-x-3 hover:border-purple-300 transition-colors cursor-pointer detection-item" data-lng="${coords[0]}" data-lat="${coords[1]}">
                        <img src="${p.thumbnail}" class="w-16 h-16 rounded bg-black object-cover border border-gray-200">
                        <div class="flex-1 min-w-0">
                            <div class="text-[10px] text-purple-600 font-bold uppercase tracking-tight">${p.class || 'Object'} Confirmed</div>
                            <div class="text-xs font-mono text-gray-500 truncate">${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}</div>
                            <div class="flex items-center justify-between mt-1">
                                <div class="text-[10px] text-gray-400">${p.points.length} obs</div>
                                <div class="text-[10px] font-bold text-purple-500">${Math.round(p.confidence * 100)}% conf</div>
                            </div>
                        </div>
                    </div>
                `;
            });

            if(html) {
                $list.html(html);
                $('.detection-item').off('click').on('click', function() {
                    map.flyTo({
                        center: [$(this).data('lng'), $(this).data('lat')],
                        zoom: 19,
                        essential: true
                    });
                });
            } else {
                $list.html('<div class="text-center py-10 text-gray-400 italic">Scanning Area...</div>');
            }
        }

        function captureThumbnail(video, bbox) {
            var cropCanvas = document.createElement('canvas');
            cropCanvas.width = 128;
            cropCanvas.height = 128;
            var ctx = cropCanvas.getContext('2d');
            ctx.drawImage(video, bbox.x - bbox.width/2, bbox.y - bbox.height/2, bbox.width, bbox.height, 0, 0, 128, 128);
            return cropCanvas.toDataURL();
        }

        // --- Batch Mosaic Trigger ---
        $('#run-batch-mosaic-btn').click(async function() {
            if(!map.getSource('mosaic')) initMosaicSource();
            
            isPaused = true;
            videoSource.video.pause();
            $('#play-icon').removeClass('fa-pause').addClass('fa-play');

            const $overlay = $('#batch-overlay');
            const $progress = $('#batch-progress');
            const $status = $('#batch-status');
            const $percent = $('#batch-percent');

            $overlay.removeClass('hidden');
            $status.text("Initializing...");

            // Process every 1 second (10 frames in our log)
            const step = 10; 
            const total = videoObservations.length;
            
            for(let i=0; i<total; i += step) {
                const obs = videoObservations[i];
                const time = i / 10;
                
                // Update Progress
                const p = Math.round((i / total) * 100);
                $progress.css('width', p + '%');
                $percent.text(p + '%');
                $status.text(`Processing frame ${i} of ${total}`);

                // Move video and wait for frame
                videoSource.video.currentTime = time;
                await new Promise(r => {
                    const onSeeked = () => {
                        videoSource.video.removeEventListener('seeked', onSeeked);
                        r();
                    };
                    videoSource.video.addEventListener('seeked', onSeeked);
                    setTimeout(r, 200); // timeout safety
                });

                // Calculate footprint
                const altitude = parseFloat(obs["ascent(feet)"]) * 0.3048;
                const diagonalDistance = altitude * fovAtan;
                const distance = diagonalDistance/2;
                const bearing = (parseFloat(obs["compass_heading(degrees)"]) - 90) % 360;
                const centerPoint = turf.point([parseFloat(obs.longitude), parseFloat(obs.latitude)]);
                const offset = Math.atan(videoSource.video.videoHeight / videoSource.video.videoWidth) * 180 / Math.PI;
                
                const corners = [
                    (bearing+offset+180)%360-180, // TR
                    (bearing-offset)%360-180,     // BR
                    (bearing+offset)%360-180,     // BL
                    (bearing-offset+180)%360-180  // TL
                ].map(b => turf.rhumbDestination(centerPoint, distance, b, {units: 'meters'}).geometry.coordinates);

                const pixels = corners.map(c => gpsToMosaicPixels(c[0], c[1]));

                // Warp and Draw
                window.mosaicCtx.globalAlpha = 1.0;
                drawWarpedImage(window.mosaicCtx, videoSource.video, pixels[3], pixels[0], pixels[1], pixels[2]);
                
                // Debug values on UI
                if(i % 100 === 0) {
                    $status.text(`Debug: p0x=${Math.round(pixels[0].x)} p0y=${Math.round(pixels[0].y)} w=${videoSource.video.videoWidth} b=${Math.round(bearing)}`);
                }
                
                // Allow UI to breathe
                if(i % 50 === 0) await new Promise(r => setTimeout(r, 10));
            }

            $status.text("Finalizing Export...");
            $progress.css('width', '100%');
            $percent.text('100%');

            setTimeout(() => {
                downloadMosaic();
                $overlay.addClass('hidden');
            }, 1000);
        });

        // --- JSON Export ---
        $('#export-json-btn').click(function() {
            const data = JSON.stringify(foundPoints.map(p => ({
                class: p.class,
                confidence: p.confidence,
                location: p.location.geometry.coordinates,
                observations: p.points.length
            })), null, 2);
            const blob = new Blob([data], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'detections.json';
            link.click();
        });
    });
};

const downloadMosaic = function() {
    const canvas = window.mosaicCanvas;
    if (!canvas) return;

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const ctx = exportCanvas.getContext('2d');
    
    // Fill with solid white before drawing so transparency doesn't render as black
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.drawImage(canvas, 0, 0);

    const link = document.createElement('a');
    link.download = `aerial-mosaic-${Date.now()}.png`;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
};

const drawWarpedImage = function(ctx, img, p0, p1, p2, p3) {
    const w = img.videoWidth || img.width;
    const h = img.videoHeight || img.height;
    drawTriangle(ctx, img, 0, 0, w, 0, w, h, p0.x, p0.y, p1.x, p1.y, p2.x, p2.y);
    drawTriangle(ctx, img, 0, 0, w, h, 0, h, p0.x, p0.y, p2.x, p2.y, p3.x, p3.y);
};

const drawTriangle = function(ctx, img, x0, y0, x1, y1, x2, y2, sx0, sy0, sx1, sy1, sx2, sy2) {
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(sx0, sy0);
    ctx.lineTo(sx1, sy1);
    ctx.lineTo(sx2, sy2);
    ctx.closePath();
    ctx.clip();
    const denom = x0 * (y2 - y1) - x1 * y2 + x2 * y1 + (x1 - x2) * y0;
    if (denom === 0) return;
    const m11 = -(y0 * (sx2 - sx1) - y1 * sx2 + y2 * sx1 + (y1 - y2) * sx0) / denom;
    const m12 = (y1 * sy2 - y0 * (sy2 - sy1) - y2 * sy1 - (y1 - y2) * sy0) / denom;
    const m21 = (x0 * (sx2 - sx1) - x1 * sx2 + x2 * sx1 + (x1 - x2) * sx0) / denom;
    const m22 = -(x1 * sy2 - x0 * (sy2 - sy1) - x2 * sy1 - (x1 - x2) * sy0) / denom;
    const dx = (x0 * (y2 * sx1 - y1 * sx2) + sx0 * (x1 * y2 - x2 * y1)) / denom;
    const dy = (x0 * (y2 * sy1 - y1 * sy2) + sy0 * (x1 * y2 - x2 * y1)) / denom;
    ctx.transform(m11, m12, m21, m22, dx, dy);
    ctx.drawImage(img, 0, 0);
    ctx.restore();
};

const getVideoDuration = function(file) {
    return new Promise(function(resolve) {
        var video = document.createElement('video');
        video.preload = 'metadata';
        video.onloadedmetadata = function() {
            window.URL.revokeObjectURL(video.src);
            resolve(video.duration);
        };
        video.onerror = function() { resolve(0); };
        video.src = URL.createObjectURL(file);
    });
};

const readCSVFile = function(file) {
    return new Promise(function(resolve) {
        var reader = new FileReader();
        reader.onload = function (e) {
            var text = e.target.result;
            var results = Papa.parse(text, {
                header: true,
                transformHeader:function(h) { return h.trim(); }
            });
            resolve(results.data);
        }
        reader.readAsText(file);
    });
};

module.exports = renderMap;