const ROBOFLOW_SETTINGS = {
    publishable_key: "rf_5w20VzQObTXjJhTjq6kad9ubrm33",
    model: "aerial-solar-panels",
    version: 5,
    threshold: 0.6,
    overlap: 0.5
};

const $ = require("jquery");
window.$ = $;

const _ = require("lodash");
window._ = _;

// Global to store the current model
window.model = null;

// Function to switch model dynamically
window.switchModel = function(modelId, version) {
    console.log(`Switching model to: ${modelId} v${version}`);
    
    // Show a loading state if possible
    $('#model-preset-select').prop('disabled', true);
    
    return roboflow
        .auth({
            publishable_key: ROBOFLOW_SETTINGS.publishable_key
        })
        .load({
            model: modelId,
            version: parseInt(version),
        })
        .then(function(m) {
            m.configure({
                threshold: ROBOFLOW_SETTINGS.threshold,
                overlap: ROBOFLOW_SETTINGS.overlap
            });
            window.model = m;
            $('#model-preset-select').prop('disabled', false);
            console.log("Model swapped successfully!");
            return m;
        })
        .catch(err => {
            alert("Error loading model: " + (err.message || "Invalid Model ID"));
            $('#model-preset-select').prop('disabled', false);
        });
};

$(function() {
    // setup the initial screen which asks users for their video and flight log CSV
    var setupDrop = require(__dirname + "/setupDrop.js");
    setupDrop();

    // Initial load
    window.switchModel(ROBOFLOW_SETTINGS.model, ROBOFLOW_SETTINGS.version);
});