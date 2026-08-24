from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from rim_gateway.rim_engine_v2 import ContextLoader, FinanceIntuititionEngine, build_finance_registry
from rim_gateway.rim_engine_v2_1 import RIMEngineV2

# Initialize the RIM API Server
app = FastAPI(
    title="RIM Universal Gateway API",
    description="Ramanujan Intuition Model - Neuro-Symbolic Verification Engine",
    version="2.1.0"
)

# Initialize the RIM Engine (Finance Domain Example)
registry = build_finance_registry()
engine = RIMEngineV2(
    intuition=FinanceIntuititionEngine("finance", "POST_BANK_STATEMENT", "EXTRACT"),
    context_loader=ContextLoader(),
    rule_registry=registry,
    approval_threshold=5000.0
)

# Pydantic model for incoming API requests
class VerificationRequest(BaseModel):
    entity_id: str
    document_data: Dict[str, Any]
    ground_truth: Optional[bool] = None

@app.post("/api/v1/verify/finance")
async def verify_financial_document(request: VerificationRequest):
    """
    Endpoint to verify a financial document using RIM v2.1
    """
    try:
        # Pass the incoming JSON directly to the RIM Engine
        result = engine.process_v2(
            raw_input=request.document_data,
            entity_id=request.entity_id,
            ground_truth=request.ground_truth
        )
        
        # Return the structured verdict to the caller
        return {
            "status": "success",
            "entity_id": request.entity_id,
            "rim_verdict": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """Check if the RIM API is operational"""
    return {"status": "operational", "version": "2.1.0"}

if __name__ == "__main__":
    import uvicorn
    print("Starting RIM API Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
