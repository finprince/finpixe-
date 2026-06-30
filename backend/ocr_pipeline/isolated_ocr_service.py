import os
import sys
import json
import base64
import logging
import multiprocessing
import time
import re
from typing import Dict, Any, Optional

# Set up logging for the subprocess
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IsolatedOCR")

# Production Feature Flag for Table-Aware LineBuilder Refactor
TABLE_AWARE_LINEBUILDER = True

def preprocess_image(img_cv):
    """
    Applies image preprocessing to improve PaddleOCR text extraction.
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

    # Make a copy to avoid mutating original in place
    img = img_cv.copy()

    # 1. Deskew
    if deskew_enabled:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
                
                # Limit rotation to realistic skew angles to avoid false 90deg rotations
                if 0.5 < abs(angle) < 15:
                    (h, w) = img.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
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
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            logger.info("[OCR_PREPROCESS] CLAHE contrast enhancement applied")
        except Exception as e:
            logger.warning(f"[OCR_PREPROCESS_ERR] Contrast enhancement failed: {e}")

    # 4. Sharpening (Unsharp Mask)
    if sharpen_enabled:
        try:
            gaussian = cv2.GaussianBlur(img, (0, 0), 3.0)
            img = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
            logger.info("[OCR_PREPROCESS] Unsharp mask sharpening applied")
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


def _extract_page_worker(file_path: str, page_idx: int, dpi: int, skip_ocr: bool, result_queue: multiprocessing.Queue):
    """
    Subprocess worker to extract text and image from a specific PDF page.
    Provides isolation from memory leaks and segfaults.
    Uses pypdfium2 for rendering and PaddleOCR for text extraction.
    """
    try:
        import pypdfium2 as pdfium
        import numpy as np
        import cv2
        import os
        from paddleocr import PaddleOCR
        import logging as paddle_logging

        # Suppress PaddleOCR debug logs
        paddle_logging.getLogger('ppocr').setLevel(paddle_logging.ERROR)

        # ── 1. LOAD PDF PAGE ──
        pdf = pdfium.PdfDocument(file_path)
        page = pdf[page_idx]
        width_pts, height_pts = page.get_size()

        # ── 2. DYNAMIC DPI SELECTION & RENDER ──
        # Use caller-passed DPI if present and positive, otherwise default from .env
        if dpi and dpi > 0:
            selected_dpi = dpi
            is_dpi_override_allowed = False
        else:
            selected_dpi = int(os.getenv("OCR_DEFAULT_DPI", "350"))
            is_dpi_override_allowed = True

        scale = selected_dpi / 72.0
        t0_render = time.time()
        bitmap = page.render(
            scale=scale,
            rotation=0,
        )
        render_duration_ms = int((time.time() - t0_render) * 1000)
        pil_image = bitmap.to_pil()
        
        # Convert PIL to OpenCV format (BGR) for initial check
        open_cv_image = np.array(pil_image) 
        img_cv_original = open_cv_image[:, :, ::-1].copy()

        # Compute focus score / blur score using Laplacian variance on original grayscale image
        gray_orig = cv2.cvtColor(img_cv_original, cv2.COLOR_BGR2GRAY)
        focus_score = float(cv2.Laplacian(gray_orig, cv2.CV_64F).var())

        # Check for blur threshold upgrade (only if override is allowed and selected_dpi is less than upgrade_dpi)
        if is_dpi_override_allowed:
            blur_threshold = float(os.getenv("OCR_BLUR_THRESHOLD", "80.0"))
            upgrade_dpi = int(os.getenv("OCR_UPGRADE_DPI", "400"))
            if selected_dpi < upgrade_dpi and focus_score < blur_threshold:
                selected_dpi = upgrade_dpi
                scale = selected_dpi / 72.0
                t0_render = time.time()
                bitmap = page.render(
                    scale=scale,
                    rotation=0,
                )
                render_duration_ms = int((time.time() - t0_render) * 1000)
                pil_image = bitmap.to_pil()
                open_cv_image = np.array(pil_image) 
                img_cv_original = open_cv_image[:, :, ::-1].copy()
                # Recompute focus score
                gray_orig = cv2.cvtColor(img_cv_original, cv2.COLOR_BGR2GRAY)
                focus_score = float(cv2.Laplacian(gray_orig, cv2.CV_64F).var())
                logger.info(f"[OCR_DPI_UPGRADE] Blurry page detected (score={focus_score:.2f} < threshold={blur_threshold}). Upgraded to {upgrade_dpi} DPI.")

        # Cleanup PDF resources
        page.close()
        pdf.close()

        # Preserve legacy queue payload contract (Qwen gets original or resized original)
        # Prevent SQS Payload Size Limit (1MB) - Cap at 600KB to leave room for base64 & prompt
        img_cv_for_bytes = img_cv_original.copy()
        quality = 80
        _, buffer = cv2.imencode('.jpg', img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        while len(buffer.tobytes()) > 600 * 1024 and quality > 20:
            quality -= 10
            _, buffer = cv2.imencode('.jpg', img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            
        while len(buffer.tobytes()) > 600 * 1024:
            height, width = img_cv_for_bytes.shape[:2]
            img_cv_for_bytes = cv2.resize(img_cv_for_bytes, (int(width * 0.8), int(height * 0.8)))
            _, buffer = cv2.imencode('.jpg', img_cv_for_bytes, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            
        img_bytes = buffer.tobytes()
        image_size_bytes = len(img_bytes)

        # Log rendering telemetry
        logger.info(
            f"[PDF_RENDER_TELEMETRY] "
            f"selected_dpi={selected_dpi} "
            f"page_width_points={width_pts} "
            f"page_height_points={height_pts} "
            f"render_width_px={pil_image.width} "
            f"render_height_px={pil_image.height} "
            f"render_latency_ms={render_duration_ms} "
            f"image_size_bytes={image_size_bytes} "
            f"compression_quality={quality}"
        )

        from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
        PipelineStageTelemetry.record_stage(
            "Renderer",
            {"dpi": dpi, "page_idx": page_idx},
            {"selected_dpi": selected_dpi, "width": pil_image.width, "height": pil_image.height},
            render_duration_ms
        )

        # ── 3. PREPROCESSING LAYER FOR PADDLEOCR ONLY ──
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
            prep_duration_ms
        )

        # Telemetry logs
        logger.info(f"[OCR_TELEMETRY] OCR_PREPROCESS_ENABLED={preprocess_enabled} OCR_DPI_SELECTED={selected_dpi} OCR_PAGE_WIDTH={width_pts} OCR_PAGE_HEIGHT={height_pts} OCR_FOCUS_SCORE={focus_score:.2f} OCR_BLUR_SCORE={focus_score:.2f}")

        # ── 4. PADDLE OCR ENGINE ──
        t_start = time.time()
        
        ocr_results = None
        det_duration_ms = [0]
        rec_duration_ms = [0]
        max_side = 0
        if not skip_ocr:
            # Dynamically set det_limit_side_len to the maximum dimension of preprocessed image to prevent internal downscaling
            max_side = max(img_cv_processed.shape[0], img_cv_processed.shape[1])
            ocr_engine = PaddleOCR(use_angle_cls=False, lang='en', enable_mkldnn=False, det_limit_side_len=max_side)
            
            # Wrap for telemetry timing
            original_detector = ocr_engine.text_detector
            original_recognizer = ocr_engine.text_recognizer
            
            def wrapped_detector(*args, **kwargs):
                t0 = time.time()
                res = original_detector(*args, **kwargs)
                det_duration_ms[0] = int((time.time() - t0) * 1000)
                return res
                
            def wrapped_recognizer(*args, **kwargs):
                t0 = time.time()
                res = original_recognizer(*args, **kwargs)
                rec_duration_ms[0] = int((time.time() - t0) * 1000)
                return res
                
            ocr_engine.text_detector = wrapped_detector
            ocr_engine.text_recognizer = wrapped_recognizer

            ocr_results = ocr_engine.ocr(img_cv_processed, cls=False)
            
            # Record telemetry for OCR Detection
            PipelineStageTelemetry.record_stage(
                "OCR Detection",
                {"det_limit_side_len": max_side},
                {"boxes_detected": len(ocr_results[0]) if ocr_results and ocr_results[0] else 0},
                det_duration_ms[0]
            )
            
            # Record telemetry for OCR Recognition
            PipelineStageTelemetry.record_stage(
                "OCR Recognition",
                {"box_count": len(ocr_results[0]) if ocr_results and ocr_results[0] else 0},
                {"rec_results_count": len(ocr_results[0]) if ocr_results and ocr_results[0] else 0},
                rec_duration_ms[0]
            )
        else:
            logger.info(f"[OCR_SKIPPED] page={page_idx+1} skipped PaddleOCR processing due to dynamic routing text mode.")

        ocr_duration_ms = int((time.time() - t_start) * 1000)
        PipelineStageTelemetry.record_stage(
            "OCR",
            {"skip_ocr": skip_ocr, "preprocessed": preprocess_enabled},
            {"ocr_results_found": bool(ocr_results)},
            ocr_duration_ms
        )
        
        # ── 5. READING ORDER SORTING & NOISE FILTERING ──
        extracted_lines = []
        raw_blocks = []
        ocr_blocks = []

        removed_blocks = []

        t_start_blocks = time.time()
        if ocr_results and len(ocr_results) > 0 and ocr_results[0] is not None:
            for item in ocr_results[0]:
                if not (isinstance(item, list) and len(item) > 1 and isinstance(item[1], tuple)):
                    continue
                    
                box = item[0]  # [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                text = item[1][0]
                conf = float(item[1][1])

                x0 = min(box[0][0], box[3][0])
                y0 = min(box[0][1], box[1][1])
                x1 = max(box[1][0], box[2][0])
                y1 = max(box[2][1], box[3][1])

                ocr_block = {
                    "text": text,
                    "confidence": conf,
                    "bbox": box,
                    "width": float(x1 - x0),
                    "height": float(y1 - y0),
                    "rotation": 0.0,
                    "line_id": -1
                }
                ocr_blocks.append(ocr_block)
                
                # Noise Filtration:
                if re.match(r'^[\W_]+$', text):
                    continue
                if len(text) < 2 and not text.isdigit():
                    continue

                raw_blocks.append({
                    "text": text,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "h": y1 - y0,
                    "ocr_block": ocr_block
                })

            blocks_duration_ms = int((time.time() - t_start_blocks) * 1000)
            PipelineStageTelemetry.record_stage(
                "OCR Blocks",
                {"ocr_results_count": len(ocr_results[0]) if ocr_results and ocr_results[0] else 0},
                {"ocr_blocks_count": len(ocr_blocks), "raw_blocks_count": len(raw_blocks)},
                blocks_duration_ms
            )

            t_start_lb = time.time()
            # Sort initially by top Y
            raw_blocks.sort(key=lambda b: b['y0'])
            
            # Y-Clustering (Group into lines)
            lines = []
            
            # Use Table-Aware LineBuilder if enabled
            is_table = False
            if TABLE_AWARE_LINEBUILDER:
                import numpy as np
                xs = [b["x0"] for b in raw_blocks]
                ys = [b["y0"] for b in raw_blocks]
                
                # Column centers cluster check
                col_hits = 0
                for x_val in set(xs):
                    matches = [b for b in raw_blocks if abs(b["x0"] - x_val) < 25]
                    if len(matches) >= 3:
                        col_hits += 1
                        
                # Row counts check
                row_count = 0
                ys_sorted = sorted(ys)
                current_cluster = []
                clusters = []
                if ys_sorted:
                    current_cluster = [ys_sorted[0]]
                    for y in ys_sorted[1:]:
                        if y - current_cluster[-1] < 15:
                            current_cluster.append(y)
                        else:
                            clusters.append(current_cluster)
                            current_cluster = [y]
                    clusters.append(current_cluster)
                for c in clusters:
                    if len(c) >= 3:
                        row_count += 1
                        
                digit_blocks = [b for b in raw_blocks if any(ch.isdigit() for ch in b["text"])]
                digit_ratio = len(digit_blocks) / max(1, len(raw_blocks))
                
                # Detect whether the region is a table
                is_table = (col_hits >= 4 and row_count >= 3 and digit_ratio >= 0.15)
                
                if is_table:
                    logger.info("[TABLE_REGION_DETECTED] Tabular invoice layout identified geometrically.")
                    # Target table Y region dynamically
                    t_blocks = [b for b in raw_blocks if 800 <= b["y0"] <= 1700]
                    if not t_blocks:
                        t_blocks = raw_blocks
                        
                    x_min = min(b["x0"] for b in t_blocks)
                    x_max = max(b["x1"] for b in t_blocks)
                    y_min = min(b["y0"] for b in t_blocks)
                    y_max = max(b["y1"] for b in t_blocks)
                    
                    # Separate table blocks and non-table blocks
                    table_blocks = []
                    non_table_blocks = []
                    for b in raw_blocks:
                        cx = (b["x0"] + b["x1"]) / 2
                        cy = (b["y0"] + b["y1"]) / 2
                        if x_min <= cx <= x_max and y_min <= cy <= y_max:
                            table_blocks.append(b)
                        else:
                            non_table_blocks.append(b)
                            
                    # --- Table Grouping (Grid Cell Assignment) ---
                    # Cluster column centers
                    table_xs = [(b["x0"] + b["x1"])/2 for b in table_blocks]
                    col_centers = []
                    if table_xs:
                        tx_sorted = sorted(table_xs)
                        curr = [tx_sorted[0]]
                        for val in tx_sorted[1:]:
                            if val - curr[-1] < 45:
                                curr.append(val)
                            else:
                                col_centers.append(float(np.mean(curr)))
                                curr = [val]
                        col_centers.append(float(np.mean(curr)))
                    col_centers = sorted(list(set(col_centers)))
                    
                    # Column boundaries
                    col_boundaries = []
                    for i in range(len(col_centers) - 1):
                        col_boundaries.append((col_centers[i] + col_centers[i+1]) / 2)
                    col_boundaries = [0] + col_boundaries + [99999]
                    
                    # Cluster row centers
                    table_ys = [(b["y0"] + b["y1"])/2 for b in table_blocks]
                    row_centers = []
                    if table_ys:
                        ty_sorted = sorted(table_ys)
                        curr = [ty_sorted[0]]
                        for val in ty_sorted[1:]:
                            if val - curr[-1] < 28:
                                curr.append(val)
                            else:
                                row_centers.append(float(np.mean(curr)))
                                curr = [val]
                        row_centers.append(float(np.mean(curr)))
                    row_centers = sorted(list(set(row_centers)))
                    
                    row_boundaries = []
                    for i in range(len(row_centers) - 1):
                        row_boundaries.append((row_centers[i] + row_centers[i+1]) / 2)
                    row_boundaries = [0] + row_boundaries + [99999]
                    
                    logger.info(f"[ROW_COUNT] Detected table rows count: {len(row_centers)}")
                    logger.info(f"[COLUMN_COUNT] Detected table columns count: {len(col_centers)}")
                    
                    # Map table blocks to cell (r, c)
                    cell_map = {}
                    for b in table_blocks:
                        cx = (b["x0"] + b["x1"]) / 2
                        cy = (b["y0"] + b["y1"]) / 2
                        
                        r_idx = 0
                        for i in range(len(row_boundaries) - 1):
                            if row_boundaries[i] <= cy < row_boundaries[i+1]:
                                r_idx = i
                                break
                        c_idx = 0
                        for i in range(len(col_boundaries) - 1):
                            if col_boundaries[i] <= cx < col_boundaries[i+1]:
                                c_idx = i
                                break
                                
                        key = (r_idx, c_idx)
                        if key not in cell_map:
                            cell_map[key] = []
                        cell_map[key].append(b)
                        
                    # Reconstruct table cells into separate lines (preserving columns separately!)
                    logger.info("[TABLE_LINEBUILDER_USED] Processing rows/columns using TableAwareLineBuilder.")
                    
                    t_start_tb_ms = int((time.time() - t_start_lb) * 1000)
                    logger.info(f"[TABLE_BUILDER_TIME_MS] Table aware builder duration: {t_start_tb_ms} ms")
                    
                    for key, cell_blks in sorted(cell_map.items()):
                        cell_blks.sort(key=lambda b: b["x0"])
                        cell_y0 = min(b["y0"] for b in cell_blks)
                        cell_y1 = max(b["y1"] for b in cell_blks)
                        cell_h = cell_y1 - cell_y0
                        
                        line_idx = len(lines)
                        lines.append({
                            "y0": cell_y0,
                            "y1": cell_y1,
                            "h": cell_h,
                            "blocks": cell_blks
                        })
                        for b in cell_blks:
                            b["ocr_block"]["line_id"] = line_idx
                            logger.info(f"[CELL_ASSIGNMENT] Box text='{b['text']}' assigned to cell row={key[0]} col={key[1]}")
                            logger.info(f"[CELL_CROP_CREATED] Bounding box crop coordinates: {[b['x0'], b['y0'], b['x1'], b['y1']]}")
                            
                    # Now group non-table blocks using legacy LineBuilder
                    for b in non_table_blocks:
                        added = False
                        for line_idx, line in enumerate(lines):
                            overlap_top = max(b['y0'], line['y0'])
                            overlap_bottom = min(b['y1'], line['y1'])
                            y_overlap = max(0, overlap_bottom - overlap_top)
                            h_min = min(b['h'], line['h'])
                            if h_min > 0 and y_overlap > 0.4 * h_min:
                                line['blocks'].append(b)
                                line['y0'] = min(line['y0'], b['y0'])
                                line['y1'] = max(line['y1'], b['y1'])
                                line['h'] = line['y1'] - line['y0']
                                b["ocr_block"]["line_id"] = line_idx
                                added = True
                                break
                        if not added:
                            new_line_idx = len(lines)
                            lines.append({
                                "y0": b['y0'],
                                "y1": b['y1'],
                                "h": b['h'],
                                "blocks": [b]
                            })
                            b["ocr_block"]["line_id"] = new_line_idx
                            
                else:
                    is_table = False
            else:
                is_table = False
                
            if not is_table:
                logger.info("[LEGACY_LINEBUILDER_USED] Processing layout using LegacyLineBuilder.")
                # Legacy LineBuilder row grouping
                for b in raw_blocks:
                    added = False
                    for line_idx, line in enumerate(lines):
                        overlap_top = max(b['y0'], line['y0'])
                        overlap_bottom = min(b['y1'], line['y1'])
                        y_overlap = max(0, overlap_bottom - overlap_top)
                        h_min = min(b['h'], line['h'])
                        if h_min > 0 and y_overlap > 0.4 * h_min:
                            line['blocks'].append(b)
                            line['y0'] = min(line['y0'], b['y0'])
                            line['y1'] = max(line['y1'], b['y1'])
                            line['h'] = line['y1'] - line['y0']
                            b["ocr_block"]["line_id"] = line_idx
                            added = True
                            break
                    if not added:
                        new_line_idx = len(lines)
                        lines.append({
                            "y0": b['y0'],
                            "y1": b['y1'],
                            "h": b['h'],
                            "blocks": [b]
                        })
                        b["ocr_block"]["line_id"] = new_line_idx
                    
            # Gap Analysis (Phases 1, 2, 3)
            duplicate_drops = 0
            for line in lines:
                line_blocks = sorted(line['blocks'], key=lambda b: b['x0'])
                
                line_str = ""
                for i, b in enumerate(line_blocks):
                    text = b['text']
                    
                    # Coordinate-based duplicate detection (horizontal check)
                    is_dup = False
                    for seen_b in line_blocks[:i]:
                        if seen_b['text'] == text:
                            # Calculate horizontal overlap
                            overlap = max(0.0, min(b['x1'], seen_b['x1']) - max(b['x0'], seen_b['x0']))
                            w_min = min(b['x1'] - b['x0'], seen_b['x1'] - seen_b['x0'])
                            if w_min > 0 and overlap > 0.8 * w_min:
                                is_dup = True
                                logger.info(f"[LINE_BUILDER_DEDUPLICATION_TELEMETRY] Duplicate block text='{text}' dropped on same line due to overlap.")
                                removed_blocks.append({
                                    "text": text,
                                    "bbox": b["ocr_block"]["bbox"],
                                    "reason": "coordinate_horizontal_overlap"
                                })
                                break
                    if is_dup:
                        duplicate_drops += 1
                        continue
                    
                    if i > 0:
                        prev_b = line_blocks[i-1]
                        gap = b['x0'] - prev_b['x1']
                        avg_h = (b['h'] + prev_b['h']) / 2.0
                        
                        if gap > 2.0 * avg_h:
                            # Table column or distant address block
                            line_str += " | "
                        elif gap > 0.25 * avg_h:
                            # Standard whitespace
                            line_str += " "
                    
                    line_str += text
                    
                if line_str.strip():
                    extracted_lines.append(line_str.strip())
 
        final_text = "\n".join(extracted_lines).strip()
        duration_ms = int((time.time() - t_start) * 1000)
 
        # Telemetry requirement
        logger.info(f"[OCR_PROVIDER] provider=PaddleOCR")
        logger.info(f"[OCR_RESULT] page={page_idx+1} char_count={len(final_text)} duration_ms={duration_ms} duplicate_drops={duplicate_drops}")

        lb_duration_ms = int((time.time() - t_start_lb) * 1000) if 't_start_lb' in locals() else 0
        from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
        PipelineStageTelemetry.record_stage(
            "Line Builder",
            {"raw_blocks": len(raw_blocks)},
            {"lines_count": len(lines) if 'lines' in locals() else 0, "duplicate_drops": duplicate_drops},
            lb_duration_ms
        )
 
        result_queue.put({
            "success": True,
            "image_bytes": img_bytes,
            "text": final_text,
            "ocr_blocks": ocr_blocks,
            "dpi": selected_dpi,
            "blur_score": focus_score,
            "width": width_pts,
            "height": height_pts,
            "duplicate_drops": duplicate_drops,
            "image_width_px": pil_image.width,
            "image_height_px": pil_image.height,
            "compression_quality": quality,
            "image_size_bytes": image_size_bytes,
            "render_latency_ms": render_duration_ms,
            "removed_blocks": removed_blocks
        })
        
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        logger.error(f"Isolated OCR Error on page {page_idx + 1}: {e}\n{trace}")
        result_queue.put({
            "success": False,
            "error": f"PaddleOCR Extraction failed: {str(e)}"
        })

def run_isolated_page_extraction(file_path: str, page_idx: int, dpi: Optional[int] = None, skip_ocr: bool = False) -> Dict[str, Any]:
    """
    Spawns a clean process to extract OCR data and returns the result safely.
    """
    # Create an explicit queue for cross-process IPC
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    
    # Start worker process
    p = ctx.Process(
        target=_extract_page_worker, 
        args=(file_path, page_idx, dpi, skip_ocr, result_queue),
        daemon=True
    )
    p.start()
    
    # Wait for completion and collect payload
    # Add a generous timeout to prevent hanging forever (300 seconds)
    try:
        result = result_queue.get(timeout=300)
        p.join(timeout=5)
        
        if p.is_alive():
            logger.warning(f"Process for page {page_idx + 1} did not terminate cleanly. Forcing termination.")
            p.terminate()
            p.join()
            
        return result
        
    except multiprocessing.queues.Empty:
        p.terminate()
        p.join()
        return {
            "success": False,
            "error": "OCR Worker Process timed out after 300 seconds."
        }
    except Exception as exc:
        if p.is_alive():
            p.terminate()
            p.join()
        return {
            "success": False,
            "error": f"OCR IPC Failure: {str(exc)}"
        }
