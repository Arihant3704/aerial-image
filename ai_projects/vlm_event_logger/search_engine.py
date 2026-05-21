import json
import os
import math
from typing import List, Dict, Any

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    HAS_VECTOR_DB = True
except ImportError:
    HAS_VECTOR_DB = False

class EventSearchEngine:
    def __init__(self, log_json_path: str):
        self.log_json_path = log_json_path
        if not os.path.exists(log_json_path):
            raise FileNotFoundError(f"Log file not found: {log_json_path}")
            
        with open(log_json_path, "r") as f:
            self.logs = json.load(f)
            
        print(f"[Search Engine] Loaded {len(self.logs)} event logs for indexing.")
        
        if HAS_VECTOR_DB:
            print("[Search Engine] ChromaDB and SentenceTransformers found. Initializing Vector Database...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.client = chromadb.Client()
            self.collection = self.client.create_collection(name="video_events")
            self._index_vector_db()
        else:
            print("[Search Engine] Using TF-IDF/Token cosine similarity fallback (no chromadb/sentence-transformers installed).")
            self._index_fallback()

    def _index_vector_db(self):
        documents = [log["description"] for log in self.logs]
        embeddings = self.model.encode(documents).tolist()
        ids = [f"event_{i}" for i in range(len(self.logs))]
        metadatas = [{"timestamp_sec": log["timestamp_sec"], "image_path": log["image_path"]} for log in self.logs]
        
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print("[Search Engine] Indexing complete in ChromaDB.")

    def _index_fallback(self):
        # Build simple vocabulary and term frequency index
        self.doc_tokens = []
        for log in self.logs:
            tokens = set(log["description"].lower().replace(".", "").replace(",", "").split())
            self.doc_tokens.append(tokens)

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        print(f"\n[Search Engine] Query: '{query}'")
        if HAS_VECTOR_DB:
            query_embedding = self.model.encode([query]).tolist()[0]
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            matches = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for idx in range(len(results["documents"][0])):
                    matches.append({
                        "timestamp_sec": results["metadatas"][0][idx]["timestamp_sec"],
                        "description": results["documents"][0][idx],
                        "image_path": results["metadatas"][0][idx]["image_path"],
                        "confidence_score": float(1.0 - results["distances"][0][idx]) # Sim approximation
                    })
            return matches
        else:
            # Simple TF-IDF cosine-similarity mock fallback
            query_tokens = set(query.lower().replace(".", "").replace(",", "").split())
            matches = []
            
            for idx, doc_toks in enumerate(self.doc_tokens):
                intersection = query_tokens.intersection(doc_toks)
                if not intersection:
                    score = 0.0
                else:
                    score = len(intersection) / (math.sqrt(len(query_tokens)) * math.sqrt(len(doc_toks)))
                
                if score > 0.0:
                    matches.append({
                        "timestamp_sec": self.logs[idx]["timestamp_sec"],
                        "description": self.logs[idx]["description"],
                        "image_path": self.logs[idx]["image_path"],
                        "confidence_score": score
                    })
            
            # Sort by score descending
            matches.sort(key=lambda x: x["confidence_score"], reverse=True)
            return matches[:top_k]

if __name__ == "__main__":
    # Test path
    log_file = "logs/vlm_event_log.json"
    if os.path.exists(log_file):
        engine = EventSearchEngine(log_file)
        
        # Test Search Queries
        query1 = "red drone taking off"
        results1 = engine.search(query1, top_k=1)
        for r in results1:
            print(f"  Match at {r['timestamp_sec']:.1f}s (Conf: {r['confidence_score']:.2f}): {r['description']}")
            
        query2 = "security vehicle parked near checkpoint"
        results2 = engine.search(query2, top_k=1)
        for r in results2:
            print(f"  Match at {r['timestamp_sec']:.1f}s (Conf: {r['confidence_score']:.2f}): {r['description']}")
    else:
        print("[Error] Please run logger.py first to generate the event log JSON.")
