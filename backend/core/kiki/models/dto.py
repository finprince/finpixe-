from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
import time



@dataclass
class QuestionUnderstanding:
    intent: str
    objective: str
    entities: List[str] = field(default_factory=list)
    timeframe: str = "unknown"
    scope: str = "general database"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationStep:
    step_number: int
    description: str
    objective: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationPlan:
    goal: str
    steps: List[InvestigationStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps]
        }


@dataclass
class SchemaMatch:
    table_name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryIntent:
    objective: str
    target_tables: List[str] = field(default_factory=list)
    entity: Optional[str] = None
    metrics: List[str] = field(default_factory=list)
    period: List[str] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    order_by: List[str] = field(default_factory=list)
    limit: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryResultData:
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    status: str = "SUCCESS"
    timestamp: str = field(default_factory=lambda: str(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidencePackage:
    step_number: int
    step_description: str
    query: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    has_enough_info: bool
    reasoning: str = ""
    next_search_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationContext:
    """
    Unified Investigation Context State Object.
    Maintained and mutated by InvestigationEngine throughout the workflow.
    """
    question: str
    tenant_id: Optional[str] = None
    company_name: Optional[str] = None
    branch_name: Optional[str] = None
    financial_year: Optional[str] = None
    current_page: Optional[str] = None
    dashboard_filters: Dict[str, Any] = field(default_factory=dict)
    active_period: str = "current_month"
    understanding: Optional[QuestionUnderstanding] = None
    plan: Optional[InvestigationPlan] = None
    current_step_number: int = 0
    search_terms: List[str] = field(default_factory=list)
    relevant_schemas: List[SchemaMatch] = field(default_factory=list)
    query_intent: Optional[QueryIntent] = None
    generated_sql: Optional[str] = None
    query_results: Optional[QueryResultData] = None
    evidences: List[EvidencePackage] = field(default_factory=list)
    attempted_sqls: Set[str] = field(default_factory=set)
    evaluation: Optional[EvaluationResult] = None
    completed: bool = False
    final_response: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "tenant_id": self.tenant_id,
            "company_name": self.company_name,
            "branch_name": self.branch_name,
            "financial_year": self.financial_year,
            "current_page": self.current_page,
            "dashboard_filters": self.dashboard_filters,
            "active_period": self.active_period,
            "understanding": self.understanding.to_dict() if self.understanding else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "current_step_number": self.current_step_number,
            "search_terms": self.search_terms,
            "relevant_schemas": [s.to_dict() for s in self.relevant_schemas],
            "query_intent": self.query_intent.to_dict() if self.query_intent else None,
            "generated_sql": self.generated_sql,
            "query_results": self.query_results.to_dict() if self.query_results else None,
            "evidences": [e.to_dict() for e in self.evidences],
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "completed": self.completed,
            "final_response": self.final_response
        }



@dataclass
class InvestigationResult:
    """
    Final Output DTO returned by KikiChatView API endpoint.
    """
    question: str
    understanding: Dict[str, Any]
    plan: Dict[str, Any]
    investigation_steps: List[Dict[str, Any]]
    evidences: List[Dict[str, Any]]
    final_response: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
