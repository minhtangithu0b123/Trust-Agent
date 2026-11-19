from langchain_core.documents import Document

from app.retrieval import BM25Okapi, HybridResult, HybridRetriever, rrf_fuse


def test_rrf_fuses_overlap_before_single_source_results():
    result = rrf_fuse([["a", "b", "c"], ["x", "b", "a"]])
    assert [item_id for item_id, _ in result[:2]] == ["a", "b"]
    assert result[0][1] > result[-1][1]


def test_bm25_keyword_retrieval_prefers_exact_legal_term():
    index = BM25Okapi([
        ["người", "lao", "động", "nghỉ", "hằng", "năm"],
        ["thời", "giờ", "làm", "việc", "bình", "thường"],
        ["hợp", "đồng", "lao", "động", "thử", "việc"],
    ])
    scores = index.get_scores(["nghỉ", "hằng", "năm"])
    assert int(scores.argmax()) == 0


def test_metadata_filter_cannot_cross_domains():
    document = Document(page_content="", metadata={"domain": "traffic"})
    assert HybridRetriever._matches_metadata_filter(document, {"domain": "traffic"})
    assert not HybridRetriever._matches_metadata_filter(document, {"domain": "labor"})


def test_parent_context_keeps_child_id_and_adds_sibling_clauses():
    retriever = object.__new__(HybridRetriever)
    retriever.domain = "labor"
    child = Document(
        page_content="Nội dung khoản 1.",
        metadata={
            "id": "child-1", "domain": "labor", "so_hieu": "45/2019/QH14",
            "dieu": "Điều 25", "tieu_de_dieu": "Thời gian thử việc",
            "khoan": "Khoản 1", "clause_number": "1",
        },
    )
    sibling = Document(
        page_content="Nội dung khoản 2.",
        metadata={
            "id": "child-2", "domain": "labor", "so_hieu": "45/2019/QH14",
            "dieu": "Điều 25", "tieu_de_dieu": "Thời gian thử việc",
            "khoan": "Khoản 2", "clause_number": "2",
        },
    )
    retriever._documents = {"child-1": child, "child-2": sibling}
    results = retriever._expand_parent_context([HybridResult(child, 0.1)])
    assert results[0].document.metadata["id"] == "child-1"
    assert "Nội dung khoản 1." in results[0].document.page_content
    assert "Nội dung khoản 2." in results[0].document.page_content


def test_parent_context_never_drops_ranked_child_behind_earlier_clauses():
    retriever = object.__new__(HybridRetriever)
    retriever.domain = "traffic"
    documents = {}
    for number in [*range(1, 11), 16]:
        content = f"Nội dung không liên quan khoản {number}."
        if number == 1:
            content = "Phạt tiền từ 400.000 đến 600.000 đồng cho hành vi khác."
        elif number == 9:
            content = "Phạt tiền từ 18 đến 20 triệu đồng do không chấp hành đèn tín hiệu."
        elif number == 16:
            content = "Hành vi tại khoản 9 bị trừ điểm giấy phép lái xe."
        document = Document(
            page_content=content,
            metadata={
                "id": f"clause-{number}", "domain": "traffic",
                "so_hieu": "168/2024/NĐ-CP", "source": "same-source",
                "dieu": "Điều 6", "tieu_de_dieu": "Xử phạt ô tô",
                "khoan": f"Khoản {number}", "clause_number": str(number),
            },
        )
        documents[f"clause-{number}"] = document
    retriever._documents = documents

    child = documents["clause-9"]
    results = retriever._expand_parent_context(
        [HybridResult(child, 0.1)],
        "Ô tô vượt đèn đỏ bị phạt bao nhiêu, có bị trừ điểm bằng lái không?",
    )

    assert results[0].document.metadata["id"] == "clause-9"
    assert "Phạt tiền từ 18 đến 20 triệu" in results[0].document.page_content
    assert "400.000 đến 600.000" not in results[0].document.page_content
    assert "trừ điểm giấy phép lái xe" in results[0].document.page_content


def test_parent_context_scopes_red_light_points_to_four_not_ten():
    retriever = object.__new__(HybridRetriever)
    retriever.domain = "traffic"
    child = Document(
        page_content="Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng đối với vượt đèn đỏ.",
        metadata={
            "id": "penalty-9", "domain": "traffic", "so_hieu": "168/2024/NĐ-CP",
            "source": "same-source", "dieu": "Điều 6", "khoan": "Khoản 9",
        },
    )
    points = Document(
        page_content=(
            "Ngoài việc bị áp dụng hình thức xử phạt, điểm b, điểm c, điểm d khoản 9 "
            "Điều này bị trừ điểm giấy phép lái xe 04 điểm; d) điểm a khoản 9 "
            "Điều này bị trừ điểm giấy phép lái xe 10 điểm."
        ),
        metadata={
            "id": "points-16", "domain": "traffic", "so_hieu": "168/2024/NĐ-CP",
            "source": "same-source", "dieu": "Điều 6", "khoan": "Khoản 16",
        },
    )
    retriever._documents = {"penalty-9": child, "points-16": points}

    result = retriever._expand_parent_context(
        [HybridResult(child, 0.1)],
        "Ô tô vượt đèn đỏ có bị trừ điểm bằng lái không?",
    )[0].document.page_content

    assert "04 điểm" in result
    assert "10 điểm" not in result
    assert "giấy phép lái xe" in result


def test_top_red_light_hit_does_not_expose_other_point_branches():
    retriever = object.__new__(HybridRetriever)
    retriever.domain = "traffic"
    child = Document(
        page_content=(
            "Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng đối với hành vi "
            "không chấp hành hiệu lệnh của đèn tín hiệu giao thông; "
            "b) Thực hiện hành vi quy định tại điểm h khoản 5; khoản 6; "
            "điểm b, điểm c, điểm d khoản 9 Điều này bị trừ điểm giấy phép lái xe 04 điểm; "
            "c) Thực hiện hành vi quy định tại điểm a khoản 9 bị trừ điểm giấy phép lái xe 10 điểm."
        ),
        metadata={
            "id": "full-clause-9", "domain": "traffic", "so_hieu": "168/2024/NĐ-CP",
            "source": "same-source", "dieu": "Điều 6", "khoan": "Khoản 9",
        },
    )
    retriever._documents = {"full-clause-9": child}
    result = retriever._expand_parent_context(
        [HybridResult(child, 0.1)],
        "Ô tô vượt đèn đỏ có bị trừ điểm bằng lái không?",
    )[0].document.page_content

    assert "18.000.000 đồng" in result
    assert "04 điểm" in result
    assert "10 điểm" not in result


def test_formal_red_light_query_uses_same_point_branch_filter():
    retriever = object.__new__(HybridRetriever)
    retriever.domain = "traffic"
    child = Document(
        page_content=(
            "Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng; "
            "b) Thực hiện hành vi quy định tại điểm b khoản 9 Điều này bị trừ "
            "điểm giấy phép lái xe 04 điểm; d) điểm a khoản 9 bị trừ 10 điểm."
        ),
        metadata={
            "id": "formal-red-light", "domain": "traffic", "so_hieu": "168/2024/NĐ-CP",
            "source": "same-source", "dieu": "Điều 6", "khoan": "Khoản 9",
        },
    )
    retriever._documents = {"formal-red-light": child}
    result = retriever._expand_parent_context(
        [HybridResult(child, 0.1)],
        "Ô tô không chấp hành hiệu lệnh của đèn tín hiệu giao thông và bị trừ bao nhiêu điểm?",
    )[0].document.page_content

    assert "04 điểm" in result
    assert "10 điểm" not in result
