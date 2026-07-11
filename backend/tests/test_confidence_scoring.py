import pytest
import asyncio
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from app.services.confidence_scoring import compute_confidence, _keyword_score


@pytest.mark.asyncio
async def test_compute_confidence_unknown_intent():
    # 3. compute_confidence("anything", "unknown") returns 0.0 immediately (no API call)
    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_ainvoke:
        score = await compute_confidence("anything", "unknown")
        assert score == 0.0
        mock_ainvoke.assert_not_called()


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_compute_confidence_sales_lead_high_score(mock_ainvoke):
    # 1. compute_confidence("enterprise lead demo", "sales_lead") returns score >= 0.7
    mock_ainvoke.return_value = AIMessage(
        content='{"score": 0.85, "explanation": "Strong sales intent"}'
    )
    score = await compute_confidence("enterprise lead demo", "sales_lead")
    assert score >= 0.7
    mock_ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_compute_confidence_invoice_processing_high_score(mock_ainvoke):
    # 2. compute_confidence("invoice $500 due Nov 30", "invoice_processing") returns score >= 0.7
    mock_ainvoke.return_value = AIMessage(
        content='{"score": 0.9, "explanation": "Strong invoice intent"}'
    )
    score = await compute_confidence("invoice $500 due Nov 30", "invoice_processing")
    assert score >= 0.7
    mock_ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_keyword_score_high_confidence():
    # 7. _keyword_score with 4+ positive matches returns score >= 0.8
    # positive keywords for sales_lead: "lead", "prospect", "demo", "trial", "pricing", "quote", "contract", "enterprise"
    # total_positive = 15. We supply 8 positive keywords.
    # min(0.9, 0.6 + (8 / 15) * 0.4) = 0.813 >= 0.8
    content = "lead prospect demo trial pricing quote contract enterprise"
    score = _keyword_score(content, "sales_lead")
    assert score is not None
    assert score >= 0.8

    # Also test integration: compute_confidence bypasses LLM
    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_ainvoke:
        res = await compute_confidence(content, "sales_lead")
        assert res == score
        mock_ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_keyword_score_low_confidence():
    # 8. _keyword_score with 0 positive + 2 negative returns 0.1
    # negative keywords for customer_support: "lead", "prospect", "demo", "invoice", "board"
    # We supply 2 negative keywords: "lead demo"
    content = "lead demo"
    score = _keyword_score(content, "customer_support")
    assert score == 0.1

    # Also test integration: compute_confidence bypasses LLM
    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_ainvoke:
        res = await compute_confidence(content, "customer_support")
        assert res == 0.1
        mock_ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_keyword_score_inconclusive():
    # 9. _keyword_score with inconclusive result returns None
    content = "demo"  # only 1 positive keyword, positive_hits < 4
    score = _keyword_score(content, "sales_lead")
    assert score is None


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_gpt4o_timeout_fallback(mock_ainvoke):
    # 4. GPT-4o timeout -> returns 0.5
    mock_ainvoke.side_effect = asyncio.TimeoutError()

    score = await compute_confidence("We want a demo", "sales_lead")
    assert score == 0.5


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_gpt4o_clamping_upper(mock_ainvoke):
    # 5. GPT-4o returns {"score": 1.8} -> clamped to 1.0
    mock_ainvoke.return_value = AIMessage(
        content='{"score": 1.8, "explanation": "Perfect score"}'
    )

    score = await compute_confidence("We want a demo", "sales_lead")
    assert score == 1.0


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_gpt4o_invalid_json(mock_ainvoke):
    # 6. GPT-4o returns invalid JSON -> returns 0.5
    mock_ainvoke.return_value = AIMessage(
        content="invalid json output string"
    )

    score = await compute_confidence("We want a demo", "sales_lead")
    assert score == 0.5


@pytest.mark.asyncio
@patch("langchain_openai.ChatOpenAI.ainvoke")
async def test_gpt4o_sales_content_invoice_intent_low_score(mock_ainvoke):
    # 10. Score for sales content against invoice_processing intent is < 0.3
    mock_ainvoke.return_value = AIMessage(
        content='{"score": 0.15, "explanation": "Sales content evaluated against invoice intent"}'
    )
    score = await compute_confidence(
        "We want to purchase enterprise plan demo", "invoice_processing"
    )
    assert score < 0.3
