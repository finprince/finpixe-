import logging
import json
from typing import Any

# Configure logger inheriting from ocr_pipeline
logger = logging.getLogger("ocr_pipeline.pipeline_telemetry")

class PipelineStageTelemetry:
    """
    PHASE 11.9: STRUCTURED PIPELINE TELEMETRY.
    Standardized, robust collector for pipeline stage execution metrics.
    Ensures safe serialization of complex Django and dynamic models without throwing errors.
    """
    @staticmethod
    def safe_serialize(obj: Any) -> Any:
        try:
            if isinstance(obj, dict):
                return {str(k): PipelineStageTelemetry.safe_serialize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [PipelineStageTelemetry.safe_serialize(x) for x in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                # Truncate extremely long strings to prevent log bloat (e.g. base64 or raw text dumps)
                if isinstance(obj, str) and len(obj) > 1000:
                    return obj[:1000] + "... [TRUNCATED]"
                return obj
            else:
                return str(obj)
        except Exception:
            return str(obj)

    @classmethod
    def record_stage(cls, stage_name: str, input_data: Any, output_data: Any, duration_ms: int) -> None:
        try:
            clean_input = cls.safe_serialize(input_data)
            clean_output = cls.safe_serialize(output_data)
            
            # Format as single line for easy log parsing / grepping
            # Using standard [PIPELINE_STAGE] prefix for mining tools
            logger.info(
                f"[PIPELINE_STAGE] stage='{stage_name}' "
                f"duration_ms={duration_ms} "
                f"input={json.dumps(clean_input, default=str)} "
                f"output={json.dumps(clean_output, default=str)}"
            )
        except Exception as e:
            # Fallback to prevent telemetry failure from breaking core pipeline execution
            logger.error(f"[TELEMETRY_RECORD_FAILED] stage='{stage_name}' error='{str(e)}'")
