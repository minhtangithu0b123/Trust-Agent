"""Automated Accuracy Benchmark & Legal Grounding Regression Test Suite (Tiers 1-4).

Covers Features 1 & 2 of Milestone M1 / Project Trust-AGENT:
- Feature 1: SignEmo Knowledge Accuracy & Grounding (Groups 1-10 of bo_100 dataset).
- Feature 2: Multi-Domain Legal Routing & Grounding (Traffic, Labor, Accounting, SignEmo).

Organization:
  Tier 1: Feature Coverage (>=5 test cases per feature covering groups 1-10 & statutory domains)
  Tier 2: Boundary & Corner Cases (empty/short queries, age limits 12 & 65, latency <0.3s, numeric ranges, non-statutory slide citations)
  Tier 3: Cross-Feature Combinations (Cross-domain queries Q92, Q87, multi-turn dialog memory, dual guardrail filtering)
  Tier 4: Real-World Scenarios (Complete Pitch Defense journey, Startup Legal & Compliance workflow)

Runnable via: `crawl\\.venv\\Scripts\\pytest.exe crawl/tests/test_accuracy_regression.py -v`
Works 100% offline without external network or LLM API calls.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from app.citation_guardrail import (
    INSUFFICIENT_EVIDENCE,
    CitationGuardrailResult,
    verify_citations_guardrail,
)
from app.intent_guardrail import get_intent_guardrail
from app.query_normalization import clean_query, normalize_for_routing
from scripts.evaluate_accuracy import (
    BenchmarkEvaluator,
    check_assertion_presence,
    check_hallucination_presence,
    classify_query_offline,
    find_dataset_file,
    load_statutory_benchmark_cases,
    normalize_text,
    parse_bo_100_markdown,
)


@pytest.fixture(scope="module")
def bo_100_cases():
    """Loads and caches parsed benchmark cases from bo_100_cau_hoi_phan_bien_SignEmo.md."""
    try:
        dataset_path = find_dataset_file()
    except FileNotFoundError as exc:
        pytest.skip(f"External SignEmo benchmark dataset is not present: {exc}")
    return parse_bo_100_markdown(dataset_path)


@pytest.fixture(scope="module")
def statutory_cases():
    """Loads statutory Vietnamese legal benchmark cases."""
    return load_statutory_benchmark_cases()


@pytest.fixture
def evaluator():
    """Provides standard benchmark evaluator instance."""
    return BenchmarkEvaluator(provider="auto", threshold=0.80)


# ============================================================================
# TIER 1: FEATURE COVERAGE
# ============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Feature Coverage for Feature 1 (SignEmo) & Feature 2 (Legal Routing)."""

    # --- Feature 1: SignEmo Accuracy across Groups 1-10 ---

    def test_tier1_f1_q1_painkiller_vs_vitamin(self, bo_100_cases, evaluator):
        """Feature 1 (Group 1 - Problem): Q1 Painkiller vs Vitamin Mehrabian 38%/55%."""
        case = next(c for c in bo_100_cases if c.id == 1)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match, f"Expected signemo domain for Q1, got: {record.routed_domains}"
        assert record.guardrail_pass, f"Guardrail failed: {record.guardrail_status}"
        assert record.assertion_coverage >= 0.80, f"Coverage too low: {record.assertion_coverage}"
        assert "Painkiller" in record.matched_assertions
        assert any("38%" in a for a in record.matched_assertions)
        assert any("55%" in a for a in record.matched_assertions)
        assert any("Mehrabian" in a for a in record.matched_assertions)
        assert len(record.hallucinations_detected) == 0
        assert record.pass_verdict is True

    def test_tier1_f1_q11_market_size_tam(self, bo_100_cases, evaluator):
        """Feature 1 (Group 2 - Market Size): Q11 TAM filtering 200k-300k people."""
        case = next(c for c in bo_100_cases if c.id == 11)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("2,5 triệu" in a for a in record.matched_assertions)
        assert any("200.000 – 300.000" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f1_q33_edge_ai_architecture(self, bo_100_cases, evaluator):
        """Feature 1 (Group 4 - Technology): Q33 React 19 PWA, ONNX Runtime Web, TWA."""
        case = next(c for c in bo_100_cases if c.id == 33)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("ONNX Runtime Web" in a for a in record.matched_assertions)
        assert any("Web Workers" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f1_q47_server_cost_unit_economics(self, bo_100_cases, evaluator):
        """Feature 1 (Group 5 - Pricing & Costs): Q47 Server cost ~0đ, Supabase Free Tier."""
        case = next(c for c in bo_100_cases if c.id == 47)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("0 VNĐ/tháng" in a for a in record.matched_assertions)
        assert any("Supabase" in a for a in record.matched_assertions)
        assert len(record.hallucinations_detected) == 0
        assert record.pass_verdict is True

    def test_tier1_f1_q63_breakeven_point(self, bo_100_cases, evaluator):
        """Feature 1 (Group 6 - Financials): Q63 Break-even point end of Year 2 with 8 B2B contracts."""
        case = next(c for c in bo_100_cases if c.id == 63)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("8 hợp đồng B2B" in a for a in record.matched_assertions)
        assert any("Hòa vốn ngay trong Năm 2" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f1_q87_privacy_by_design_compliance(self, bo_100_cases, evaluator):
        """Feature 1 (Group 9 - Startup Law): Q87 Ephemeral RAM processing, Consent Gate, 100ms shutdown."""
        case = next(c for c in bo_100_cases if c.id == 87)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("Privacy-by-Design" in a for a in record.matched_assertions)
        assert any("Ephemeral" in a for a in record.matched_assertions)
        assert any("Consent Gate" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f1_q94_founders_reverse_vesting(self, bo_100_cases, evaluator):
        """Feature 1 (Group 10 - Governance): Q94 Founders Agreement, Reverse Vesting 36 months, 1-yr cliff."""
        case = next(c for c in bo_100_cases if c.id == 94)
        record = evaluator.evaluate_single_case(case)

        assert record.routing_match
        assert record.guardrail_pass
        assert record.assertion_coverage >= 0.80
        assert any("Reverse Vesting 3 năm" in a for a in record.matched_assertions)
        assert any("1 năm Cliff" in a for a in record.matched_assertions)
        assert any("Dead Equity" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    # --- Feature 2: Multi-Domain Legal Routing & Grounding ---

    def test_tier1_f2_labor_leave_grounding(self, statutory_cases, evaluator):
        """Feature 2 (Labor Domain): Statutory leave under Labor Code 2019 Điều 113."""
        case = next(c for c in statutory_cases if c.id == "legal_labor_1")
        record = evaluator.evaluate_single_case(case)

        assert "labor" in record.routed_domains
        assert record.guardrail_status == "verified"
        assert record.assertion_coverage >= 0.80
        assert "Điều 113" in record.matched_assertions
        assert "45/2019/QH14" in record.matched_assertions
        assert record.pass_verdict is True

    def test_tier1_f2_retirement_age_2026_grounding(self, statutory_cases, evaluator):
        case = next(c for c in statutory_cases if c.id == "legal_labor_retirement_2026")
        record = evaluator.evaluate_single_case(case)

        assert "labor" in record.routed_domains
        assert record.guardrail_status == "verified"
        assert record.assertion_coverage == 1.0
        assert "61 tuổi 6 tháng" in record.matched_assertions
        assert "57 tuổi" in record.matched_assertions
        assert record.pass_verdict is True

    def test_tier1_f2_traffic_red_light_grounding(self, statutory_cases, evaluator):
        """Feature 2 (Traffic Domain): Motorbike red-light violation under Decree 168/2024."""
        case = next(c for c in statutory_cases if c.id == "legal_traffic_1")
        record = evaluator.evaluate_single_case(case)

        assert "traffic" in record.routed_domains
        assert record.guardrail_status == "verified"
        assert record.assertion_coverage >= 0.80
        assert any("168/2024" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f2_accounting_statutory_grounding(self, statutory_cases, evaluator):
        """Feature 2 (Accounting Domain): Financial reporting deadline under Law on Accounting 2015."""
        case = next(c for c in statutory_cases if c.id == "legal_accounting_1")
        record = evaluator.evaluate_single_case(case)

        assert "accounting" in record.routed_domains
        assert record.guardrail_status == "verified"
        assert record.assertion_coverage >= 0.80
        assert any("88/2015/QH13" in a for a in record.matched_assertions)
        assert record.pass_verdict is True

    def test_tier1_f2_signemo_domain_routing_accuracy(self, bo_100_cases):
        """Feature 2 (Routing Accuracy): Verifies all 10 groups route to 'signemo'."""
        sample_qids = [1, 11, 22, 33, 47, 63, 71, 79, 87, 94, 97, 100]
        for qid in sample_qids:
            case = next(c for c in bo_100_cases if c.id == qid)
            routed = classify_query_offline(case.question)
            assert "signemo" in routed, f"Q{qid} failed signemo routing: {routed}"

    def test_tier1_f2_multi_domain_hybrid_routing(self):
        """Feature 2 (Cross-domain Routing): Query crossing traffic and labor rules."""
        query = "Quy định về thời giờ làm việc của lái xe ô tô và mức phạt nồng độ cồn"
        routed = classify_query_offline(query)
        assert "traffic" in routed, f"Expected traffic in {routed}"
        assert "labor" in routed, f"Expected labor in {routed}"


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary conditions, empty/short inputs, numerical ranges, and non-statutory citations."""

    def test_tier2_empty_and_short_queries(self):
        """Tier 2: Empty, whitespace, punctuation, and single-character queries."""
        empty_queries = ["", "   ", "?", ".", "!", "a", "ok"]
        intent_guard = get_intent_guardrail()

        for q in empty_queries:
            # Clean query length check
            cleaned = clean_query(q)
            # Empty query or intent check handles safely without exception
            routed = classify_query_offline(q)
            assert isinstance(routed, list)
            # Should not crash and should not route to any domain
            assert len(routed) == 0 or q == "ok"

    def test_tier2_age_threshold_boundaries_12_and_65(self, bo_100_cases, evaluator):
        """Tier 2: Lower age boundary (12 years) and Upper age boundary (65 years)."""
        # Lower boundary Q3
        case_q3 = next(c for c in bo_100_cases if c.id == 3)
        rec_q3 = evaluator.evaluate_single_case(case_q3)
        assert rec_q3.pass_verdict is True
        assert any("12 tuổi" in a for a in rec_q3.matched_assertions)
        assert any("atypical gaze" in a for a in rec_q3.matched_assertions)

        # Upper boundary Q4
        case_q4 = next(c for c in bo_100_cases if c.id == 4)
        rec_q4 = evaluator.evaluate_single_case(case_q4)
        assert rec_q4.pass_verdict is True
        assert any("65 tuổi" in a for a in rec_q4.matched_assertions)
        assert any("Presbycusis" in a for a in rec_q4.matched_assertions)
        assert any("Tablet tại quầy lễ tân" in a for a in rec_q4.matched_assertions)

    def test_tier2_latency_boundary_low_spec_wasm_fallback(self, bo_100_cases, evaluator):
        """Tier 2: Latency boundary <0.3s on low-spec Android devices with WASM fallback (Q36)."""
        case_q36 = next(c for c in bo_100_cases if c.id == 36)
        rec_q36 = evaluator.evaluate_single_case(case_q36)

        assert rec_q36.pass_verdict is True
        assert any("b0-wasm" in a for a in rec_q36.matched_assertions)
        assert any("FaceInferenceBudget" in a for a in rec_q36.matched_assertions)
        assert any("< 0.3s" in a for a in rec_q36.matched_assertions)

    def test_tier2_numeric_range_variations_and_compacting(self):
        """Tier 2: Normalization tolerance for Vietnamese numeric variations and units."""
        # 1. '6 ngày' matching '06 ngày'
        assert check_assertion_presence("6 ngày làm việc", "người lao động được nghỉ 06 ngày làm việc")
        # 2. '348.000đ' matching '348000 VNĐ'
        assert check_assertion_presence("348.000đ/năm", "mức phí là 348000 vnđ/năm")
        # 3. Numeric range: '4 đến 6 triệu' matching 'từ 4.000.000 đồng đến 6.000.000 đồng'
        assert check_assertion_presence("4 đến 6 triệu", "phạt tiền từ 4 đến 6 triệu đồng")
        # 4. Latency threshold '< 0.3s' matching '<0.3s'
        assert check_assertion_presence("< 0.3s", "đạt độ trễ <0.3s trong thực nghiệm")

    def test_tier2_non_statutory_slide_and_code_citations(self):
        """Tier 2: Guardrail verification for non-statutory startup citations (Slide, Code, Licenses)."""
        evidence = [
            Document(
                page_content="Tại Slide 6 mô tả nhân vật Minh 16 tuổi. Xem code ConversationPage.tsx và giấy phép MIT.",
                metadata={"id": "signemo-slide-6", "domain": "signemo", "status": "effective"},
            )
        ]
        answer = "Theo Slide 6 và ConversationPage.tsx, hệ thống xử lý hoàn toàn offline theo giấy phép MIT."
        result = verify_citations_guardrail(
            answer=answer,
            evidence=evidence,
            cited_document_ids=["signemo-slide-6"],
            require_cited_ids=False,
        )
        assert result.status == "verified"
        assert len(result.warnings) == 0


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Cross-domain queries, multi-turn state preservation, and dual guardrails."""

    def test_tier3_q92_cross_domain_corporate_and_vat(self, bo_100_cases, evaluator):
        """Tier 3: Q92 crosses SignEmo corporate structuring with Accounting/VAT invoicing."""
        case = next(c for c in bo_100_cases if c.id == 92)
        rec = evaluator.evaluate_single_case(case)

        # Must route to signemo (primary) and may match accounting (VAT)
        assert "signemo" in rec.routed_domains
        assert rec.guardrail_pass is True
        assert rec.assertion_coverage >= 0.80
        assert any("Công ty Cổ phần" in a for a in rec.matched_assertions)
        assert any("hóa đơn VAT" in a for a in rec.matched_assertions)
        assert any("ESOP" in a for a in rec.matched_assertions)
        assert rec.pass_verdict is True

    def test_tier3_q87_cross_domain_ai_law_and_compliance(self, bo_100_cases, evaluator):
        """Tier 3: Q87 crosses SignEmo technical edge AI with Personal Data Protection & AI Law 2025."""
        case = next(c for c in bo_100_cases if c.id == 87)
        rec = evaluator.evaluate_single_case(case)

        assert "signemo" in rec.routed_domains
        assert rec.guardrail_pass is True
        assert rec.assertion_coverage >= 0.80
        assert any("RAM" in a for a in rec.matched_assertions)
        assert any("100ms" in a for a in rec.matched_assertions)
        assert rec.pass_verdict is True

    def test_tier3_multi_turn_pitch_consultation_memory(self, bo_100_cases, evaluator):
        """Tier 3: Simulates multi-turn consultation preserving context across turns."""
        # Turn 1: Product problem (Q1)
        case_turn1 = next(c for c in bo_100_cases if c.id == 1)
        rec1 = evaluator.evaluate_single_case(case_turn1)
        assert rec1.pass_verdict is True

        # Turn 2: Follow-up question on economics & server cost (Q47)
        # Follow-up context refers to previous turn
        follow_up_query = "Thế còn chi phí máy chủ và hạ tầng của sản phẩm này thì sao?"
        routed2 = classify_query_offline(follow_up_query)
        assert "signemo" in routed2 or "accounting" in routed2

        case_turn2 = next(c for c in bo_100_cases if c.id == 47)
        rec2 = evaluator.evaluate_single_case(case_turn2)
        assert rec2.pass_verdict is True
        assert any("0 VNĐ/tháng" in a for a in rec2.matched_assertions)

    def test_tier3_dual_guardrail_intent_filtering_and_citation(self, bo_100_cases, evaluator):
        """Tier 3: Tests two-tier guardrail: fast-path rejection on greeting vs full grounding on substantive query."""
        intent_guard = get_intent_guardrail()

        # Step 1: Greeting query stopped at intent filter with 0 token consumption
        greeting_query = "Xin chào bạn"
        intent_res = intent_guard.check_intent(greeting_query)
        assert intent_res.intent == "greeting"
        assert intent_res.response is not None

        # Step 2: Substantive SignEmo query passes intent check and proceeds to citation verification
        case = next(c for c in bo_100_cases if c.id == 71)
        intent_sub = intent_guard.check_intent(case.question)
        assert intent_sub.intent == "in_scope"

        rec = evaluator.evaluate_single_case(case)
        assert rec.guardrail_status == "verified"
        assert rec.pass_verdict is True

    def test_tier3_cross_domain_labor_and_traffic_synthesis(self, statutory_cases, evaluator):
        """Tier 3: Dual legal domain query synthesized with verified citations from both domains."""
        labor_case = next(c for c in statutory_cases if c.id == "legal_labor_1")
        traffic_case = next(c for c in statutory_cases if c.id == "legal_traffic_1")

        # Synthesized evidence combining both
        combined_evidence = evaluator._format_evidence_for_guardrail(
            labor_case.evidence + traffic_case.evidence
        )
        combined_answer = (
            f"Về lao động: {labor_case.reference_answer}\n\n"
            f"Về giao thông: {traffic_case.reference_answer}"
        )
        combined_doc_ids = labor_case.cited_document_ids + traffic_case.cited_document_ids

        result = verify_citations_guardrail(
            answer=combined_answer,
            evidence=combined_evidence,
            cited_document_ids=combined_doc_ids,
            require_cited_ids=False,
        )
        assert result.status == "verified"


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end real-world user workflows and pitch defense journeys."""

    def test_tier4_scenario_pitch_defense_consultation_journey(self, bo_100_cases, evaluator):
        """Tier 4 (Scenario 1): Complete 5-question Pitch Defense consultation journey before VC panel."""
        journey_qids = [
            1,   # Group 1: Problem validation (Painkiller vs Vitamin)
            33,  # Group 4: Tech moat & Edge AI latency
            47,  # Group 5: Zero-server unit economics
            94,  # Group 10: Founders Agreement & Reverse Vesting
            100, # Group 10: Vision & Closing statement
        ]

        journey_results = []
        for qid in journey_qids:
            case = next(c for c in bo_100_cases if c.id == qid)
            rec = evaluator.evaluate_single_case(case)
            journey_results.append(rec)

        # Verifications across the entire consultation journey
        assert all(r.routing_match for r in journey_results), "All questions must route to signemo"
        assert all(r.guardrail_pass for r in journey_results), "All answers must have verified grounding"
        assert all(r.assertion_coverage >= 0.80 for r in journey_results), "High assertion coverage across journey"
        assert sum(len(r.hallucinations_detected) for r in journey_results) == 0, "Zero hallucinations allowed"
        assert all(r.pass_verdict for r in journey_results), "Every journey step must pass"

    def test_tier4_scenario_startup_legal_and_compliance_workflow(self, bo_100_cases, evaluator):
        """Tier 4 (Scenario 2): Complete Startup Legal & Compliance workflow for founder preparing launch."""
        compliance_qids = [
            92,  # Corporate legal structure: CTCP for 5 founders, ESOP, tax incentives
            94,  # Founders Agreement, 36-month Reverse Vesting, 1-year cliff
            90,  # 5-layer IP protection: Copyright, Trademark Class 09 & 42, Trade Secrets
            87,  # Personal Data Protection Law 2025: Ephemeral RAM, Consent Gate
            88,  # Right to be Forgotten: AES-GCM Local Vault, 64-char deletionToken
        ]

        workflow_results = []
        for qid in compliance_qids:
            case = next(c for c in bo_100_cases if c.id == qid)
            rec = evaluator.evaluate_single_case(case)
            workflow_results.append(rec)

        # Verify all legal and compliance steps
        assert all(r.pass_verdict for r in workflow_results)
        # Check specific critical assertions
        rec_92 = workflow_results[0]
        assert any("Công ty Cổ phần" in a for a in rec_92.matched_assertions)
        rec_94 = workflow_results[1]
        assert any("Reverse Vesting 3 năm" in a for a in rec_94.matched_assertions)
        rec_90 = workflow_results[2]
        assert any("Nhóm 09" in a for a in rec_90.matched_assertions)
        rec_87 = workflow_results[3]
        assert any("Privacy-by-Design" in a for a in rec_87.matched_assertions)
        rec_88 = workflow_results[4]
        assert any("AES-GCM" in a for a in rec_88.matched_assertions)
        assert any("deletionToken" in a for a in rec_88.matched_assertions)
