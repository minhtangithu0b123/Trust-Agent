"""Unit tests for Citation Verification Guardrail module (crawl/app/citation_guardrail.py).

Tests:
1. Valid citation verification (so_hieu, dieu, khoan, cross-reference match).
2. Hallucinated law/article detection and downgrade to unverified with warnings.
3. Cross-reference mismatch detection (article from law A cited with law B).
4. Insufficient evidence detection (standard phrase, empty evidence, missing cited IDs).
5. GroundingIndex extraction and normalization edge cases.
6. Tuple unpacking contract (verify_answer_citations).
"""

import unicodedata
from langchain_core.documents import Document

from app.citation_guardrail import (
    INSUFFICIENT_EVIDENCE,
    CitationGuardrailResult,
    GroundingIndex,
    _check_article_law_cross_reference,
    build_grounding_index,
    contains_insufficient_evidence,
    extract_dieu,
    extract_khoan,
    extract_so_hieu,
    normalize_dieu_number,
    normalize_khoan_number,
    normalize_so_hieu,
    verify_answer_citations,
    verify_citations_guardrail,
)
from app.retrieval import HybridResult


def make_hybrid_item(doc_id: str, content: str, metadata: dict) -> HybridResult:
    meta = {"id": doc_id, **metadata}
    return HybridResult(Document(page_content=content, metadata=meta), 0.05)


def standard_evidence() -> list[HybridResult]:
    return [
        make_hybrid_item(
            "labor-113",
            "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm 12 ngày làm việc.",
            {
                "domain": "labor",
                "so_hieu": "45/2019/QH14",
                "ten_van_ban": "Bộ luật Lao động 2019",
                "chuong": "Chương VII",
                "dieu": "Điều 113",
                "khoan": "Khoản 1",
                "source": "https://thuvienphapluat.vn/labor",
                "status": "effective",
                "effective_from": "2021-01-01",
            },
        ),
        make_hybrid_item(
            "traffic-6",
            "Xử phạt người điều khiển xe mô tô, xe gắn máy vi phạm quy định về nồng độ cồn.",
            {
                "domain": "traffic",
                "so_hieu": "168/2024/NĐ-CP",
                "ten_van_ban": "Nghị định 168/2024/NĐ-CP",
                "chuong": "Chương II",
                "dieu": "Điều 6",
                "khoan": "Khoản 6",
                "source": "https://thuvienphapluat.vn/traffic",
                "status": "effective",
                "effective_from": "2025-01-01",
            },
        ),
    ]


class TestNormalizationAndExtraction:
    def test_normalize_so_hieu(self):
        assert normalize_so_hieu("45/2019/qh14.") == "45/2019/QH14"
        assert normalize_so_hieu(" 168/2024/NĐ-CP; ") == "168/2024/NĐ-CP"
        assert normalize_so_hieu("12/VBHN-BGTVT)") == "12/VBHN-BGTVT"

    def test_normalize_dieu_number(self):
        assert normalize_dieu_number("Điều 113") == "113"
        assert normalize_dieu_number("điều 32a") == "32a"
        assert normalize_dieu_number("15") == "15"
        assert normalize_dieu_number(None) is None
        assert normalize_dieu_number("") is None

    def test_normalize_khoan_number(self):
        assert normalize_khoan_number("Khoản 1") == "1"
        assert normalize_khoan_number("khoản 12.") == "12"
        assert normalize_khoan_number(5) == "5"
        assert normalize_khoan_number(None) is None

    def test_extract_so_hieu(self):
        text = "Căn cứ Nghị định 168/2024/NĐ-CP và Bộ luật Lao động 45/2019/QH14, cùng 168/2024/NĐ-CP."
        extracted = extract_so_hieu(text)
        assert extracted == ["168/2024/NĐ-CP", "45/2019/QH14"]

    def test_extract_dieu(self):
        text = "Theo quy định tại Điều 113 và điều 6, khoản 1 và Điều 113 Bộ luật."
        extracted = extract_dieu(text)
        assert extracted == ["113", "6"]

    def test_extract_khoan(self):
        text = "Khoản 1 và khoản 2 Điều 113, cùng Khoản 1."
        assert extract_khoan(text) == ["1", "2"]

    def test_normalize_so_hieu_strips_brackets_and_quotes(self):
        assert normalize_so_hieu("(45/2019/QH14)") == "45/2019/QH14"
        assert normalize_so_hieu("[168/2024/NĐ-CP]") == "168/2024/NĐ-CP"
        assert normalize_so_hieu('"35/2024/TT-BGTVT"') == "35/2024/TT-BGTVT"

    def test_extract_dieu_and_khoan_uppercase(self):
        text = "Căn cứ ĐIỀU 113 và KHOẢN 2 Bộ luật Lao động."
        assert extract_dieu(text) == ["113"]
        assert extract_khoan(text) == ["2"]

    def test_nfd_unicode_normalization_extraction(self):
        # Text decomposed into NFD form
        nfd_text = unicodedata.normalize("NFD", "Căn cứ Điều 113 và Khoản 1 số 45/2019/QH14.")
        assert extract_dieu(nfd_text) == ["113"]
        assert extract_khoan(nfd_text) == ["1"]
        assert extract_so_hieu(nfd_text) == ["45/2019/QH14"]

    def test_contains_insufficient_evidence(self):
        assert contains_insufficient_evidence("Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.")
        assert contains_insufficient_evidence("Hiện tại chưa đủ căn cứ từ dữ liệu hiện có để kết luận...")
        assert not contains_insufficient_evidence("Căn cứ Điều 113 Bộ luật Lao động 2019.")


class TestGroundingIndex:
    def test_build_grounding_index_populates_elements(self):
        evidence = standard_evidence()
        index = build_grounding_index(evidence)

        assert "45/2019/QH14" in index.valid_so_hieu
        assert "168/2024/NĐ-CP" in index.valid_so_hieu
        assert "113" in index.valid_dieu
        assert "6" in index.valid_dieu
        assert "1" in index.valid_khoan
        assert "6" in index.valid_khoan
        assert "labor-113" in index.doc_ids
        assert "traffic-6" in index.doc_ids
        assert index.valid_dieu_by_so_hieu["45/2019/QH14"] == {"113"}
        assert index.valid_dieu_by_so_hieu["168/2024/NĐ-CP"] == {"6"}

    def test_build_grounding_index_handles_plain_dicts(self):
        dict_evidence = [
            {
                "document_id": "custom-1",
                "so_hieu": "88/2015/QH13",
                "dieu": "Điều 5",
                "khoan": "Khoản 2",
            }
        ]
        index = build_grounding_index(dict_evidence)
        assert "88/2015/QH13" in index.valid_so_hieu
        assert "5" in index.valid_dieu
        assert "custom-1" in index.doc_ids

    def test_build_grounding_index_with_tieu_de_dieu_fallback(self):
        evidence = [
            {
                "document_id": "doc-fallback",
                "so_hieu": "45/2019/QH14",
                "dieu": None,
                "tieu_de_dieu": "Điều 115. Nghỉ việc riêng, nghỉ không hưởng lương",
            }
        ]
        index = build_grounding_index(evidence)
        assert "115" in index.valid_dieu
        assert "115" in index.valid_dieu_by_so_hieu["45/2019/QH14"]


class TestValidCitationsVerification:
    def test_valid_labor_citation_passes_verification(self):
        evidence = standard_evidence()
        answer = (
            "Theo quy định tại Điều 113 Bộ luật Lao động số 45/2019/QH14, "
            "người lao động làm việc đủ 12 tháng được nghỉ hằng năm 12 ngày làm việc."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )

        assert result.status == "verified"
        assert result.is_verified is True
        assert result.verified_answer == answer
        assert len(result.warnings) == 0
        assert len(result.citations) == 1
        assert result.citations[0]["document_id"] == "labor-113"
        assert result.citations[0]["so_hieu"] == "45/2019/QH14"
        assert result.citations[0]["dieu"] == "Điều 113"

    def test_valid_traffic_citation_passes_verification(self):
        evidence = standard_evidence()
        answer = (
            "Căn cứ Điều 6 Nghị định 168/2024/NĐ-CP, hành vi vi phạm nồng độ cồn "
            "khi điều khiển xe mô tô bị xử phạt theo Khoản 6."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["traffic-6"],
        )

        assert result.status == "verified"
        assert result.warnings == []
        assert len(result.citations) == 1
        assert result.citations[0]["document_id"] == "traffic-6"
        assert result.citations[0]["so_hieu"] == "168/2024/NĐ-CP"

    def test_implicit_citations_matched_from_text(self):
        evidence = standard_evidence()
        answer = "Theo Điều 113 số 45/2019/QH14, người lao động được nghỉ phép."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=None,
        )
        assert result.status == "verified"
        assert len(result.citations) == 1
        assert result.citations[0]["document_id"] == "labor-113"


class TestHallucinatedCitationsDetection:
    def test_hallucinated_article_downgrades_to_unverified_with_warning(self):
        evidence = standard_evidence()
        # "Điều 999" does not exist in evidence
        answer = (
            "Theo quy định tại Điều 999 Bộ luật Lao động số 45/2019/QH14, "
            "người lao động được nghỉ phép vô hạn."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )

        assert result.status == "unverified"
        assert result.is_verified is False
        assert result.citations == []
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert "CẢNH BÁO: Phát hiện trích dẫn pháp lý không có căn cứ" in warning
        assert "Điều 999" in warning
        assert "Trạng thái hạ xuống unverified." in warning
        assert "[CẢNH BÁO:" in result.verified_answer

    def test_hallucinated_uppercase_article_downgraded(self):
        evidence = standard_evidence()
        # "ĐIỀU 999" in uppercase
        answer = "Căn cứ ĐIỀU 999 Bộ luật Lao động 45/2019/QH14 và KHOẢN 10."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )
        assert result.status == "unverified"
        assert len(result.warnings) >= 1
        assert "Điều 999" in result.warnings[0]
        assert result.citations == []

    def test_hallucinated_document_number_downgrades_to_unverified(self):
        evidence = standard_evidence()
        # "999/2026/QH99" does not exist in evidence
        answer = (
            "Theo quy định tại Điều 113 Luật Lao động số 999/2026/QH99, "
            "thời giờ làm việc bình thường là 8 giờ/ngày."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )

        assert result.status == "unverified"
        assert len(result.warnings) == 1
        assert "999/2026/QH99" in result.warnings[0]
        assert result.citations == []

    def test_cross_reference_mismatch_detected(self):
        evidence = standard_evidence()
        # Điều 6 belongs to 168/2024/NĐ-CP, NOT 45/2019/QH14
        mismatches = _check_article_law_cross_reference(
            "Căn cứ Điều 6 Bộ luật Lao động số 45/2019/QH14.",
            {"45/2019/QH14": {"113"}, "168/2024/NĐ-CP": {"6"}},
        )
        assert len(mismatches) == 1
        assert "Điều 6 không thuộc văn bản 45/2019/QH14" in mismatches[0]

    def test_cross_reference_mismatch_downgrades_guardrail(self):
        evidence = standard_evidence()
        answer = "Căn cứ Điều 6 Bộ luật Lao động số 45/2019/QH14 để xử phạt."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )
        assert result.status == "unverified"
        assert any("không thuộc văn bản" in w for w in result.warnings)


class TestInsufficientEvidenceAndEdgeCases:
    def test_insufficient_evidence_phrase_in_answer(self):
        evidence = standard_evidence()
        answer = "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
        result = verify_citations_guardrail(answer=answer, evidence=evidence)

        assert result.status == "insufficient_evidence"
        assert result.citations == []
        assert result.warnings == []

    def test_empty_evidence_pool_returns_insufficient_evidence(self):
        result = verify_citations_guardrail(
            answer="Bất kỳ câu trả lời nào",
            evidence=[],
        )
        assert result.status == "insufficient_evidence"
        assert result.verified_answer == INSUFFICIENT_EVIDENCE
        assert len(result.warnings) == 1
        assert "Không có tài liệu chứng cứ" in result.warnings[0]

    def test_missing_required_cited_document_ids(self):
        evidence = standard_evidence()
        result = verify_citations_guardrail(
            answer="Câu trả lời chung chung",
            evidence=evidence,
            cited_document_ids=[],
            require_cited_ids=True,
        )
        assert result.status == "insufficient_evidence"
        assert result.verified_answer == INSUFFICIENT_EVIDENCE

    def test_invalid_cited_document_id_not_in_evidence(self):
        evidence = standard_evidence()
        result = verify_citations_guardrail(
            answer="Theo quy định pháp luật.",
            evidence=evidence,
            cited_document_ids=["ghost-doc-id"],
        )
        assert result.status == "insufficient_evidence"
        assert any("ghost-doc-id" in w for w in result.warnings)

    def test_contract_verify_answer_citations_unpacking(self):
        evidence = standard_evidence()
        answer = "Theo Điều 113 số 45/2019/QH14 người lao động được nghỉ phép."
        status, verified_ans, citations, warnings = verify_answer_citations(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )
        assert status == "verified"
        assert verified_ans == answer
        assert len(citations) == 1
        assert warnings == []

    def test_empty_and_whitespace_answer_returns_insufficient_evidence(self):
        evidence = standard_evidence()
        for empty_val in ["", "   ", "\n\t  ", None]:
            result = verify_citations_guardrail(
                answer=empty_val,
                evidence=evidence,
            )
            assert result.status == "insufficient_evidence"
            assert result.verified_answer == INSUFFICIENT_EVIDENCE
            assert result.citations == []
            assert len(result.warnings) == 1

    def test_extract_and_normalize_dieu_with_vietnamese_letter_d_cross_suffix(self):
        assert normalize_dieu_number("Điều 32đ") == "32đ"
        assert normalize_dieu_number("ĐIỀU 32Đ") == "32đ"
        assert normalize_dieu_number("Điều 5a") == "5a"
        text = "Căn cứ Điều 32đ và ĐIỀU 5Đ Bộ luật Lao động."
        assert extract_dieu(text) == ["32đ", "5đ"]

    def test_normalize_so_hieu_strips_vietnamese_smart_quotes(self):
        assert normalize_so_hieu("“168/2024/NĐ-CP”") == "168/2024/NĐ-CP"
        assert normalize_so_hieu("‘45/2019/QH14’") == "45/2019/QH14"
        assert normalize_so_hieu("«35/2024/TT-BGTVT»") == "35/2024/TT-BGTVT"

    def test_build_grounding_index_with_title_fallback(self):
        evidence = [
            {
                "document_id": "doc-title",
                "so_hieu": "45/2019/QH14",
                "dieu": None,
                "tieu_de_dieu": None,
                "title": "Điều 113. Nghỉ hằng năm",
            }
        ]
        index = build_grounding_index(evidence)
        assert "113" in index.valid_dieu
        assert "113" in index.valid_dieu_by_so_hieu["45/2019/QH14"]

    def test_hallucinated_d_suffix_article_downgraded(self):
        evidence = standard_evidence()
        # "Điều 999đ" is not in evidence
        answer = "Căn cứ Điều 999đ Bộ luật Lao động 45/2019/QH14."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-113"],
        )
        assert result.status == "unverified"
        assert len(result.warnings) >= 1
        assert "Điều 999đ" in result.warnings[0]
        assert result.citations == []

    def test_valid_d_suffix_article_passes_verification(self):
        evidence = [
            make_hybrid_item(
                "labor-32d",
                "Nội dung quy định bổ sung.",
                {
                    "domain": "labor",
                    "so_hieu": "45/2019/QH14",
                    "ten_van_ban": "Bộ luật Lao động",
                    "dieu": "Điều 32đ",
                    "khoan": "Khoản 1",
                },
            )
        ]
        answer = "Theo quy định tại Điều 32đ Bộ luật Lao động 45/2019/QH14."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["labor-32d"],
        )
        assert result.status == "verified"
        assert result.warnings == []
        assert len(result.citations) == 1
        assert result.citations[0]["document_id"] == "labor-32d"

    def test_cross_reference_across_paragraph_break_not_falsely_flagged(self):
        """Verifies that an article in paragraph 1 is not falsely linked across a newline
        to an unrelated document number in paragraph 2."""
        evidence = standard_evidence()
        answer = (
            "Theo quy định tại Điều 113, người lao động được nghỉ 12 ngày phép hằng năm.\n"
            "Ngoài ra theo Nghị định 168/2024/NĐ-CP về giao thông, mức phạt vi phạm nồng độ cồn là rất nghiêm."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=None,
        )
        assert result.status == "verified"
        assert result.warnings == []
        assert len(result.citations) == 2

    def test_cross_reference_across_sentence_break_not_falsely_flagged(self):
        """Verifies that an article in sentence 1 is not falsely linked across sentence-ending period
        to an unrelated document number in sentence 2."""
        evidence = standard_evidence()
        answer = (
            "Căn cứ Điều 113 người lao động được nghỉ phép 12 ngày. "
            "Ngoài ra theo Nghị định 168/2024/NĐ-CP người điều khiển xe vi phạm bị xử lý nghiêm."
        )
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=None,
        )
        assert result.status == "verified"
        assert result.warnings == []
        assert len(result.citations) == 2

    def test_cross_reference_with_article_title_dot_properly_checked(self):
        """Verifies that an article with title separator dot (e.g. 'Điều 113. Nghỉ hằng năm')
        is properly evaluated: matching document passes, mismatched document is flagged."""
        evidence = standard_evidence()
        # Case A: Valid article 113 with title dot and correct law 45/2019/QH14 -> passes
        valid_ans = "Theo Điều 113. Nghỉ hằng năm của Bộ luật Lao động 45/2019/QH14 được nghỉ 12 ngày."
        res_valid = verify_citations_guardrail(valid_ans, evidence, cited_document_ids=["labor-113"])
        assert res_valid.status == "verified"
        assert res_valid.warnings == []

        # Case B: Cross-reference mismatch: Điều 6 belongs to 168/2024/NĐ-CP, not 45/2019/QH14 -> flagged
        invalid_ans = "Theo Điều 6. Xử phạt vi phạm của Bộ luật Lao động 45/2019/QH14."
        res_invalid = verify_citations_guardrail(invalid_ans, evidence, cited_document_ids=["labor-113"])
        assert res_invalid.status == "unverified"
        assert any("Điều 6 không thuộc văn bản 45/2019/QH14" in w for w in res_invalid.warnings)

    def test_grounding_index_does_not_contaminate_article_mapping_from_title_so_hieu(self):
        """Verifies that when an evidence item has its own so_hieu (e.g. Decree 145/2020/NĐ-CP)
        and mentions the parent law in ten_van_ban, the article is mapped only to Decree 145, not to the parent law."""
        evidence = [
            {
                "document_id": "decree-145-doc",
                "so_hieu": "145/2020/NĐ-CP",
                "dieu": "Điều 5",
                "ten_van_ban": "Nghị định quy định chi tiết thi hành một số điều của Bộ luật Lao động 45/2019/QH14",
            }
        ]
        index = build_grounding_index(evidence)
        # Both document numbers are recognized in valid_so_hieu
        assert "145/2020/NĐ-CP" in index.valid_so_hieu
        assert "45/2019/QH14" in index.valid_so_hieu
        # But Điều 5 belongs ONLY to 145/2020/NĐ-CP, NOT 45/2019/QH14
        assert "5" in index.valid_dieu_by_so_hieu.get("145/2020/NĐ-CP", set())
        assert "5" not in index.valid_dieu_by_so_hieu.get("45/2019/QH14", set())



def test_quantitative_claim_missing_from_evidence_is_not_verified():
    evidence = [{
        "document_id": "traffic-quant-1",
        "text": "Quy dinh ve nong do con.",
        "metadata": {"id": "traffic-quant-1", "domain": "traffic", "dieu": "\u0110i\u1ec1u 6"},
    }]
    result = verify_citations_guardrail(
        answer="Muc phat la 500.000 \u0111\u1ed3ng theo \u0110i\u1ec1u 6.",
        evidence=evidence,
        cited_document_ids=["traffic-quant-1"],
        verify_quantitative_claims=True,
    )
    assert result.status == "unverified"
    assert result.citations == []
    assert result.warnings


def test_quantitative_guardrail_normalizes_leading_zero_and_deduplicates():
    evidence = [{
        "document_id": "traffic-speed-1",
        "text": "Chạy quá tốc độ từ 5 km/h đến 20 km/h.",
        "metadata": {"id": "traffic-speed-1", "domain": "traffic"},
    }]
    result = verify_citations_guardrail(
        answer="Mức 05 km/h và 20 km/h; mức 20 km/h áp dụng theo quy định.",
        evidence=evidence,
        cited_document_ids=["traffic-speed-1"],
        verify_quantitative_claims=True,
    )
    assert result.status == "verified"


def test_quantitative_guardrail_normalizes_units_and_decimal_values():
    evidence = [{
        "document_id": "traffic-alcohol-1",
        "text": "Nồng độ cồn từ 0,25 mg/l đến 0,4 mg/l khí thở; mức phạt 4.000.000 đồng.",
        "metadata": {"id": "traffic-alcohol-1", "domain": "traffic"},
    }]
    result = verify_citations_guardrail(
        answer="Nồng độ cồn từ 0.25 mg/l đến 0,4 miligam/l; phạt 4 triệu đồng.",
        evidence=evidence,
        cited_document_ids=["traffic-alcohol-1"],
        verify_quantitative_claims=True,
    )
    assert result.status == "verified"


def test_quantitative_guardrail_does_not_confuse_decimal_with_integer():
    evidence = [{
        "document_id": "traffic-alcohol-2",
        "text": "Nồng độ cồn 25 mg/l.",
        "metadata": {"id": "traffic-alcohol-2", "domain": "traffic"},
    }]
    result = verify_citations_guardrail(
        answer="Nồng độ cồn 0,25 mg/l.",
        evidence=evidence,
        cited_document_ids=["traffic-alcohol-2"],
        verify_quantitative_claims=True,
    )
    assert result.status == "unverified"


def test_quantitative_guardrail_matches_million_currency_to_full_dong():
    evidence = [{
        "document_id": "traffic-fine-1",
        "text": "Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng.",
        "metadata": {"id": "traffic-fine-1", "domain": "traffic"},
    }]
    result = verify_citations_guardrail(
        answer="Mức phạt từ 4 triệu đồng đến 6 triệu đồng.",
        evidence=evidence,
        cited_document_ids=["traffic-fine-1"],
        verify_quantitative_claims=True,
    )
    assert result.status == "verified"
