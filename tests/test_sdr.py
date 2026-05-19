"""Tests for the pure SDR state machine."""
import pytest
from src.core.sdr import process_message, initial_state, is_qualified, build_lead_card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_flow(messages: list[str]) -> dict:
    state = initial_state()
    for msg in messages:
        state, _ = process_message(state, msg)
    return state


def run_flow_with_replies(messages: list[str]) -> tuple[dict, list[str]]:
    state = initial_state()
    replies = []
    for msg in messages:
        state, reply = process_message(state, msg)
        replies.append(reply)
    return state, replies


# ---------------------------------------------------------------------------
# Language selection
# ---------------------------------------------------------------------------

class TestLanguageSelection:
    def test_select_pt_by_number(self):
        state, _ = process_message(initial_state(), "1")
        assert state["idioma"] == "PT"
        assert state["etapa"] == "ask_name"

    def test_select_es_by_number(self):
        state, _ = process_message(initial_state(), "2")
        assert state["idioma"] == "ES"

    def test_select_en_by_number(self):
        state, _ = process_message(initial_state(), "3")
        assert state["idioma"] == "EN"

    def test_detect_pt_by_keyword(self):
        state, _ = process_message(initial_state(), "oi")
        assert state["idioma"] == "PT"
        assert state["etapa"] == "ask_name"

    def test_detect_en_by_keyword(self):
        state, _ = process_message(initial_state(), "hi")
        assert state["idioma"] == "EN"
        assert state["etapa"] == "ask_name"

    def test_invalid_choice_stays(self):
        state, reply = process_message(initial_state(), "99")
        assert state["etapa"] == "select_language"

    def test_invalid_choice_reply_is_not_empty(self):
        _, reply = process_message(initial_state(), "xyz")
        assert reply


# ---------------------------------------------------------------------------
# Name step
# ---------------------------------------------------------------------------

class TestAskName:
    def test_name_saved_and_title_cased(self):
        state = run_flow(["3", "john doe"])
        assert state["nome"] == "John Doe"
        assert state["etapa"] == "ask_interest"

    def test_reply_contains_name(self):
        state, replies = run_flow_with_replies(["3", "Alice"])
        assert "Alice" in replies[-1]


# ---------------------------------------------------------------------------
# Buy flow
# ---------------------------------------------------------------------------

class TestBuyFlow:
    def _buy_base(self) -> dict:
        return run_flow(["3", "Bob", "1"])

    def test_interest_buy_sets_etapa(self):
        state = self._buy_base()
        assert state["interesse"] == "buy"
        assert state["etapa"] == "buy_vehicle"

    def test_full_buy_flow_no_trade_no_financing(self):
        state = run_flow([
            "3", "Bob", "1",          # lang, name, buy
            "Honda Civic 2020",        # vehicle
            "under $20,000",           # budget
            "no",                      # no trade-in
            "no",                      # no financing
            "afternoons",              # best time
        ])
        assert state["etapa"] == "done"
        assert state["veiculo_interesse"] == "Honda Civic 2020"
        assert state["budget"] == "under $20,000"
        assert state["tem_trade_in"] is False
        assert state["precisa_financing"] is False
        assert state["contato_preferido"] == "afternoons"

    def test_full_buy_flow_with_trade_and_financing(self):
        state = run_flow([
            "3", "Ana", "1",
            "Toyota RAV4",
            "$25,000-$35,000",
            "yes",
            "Toyota Camry 2018, 80k miles",
            "no",                       # no payoff
            "yes",                      # needs financing
            "$5,000",                   # down payment
            "2",                        # credit score: Good
            "mornings",
        ])
        assert state["etapa"] == "done"
        assert state["tem_trade_in"] is True
        assert state["trade_in"]["descricao"] == "Toyota Camry 2018, 80k miles"
        assert state["precisa_financing"] is True
        assert state["down_payment"] == "$5,000"
        assert state["credit_score_range"] == "Good (700-749)"

    def test_invalid_credit_score_retries(self):
        state, replies = run_flow_with_replies([
            "3", "Bob", "1",
            "Honda Civic",
            "under $15k",
            "no", "yes",
            "$2,000",
            "5",  # invalid
        ])
        assert state["etapa"] == "buy_credit_score"

    def test_qualified_after_done(self):
        state = run_flow([
            "3", "Bob", "1",
            "Honda Civic",
            "under $15k",
            "no", "no",
            "evenings",
        ])
        assert is_qualified(state)


# ---------------------------------------------------------------------------
# Trade flow
# ---------------------------------------------------------------------------

class TestTradeFlow:
    def test_full_trade_flow(self):
        state = run_flow([
            "1", "Carlos", "2",
            "Toyota Corolla 2019",
            "45,000",
            "2",                # condition: Good
            "no",               # no payoff
            "yes, clean title",
            "mornings",
        ])
        assert state["etapa"] == "done"
        assert state["interesse"] == "trade"
        assert state["trade_in"]["condicao"] == "Good"
        assert state["trade_in"]["payoff"] is False

    def test_invalid_condition_retries(self):
        state, _ = run_flow_with_replies([
            "1", "Carlos", "2",
            "Toyota Corolla 2019",
            "45,000",
            "9",  # invalid condition
        ])
        assert state["etapa"] == "trade_condition"


# ---------------------------------------------------------------------------
# Financing flow
# ---------------------------------------------------------------------------

class TestFinancingFlow:
    def test_full_financing_flow(self):
        state = run_flow([
            "3", "Maria", "3",
            "Ford Explorer 2022",
            "$8,000",
            "1",        # Excellent credit
            "yes",      # pre-approved
            "weekends",
        ])
        assert state["etapa"] == "done"
        assert state["down_payment"] == "$8,000"
        assert state["credit_score_range"] == "Excellent (750+)"
        assert state["pre_aprovado"] is True


# ---------------------------------------------------------------------------
# Agent redirect
# ---------------------------------------------------------------------------

class TestAgentFlow:
    def test_agent_redirect(self):
        state, replies = run_flow_with_replies(["3", "John", "4"])
        assert state["etapa"] == "agent"
        assert state["interesse"] == "agent"
        assert replies[-1]  # has a reply


# ---------------------------------------------------------------------------
# Lead card
# ---------------------------------------------------------------------------

class TestLeadCard:
    def test_card_contains_key_fields(self):
        state = run_flow([
            "3", "Alice Smith", "1",
            "Honda Civic",
            "under $20k",
            "no", "no",
            "evenings",
        ])
        card = build_lead_card(state, "15081234567@c.us")
        assert "Alice Smith" in card
        assert "15081234567" in card
        assert "Honda Civic" in card
        assert "wa.me/15081234567" in card

    def test_card_does_not_contain_at_cus(self):
        state = run_flow(["3", "Bob", "1", "Toyota", "15k", "no", "no", "mornings"])
        card = build_lead_card(state, "15551234567@c.us")
        assert "@c.us" not in card
