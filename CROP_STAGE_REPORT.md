# CROP STAGE REPORT

## 1. Crop Generation Mechanics
- **Mechanism:** Production does NOT generate isolated image crops for individual line items or fields to send to Qwen. 
- **Virtual Cropping:** The LineBuilder coordinates (`x0`, `y0`, `x1`, `y1`) act as virtual cropping identifiers for telemetry tracking and layout analysis. However, no actual physical image crops are sent to the Ollama endpoint.
- **Log Reference:** `[CELL_CROP_CREATED] Bounding box crop coordinates: [321, 1752, 444, 1803]`

## 2. Virtual Coordinates Directory
- **Crop ID:** `crop_buyer_details`
  - Source Page: `1`
  - Coordinates: `[[152.0, 400.0], [755.0, 431.0]]`
  - Width: `603` | Height: `31`
  - OCR Text: `'NaneACCUTUPN FACHNERg PVTLTE'` | Conf: `0.607`
- **Crop ID:** `crop_item_1_hsn`
  - Source Page: `1`
  - Coordinates: `[[757.0, 743.0], [853.0, 776.0]]`
  - Width: `96` | Height: `33`
  - OCR Text: `'9957'` | Conf: `0.571`
- **Crop ID:** `crop_item_4_desc`
  - Source Page: `1`
  - Coordinates: `[[196.0, 1173.0], [742.0, 1258.0]]`
  - Width: `546` | Height: `85`
  - OCR Text: `'e ch f tn alynma'` | Conf: `0.609`
