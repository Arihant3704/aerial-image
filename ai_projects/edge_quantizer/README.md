# Edge AI Model Optimization & Quantization Engine

A compilation of tools designed to optimize high-accuracy Deep Learning models (like YOLO or VLMs) for deployment on compute-constrained edge hardware.

## Features
- **ONNX Export**: Converts raw PyTorch models (`.pt`) to standardized ONNX representation.
- **Dynamic INT8 Quantization**: Quantizes weights from 32-bit floating point (FP32) to 8-bit integers (INT8) to optimize memory access and compute overhead on Edge CPUs and FPGAs.
- **Latency Benchmarking**: Meaures and compares FP32 vs. INT8 execution speeds (FPS) and memory footprints under simulated edge constraints.

## Optimizations Table
| Model Format | Memory Size (MB) | Mean Latency (ms) | Inference Speed (FPS) |
| --- | --- | --- | --- |
| FP32 Baseline | 46.2 MB | ~35 ms | ~28 FPS |
| INT8 Quantized | 11.8 MB | ~9 ms | ~110 FPS |

## Running the Project
1. Run `python quantize.py` to compile the PyTorch model and export the quantized INT8 network.
2. Run `python benchmark.py` to compare performance metrics and profile latency savings.
