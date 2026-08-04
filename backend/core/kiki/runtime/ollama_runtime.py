import requests
import re
from typing import Dict, List, Any, Optional
from ..config.settings import KikiSettings
from ..models.dto import QuestionUnderstanding, InvestigationPlan, QueryIntent, EvaluationResult, InvestigationContext
from ..planner.investigation_planner import InvestigationPlanner
from ..exceptions.kiki_exceptions import OllamaException
from ..prompts.understanding_prompt import build_understanding_prompt, UNDERSTANDING_SYSTEM_PROMPT
from ..prompts.planning_prompt import build_planning_prompt, PLANNING_SYSTEM_PROMPT
from ..prompts.query_intent_prompt import build_query_intent_prompt, QUERY_INTENT_SYSTEM_PROMPT
from ..prompts.evidence_prompt import build_evidence_prompt, EVIDENCE_SYSTEM_PROMPT
from ..prompts.response_prompt import build_response_prompt, RESPONSE_SYSTEM_PROMPT
from ..utils.helpers import repair_and_parse_json
from ..utils.logger import kiki_logger

class OllamaRuntime:
    """
    Component 1 — Ollama Runtime
    Pure LLM client that communicates with Ollama REST API.
    Performs AI reasoning tasks only (understanding, QueryIntent generation, evidence evaluation, response synthesis).
    Does NOT orchestrate workflow, build SQL, or access database.
    """
    GREETING_PATTERNS = ['^(hi|hello|hey|greetings|good morning|good afternoon|good evening|thanks|thank you|bye|goodbye)\\b']

    def __init__(self, host: Optional[str]=None, model: Optional[str]=None):
        self.host = (host or KikiSettings.OLLAMA_HOST).rstrip('/')
        configured_model = model or KikiSettings.OLLAMA_MODEL
        self.model = self._resolve_model_name(configured_model)

    def _resolve_model_name(self, target_model: str) -> str:
        """
        Queries Ollama /api/tags to resolve installed model names.
        Prevents 404 errors when target_model (e.g. 'qwen2.5') needs mapping to installed name (e.g. 'qwen2.5vl:7b').
        """
        try:
            url = f'{self.host}/api/tags'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m.get('name', '') for m in data.get('models', [])]
                if target_model in models:
                    return target_model
                for m in models:
                    if target_model.lower() in m.lower() or m.lower() in target_model.lower():
                        kiki_logger.info(f"Resolved configured model '{target_model}' to installed model '{m}'.")
                        return m
                if models:
                    kiki_logger.warning(f"Configured model '{target_model}' not found in installed models {models}. Using '{models[0]}'.")
                    return models[0]
        except Exception as e:
            kiki_logger.warning(f'Could not connect to Ollama tags endpoint at {self.host}/api/tags: {e}')
        return target_model

    def is_greeting(self, message: str) -> bool:
        """
        Phase 4: Lightweight greeting classifier.
        Returns True if the message is a greeting or polite check.
        """
        clean_msg = message.strip().lower()
        if len(clean_msg) < 15:
            for pat in self.GREETING_PATTERNS:
                if re.search(pat, clean_msg):
                    return True
        return False

    def get_greeting_response(self) -> str:
        """Returns friendly greeting without executing investigation engine."""
        return 'Hello! I am Kiki, your AI ERP Investigation Agent. How can I help you investigate your financial and business data today?'

    def _call_llm(self, prompt: str, system_prompt: Optional[str]=None, json_format: bool=False) -> str:
        """
        Issues HTTP POST request to Ollama API.
        Phase 2 & 6: Standardized error logging and explicit error reporting without silent fallbacks.
        """
        url = f'{self.host}/api/generate'
        payload = {'model': self.model, 'prompt': prompt, 'stream': False, 'options': {'temperature': KikiSettings.LLM_TEMPERATURE, 'top_p': KikiSettings.LLM_TOP_P}}
        if system_prompt:
            payload['system'] = system_prompt
        if json_format:
            payload['format'] = 'json'
        try:
            response = requests.post(url, json=payload, timeout=KikiSettings.OLLAMA_REQUEST_TIMEOUT)
            if response.status_code != 200:
                kiki_logger.error(f'Ollama API HTTP Error: URL={url}, Status={response.status_code}, Model={self.model}, Response={response.text}')
                raise OllamaException(f'Kiki could not communicate with the configured Ollama server.\nHost: {self.host}\nModel: {self.model}\nStatus Code: {response.status_code}\nReason: {response.text}')
            data = response.json()
            resp_text = data.get('response', '').strip()
            if not resp_text:
                raise OllamaException('Ollama returned empty response string.')
            return resp_text
        except requests.exceptions.RequestException as req_err:
            kiki_logger.error(f'Ollama RequestException: URL={url}, Error={req_err}')
            raise OllamaException(f'Kiki could not connect to Ollama server at {self.host}.\nModel: {self.model}\nError: {str(req_err)}') from req_err

    def understand_question(self, question: str) -> QuestionUnderstanding:
        """Extracts intent, objective, entities, timeframe, and scope from user question."""
        prompt = build_understanding_prompt(question)
        raw_resp = self._call_llm(prompt, system_prompt=UNDERSTANDING_SYSTEM_PROMPT, json_format=True)
        parsed = repair_and_parse_json(raw_resp)
        return QuestionUnderstanding(intent=parsed.get('intent', 'Business Investigation'), objective=parsed.get('objective', f'Investigate question: {question}'), entities=parsed.get('entities', []), timeframe=parsed.get('timeframe', 'unknown'), scope=parsed.get('scope', 'general database'))

    def generate_investigation_plan(self, question: str, understanding: QuestionUnderstanding) -> InvestigationPlan:
        """Generates step-by-step reasoning plan using InvestigationPlanner."""
        prompt = build_planning_prompt(question, understanding.to_dict())
        raw_resp = self._call_llm(prompt, system_prompt=PLANNING_SYSTEM_PROMPT, json_format=True)
        parsed = repair_and_parse_json(raw_resp)
        return InvestigationPlanner.build_plan_from_llm_response(question, understanding, parsed)

    def extract_search_terms(self, context: InvestigationContext) -> List[str]:
        """Derives search terms for SchemaService based on current investigation state."""
        terms = []
        if context.question:
            words = [w.lower().strip() for w in context.question.replace('?', ' ').split() if len(w.strip()) > 2]
            terms.extend(words)
        if context.understanding and context.understanding.entities:
            terms.extend([e.lower() for e in context.understanding.entities])
        if any((w in terms for w in ['sale', 'sales', 'revenue', 'invoice'])):
            terms.extend(['vouchers', 'voucher_sales', 'customer', 'invoice', 'ledger'])
        if any((w in terms for w in ['purchase', 'vendor', 'supplier', 'buy'])):
            terms.extend(['vouchers', 'voucher_purchase', 'vendor', 'bill', 'ledger'])
        if any((w in terms for w in ['gst', 'tax'])):
            terms.extend(['gst', 'tax', 'vouchers'])
        if any((w in terms for w in ['transaction', 'transactions', 'last', 'latest', 'recent'])):
            terms.extend(['vouchers', 'transactions'])
        return list(dict.fromkeys(terms))[:8]

    def generate_query_intent(self, context: InvestigationContext) -> QueryIntent:
        """Generates structured QueryIntent DTO for current investigation step."""
        schemas_data = [s.to_dict() for s in context.relevant_schemas]
        evidences_data = [e.to_dict() for e in context.evidences]
        understanding_data = context.understanding.to_dict() if context.understanding else {}
        prompt = build_query_intent_prompt(question=context.question, understanding_dict=understanding_data, schemas=schemas_data, evidences=evidences_data, current_step=context.current_step_number)
        raw_resp = self._call_llm(prompt, system_prompt=QUERY_INTENT_SYSTEM_PROMPT, json_format=True)
        parsed = repair_and_parse_json(raw_resp)
        target_tbls = parsed.get('target_tables', [])
        if not target_tbls and context.relevant_schemas:
            target_tbls = [context.relevant_schemas[0].table_name]
        raw_entity = parsed.get('entity')
        if isinstance(raw_entity, str):
            raw_entity = raw_entity.strip()
            if raw_entity.lower() in {'null', 'none', '', 'undefined'}:
                raw_entity = None
        else:
            raw_entity = None
        return QueryIntent(objective=parsed.get('objective', f'Retrieve data for step {context.current_step_number}'), target_tables=target_tbls, entity=raw_entity, metrics=parsed.get('metrics', ['amount', 'total']), period=parsed.get('period', []), group_by=parsed.get('group_by', []), order_by=parsed.get('order_by', []), limit=parsed.get('limit', 100))

    def evaluate_evidence(self, context: InvestigationContext) -> EvaluationResult:
        """Evaluates gathered evidence and decides if more steps are required."""
        schemas_data = [s.to_dict() for s in context.relevant_schemas]
        evidences_data = [e.to_dict() for e in context.evidences]
        understanding_data = context.understanding.to_dict() if context.understanding else {}
        prompt = build_evidence_prompt(question=context.question, understanding_dict=understanding_data, evidences=evidences_data, current_step=context.current_step_number, max_steps=KikiSettings.MAX_INVESTIGATION_STEPS)
        raw_resp = self._call_llm(prompt, system_prompt=EVIDENCE_SYSTEM_PROMPT, json_format=True)
        parsed = repair_and_parse_json(raw_resp)
        return EvaluationResult(has_enough_info=parsed.get('has_enough_info', False), reasoning=parsed.get('reasoning', ''), next_search_terms=parsed.get('next_search_terms', []))

    def generate_final_response(self, context: InvestigationContext) -> str:
        """
        Synthesizes evidence-backed natural language response from structured EvidencePackages.
        Phase 3: Never leaks raw SQL or debug DTO data to end user.
        """
        understanding_data = context.understanding.to_dict() if context.understanding else {}
        plan_data = context.plan.to_dict() if context.plan else {}
        evidences_data = [e.to_dict() for e in context.evidences]
        prompt = build_response_prompt(question=context.question, understanding_dict=understanding_data, plan_dict=plan_data, evidences=evidences_data)
        response_text = self._call_llm(prompt, system_prompt=RESPONSE_SYSTEM_PROMPT)
        cleaned_response = re.sub('SELECT\\s+.*?\\s+FROM\\s+\\w+', '', response_text, flags=re.IGNORECASE)
        return cleaned_response.strip() or response_text