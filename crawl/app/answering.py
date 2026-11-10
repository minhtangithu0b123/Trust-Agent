import logging
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.documents import Document

from .config import Settings
from .domains import DomainConfig, get_domain_config
from .retrieval import HybridResult, get_hybrid_retriever

logger = logging.getLogger(__name__)
from .citation_guardrail import INSUFFICIENT_EVIDENCE


def contains_insufficient_evidence(answer: str) -> bool:
    normalized = " ".join(str(answer).casefold().split()).rstrip(".")
    phrase = "chưa đủ căn cứ từ dữ liệu hiện có để kết luận"
    return phrase in normalized


SYSTEM_PROMPT = """Bạn là {prompt_name} của Trust Agent.

Chỉ trả lời dựa trên evidence được cung cấp trong prompt. Không sử dụng kiến thức bên ngoài evidence. Không tự bịa Điều, Khoản, tên văn bản, số hiệu, mức tiền hoặc ngày hiệu lực.

Nếu evidence không đủ để kết luận, phải nói đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận." Không thay thế tư vấn pháp lý chuyên nghiệp.

Trả lời bằng tiếng Việt rõ ràng, dễ hiểu. Phân biệt rõ phần "Quy định pháp luật" và phần "Suy luận theo tình huống" nếu có suy luận. Chỉ đưa các document_id thực sự dùng để trả lời vào cited_document_ids.
"""


class ProviderError(RuntimeError):
    pass


class LLMProvider(Protocol):
    def generate(self, query: str, context: str) -> "GenerationResult": ...


@dataclass
class GenerationResult:
    answer: str
    cited_document_ids: list[str]


def build_legal_context(evidence: list[HybridResult], domain_config: DomainConfig | None = None) -> str:
    label = domain_config.prompt_name if domain_config else "legal_agent"
    blocks = []
    for item in evidence:
        metadata = item.document.metadata
        blocks.append("\n".join([
            f"[DOMAIN: {metadata.get('domain', label)}]",
            f"[DOCUMENT_ID: {metadata.get('id')}]",
            f"Tên văn bản: {metadata.get('ten_van_ban')}",
            f"Số hiệu: {metadata.get('so_hieu')}",
            f"Chương: {metadata.get('chuong')}",
            f"Điều: {metadata.get('dieu')}",
            f"Khoản: {metadata.get('khoan')}",
            f"Source: {metadata.get('source')}",
            f"Nội dung:\n{item.document.page_content}",
        ]))
    return "\n\n--- EVIDENCE ---\n\n".join(blocks)


class OpenAIProvider:
    def __init__(self, settings: Settings, domain_config: DomainConfig):
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is not configured")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ProviderError("langchain-openai is not installed") from exc
        from pydantic import BaseModel, Field

        class AnswerPayload(BaseModel):
            answer: str = Field(description="Vietnamese answer grounded in evidence")
            cited_document_ids: list[str] = Field(default_factory=list)

        self._system_prompt = SYSTEM_PROMPT.format(prompt_name=domain_config.prompt_name)
        self._model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        ).with_structured_output(AnswerPayload)

    def generate(self, query: str, context: str) -> GenerationResult:
        prompt = f"{self._system_prompt}\n\nUser query:\n{query}\n\nEvidence:\n{context}\n\nReturn only the structured answer and cited_document_ids."
        try:
            payload = self._model.invoke(prompt)
            return GenerationResult(
                answer=str(payload.answer).strip(),
                cited_document_ids=list(payload.cited_document_ids),
            )
        except Exception as exc:
            raise ProviderError(f"LLM generation failed: {exc}") from exc


def get_llm_provider(settings: Settings, domain_config: DomainConfig) -> LLMProvider:
    return OpenAIProvider(settings, domain_config)


def citation_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": metadata.get("id"),
        "so_hieu": metadata.get("so_hieu"),
        "ten_van_ban": metadata.get("ten_van_ban"),
        "chuong": metadata.get("chuong"),
        "dieu": metadata.get("dieu"),
        "khoan": metadata.get("khoan"),
        "source": metadata.get("source"),
        "status": metadata.get("status", "unknown"),
        "effective_from": metadata.get("effective_from") or None,
    }


from .citation_guardrail import verify_citations_guardrail


def verify_citations(generated: GenerationResult, evidence: list[HybridResult]) -> tuple[str, str, list[dict[str, Any]]]:
    guardrail_result = verify_citations_guardrail(
        answer=generated.answer,
        evidence=evidence,
        cited_document_ids=generated.cited_document_ids,
        require_cited_ids=True,
    )
    verified_answer = INSUFFICIENT_EVIDENCE if guardrail_result.status == "insufficient_evidence" else guardrail_result.verified_answer
    return guardrail_result.status, verified_answer, guardrail_result.citations


def evidence_payload(evidence: list[HybridResult]) -> list[dict[str, Any]]:
    result = []
    for item in evidence:
        metadata = dict(item.document.metadata)
        if metadata.get("effective_from") == "":
            metadata["effective_from"] = None
        result.append({
            "document_id": metadata.get("id"),
            "text": item.document.page_content,
            "fused_score": item.fused_score,
            "metadata": metadata,
        })
    return result


def answer_question(
    query: str,
    k: int,
    settings: Settings,
    provider: LLMProvider | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    requested_domain = domain or settings.labor_domain
    config = settings.domain_config(requested_domain) if hasattr(settings, "domain_config") else get_domain_config(requested_domain)
    evidence = get_hybrid_retriever(settings, domain=config.name).search(query, k=k)
    payload = evidence_payload(evidence)
    base = {
        "query": query,
        "domain": config.name,
        "evidence": payload,
        "retrieval_strategy": "hybrid_rrf",
    }
    if not evidence:
        return {**base, "answer": INSUFFICIENT_EVIDENCE, "status": "insufficient_evidence", "citations": []}
    try:
        selected_provider = provider or get_llm_provider(settings, config)
        generated = selected_provider.generate(query, build_legal_context(evidence, config))
    except ProviderError as exc:
        logger.warning("LLM provider unavailable: %s", exc)
        return {
            **base,
            "answer": "Chưa thể tạo câu trả lời vì LLM provider chưa được cấu hình hoặc đang gặp lỗi.",
            "status": "provider_error",
            "citations": [],
        }
    status, answer, citations = verify_citations(generated, evidence)
    if contains_insufficient_evidence(generated.answer):
        return {**base, "answer": generated.answer, "status": "insufficient_evidence", "citations": []}
    return {**base, "answer": answer, "status": status, "citations": citations}
