# VLM Temporal Event Logger & Search Engine

A high-performance pipeline designed to ingest surveillance or flight video streams, extract keyframes, generate dense semantic descriptions using a Vision-Language Model (VLM), and store them in a local Vector Database (ChromaDB) for real-time natural language query and retrieval.

## Features
- **Keyframe Extraction**: Extracts frame sequences from raw flight videos (`.mp4`/`.avi`) at configurable time steps.
- **Visual Description Ingestion**: Interacts with local/remote VLMs (e.g., Qwen-VL, Llava, Ollama) to transcribe video frames into human-readable logs.
- **RAG Integration**: Embeds the frame descriptions and indexes them using ChromaDB.
- **Semantic Search**: Allows querying the video database using natural language (e.g., "when did the red drone land?") to retrieve exact timestamps and keyframe images.

## Architecture
```
[Flight Video] ──> [Keyframe Extractor] ──> [VLM Inference] ──> [Embeddings Model] ──> [ChromaDB Index]
                                                                                               │
                                                                   [Query: "SUV entering"] ────┘
                                                                   [Result: Timestamp & Frame]
```

## Running the Project
1. Run `python logger.py` to extract frames and generate descriptions (saves logs to `logs/vlm_event_log.json`).
2. Run `python search_engine.py` to index the descriptions and perform semantic searches.
