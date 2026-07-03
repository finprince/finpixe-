import os
import sys
import json
import base64
import logging
import multiprocessing
import time
import re
from typing import Dict, Any, Optional

from dotenv import load_dotenv
# Load .env relative to this file's directory: backend/ocr_pipeline/../.env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

# Set up logging for the subprocess
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IsolatedOCR")


# ── UTILITY FUNCTIONS ─────────────────────────────────────────────────────────

def is_valid_gstin(text: str) -> bool:
    pattern = re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$')
    clean = re.sub(r'[^A-Z0-9]', '', text.upper())
    return bool(pattern.match(clean))


def is_valid_date(text: str) -> bool:
    pattern = re.compile(r'^\d{2}[-/]\d{2}[-/]\d{4}$')
    clean = text.strip()
    return bool(pattern.match(clean))


def count_format_matches(text: str) -> int:
    gstins = len(re.findall(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}\b', text.upper()))
    dates = len(re.findall(r'\b\d{2}[-/]\d{2}[-/]\d{4}\b', text))
    return gstins * 3 + dates * 2


# ── IMAGE PREPROCESSING ───────────────────────────────────────────────────────

def preprocess_image(img_cv):
    """
    Applies image preprocessing to improve OCR text extraction quality.
    Configurable via environment variables:
      OCR_DESKEW_ENABLED
      OCR_NOISE_REDUCTION_ENABLED
      OCR_CLAHE_ENABLED
      OCR_SHARPEN_ENABLED
      OCR_BORDER_CLEANUP_ENABLED
    """
    import numpy as np
    import cv2
    import os

    deskew_enabled = os.getenv("OCR_DESKEW_ENABLED", "true").lower() == "true"
    noise_reduction_enabled = os.getenv("OCR_NOISE_REDUCTION_ENABLED", "true").lower() == "true"
    clahe_enabled = os.getenv("OCR_CLAHE_ENABLED", "true").lower() == "true"
    sharpen_enabled = os.getenv("OCR_SHARPEN_ENABLED", "true").lower() == "true"
    border_cleanup_enabled = os.getenv("OCR_BORDER_CLEANUP_ENABLED", "true").lower() == "true"
    border_width = int(os.getenv("OCR_BORDER_CLEANUP_WIDTH", "10"))

    # Load custom parameters from environment
    clahe_clip = float(os.getenv("OCR_CLAHE_CLIP_LIMIT", "2.0"))
    clahe_tile = int(os.getenv("OCR_CLAHE_TILE_GRID_SIZE", "8"))
    sharpen_sigma = float(os.getenv("OCR_SHARPEN_SIGMA", "3.0"))
    sharpen_kernel = int(os.getenv("OCR_SHARPEN_KERNEL_SIZE", "0"))
    sharpen_weight = float(os.getenv("OCR_SHARPEN_WEIGHT", "1.5"))

    # Make a copy to avoid mutating original in place
    img = img_cv.copy()

    # Convert to grayscale to compute image statistics
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    focus_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    std_dev = float(np.std(gray))

    # Adaptive Preprocessing Selection based on image quality statistics
    adaptive_mode = os.getenv("OCR_ADAPTIVE_PREPROCESS_ENABLED", "true").lower() == "true"
    if adaptive_mode:
        blur_thresh = float(os.getenv("OCR_BLUR_THRESHOLD", "80.0"))
        contrast_thresh = float(os.getenv("OCR_CONTRAST_THRESHOLD", "40.0"))

        is_blurry = focus_score < blur_thresh
        is_low_contrast = std_dev < contrast_thresh

        if not is_blurry and not is_low_contrast:
            # High-quality digital/scanned copy — disable heavy filters to prevent distortion
            noise_reduction_enabled = False
            clahe_enabled = False
            sharpen_enabled = False
            logger.info(
                f"[OCR_ADAPTIVE] High-quality page detected "
                f"(focus={focus_score:.1f}, contrast={std_dev:.1f}). "
                f"Disabling preprocessing."
            )
        else:
            clahe_enabled = is_low_contrast
            sharpen_enabled = is_blurry
            logger.info(
                f"[OCR_ADAPTIVE] focus={focus_score:.1f} (blurry={is_blurry}), "
                f"contrast={std_dev:.1f} (low={is_low_contrast})"
            )

    # 1. Deskew
    if deskew_enabled:
        try:
            gray_inv = cv2.bitwise_not(gray)
            thresh = cv2.threshold(gray_inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) > 0:
                rect = cv2.minAreaRect(coords)
                angle = rect[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle

                # Limit rotation to realistic skew angles to avoid false 90-degree rotations
                if 0.5 < abs(angle) < 15:
                    (h, w) = img.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    img = cv2.warpAffine(
                        img, M, (w, h),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE
                    )
                    logger.info(f"[OCR_PREPROCESS] Deskew applied with angle={angle:.2f}°")
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Deskew failed: {e}")

    # 2. Noise Reduction (Bilateral Filter)
    if noise_reduction_enabled:
        try:
            img = cv2.bilateralFilter(img, 9, 75, 75)
            logger.info("[OCR_PREPROCESS] Bilateral noise reduction applied")
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Noise reduction failed: {e}")

    # 3. CLAHE Contrast Enhancement
    if clahe_enabled:
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            logger.info(
                f"[OCR_PREPROCESS] CLAHE contrast enhancement applied "
                f"(clipLimit={clahe_clip}, tileGridSize={clahe_tile})"
            )
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Contrast enhancement failed: {e}")

    # 4. Sharpening (Unsharp Mask)
    if sharpen_enabled:
        try:
            gaussian = cv2.GaussianBlur(img, (sharpen_kernel, sharpen_kernel), sharpen_sigma)
            img = cv2.addWeighted(img, sharpen_weight, gaussian, 1.0 - sharpen_weight, 0)
            logger.info(
                f"[OCR_PREPROCESS] Unsharp mask sharpening applied "
                f"(sigma={sharpen_sigma}, weight={sharpen_weight})"
            )
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Sharpening failed: {e}")

    # 5. Border Cleanup
    if border_cleanup_enabled and border_width > 0:
        try:
            h, w = img.shape[:2]
            cv2.rectangle(img, (0, 0), (w, h), (255, 255, 255), thickness=border_width)
            logger.info(f"[OCR_PREPROCESS] Border cleanup applied (width={border_width}px)")
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Border cleanup failed: {e}")

    return img


# ── MISTRAL OCR ENGINE ────────────────────────────────────────────────────────

def _ocr_single_pass(
    img_cv_original,
    page_idx: int,
    selected_dpi: int,
    skip_ocr: bool,
    width_pts: float,
    height_pts: float,
    pil_image,
    focus_score: float,
    render_duration_ms: int,
) -> Dict[str, Any]:
    """
    Mistral OCR single-pass engine.

    Sends the preprocessed page image to the Mistral OCR API and returns a
    normalized internal OCR contract dict. The return signature is identical
    to the previous implementation; no downstream code requires changes.

    Return contract fields:
        success, image_bytes, text, ocr_blocks, dpi, avg_confidence,
        blur_score, width, height, duplicate_drops, image_width_px,
        image_height_px, compression_quality, image_size_bytes,
        render_latency_ms, removed_blocks
    """
    import numpy as np
    import cv2
    import os
    import time

    # ── 3. PREPROCESSING LAYER ──────────────────────────────────────────────
    t_start_prep = time.time()
    preprocess_enabled = os.getenv("OCR_PREPROCESS_ENABLED", "true").lower() == "true"
    if preprocess_enabled:
        img_cv_processed = preprocess_image(img_cv_original)
    else:
        img_cv_processed = img_cv_original.copy()
    prep_duration_ms = int((time.time() - t_start_prep) * 1000)

    from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
    PipelineStageTelemetry.record_stage(
        "Preprocessing",
        {"preprocess_enabled": preprocess_enabled},
        {"processed_shape": img_cv_processed.shape},
        prep_duration_ms,
    )

    logger.info(
        f"[OCR_TELEMETRY] OCR_PREPROCESS_ENABLED={preprocess_enabled} "
        f"OCR_DPI_SELECTED={selected_dpi} "
        f"OCR_PAGE_WIDTH={width_pts} "
        f"OCR_PAGE_HEIGHT={height_pts} "
        f"OCR_FOCUS_SCORE={focus_score:.2f} "
        f"OCR_BLUR_SCORE={focus_score:.2f}"
    )

    # ── 4. MISTRAL OCR ENGINE ────────────────────────────────────────────────
    t_start = time.time()
    ocr_blocks: list = []
    final_text: str = ""

    if not skip_ocr:
        # Encode the preprocessed image as JPEG base64 for the Mistral API.
        # We render with pypdfium2 first (preserving DPI control) then send the
        # rasterised image to Mistral, which gives it the highest-resolution
        # input available.
        encode_quality = int(os.getenv("MISTRAL_OCR_ENCODE_QUALITY", "95"))
        _, jpeg_buffer = cv2.imencode(
            ".jpg",
            img_cv_processed,
            [int(cv2.IMWRITE_JPEG_QUALITY), encode_quality],
        )
        b64_image = base64.b64encode(jpeg_buffer.tobytes()).decode("utf-8")
        img_h, img_w = img_cv_processed.shape[:2]

        # ── Authentication ──────────────────────────────────────────────────
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "[MISTRAL_OCR] MISTRAL_API_KEY environment variable is not set. "
                "Add MISTRAL_API_KEY=<your-key> to backend/.env before running."
            )

        from mistralai.client import Mistral

        mistral_model = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
        max_retries = int(os.getenv("MISTRAL_OCR_MAX_RETRIES", "3"))
        retry_delay_s = float(os.getenv("MISTRAL_OCR_RETRY_DELAY_S", "2.0"))

        client = Mistral(api_key=api_key)

        # ── API call with exponential-backoff retry ─────────────────────────
        response = None
        last_error = None
        for attempt in range(max_retries):
            try:
                response = client.ocr.process(
                    model=mistral_model,
                    document={
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{b64_image}",
                    },
                    include_blocks=True,
                    confidence_scores_granularity="page",
                )
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    wait_s = retry_delay_s * (attempt + 1)
                    logger.warning(
                        f"[MISTRAL_OCR_RETRY] page={page_idx + 1} "
                        f"attempt={attempt + 1}/{max_retries} "
                        f"waiting={wait_s:.1f}s error={exc}"
                    )
                    time.sleep(wait_s)

        if response is None:
            raise RuntimeError(
                f"[MISTRAL_OCR] All {max_retries} attempts failed for page "
                f"{page_idx + 1}. Last error: {last_error}"
            )

        # ── 5. PARSE MISTRAL RESPONSE ────────────────────────────────────────
        pages = getattr(response, "pages", None) or []

        if pages:
            page_data = pages[0]

            # Full-page text in natural reading order from Mistral's markdown.
            # Mistral preserves reading order natively — no geometric
            # reconstruction required.
            final_text = getattr(page_data, "markdown", "") or ""

            blocks = getattr(page_data, "blocks", None) or []

            for block_idx, block in enumerate(blocks):
                # ── Text content ─────────────────────────────────────────
                # Mistral SDK v2.5.1: block text is in block.content
                # (not .text or .markdown as in earlier preview API docs).
                block_text = getattr(block, "content", None) or ""
                if not block_text.strip():
                    continue

                # ── Confidence ────────────────────────────────────────────
                # Blocks do not carry per-block confidence in SDK v2.5.1.
                # Page-level confidence is available via page.confidence_scores.
                # Fall back to 0.95 (Mistral's documented production accuracy).
                page_conf_scores = getattr(page_data, "confidence_scores", None)
                if page_conf_scores is not None:
                    raw_conf = getattr(page_conf_scores, "score", None)
                    conf = float(raw_conf) if raw_conf is not None else 0.95
                else:
                    conf = 0.95

                # ── Bounding box ──────────────────────────────────────────
                # Mistral SDK v2.5.1: flat normalised fields on the block.
                #   block.top_left_x, block.top_left_y     (0.0–1.0)
                #   block.bottom_right_x, block.bottom_right_y  (0.0–1.0)
                # Convert to absolute pixel polygon [[x,y]×4] matching the
                # 4-point format expected by downstream confidence computation.
                tlx = getattr(block, "top_left_x", None)
                tly = getattr(block, "top_left_y", None)
                brx = getattr(block, "bottom_right_x", None)
                bry = getattr(block, "bottom_right_y", None)

                if None not in (tlx, tly, brx, bry):
                    try:
                        # Mistral SDK v2.5.1 returns absolute pixel coordinates.
                        ax0 = float(tlx)
                        ay0 = float(tly)
                        ax1 = float(brx)
                        ay1 = float(bry)
                        bbox_poly = [
                            [ax0, ay0],  # top-left
                            [ax1, ay0],  # top-right
                            [ax1, ay1],  # bottom-right
                            [ax0, ay1],  # bottom-left
                        ]
                    except Exception as bbox_err:
                        logger.warning(
                            f"[MISTRAL_OCR_BBOX_ERR] "
                            f"page={page_idx + 1} block={block_idx} "
                            f"error={bbox_err}"
                        )
                        bbox_poly = [
                            [0.0,          0.0         ],
                            [float(img_w), 0.0         ],
                            [float(img_w), float(img_h)],
                            [0.0,          float(img_h)],
                        ]
                else:
                    # Fallback: full-page bbox if coordinates are missing
                    bbox_poly = [
                        [0.0,          0.0         ],
                        [float(img_w), 0.0         ],
                        [float(img_w), float(img_h)],
                        [0.0,          float(img_h)],
                    ]

                xs = [pt[0] for pt in bbox_poly]
                ys = [pt[1] for pt in bbox_poly]
                x0, y0 = min(xs), min(ys)
                x1, y1 = max(xs), max(ys)

                ocr_blocks.append({
                    "text":       block_text,
                    "confidence": conf,
                    "bbox":       bbox_poly,
                    "width":      float(x1 - x0),
                    "height":     float(y1 - y0),
                    "rotation":   0.0,
                    "line_id":    block_idx,
                })

        # ── Telemetry ────────────────────────────────────────────────────────
        PipelineStageTelemetry.record_stage(
            "OCR Detection",
            {"model": mistral_model, "provider": "MistralOCR"},
            {"blocks_detected": len(ocr_blocks)},
            0,
        )
        PipelineStageTelemetry.record_stage(
            "OCR Recognition",
            {"block_count": len(ocr_blocks)},
            {"text_length": len(final_text)},
            0,
        )

    else:
        logger.info(
            f"[OCR_SKIPPED] page={page_idx + 1} "
            f"skipped Mistral OCR processing due to dynamic routing text mode."
        )

    ocr_duration_ms = int((time.time() - t_start) * 1000)
    PipelineStageTelemetry.record_stage(
        "OCR",
        {"skip_ocr": skip_ocr, "preprocessed": preprocess_enabled},
        {"ocr_blocks_found": len(ocr_blocks)},
        ocr_duration_ms,
    )

    PipelineStageTelemetry.record_stage(
        "Line Builder",
        {"ocr_blocks": len(ocr_blocks)},
        {"text_length": len(final_text), "duplicate_drops": 0},
        0,
    )

    # ── Average confidence ───────────────────────────────────────────────────
    avg_conf = (
        float(np.mean([b["confidence"] for b in ocr_blocks]))
        if ocr_blocks
        else 0.0
    )

    # ── 6. IMAGE BYTES — preserve legacy queue payload contract ─────────────
    # Downstream workers (extraction.py, bank_upload) expect a JPEG ≤ 600 KB
    # as image_bytes for the AI vision model.
    img_cv_for_bytes = img_cv_original.copy()
    quality = 80
    _, buffer = cv2.imencode(
        ".jpg", img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    )
    while len(buffer.tobytes()) > 600 * 1024 and quality > 20:
        quality -= 10
        _, buffer = cv2.imencode(
            ".jpg", img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )

    while len(buffer.tobytes()) > 600 * 1024:
        h_px, w_px = img_cv_for_bytes.shape[:2]
        img_cv_for_bytes = cv2.resize(
            img_cv_for_bytes, (int(w_px * 0.8), int(h_px * 0.8))
        )
        _, buffer = cv2.imencode(
            ".jpg", img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )

    img_bytes = buffer.tobytes()
    image_size_bytes = len(img_bytes)

    return {
        "success":            True,
        "image_bytes":        img_bytes,
        "text":               final_text,
        "ocr_blocks":         ocr_blocks,
        "dpi":                selected_dpi,
        "avg_confidence":     avg_conf,
        "blur_score":         focus_score,
        "width":              width_pts,
        "height":             height_pts,
        "duplicate_drops":    0,
        "image_width_px":     pil_image.width,
        "image_height_px":    pil_image.height,
        "compression_quality": quality,
        "image_size_bytes":   image_size_bytes,
        "render_latency_ms":  render_duration_ms,
        "removed_blocks":     [],
    }


# ── SUBPROCESS WORKER ─────────────────────────────────────────────────────────

def _extract_page_worker(
    file_path: str,
    page_idx: int,
    dpi: int,
    skip_ocr: bool,
    result_queue: multiprocessing.Queue,
):
    """
    Subprocess worker: renders a single PDF page with pypdfium2, then
    dispatches to _ocr_single_pass (Mistral OCR) and places the result on
    the IPC queue. Supports adaptive DPI retry and intelligent result
    selection.
    """
    try:
        import pypdfium2 as pdfium
        import numpy as np
        import cv2
        import os

        # ── 1. LOAD PDF PAGE ─────────────────────────────────────────────────
        pdf = pdfium.PdfDocument(file_path)
        page = pdf[page_idx]
        width_pts, height_pts = page.get_size()

        # Determine rendering DPI
        if dpi and dpi > 0:
            selected_dpi = dpi
            is_dpi_override_allowed = False
        else:
            selected_dpi = int(os.getenv("OCR_DEFAULT_DPI", "350"))
            is_dpi_override_allowed = True

        # ── 2. RENDER PDF PAGE ───────────────────────────────────────────────
        scale = selected_dpi / 72.0
        t0_render = time.time()
        bitmap = page.render(scale=scale, rotation=0)
        render_duration_ms = int((time.time() - t0_render) * 1000)
        pil_image = bitmap.to_pil()
        open_cv_image = np.array(pil_image)
        img_cv_original = open_cv_image[:, :, ::-1].copy()

        # Compute focus score for adaptive preprocessing
        gray_orig = cv2.cvtColor(img_cv_original, cv2.COLOR_BGR2GRAY)
        focus_score = float(cv2.Laplacian(gray_orig, cv2.CV_64F).var())

        # ── First pass ───────────────────────────────────────────────────────
        logger.info(
            f"[OCR_PASS_1] Running Mistral OCR at {selected_dpi} DPI "
            f"for page {page_idx + 1}"
        )
        res_pass1 = _ocr_single_pass(
            img_cv_original, page_idx, selected_dpi, skip_ocr,
            width_pts, height_pts, pil_image, focus_score, render_duration_ms,
        )

        # ── Adaptive DPI Retry ───────────────────────────────────────────────
        retry_threshold = float(os.getenv("OCR_PAGE_RETRY_THRESHOLD", "0.75"))
        escalate_dpi = int(os.getenv("OCR_UPGRADE_DPI", "450"))

        if (
            is_dpi_override_allowed
            and res_pass1["avg_confidence"] < retry_threshold
            and selected_dpi < escalate_dpi
        ):
            logger.info(
                f"[OCR_RETRY_TRIGGERED] Page={page_idx + 1} "
                f"avg_conf={res_pass1['avg_confidence']:.3f} < "
                f"threshold={retry_threshold}. "
                f"Escalating to {escalate_dpi} DPI."
            )
            scale_2 = escalate_dpi / 72.0
            t0_render_2 = time.time()
            bitmap_2 = page.render(scale=scale_2, rotation=0)
            render_duration_ms_2 = int((time.time() - t0_render_2) * 1000)
            pil_image_2 = bitmap_2.to_pil()
            open_cv_image_2 = np.array(pil_image_2)
            img_cv_original_2 = open_cv_image_2[:, :, ::-1].copy()

            res_pass2 = _ocr_single_pass(
                img_cv_original_2, page_idx, escalate_dpi, skip_ocr,
                width_pts, height_pts, pil_image_2, focus_score,
                render_duration_ms_2,
            )

            # Intelligent Result Selection: prefer result with more
            # detectable format anchors (GSTIN / dates), then confidence.
            matches1 = count_format_matches(res_pass1["text"])
            matches2 = count_format_matches(res_pass2["text"])

            accept_retry = False
            if matches2 > matches1:
                accept_retry = True
                logger.info(
                    f"[RESULT_SELECTION] Rerun accepted: higher format "
                    f"matches ({matches2} > {matches1})."
                )
            elif matches2 == matches1:
                if res_pass2["avg_confidence"] > res_pass1["avg_confidence"]:
                    accept_retry = True
                    logger.info(
                        f"[RESULT_SELECTION] Rerun accepted: higher average "
                        f"block confidence "
                        f"({res_pass2['avg_confidence']:.3f} > "
                        f"{res_pass1['avg_confidence']:.3f})."
                    )
                else:
                    logger.info(
                        "[RESULT_SELECTION] Rerun rejected: original has "
                        "higher average confidence."
                    )
            else:
                logger.info(
                    "[RESULT_SELECTION] Rerun rejected: original has higher "
                    "format matches."
                )

            res_final = res_pass2 if accept_retry else res_pass1
        else:
            res_final = res_pass1

        # Cleanup PDF resources
        page.close()
        pdf.close()

        logger.info("[OCR_PROVIDER] provider=MistralOCR model=mistral-ocr-latest")
        logger.info(
            f"[OCR_RESULT] page={page_idx + 1} "
            f"char_count={len(res_final['text'])} "
            f"blocks={len(res_final['ocr_blocks'])} "
            f"avg_conf={res_final['avg_confidence']:.3f}"
        )

        result_queue.put(res_final)

    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        logger.error(f"Isolated OCR Error on page {page_idx + 1}: {e}\n{trace}")
        result_queue.put({
            "success": False,
            "error":   f"Mistral OCR Extraction failed: {str(e)}",
        })


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def run_isolated_page_extraction(
    file_path: str,
    page_idx: int,
    dpi: Optional[int] = None,
    skip_ocr: bool = False,
) -> Dict[str, Any]:
    """
    Spawns a clean subprocess to render and OCR a single PDF page using
    Mistral OCR, then returns the result safely via IPC.

    Return contract (identical to previous implementation):
        {
          "success":             bool,
          "image_bytes":         bytes,   # JPEG ≤ 600 KB
          "text":                str,     # full-page text, reading order
          "ocr_blocks":          list,    # [{text, confidence, bbox, ...}]
          "dpi":                 int,
          "avg_confidence":      float,
          "blur_score":          float,
          "width":               float,
          "height":              float,
          "duplicate_drops":     int,
          "image_width_px":      int,
          "image_height_px":     int,
          "compression_quality": int,
          "image_size_bytes":    int,
          "render_latency_ms":   int,
          "removed_blocks":      list,
        }
    On failure:
        {"success": False, "error": str}
    """
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    p = ctx.Process(
        target=_extract_page_worker,
        args=(file_path, page_idx, dpi, skip_ocr, result_queue),
        daemon=True,
    )
    p.start()

    try:
        result = result_queue.get(timeout=300)
        p.join(timeout=5)

        if p.is_alive():
            logger.warning(
                f"Process for page {page_idx + 1} did not terminate cleanly. "
                f"Forcing termination."
            )
            p.terminate()
            p.join()

        return result

    except multiprocessing.queues.Empty:
        p.terminate()
        p.join()
        return {
            "success": False,
            "error":   "OCR Worker Process timed out after 300 seconds.",
        }
    except Exception as exc:
        if p.is_alive():
            p.terminate()
            p.join()
        return {
            "success": False,
            "error":   f"OCR IPC Failure: {str(exc)}",
        }
