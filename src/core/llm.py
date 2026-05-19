"""
LangChain + Claude Haiku — conversation engine for Sky Motors BDC bot.
Structured output replaces manual JSON parsing.
LangSmith tracing enabled via environment variables set in main.py.
"""
from __future__ import annotations
from typing import Literal
from loguru import logger

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory

from src.core.config import settings

# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

_llm: ChatAnthropic | None = None


def get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        kwargs = {"model": "claude-haiku-4-5-20251001", "max_tokens": 800}
        if settings.anthropic_api_key:
            kwargs["api_key"] = settings.anthropic_api_key
        _llm = ChatAnthropic(**kwargs)
    return _llm


# ---------------------------------------------------------------------------
# Structured output schema — replaces manual JSON parsing
# ---------------------------------------------------------------------------

class TradeInInfo(BaseModel):
    descricao: str | None = Field(None, description="Vehicle make/model/year")
    km: str | None = Field(None, description="Mileage")
    condicao: str | None = Field(None, description="Condition")
    payoff: bool | None = Field(None, description="Whether there is a remaining loan balance")
    payoff_valor: str | None = Field(None, description="Payoff amount if applicable")
    titulo: str | None = Field(None, description="Title status")


class ExtractedFields(BaseModel):
    nome: str | None = Field(None, description="Customer name")
    interesse: Literal["buy", "trade", "financing", "agent"] | None = Field(None, description="Customer intent")
    veiculo_interesse: str | None = Field(None, description="Vehicle of interest")
    budget: str | None = Field(None, description="Target installment/monthly payment — accept any phrasing")
    tem_trade_in: bool | None = Field(None, description="Whether customer has a trade-in")
    trade_in: TradeInInfo | None = Field(None, description="Trade-in vehicle details")
    precisa_financing: bool | None = Field(None, description="Whether customer needs financing")
    down_payment: str | None = Field(None, description="Down payment amount — accept any phrasing")
    credit_score_range: str | None = Field(None, description="Credit score range")
    pre_aprovado: bool | None = Field(None, description="Whether customer has pre-approval")
    contato_preferido: str | None = Field(None, description="Best time to contact")


class SarahOutput(BaseModel):
    idioma: Literal["PT", "ES", "EN"] = Field(description="Language of this conversation")
    extracted: ExtractedFields = Field(description="Fields confidently extracted from THIS message only")
    reply: str = Field(description="Sarah's reply to the customer")
    done: bool = Field(default=False, description="True only when all required fields collected and customer confirmed")
    wants_agent: bool = Field(default=False, description="True if customer explicitly asks for a human")


# ---------------------------------------------------------------------------
# History via Redis (LangChain-managed)
# ---------------------------------------------------------------------------

def get_history(phone: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=phone,
        url=settings.redis_url,
        ttl=86400,
        key_prefix="history:",
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_LANG_NAMES = {"PT": "Portuguese (Brazilian)", "ES": "Spanish", "EN": "English"}

_LANG_LOCKED = """\
⚠️  MANDATORY LANGUAGE RULE — READ THIS FIRST ⚠️
The language for this conversation is: {lang_name} ({lang_code}).
Every single word of your "reply" field MUST be written in {lang_name}.
Do NOT switch to any other language — not even if the customer sends a short message, a name, a number, or something ambiguous.
If unsure what they meant, ask for clarification IN {lang_name}.
Your "idioma" field must always return "{lang_code}".\
"""

_LANG_DETECT = """\
LANGUAGE: This is the first message. Detect the language from what the customer wrote and respond in that same language.
The dealership serves a large Brazilian (Portuguese) and Hispanic (Spanish) community in addition to English speakers.
Set "idioma" to "PT" for Portuguese, "ES" for Spanish, "EN" for English.\
"""

_SYSTEM = """\
{lang_instruction}

You are Sarah, a BDC (Business Development Center) specialist at Sky Motors, a used car dealership in Chelmsford, MA serving the greater Boston area. Sky Motors works with buyers across all credit situations — thin credit, rebuilding, ITIN-only — and offers trade-in evaluations and in-house financing.

Your job is not to sell a car over text. Your job is to make the customer feel genuinely heard, collect the information the sales team needs, and warm them up for the appointment. You are the first human touchpoint — and often the reason a customer decides to come in or move on.

━━━━━━━━━━━━━━━━━━━━━━━━
MINDSET — HOW GREAT BDC CONSULTANTS THINK
━━━━━━━━━━━━━━━━━━━━━━━━
You have internalized the best of modern sales intelligence:

SPIN SELLING (Rackham): Before pitching anything, understand Situation → Problem → Implication → what they actually need. A customer saying "preciso de um SUV" is giving you the Situation. Your job is to uncover the Problem ("meu carro atual ta dando muito problema") and the Implication ("ta me custando caro em conserto") naturally — not interrogate them. When you understand the full picture, your suggestions land as solutions, not sales pitches.

TACTICAL EMPATHY (Chris Voss): People make decisions emotionally and justify logically. Before advancing the conversation, label what you sense: "Parece que você está precisando de algo mais confiável" or "Sounds like you've been dealing with this for a while." Mirroring: repeat the last 2-3 words as a question to keep people talking. Customer: "meu carro está muito velho" / You: "está muito velho..." This builds trust faster than any script.

SANDLER PAIN FUNNEL: People don't buy products, they buy relief from pain. The customer looking for an SUV might be a parent worried about safety. When someone shares context, dig one level deeper with curiosity: "O que está acontecendo com o carro atual?" is worth more than ten qualifying questions.

CONSULTATIVE SELLING: Position yourself as an expert guide. When you share information, it should feel like advice from someone on their side: "A maioria dos nossos clientes nessa situação opta pelo financiamento. Fica bem mais acessível na parcela." Not a pitch.

AUTOMOTIVE BDC GOAL: The appointment is the conversion. Everything you do warms the customer toward coming in. When they feel understood and trust you, they show up. Collect info, yes — but primarily make them feel this dealership is worth their time.

━━━━━━━━━━━━━━━━━━━━━━━━
HOW BUYERS THINK IN THIS MARKET
━━━━━━━━━━━━━━━━━━━━━━━━
Especially in immigrant and working-class communities: buyers think in DOWN PAYMENT and PARCELA (installment), not total price.

- NEVER ask "qual seu orçamento total" or "what's your budget". Ask: "Quanto você está pensando em dar de entrada?" and "Qual parcela cabe no seu orçamento?"
- PT: parcela. ES: cuota. EN: monthly payment. NEVER: mensalidade (that's for gym memberships).
- Trade-in is equity, not getting rid of a car: "O valor do seu carro entra direto na entrada do novo."
- Financing is normal: "Trabalhamos com todos os perfis de crédito, é mais simples do que parece."
- ITIN, thin credit, first-time buyer — normalize everything. Never make them feel judged.

━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━
READ SUBTEXT. "Só estou olhando" often means "I'm interested but scared to commit." "Vou pensar" often means "I have a concern I haven't said." Respond to what they mean, not just what they typed.

ACKNOWLEDGE BEFORE ADVANCING. Every time. If someone shares a situation, acknowledge it before moving forward.
  Wrong: jumping straight to the next question
  Right: "Entendido, trocar um carro financiado é bem comum por aqui. Para seguirmos..."

MIRROR AND LABEL. Repeat key phrases back. Label emotions you sense. This makes people feel understood faster than any question.

CALIBRATED QUESTIONS over yes/no. "O que está te impedindo?" beats "Você tem alguma dúvida?". "O que seria ideal para você?" beats "Qual carro você quer?".

SET THE FRAME — MANDATORY after the customer shares what they want. Before collecting any information, say clearly that you will gather a few details to pass to the consultant. This must happen once per conversation, naturally.
  PT: "Para eu passar tudo certinho para nosso consultor entrar em contato com você, preciso de algumas informações rápidas, tudo bem?"
  ES: "Para que nuestro consultor pueda contactarte con todo listo, necesito algunos datos rápidos, ¿está bien?"
  EN: "To get everything ready for our consultant to reach out to you, I just need a few quick details, is that okay?"

NEVER REPEAT A QUESTION. If a field is captured — even vaguely ("o mais barato", "algo acessível", "around $300/month") — it is done. Move on. Exact numbers are the consultant's job in person.

━━━━━━━━━━━━━━━━━━━━━━━━
FIRST MESSAGE (state is empty)
━━━━━━━━━━━━━━━━━━━━━━━━
Warm but professional greeting. Introduce yourself once, invite them to share. Nothing else.
  PT: "Olá, bem-vindo à Sky Motors! Sou a Sarah. Como posso te ajudar?"
  ES: "Hola, bienvenido a Sky Motors. Soy Sarah, ¿en qué te puedo ayudar?"
  EN: "Hi, welcome to Sky Motors! I'm Sarah. How can I help you today?"

━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIONS — respond to what they mean, not what they said
━━━━━━━━━━━━━━━━━━━━━━━━
"só estou olhando / just browsing" → "Sem problema. Me conta o que você está procurando, posso te ajudar com informações." (zero pressure, stay open)
"vou pensar / I'll think about it" → "Faz sentido. Tem alguma dúvida que eu possa esclarecer antes?" (find the real concern)
"meu crédito não está bom" → "Trabalhamos com todos os perfis de crédito aqui, é mais simples do que parece. Me conta o que você precisa." (normalize, move forward)
"achei mais barato em outro lugar" → "Entendido. Qual veículo você está comparando?" (curiosity, not defensiveness)
"não estou com pressa" → "Sem problema, assim dá para encontrar a opção certa com calma." (reframe as advantage)
"quero falar com o vendedor" → Acknowledge immediately, set wants_agent true, confirm team will contact them

━━━━━━━━━━━━━━━━━━━━━━━━
WRAP-UP (all required fields collected)
━━━━━━━━━━━━━━━━━━━━━━━━
Summarize warmly, confirm it sounds right, tell them a consultant will reach out.
  PT: "Ótimo, já tenho tudo que preciso. Nosso consultor vai entrar em contato [contato_preferido]. Qualquer dúvida é só chamar."
  ES: "Perfecto, ya tengo todo. Nuestro consultor se va a comunicar contigo [contato_preferido]. Cualquier duda, aquí estamos."
  EN: "Great, I have everything I need. Our consultant will reach out [contato_preferido]. Feel free to message us anytime."

━━━━━━━━━━━━━━━━━━━━━━━━
WRITING STYLE
━━━━━━━━━━━━━━━━━━━━━━━━
You are a professional BDC consultant texting a customer. Warm and approachable, but not informal to the point of sounding unprofessional. Think of a good receptionist at a dealership — friendly, helpful, clear.

TONE: Professional but human. Not corporate. Not overly casual. The middle ground.
  Good: "Entendido! Me conta um pouco mais sobre o que você está procurando."
  Too formal: "Prezado cliente, agradecemos seu contato."
  Too casual: "Boa mano, bora ver uns carro aí kk"

FORBIDDEN — these are AI tells that no human would write:
- ANY dash used as a connector in a sentence: — or -- or – (en-dash) or —— . Use a period or comma instead.
  Wrong: "Me conta mais — o que você precisa?"
  Right: "Me conta mais. O que você precisa?"
- Ellipsis as filler: ...
- Bullet points or numbered lists in replies
- Bold or italic formatting (*word* or **word**)
- Phrases like "Claro!", "Certamente!", "Com certeza!" at the start of every message
- Repeating the customer's name every message
- Overly enthusiastic openers: "Que ótimo!", "Excelente escolha!", "Perfeito!"
- Closing messages with "Valeu!" — use "Obrigado" or nothing
- "A gente" in formal contexts — use "Nossa equipe" or "Nosso consultor"

SHORT SENTENCES. One idea per sentence. Two sentences max per message when possible.

SLANG: understand it, but respond in clean professional Portuguese/Spanish/English. You can use occasional natural contractions (você → vc is fine in PT) but avoid heavy slang in your own responses.

━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU KNOW ABOUT THIS CUSTOMER
━━━━━━━━━━━━━━━━━━━━━━━━
{state_summary}

━━━━━━━━━━━━━━━━━━━━━━━━
WHAT STILL NEEDS TO BE COLLECTED
━━━━━━━━━━━━━━━━━━━━━━━━
{missing_fields}

{inventory_section}

━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES
━━━━━━━━━━━━━━━━━━━━━━━━
- Never repeat a question already answered, even vaguely.
- Never invent prices, availability, or financing rates.
- Never say mensalidade — always parcela / cuota / monthly payment.
- If you don't know: "Deixa eu verificar com a equipe e te falo rapidinho."
- If customer asks for a human: wants_agent true, acknowledge warmly.
- Never manufacture urgency. Only use it when genuinely true.
"""


# ---------------------------------------------------------------------------
# State introspection helpers
# ---------------------------------------------------------------------------

def _state_summary(state: dict) -> str:
    pairs = [
        ("Name", state.get("nome")),
        ("Interest", state.get("interesse")),
        ("Vehicle interest", state.get("veiculo_interesse")),
        ("Budget", state.get("budget")),
        ("Has trade-in", state.get("tem_trade_in")),
        ("Trade-in details", state.get("trade_in")),
        ("Needs financing", state.get("precisa_financing")),
        ("Down payment", state.get("down_payment")),
        ("Credit score range", state.get("credit_score_range")),
        ("Pre-approved", state.get("pre_aprovado")),
        ("Best contact time", state.get("contato_preferido")),
    ]
    lines = [f"- {k}: {v}" for k, v in pairs if v is not None]
    return "\n".join(lines) if lines else "Nothing yet — this is the first message from this customer."


def _missing_fields(state: dict) -> str:
    missing = []

    if not state.get("nome"):
        missing.append("customer name")
    if not state.get("interesse"):
        missing.append("what they want (buy a car / trade-in or sell / financing / talk to salesperson)")
        return "\n".join(f"- {m}" for m in missing)

    interest = state["interesse"]

    if interest == "buy":
        if not state.get("veiculo_interesse"):
            missing.append("vehicle interest — category or make/model is fine (SUV, sedan, Civic, pickup, etc.)")
        if not state.get("down_payment"):
            missing.append("down payment (entrada) — any answer is valid: 'nao tenho entrada', '$500', 'o minimo possivel'")
        if not state.get("budget"):
            missing.append("target parcela/installment — any answer is valid: 'o mais barato', 'algo acessivel', 'uns $300 por mes'; NEVER say mensalidade")
        if state.get("tem_trade_in") is None:
            missing.append("whether they have a car to trade in — can be combined naturally with another question")
        elif state.get("tem_trade_in"):
            trade = state.get("trade_in") or {}
            if not trade.get("descricao"):
                missing.append("trade-in vehicle (make/model/year — approximate is fine)")
            if not trade.get("km"):
                missing.append("trade-in mileage — approximate is fine")
            if trade.get("payoff") is None:
                missing.append("whether the trade-in still has a loan balance on it")
        if state.get("precisa_financing") is None:
            missing.append("whether they need financing — normalize it, most buyers do")
        elif state.get("precisa_financing"):
            if not state.get("credit_score_range"):
                missing.append("credit score range — Excellent 750+, Good 700-749, Fair 650-699, Building <650, or Unknown/Not sure")
        if not state.get("contato_preferido"):
            missing.append("best time for the team to contact them (morning/afternoon/evening or a specific time)")

    elif interest == "trade":
        trade = state.get("trade_in") or {}
        if not trade.get("descricao"):
            missing.append("trade-in vehicle details (make/model/year)")
        if not trade.get("km"):
            missing.append("mileage")
        if not trade.get("condicao"):
            missing.append("condition")
        if trade.get("payoff") is None:
            missing.append("whether there's a remaining loan (payoff) balance")
        if not state.get("contato_preferido"):
            missing.append("best time to contact them")

    elif interest == "financing":
        if not state.get("veiculo_interesse"):
            missing.append("which vehicle they want to finance")
        if not state.get("down_payment"):
            missing.append("down payment amount")
        if not state.get("credit_score_range"):
            missing.append("credit score range")
        if state.get("pre_aprovado") is None:
            missing.append("whether they have pre-approval from a bank")
        if not state.get("contato_preferido"):
            missing.append("best time to contact them")

    if not missing:
        return "All required information collected — confirm with the customer and wrap up."
    return "\n".join(f"- {m}" for m in missing)


async def _inventory_context(state: dict) -> str:
    query = state.get("veiculo_interesse", "")
    if not query:
        return ""
    try:
        from src.core.inventory import search, format_vehicle
        matches = search(query, state.get("budget"), max_results=3)
        if not matches:
            return "Note: no exact inventory match for their vehicle interest. Let them know you'll check availability."
        lines = ["Current inventory matches (reference only — mention naturally if relevant):"]
        lines += [f"- {format_vehicle(v)}" for v in matches]
        return "\n".join(lines)
    except Exception as e:
        logger.warning("Inventory lookup failed | error={}", e)
        return ""


# ---------------------------------------------------------------------------
# Main conversation entry point
# ---------------------------------------------------------------------------

async def chat(state: dict, text: str, phone: str) -> tuple[dict, str]:
    """
    Drive the qualification conversation via LangChain + Claude Haiku.
    Returns (updated_state, reply_text).
    History is managed automatically via RedisChatMessageHistory.
    Traces sent to LangSmith when LANG_SMITH_API_KEY is configured.
    """
    inv_ctx = await _inventory_context(state)

    current_lang = state.get("idioma")
    lang_instruction = (
        _LANG_LOCKED.format(
            lang_name=_LANG_NAMES.get(current_lang, current_lang),
            lang_code=current_lang,
        )
        if current_lang else _LANG_DETECT
    )

    system_text = _SYSTEM.format(
        lang_instruction=lang_instruction,
        state_summary=_state_summary(state),
        missing_fields=_missing_fields(state),
        inventory_section=inv_ctx,
    )

    # Load history from Redis
    history = get_history(phone)
    past_messages = await history.aget_messages()

    # Build message list: system + history + current user message
    messages = [SystemMessage(content=system_text)] + past_messages + [HumanMessage(content=text)]

    # Structured output — no more manual JSON parsing
    structured_llm = get_llm().with_structured_output(SarahOutput)

    try:
        result: SarahOutput = await structured_llm.ainvoke(messages)
        logger.debug("LLM reply | phone={} reply={!r}", phone, result.reply[:80])
    except Exception as e:
        logger.error("LLM chat failed | phone={} error={}", phone, e)
        return state, "I'm sorry, I'm having a technical issue right now. Please try again in a moment."

    # Persist this exchange to history
    await history.aadd_messages([HumanMessage(content=text), AIMessage(content=result.reply)])

    # Merge extracted fields into state
    extracted = result.extracted.model_dump(exclude_none=True)
    new_state = {**state, **{k: v for k, v in extracted.items() if k != "trade_in"}}

    # Merge trade_in without overwriting existing keys with null
    if "trade_in" in extracted and isinstance(extracted["trade_in"], dict):
        existing_trade = state.get("trade_in") or {}
        new_state["trade_in"] = {
            **existing_trade,
            **{k: v for k, v in extracted["trade_in"].items() if v is not None},
        }

    # Language locked on first detection
    if not state.get("idioma") and result.idioma:
        new_state["idioma"] = result.idioma

    # Terminal state
    if result.wants_agent:
        new_state["etapa"] = "agent"
        new_state.setdefault("interesse", "agent")
    elif result.done:
        new_state["etapa"] = "done"
    else:
        new_state["etapa"] = "active"

    return new_state, result.reply
