from app.retrieval import BM25Okapi, rrf_fuse


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
