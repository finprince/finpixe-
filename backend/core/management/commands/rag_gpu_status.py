"""
Django Management Command: rag_gpu_status
=========================================
Reports detailed hardware CUDA availability, VRAM allocation/free stats,
PyTorch status, BGE embedding GPU status, CrossEncoder reranker GPU status,
and local Ollama GPU offload status.
"""
try:
    import torch
except ImportError:
    torch = None
import json
import math
import urllib.request
from django.core.management.base import BaseCommand
from core.kiki.config import kiki_settings
from core.kiki.rag.providers.embedding_provider import bge_embedding_provider
from core.kiki.rag.providers.reranker_provider import local_reranker_provider


class Command(BaseCommand):
    help = "Reports empirical KIKI RAG GPU status, VRAM usage, and model device assignments."

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("  KIKI LOCAL RAG GPU STATUS & VRAM AUDIT")
        self.stdout.write("=" * 80)

        # 1. CUDA & Hardware Info
        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "N/A"
        cuda_runtime = torch.version.cuda if cuda_ok else "N/A"
        vram_total_gb = (torch.cuda.get_device_properties(0).total_memory / (1024**3)) if cuda_ok else 0.0
        vram_allocated_gb = (torch.cuda.memory_allocated(0) / (1024**3)) if cuda_ok else 0.0
        vram_reserved_gb = (torch.cuda.memory_reserved(0) / (1024**3)) if cuda_ok else 0.0
        vram_free_gb = vram_total_gb - vram_reserved_gb if cuda_ok else 0.0

        self.stdout.write(f"CUDA Available     : {cuda_ok}")
        self.stdout.write(f"GPU Hardware       : {gpu_name}")
        self.stdout.write(f"CUDA Runtime       : {cuda_runtime}")
        self.stdout.write(f"PyTorch Version    : {torch.__version__}")
        self.stdout.write(f"Total VRAM         : {vram_total_gb:.2f} GB")
        self.stdout.write(f"Allocated VRAM     : {vram_allocated_gb:.2f} GB")
        self.stdout.write(f"Reserved VRAM      : {vram_reserved_gb:.2f} GB")
        self.stdout.write(f"Estimated Free VRAM: {vram_free_gb:.2f} GB")

        # 2. Embedding Model GPU Status & Inference Verification
        self.stdout.write("\n[EMBEDDING PROVIDER]")
        if not bge_embedding_provider.is_loaded():
            bge_embedding_provider.preload()
            
        emb_test_text = "GPU Status Diagnostic Test"
        emb_test_vec = bge_embedding_provider.embed_text(emb_test_text)
        emb_test_ok = len(emb_test_vec) == 1024 and all(math.isfinite(x) for x in emb_test_vec)

        self.stdout.write(f"  Model ID         : {bge_embedding_provider.model_name}")
        self.stdout.write(f"  Local Path       : {bge_embedding_provider._local_path}")
        self.stdout.write(f"  Dimension        : {bge_embedding_provider._dim}")
        self.stdout.write(f"  Device           : {bge_embedding_provider._device}")
        self.stdout.write(f"  Loaded           : {bge_embedding_provider.is_loaded()}")
        self.stdout.write(f"  Test Embedding   : {'PASSED (1024-dim finite)' if emb_test_ok else 'FAILED'}")

        # 3. Reranker Model GPU Status & Inference Verification
        self.stdout.write("\n[RERANKER PROVIDER]")
        if not local_reranker_provider.is_loaded():
            local_reranker_provider.preload()

        rr_test_candidates = [{"text": "Sample doc text 1"}, {"text": "Sample doc text 2"}]
        rr_results = local_reranker_provider.rerank("Sample query", rr_test_candidates)
        rr_test_ok = len(rr_results) > 0 and rr_results[0].get("reranker_available") is True

        self.stdout.write(f"  Model ID         : {local_reranker_provider.model_name}")
        self.stdout.write(f"  Local Path       : {local_reranker_provider._local_path}")
        self.stdout.write(f"  Device           : {local_reranker_provider._device}")
        self.stdout.write(f"  Loaded           : {local_reranker_provider.is_loaded()}")
        self.stdout.write(f"  Test Prediction  : {'PASSED' if rr_test_ok else 'FAILED'}")

        # 4. Ollama GPU Runtime Check
        self.stdout.write("\n[OLLAMA LOCAL RUNTIME]")
        ollama_url = kiki_settings.OLLAMA_BASE_URL
        self.stdout.write(f"  Base URL         : {ollama_url}")
        self.stdout.write(f"  Configured Model : {kiki_settings.REASONING_MODEL}")
        try:
            req = urllib.request.Request(f"{ollama_url}/api/ps")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                running_models = data.get("models", [])
                if running_models:
                    for m in running_models:
                        self.stdout.write(f"  Running Model    : {m.get('name')} | Size: {m.get('size')/(1024**3):.2f} GB")
                else:
                    self.stdout.write("  Running Models   : None currently active in Ollama memory (idle)")
                ollama_status = "READY"
        except Exception as e:
            ollama_status = f"UNREACHABLE ({str(e)})"
            self.stdout.write(f"  Status           : {ollama_status}")

        # 5. Summary Verdict
        gpu_rag_ready = (
            cuda_ok and
            "cuda" in str(bge_embedding_provider._device) and
            "cuda" in str(local_reranker_provider._device) and
            emb_test_ok and
            rr_test_ok
        )
        status_str = "GPU_RAG_READY" if gpu_rag_ready else "GPU_REQUIRED_UNAVAILABLE"

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"  KIKI RAG GPU STATUS VERDICT: {status_str}")
        self.stdout.write("=" * 80)
