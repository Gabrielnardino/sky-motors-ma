"""
Pure state machine for Sky Motors SDR qualification flow.
No I/O, no side effects — all functions take state dict and return (new_state, response_text).
"""
from typing import Any

from src.core.language import (
    Lang, detect_language, get_message, is_yes, is_no,
    CREDIT_SCORE_MAP, CONDITION_MAP, INTEREST_MAP,
)

State = dict[str, Any]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def process_message(state: State, text: str) -> tuple[State, str]:
    """
    Main dispatch: routes to the handler for the current step.
    Returns (updated_state, reply_text).
    """
    text = text.strip()
    step = state.get("etapa", "select_language")

    handlers = {
        "select_language": _handle_select_language,
        "ask_name": _handle_ask_name,
        "ask_interest": _handle_ask_interest,
        # buy flow
        "buy_vehicle": _handle_buy_vehicle,
        "buy_budget": _handle_buy_budget,
        "buy_trade_in": _handle_buy_trade_in,
        "buy_trade_in_details": _handle_buy_trade_in_details,
        "buy_trade_in_payoff": _handle_buy_trade_in_payoff,
        "buy_financing": _handle_buy_financing,
        "buy_down_payment": _handle_buy_down_payment,
        "buy_credit_score": _handle_buy_credit_score,
        "buy_best_time": _handle_best_time,
        # trade flow
        "trade_vehicle": _handle_trade_vehicle,
        "trade_mileage": _handle_trade_mileage,
        "trade_condition": _handle_trade_condition,
        "trade_payoff": _handle_trade_payoff,
        "trade_title": _handle_trade_title,
        "trade_best_time": _handle_best_time,
        # financing flow
        "fin_vehicle": _handle_fin_vehicle,
        "fin_down_payment": _handle_fin_down_payment,
        "fin_credit_score": _handle_fin_credit_score,
        "fin_pre_approved": _handle_fin_pre_approved,
        "fin_best_time": _handle_best_time,
        # terminal
        "done": _handle_done,
        "agent": _handle_agent,
    }

    handler = handlers.get(step)
    if handler is None:
        return state, get_message(_lang(state), "error")

    return handler(state, text)


# ---------------------------------------------------------------------------
# Initial steps
# ---------------------------------------------------------------------------

def initial_state() -> State:
    return {"etapa": "select_language"}


def _lang(state: State) -> Lang:
    return state.get("idioma", "EN")


def _handle_select_language(state: State, text: str) -> tuple[State, str]:
    detected = detect_language(text)
    if detected:
        new_state = {**state, "idioma": detected, "etapa": "ask_name"}
        return new_state, get_message(detected, "ask_name")

    choice = text.strip()
    lang_map: dict[str, Lang] = {"1": "PT", "2": "ES", "3": "EN"}
    if choice in lang_map:
        lang = lang_map[choice]
        new_state = {**state, "idioma": lang, "etapa": "ask_name"}
        return new_state, get_message(lang, "ask_name")

    return state, get_message("EN", "invalid_lang")


def _handle_ask_name(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    name = text.title()
    new_state = {**state, "nome": name, "etapa": "ask_interest"}
    return new_state, get_message(lang, "ask_interest", name=name)


def _handle_ask_interest(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    choice = text.strip()

    if choice not in ("1", "2", "3", "4"):
        return state, get_message(lang, "invalid_option")

    if choice == "4":
        new_state = {**state, "interesse": "agent", "etapa": "agent"}
        return new_state, get_message(lang, "agent_redirect")

    interest_labels = {"1": "buy", "2": "trade", "3": "financing"}
    next_steps = {"1": "buy_vehicle", "2": "trade_vehicle", "3": "fin_vehicle"}
    next_msgs = {"1": "ask_vehicle", "2": "ask_trade_vehicle", "3": "ask_fin_vehicle"}

    new_state = {**state, "interesse": interest_labels[choice], "etapa": next_steps[choice]}
    return new_state, get_message(lang, next_msgs[choice])


# ---------------------------------------------------------------------------
# Buy flow
# ---------------------------------------------------------------------------

def _handle_buy_vehicle(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    new_state = {**state, "veiculo_interesse": text, "etapa": "buy_budget"}
    return new_state, get_message(lang, "ask_budget")


def _handle_buy_budget(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    new_state = {**state, "budget": text, "etapa": "buy_trade_in"}
    return new_state, get_message(lang, "ask_trade_in")


def _handle_buy_trade_in(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    if is_yes(lang, text):
        new_state = {**state, "tem_trade_in": True, "etapa": "buy_trade_in_details"}
        return new_state, get_message(lang, "ask_trade_in_details")
    if is_no(lang, text):
        new_state = {**state, "tem_trade_in": False, "etapa": "buy_financing"}
        return new_state, get_message(lang, "ask_financing")
    return state, get_message(lang, "ask_trade_in")


def _handle_buy_trade_in_details(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = state.get("trade_in", {})
    trade_in["descricao"] = text
    new_state = {**state, "trade_in": trade_in, "etapa": "buy_trade_in_payoff"}
    return new_state, get_message(lang, "ask_trade_in_payoff")


def _handle_buy_trade_in_payoff(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = state.get("trade_in", {})
    if is_yes(lang, text):
        trade_in["payoff"] = True
        trade_in["payoff_valor"] = text
    else:
        trade_in["payoff"] = False
    new_state = {**state, "trade_in": trade_in, "etapa": "buy_financing"}
    return new_state, get_message(lang, "ask_financing")


def _handle_buy_financing(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    if is_yes(lang, text):
        new_state = {**state, "precisa_financing": True, "etapa": "buy_down_payment"}
        return new_state, get_message(lang, "ask_down_payment")
    if is_no(lang, text):
        new_state = {**state, "precisa_financing": False, "etapa": "buy_best_time"}
        return new_state, get_message(lang, "ask_best_time")
    return state, get_message(lang, "ask_financing")


def _handle_buy_down_payment(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    new_state = {**state, "down_payment": text, "etapa": "buy_credit_score"}
    return new_state, get_message(lang, "ask_credit_score")


def _handle_buy_credit_score(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    score = CREDIT_SCORE_MAP.get(text.strip())
    if not score:
        return state, get_message(lang, "ask_credit_score")
    new_state = {**state, "credit_score_range": score, "etapa": "buy_best_time"}
    return new_state, get_message(lang, "ask_best_time")


# ---------------------------------------------------------------------------
# Trade-in / Sell flow
# ---------------------------------------------------------------------------

def _handle_trade_vehicle(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = {"descricao": text}
    new_state = {**state, "trade_in": trade_in, "etapa": "trade_mileage"}
    return new_state, get_message(lang, "ask_trade_mileage")


def _handle_trade_mileage(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = {**state.get("trade_in", {}), "km": text}
    new_state = {**state, "trade_in": trade_in, "etapa": "trade_condition"}
    return new_state, get_message(lang, "ask_trade_condition")


def _handle_trade_condition(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    condition = CONDITION_MAP.get(text.strip())
    if not condition:
        return state, get_message(lang, "ask_trade_condition")
    trade_in = {**state.get("trade_in", {}), "condicao": condition}
    new_state = {**state, "trade_in": trade_in, "etapa": "trade_payoff"}
    return new_state, get_message(lang, "ask_trade_in_payoff")


def _handle_trade_payoff(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = state.get("trade_in", {})
    if is_yes(lang, text):
        trade_in = {**trade_in, "payoff": True, "payoff_valor": text}
    else:
        trade_in = {**trade_in, "payoff": False}
    new_state = {**state, "trade_in": trade_in, "etapa": "trade_title"}
    return new_state, get_message(lang, "ask_trade_title")


def _handle_trade_title(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    trade_in = {**state.get("trade_in", {}), "titulo": text}
    new_state = {**state, "trade_in": trade_in, "etapa": "trade_best_time"}
    return new_state, get_message(lang, "ask_best_time")


# ---------------------------------------------------------------------------
# Financing flow
# ---------------------------------------------------------------------------

def _handle_fin_vehicle(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    new_state = {**state, "veiculo_interesse": text, "etapa": "fin_down_payment"}
    return new_state, get_message(lang, "ask_down_payment")


def _handle_fin_down_payment(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    new_state = {**state, "down_payment": text, "etapa": "fin_credit_score"}
    return new_state, get_message(lang, "ask_credit_score")


def _handle_fin_credit_score(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    score = CREDIT_SCORE_MAP.get(text.strip())
    if not score:
        return state, get_message(lang, "ask_credit_score")
    new_state = {**state, "credit_score_range": score, "etapa": "fin_pre_approved"}
    return new_state, get_message(lang, "ask_pre_approved")


def _handle_fin_pre_approved(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    pre = is_yes(lang, text)
    new_state = {**state, "pre_aprovado": pre, "etapa": "fin_best_time"}
    return new_state, get_message(lang, "ask_best_time")


# ---------------------------------------------------------------------------
# Shared terminal steps
# ---------------------------------------------------------------------------

def _handle_best_time(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    name = state.get("nome", "")
    new_state = {**state, "contato_preferido": text, "etapa": "done"}
    return new_state, get_message(lang, "confirm", name=name)


def _handle_done(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    return state, get_message(lang, "confirm", name=state.get("nome", ""))


def _handle_agent(state: State, text: str) -> tuple[State, str]:
    lang = _lang(state)
    return state, get_message(lang, "agent_redirect")


# ---------------------------------------------------------------------------
# Lead card builder
# ---------------------------------------------------------------------------

def build_lead_card(state: State, phone: str) -> str:
    from datetime import datetime
    import zoneinfo

    tz = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M EST")

    lang = _lang(state)
    interest_key = state.get("interesse", "")
    interest_label = INTEREST_MAP.get(
        {"buy": "1", "trade": "2", "financing": "3", "agent": "4"}.get(interest_key, ""),
        {},
    ).get(lang, interest_key)

    trade = state.get("trade_in") or {}
    trade_str = (
        f"{trade.get('descricao', 'N/A')} | {trade.get('km', '')} km | "
        f"{trade.get('condicao', '')} | payoff: {trade.get('payoff', False)}"
        if trade else "N/A"
    )

    clean_phone = phone.replace("@c.us", "")

    lines = [
        "*NEW LEAD — SKY MOTORS*",
        "------------------------",
        f"Name: {state.get('nome', 'N/A')}",
        f"WhatsApp: {clean_phone}",
        f"Language: {lang}",
        f"Time: {now}",
        "------------------------",
        f"Interest: {interest_label}",
        f"Vehicle: {state.get('veiculo_interesse', 'N/A')}",
        f"Budget: {state.get('budget', 'N/A')}",
        f"Trade-in: {trade_str}",
        f"Financing: {'Yes' if state.get('precisa_financing') else 'No'}",
        f"Down Payment: {state.get('down_payment', 'N/A')}",
        f"Credit Score: {state.get('credit_score_range', 'N/A')}",
        f"Pre-approved: {state.get('pre_aprovado', 'N/A')}",
        f"Best time to call: {state.get('contato_preferido', 'N/A')}",
        "------------------------",
        f"Open chat: https://wa.me/{clean_phone}",
    ]
    return "\n".join(lines)


def is_qualified(state: State) -> bool:
    return state.get("etapa") == "done"
