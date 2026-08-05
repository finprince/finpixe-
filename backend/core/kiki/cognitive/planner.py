from typing import Dict, Any, List, Optional
from ..models.dto import ExecutionPlan, ContextState
from ..utils.logger import kiki_logger

class CognitivePlanner:
    """
    Component — Cognitive Planner (Kiki 2.0)
    Understands the user's business objective, determines required knowledge and skills,
    and constructs an explicit ExecutionPlan object.

    Does NOT execute skills directly. Only plans execution.
    """
    SKILL_INTENT_MAP = {'sales': ['KPISkill', 'InvestigationSkill', 'NavigationSkill'], 'purchase': ['KPISkill', 'InvestigationSkill', 'NavigationSkill'], 'gst': ['GSTSkill', 'InvestigationSkill', 'NavigationSkill'], 'ocr': ['OCRSkill', 'ActionSkill'], 'navigate': ['NavigationSkill'], 'help': ['HelpSkill'], 'workflow': ['WorkflowSkill'], 'action': ['ActionSkill'], 'report': ['ReportingSkill', 'AnalyticsSkill']}

    @classmethod
    def plan(cls, question: str, context_state: ContextState, cumulative_constraints: Optional[Dict[str, Any]]=None) -> ExecutionPlan:
        clean_q = question.strip().lower()
        constraints = cumulative_constraints or {}
        goal = f"Fulfill user ERP query: '{question}'"
        obj = f"Analyze business query for entity '{constraints.get('entity', 'general')}' under page '{context_state.current_page}'."
        required_skills: List[str] = []
        required_knowledge: List[str] = []
        if constraints.get('entity') in {'purchases', 'sales'}:
            required_skills = ['KPISkill', 'InvestigationSkill']
            required_knowledge = ['Voucher Schema', 'Accounting Ledger Rules']
        elif 'gst' in clean_q or constraints.get('entity') == 'gst':
            required_skills = ['GSTSkill', 'InvestigationSkill']
            required_knowledge = ['GST Return Rules', 'Tax Ledger Schema']
        elif 'ocr' in clean_q or 'scan' in clean_q:
            required_skills = ['OCRSkill', 'ActionSkill']
            required_knowledge = ['OCR Document Pipeline']
        elif any((v in clean_q for v in ['open', 'go to', 'navigate', 'launch'])):
            required_skills = ['NavigationSkill']
            required_knowledge = ['React Routes & Workspace Navigation']
        elif any((h in clean_q for h in ['how to', 'help', 'guide'])):
            required_skills = ['HelpSkill']
            required_knowledge = ['ERP User Documentation']
        else:
            required_skills = ['InvestigationSkill', 'KPISkill']
            required_knowledge = ['General Database Schema', 'ERP Domain Knowledge']
        needs_clarification = clean_q in {'tell me', 'show me', 'check', 'display', 'what'}
        clarification_prompt = None
        if needs_clarification:
            clarification_prompt = "Could you please specify which business report or ledger metric you'd like to investigate?"
        steps = [{'step_number': 1, 'description': f'Retrieve semantic knowledge for {required_knowledge}'}, {'step_number': 2, 'description': f'Execute skills: {required_skills}'}, {'step_number': 3, 'description': 'Aggregate evidence and perform business reasoning'}]
        plan_obj = ExecutionPlan(goal=goal, business_objective=obj, required_skills=required_skills, required_knowledge=required_knowledge, execution_steps=steps, needs_clarification=needs_clarification, clarification_prompt=clarification_prompt)
        kiki_logger.info(f"[COGNITIVE PLANNER] Plan generated for '{question}': Required Skills: {plan_obj.required_skills}, Needs Clarification: {plan_obj.needs_clarification}")
        return plan_obj