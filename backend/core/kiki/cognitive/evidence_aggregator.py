from typing import Dict, Any, List
from ..utils.logger import kiki_logger


class EvidenceAggregator:
    """
    Component — Evidence Aggregator (Kiki 2.0)
    Merges, normalizes, deduplicates, and resolves evidence collected from multiple worker skills.
    Prepares clean aggregated evidence for the Business Reasoning Engine.
    """

    @classmethod
    def aggregate_evidence(cls, skill_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        kiki_logger.info(f"[EVIDENCE AGGREGATOR] Aggregating evidence from {len(skill_outputs)} skill outputs.")

        combined_sql: List[str] = []
        combined_evidences: List[Dict[str, Any]] = []
        execution_steps: List[Dict[str, Any]] = []
        metric_values: Dict[str, Any] = {}
        primary_summary = ""

        for output in skill_outputs:
            if not isinstance(output, dict):
                continue

            # Aggregate SQL
            if output.get("sql"):
                combined_sql.append(str(output["sql"]))
            elif output.get("generated_sql"):
                combined_sql.append(str(output["generated_sql"]))

            # Aggregate Evidence Packages
            if isinstance(output.get("evidences"), list):
                combined_evidences.extend(output["evidences"])
                for ev in output["evidences"]:
                    if isinstance(ev, dict) and ev.get("query"):
                        combined_sql.append(str(ev["query"]))

            # Aggregate Steps
            if isinstance(output.get("investigation_steps"), list):
                execution_steps.extend(output["investigation_steps"])

            # Extract metrics
            for k in ["total_purchase", "total_sales", "gst_total", "formatted_value", "value"]:
                if k in output and output[k] is not None:
                    metric_values[k] = output[k]

            # Primary text reply
            reply = output.get("summary") or output.get("final_response") or output.get("reply")
            if reply and not primary_summary:
                primary_summary = reply

        # Deduplicate SQL queries
        unique_sqls = list(set(combined_sql))

        aggregated = {
            "sql_queries": unique_sqls,
            "evidences": combined_evidences,
            "execution_steps": execution_steps,
            "metric_values": metric_values,
            "primary_summary": primary_summary or "Skill execution completed successfully.",
            "total_skills_executed": len(skill_outputs)
        }

        kiki_logger.info(
            f"[EVIDENCE AGGREGATOR SUCCESS] Aggregated {len(unique_sqls)} unique SQL queries and {len(metric_values)} metrics."
        )
        return aggregated
