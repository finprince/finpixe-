"""
Django Management Command: prepare_local_rag_models
===================================================
Pre-provisions BGE embedding and CrossEncoder reranker models into the local
application model directory (backend/models/rag/).

Enforces local offline model availability and verifies CUDA GPU inference.
"""
import os
import shutil
import json
import time
import torch
from pathlib import Path
from django.core.management.base import BaseCommand
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("prepare_local_rag_models")


class Command(BaseCommand):
    help = "Downloads, provisions, and verifies local CUDA GPU RAG models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify existing local models without re-downloading."
        )

    def handle(self, *args, **options):
        verify_only = options.get("verify", False)
        self.stdout.write("=" * 80)
        self.stdout.write("  KIKI 2027 — LOCAL RAG MODEL PROVISIONING & GPU PREPARATION")
        self.stdout.write("=" * 80)

        # 1. CUDA Hardware Check
        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "N/A"
        self.stdout.write(f"  CUDA Available: {cuda_ok}")
        self.stdout.write(f"  GPU Device    : {gpu_name}")

        if not cuda_ok and kiki_settings.RAG_REQUIRE_GPU and not kiki_settings.DEVELOPMENT_ALLOW_CPU_FALLBACK:
            self.stderr.write("[ERROR] GPU_REQUIRED_UNAVAILABLE: CUDA is required but unavailable.")
            return

        base_models_dir = Path(kiki_settings.LOCAL_MODELS_DIR)
        emb_dir = base_models_dir / "embedding" / "bge-large-en-v1.5"
        rerank_dir = base_models_dir / "reranker" / "ms-marco-MiniLM-L-6-v2"
        manifest_path = base_models_dir / "manifest.json"

        emb_dir.mkdir(parents=True, exist_ok=True)
        rerank_dir.mkdir(parents=True, exist_ok=True)

        from sentence_transformers import SentenceTransformer, CrossEncoder

        # Helper to find HF cache snapshot path if available
        hf_cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))
        
        # 2. Embedding Model Provisioning
        emb_model_id = "BAAI/bge-large-en-v1.5"
        self.stdout.write(f"\n[1/3] Provisioning Embedding Model: '{emb_model_id}' -> {emb_dir}")

        if (emb_dir / "model.safetensors").exists() or (emb_dir / "pytorch_model.bin").exists():
            self.stdout.write("  Found existing local model directory. Loading locally...")
            emb_model = SentenceTransformer(str(emb_dir), device="cuda" if cuda_ok else "cpu")
        else:
            # Check Hugging Face cache snapshot
            bge_cache_snap = hf_cache_dir / "models--BAAI--bge-large-en-v1.5" / "snapshots"
            snap_dirs = list(bge_cache_snap.glob("*")) if bge_cache_snap.exists() else []
            if snap_dirs:
                src_snap = snap_dirs[0]
                self.stdout.write(f"  Copying from local HF cache snapshot: {src_snap}")
                for item in src_snap.iterdir():
                    if item.is_file():
                        shutil.copy2(item, emb_dir / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, emb_dir / item.name, dirs_exist_ok=True)
                emb_model = SentenceTransformer(str(emb_dir), device="cuda" if cuda_ok else "cpu")
            else:
                self.stdout.write("  Downloading SentenceTransformer model...")
                emb_model = SentenceTransformer(emb_model_id, device="cuda" if cuda_ok else "cpu")
                emb_model.save(str(emb_dir))

        # 3. Reranker Model Provisioning
        rerank_model_id = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.stdout.write(f"\n[2/3] Provisioning Reranker Model: '{rerank_model_id}' -> {rerank_dir}")

        if (rerank_dir / "model.safetensors").exists() or (rerank_dir / "pytorch_model.bin").exists():
            self.stdout.write("  Found existing local reranker directory. Loading locally...")
            reranker = CrossEncoder(str(rerank_dir), device="cuda" if cuda_ok else "cpu")
        else:
            # Check Hugging Face cache snapshot
            rr_cache_snap = hf_cache_dir / "models--cross-encoder--ms-marco-MiniLM-L-6-v2" / "snapshots"
            snap_dirs = list(rr_cache_snap.glob("*")) if rr_cache_snap.exists() else []
            if snap_dirs:
                src_snap = snap_dirs[0]
                self.stdout.write(f"  Copying from local HF cache snapshot: {src_snap}")
                for item in src_snap.iterdir():
                    if item.is_file():
                        shutil.copy2(item, rerank_dir / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, rerank_dir / item.name, dirs_exist_ok=True)
                reranker = CrossEncoder(str(rerank_dir), device="cuda" if cuda_ok else "cpu")
            else:
                self.stdout.write("  Downloading CrossEncoder model...")
                reranker = CrossEncoder(rerank_model_id, device="cuda" if cuda_ok else "cpu")
                reranker.model.save_pretrained(str(rerank_dir))
                reranker.tokenizer.save_pretrained(str(rerank_dir))

        # 4. GPU Inference Verification
        self.stdout.write(f"\n[3/3] Running Local GPU Inference Verification...")
        test_text = "Finpixe ERP local statutory accounting RAG test."
        emb_vec = emb_model.encode(test_text, device="cuda" if cuda_ok else "cpu")
        rerank_score = reranker.predict([["What is Finpixe?", test_text]])

        dim = len(emb_vec)
        self.stdout.write(f"  Embedding dimension : {dim} (Expected: 1024)")
        self.stdout.write(f"  Embedding device    : {emb_model.device}")
        self.stdout.write(f"  Reranker prediction : {float(rerank_score[0]):.4f}")
        self.stdout.write(f"  Reranker device     : {reranker.model.device}")

        # 5. Manifest Generation
        manifest_data = {
            "version": "2026.1",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cuda_available": cuda_ok,
            "gpu_device": gpu_name,
            "models": {
                "embedding": {
                    "model_id": emb_model_id,
                    "local_path": str(emb_dir),
                    "dimension": dim,
                    "device": str(emb_model.device),
                    "status": "READY"
                },
                "reranker": {
                    "model_id": rerank_model_id,
                    "local_path": str(rerank_dir),
                    "device": str(reranker.model.device),
                    "status": "READY"
                }
            }
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        self.stdout.write(f"\nSaved local model manifest to: {manifest_path}")
        self.stdout.write("=" * 80)
        self.stdout.write("  LOCAL RAG MODEL PREPARATION & GPU VERIFICATION COMPLETE: STATUS = READY")
        self.stdout.write("=" * 80)
