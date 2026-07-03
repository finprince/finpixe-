# OCR STAGE REPORT

## 1. Original Rendered Page Info
- **File Name:** `Screenshot 2026-06-24 180236.pdf`
- **Render Resolution:** Rendered at 350 DPI to output image shape (2150, 1567, 3).
- **Physical Size:** ~1.98 MB (uncompressed raw PNG in scratch directory).
- **Path:** `scratch/stage4_crop_sent_to_ai.png`

## 2. Image Preprocessing
- **Gray-scaling / Thresholding:** Handled by `ocr_pipeline.isolated_ocr_service.preprocess_image` using Adaptive Threshold Gaussian C preprocessing for contrast resolution.

## 3. PaddleOCR Raw Detections (Target Fields)
| Field | Ground Truth | Detected Box Coordinates | Recognized Text | Confidence |
|---|---|---|---|---|
| **Invoice No** | `VMT25-26/147` | `[[1041.0, 262.0], [1280.0, 269.0], [1278.0, 314.0], [1040.0, 307.0]]` | `'5-26/47'` | `0.861` |
| **Invoice Date** | `30-09-2025` | `[[1041.0, 326.0], [1243.0, 317.0], [1245.0, 348.0], [1042.0, 356.0]]` | `'-04-'` | `0.718` |
| **Vendor Name** | `ULTRA MACHINE TOOLS...` | `[[155.0, 222.0], [534.0, 222.0], [534.0, 244.0], [155.0, 244.0]]` | `'ULTRA MACHINE TOOLS AND SERVICE'` | `0.942` |
| **Vendor GSTIN** | `33BTTPM6743D1ZF` | `[[154.0, 324.0], [512.0, 322.0], [512.0, 345.0], [154.0, 347.0]]` | `'GSTN:338TTP0674301ZF'` | `0.788` |
| **Buyer GSTIN** | `33AABCA5718R1ZD` | `[[152.0, 619.0], [655.0, 618.0], [655.0, 646.0], [152.0, 647.0]]` | `'GSTNUD33AAA58'` | `0.708` |
| **Item 1 HSN** | `998711` | `[[757.0, 743.0], [852.0, 741.0], [853.0, 774.0], [758.0, 776.0]]` | `'9957'` | `0.571` |
| **Item 2-6 HSN** | `"` (ditto marks) | `[[321.0, 1752.0], [444.0, 1760.0], [441.0, 1803.0], [318.0, 1795.0]]` | `'tt'` | `0.524` |
| **Item 4 Desc** | `"turret alignment"` | `[[196.0, 1210.0], [739.0, 1173.0], [742.0, 1221.0], [199.0, 1258.0]]` | `'e ch f tn alynma'` | `0.609` |
| **CGST (Header)** | `1260.00` | `[[1129.0, 1699.0], [1214.0, 1704.0], [1212.0, 1742.0], [1127.0, 1736.0]]` | `'1ALo'` | `0.515` |
| **SGST (Header)** | `1260.00` | `[[1124.0, 1743.0], [1210.0, 1743.0], [1210.0, 1776.0], [1124.0, 1776.0]]` | `'140'` | `0.514` |
