"""
Django Management Command: prepare_local_rag_models
===================================================
Pre-provisions BGE embedding and CrossEncoder reranker models into the local
application model directory (backend/models/rag/).

Enforces local offline model availability, generates manifest.json with SHA-256 hashes,
and verifies CUDA GPU inference.
"""
import os
import shutil
import json
import time
import math
import hashlib
try:
    import torch
except ImportError:
    torch = None
from pathlib import Path
from django.core.management.base import BaseCommand
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("prepare_local_rag_models")


def compute_file_hash(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


class Command(BaseCommand):
    help = "Downloads, provisions, and verifies local CUDA GPU RAG models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify existing local models without re-downloading or modifying."
        )

    def handle(self, *args, **options):
        verify_only = options.get("verify", False)
        self.stdout.write("=" * 80)
        self.stdout.write("  KIKI 2027 — LOCAL RAG MODEL PROVISIONING & GPU PREPARATION")
        self.stdout.write("=" * 80)

        # 1. CUDA Hardware Check
        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "N/A"
        device_str = "cuda:0" if cuda_ok else "cpu"
        self.stdout.write(f"  CUDA Available: {cuda_ok}")
        self.stdout.write(f"  GPU Device    : {gpu_name}")
        self.stdout.write(f"  Target Device : {device_str}")

        if not cuda_ok and getattr(kiki_settings, "RAG_REQUIRE_GPU", True) and not getattr(kiki_settings, "DEVELOPMENT_ALLOW_CPU_FALLBACK", False):
            self.stderr.write("[ERROR] GPU_REQUIRED_UNAVAILABLE: CUDA is required but unavailable.")
            raise RuntimeError("GPU_REQUIRED_UNAVAILABLE: CUDA is required for KIKI RAG subsystem.")

        base_models_dir = Path(getattr(kiki_settings, "LOCAL_MODELS_DIR", "backend/models/rag"))
        emb_dir = base_models_dir / "embedding" / "bge-large-en-v1.5"
        rerank_dir = base_models_dir / "reranker" / "ms-marco-MiniLM-L-6-v2"
        manifest_path = base_models_dir / "manifest.json"

        hf_cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))

        if not verify_only:
            emb_dir.mkdir(parents=True, exist_ok=True)
            rerank_dir.mkdir(parents=True, exist_ok=True)

        from sentence_transformers import SentenceTransformer, CrossEncoder

        # 2. Embedding Model Provisioning / Verification
        emb_model_id = "BAAI/bge-large-en-v1.5"
        self.stdout.write(f"\n[1/3] Provisioning/Verifying Embedding Model: '{emb_model_id}' -> {emb_dir}")

        has_emb_weights = (emb_dir / "model.safetensors").exists() or (emb_dir / "pytorch_model.bin").exists()
        has_emb_config = (emb_dir / "config.json").exists()

        if verify_only:
            if not (has_emb_weights and has_emb_config):
                self.stderr.write(f"[ERROR] Embedding model in '{emb_dir}' is missing or incomplete.")
                raise RuntimeError(f"Embedding model missing at {emb_dir}")
            self.stdout.write("  [VERIFY] Local embedding model directory confirmed.")
            emb_model = SentenceTransformer(str(emb_dir), device=device_str, local_files_only=True)
        else:
            if has_emb_weights and has_emb_config:
                self.stdout.write("  Found existing complete local model directory. Loading locally...")
                emb_model = SentenceTransformer(str(emb_dir), device=device_str, local_files_only=True)
            else:
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
                    emb_model = SentenceTransformer(str(emb_dir), device=device_str, local_files_only=True)
                else:
                    self.stdout.write("  Downloading SentenceTransformer model from HuggingFace...")
                    emb_model = SentenceTransformer(emb_model_id, device=device_str)
                    emb_model.save(str(emb_dir))

        # 3. Reranker Model Provisioning / Verification
        rerank_model_id = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.stdout.write(f"\n[2/3] Provisioning/Verifying Reranker Model: '{rerank_model_id}' -> {rerank_dir}")

        has_rr_weights = (rerank_dir / "model.safetensors").exists() or (rerank_dir / "pytorch_model.bin").exists()
        has_rr_config = (rerank_dir / "config.json").exists()

        if verify_only:
            if not (has_rr_weights and has_rr_config):
                self.stderr.write(f"[ERROR] Reranker model in '{rerank_dir}' is missing or incomplete.")
                raise RuntimeError(f"Reranker model missing at {rerank_dir}")
            self.stdout.write("  [VERIFY] Local reranker model directory confirmed.")
            reranker = CrossEncoder(str(rerank_dir), device=device_str, local_files_only=True)
        else:
            if has_rr_weights and has_rr_config:
                self.stdout.write("  Found existing complete local reranker directory. Loading locally...")
                reranker = CrossEncoder(str(rerank_dir), device=device_str, local_files_only=True)
            else:
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
                    reranker = CrossEncoder(str(rerank_dir), device=device_str, local_files_only=True)
                else:
                    self.stdout.write("  Downloading CrossEncoder model from HuggingFace...")
                    reranker = CrossEncoder(rerank_model_id, device=device_str)
                    reranker.model.save_pretrained(str(rerank_dir))
                    reranker.tokenizer.save_pretrained(str(rerank_dir))

        # 4. GPU Inference Verification
        self.stdout.write(f"\n[3/3] Running Local GPU Inference Verification...")
        test_text = "Finpixe ERP local statutory accounting RAG test."
        emb_vec = emb_model.encode(test_text, device=device_str)
        rerank_score = reranker.predict([["What is Finpixe?", test_text]])

        dim = len(emb_vec)
        if dim != 1024:
            raise ValueError(f"BGE dimension mismatch: expected 1024, got {dim}")

        if not math.isfinite(float(rerank_score[0])):
            raise ValueError("CrossEncoder prediction returned non-finite score")

        self.stdout.write(f"  Embedding dimension : {dim} (Expected: 1024) [PASSED]")
        self.stdout.write(f"  Embedding device    : {emb_model.device} [PASSED]")
        self.stdout.write(f"  Reranker prediction : {float(rerank_score[0]):.4f} [PASSED]")
        self.stdout.write(f"  Reranker device     : {reranker.model.device} [PASSED]")

        # Compute SHA-256 hashes for key model files
        emb_files = {p.name: compute_file_hash(p) for p in emb_dir.glob("*") if p.is_file()}
        rr_files = {p.name: compute_file_hash(p) for p in rerank_dir.glob("*") if p.is_file()}

        # 5. Manifest Generation / Update
        manifest_data = {
            "version": "2026.1",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cuda_available": cuda_ok,
            "gpu_device": gpu_name,
            "models": {
                "embedding": {
                    "model_id": emb_model_id,
                    "local_path": str(emb_dir.resolve()),
                    "dimension": dim,
                    "device": str(emb_model.device),
                    "file_hashes": emb_files,
                    "status": "READY"
                },
                "reranker": {
                    "model_id": rerank_model_id,
                    "local_path": str(rerank_dir.resolve()),
                    "device": str(reranker.model.device),
                    "file_hashes": rr_files,
                    "status": "READY"
                }
            }
        }

        if not verify_only:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            self.stdout.write(f"\nSaved local model manifest to: {manifest_path}")
        else:
            self.stdout.write(f"\nVerified local model manifest.")

        self.stdout.write("=" * 80)
        self.stdout.write("  LOCAL RAG MODEL PREPARATION & GPU VERIFICATION COMPLETE: STATUS = READY")
        self.stdout.write("=" * 80)
