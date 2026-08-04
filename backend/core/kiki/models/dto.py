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
class ContextState:
    question: str
    tenant_id: str = ""
    company_name: Optional[str] = None
    branch_name: Optional[str] = None
    financial_year: str = "2025-2026"
    current_page: str = "Dashboard"
    active_module: str = "Accounting ERP"
    dashboard_filters: Dict[str, Any] = field(default_factory=dict)
    active_period: str = "current_month"
    persona: str = "Accountant"
    user_role: Optional[str] = None
    selected_entity: Optional[Dict[str, Any]] = None
    previous_investigations: List[Dict[str, Any]] = field(default_factory=list)
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    cumulative_constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    goal: str
    business_objective: str
    required_skills: List[str] = field(default_factory=list)
    required_knowledge: List[str] = field(default_factory=list)
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievedKnowledgeItem:
    source_type: str  # route, metadata, schema, workflow, rule, doc
    title: str
    content: str
    relevance_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionSummary:
    answered_user_question: bool = True
    has_sufficient_evidence: bool = True
    detected_conflicts: bool = False
    requires_clarification: bool = False
    confidence_justified: bool = True
    reflection_notes: str = "Evidence validates final business response."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QuickActionItem:
    title: str
    action_type: str = "navigate"  # navigate, export, trigger_workflow
    route: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveThinking:
    user_objective: str
    business_task: str
    needs_data: bool = True
    needs_navigation: bool = False
    needs_clarification: bool = False
    reasoning_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationItem:
    title: str
    action_type: str = "navigate"  # navigate, query, filter, export
    route: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeveloperDetails:
    sql_queries: List[str] = field(default_factory=list)
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    evidences: List[Dict[str, Any]] = field(default_factory=list)
    planner_output: Dict[str, Any] = field(default_factory=dict)
    retrieved_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    reflection_summary: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    selected_engine: str = "KikiCognitiveOrchestrator"
    skills_executed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessResponse:
    title: str
    summary: str
    reply: str
    result: Optional[str] = None
    insights: List[str] = field(default_factory=list)
    recommendations: List[RecommendationItem] = field(default_factory=list)
    quick_actions: List[QuickActionItem] = field(default_factory=list)
    persona: str = "Accountant"
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    thinking: Optional[CognitiveThinking] = None
    execution_plan: Optional[ExecutionPlan] = None
    reflection: Optional[ReflectionSummary] = None
    developer_details: Optional[DeveloperDetails] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "title": self.title,
            "result": self.result,
            "summary": self.summary,
            "reply": self.reply,
            "final_response": self.reply,
            "insights": self.insights,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "quick_actions": [q.to_dict() for q in self.quick_actions],
            "navigation_suggestions": [r.to_dict() for r in self.recommendations if r.route],
            "persona": self.persona,
            "confidence": self.confidence,
            "thinking": self.thinking.to_dict() if self.thinking else None,
            "execution_plan": self.execution_plan.to_dict() if self.execution_plan else None,
            "reflection": self.reflection.to_dict() if self.reflection else None,
            "developer_details": self.developer_details.to_dict() if self.developer_details else None,
        }
        return res


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
    business_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

