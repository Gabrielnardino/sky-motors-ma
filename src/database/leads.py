import json
from typing import Any

from loguru import logger

from src.core.sdr import State
from src.database.connection import get_pool


async def upsert_lead(phone: str, state: State) -> None:
    pool = get_pool()
    clean_phone = phone.replace("@c.us", "").replace("@lid", "")
    trade_in = state.get("trade_in")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO skymotors.leads (
                telefone, nome, idioma, interesse, veiculo_interesse, budget,
                tem_trade_in, trade_in_details, precisa_financing, down_payment,
                credit_score_range, pre_aprovado, contato_preferido,
                status, link_whatsapp, atualizado_em
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13,
                'New Lead', $14, NOW()
            )
            ON CONFLICT DO NOTHING
            """,
            clean_phone,
            state.get("nome"),
            state.get("idioma", "EN"),
            state.get("interesse"),
            state.get("veiculo_interesse"),
            state.get("budget"),
            bool(state.get("tem_trade_in")),
            json.dumps(trade_in) if trade_in else None,
            bool(state.get("precisa_financing")),
            state.get("down_payment"),
            state.get("credit_score_range"),
            state.get("pre_aprovado"),
            state.get("contato_preferido"),
            f"https://wa.me/{clean_phone}",
        )
        logger.info("Lead saved | phone={}", clean_phone)


async def log_message(phone: str, direction: str, text: str, step: str, lang: str) -> None:
    pool = get_pool()
    clean_phone = phone.replace("@c.us", "").replace("@lid", "")
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO skymotors.mensagens (telefone, direcao, texto, etapa, idioma)
            VALUES ($1, $2, $3, $4, $5)
            """,
            clean_phone, direction, text, step, lang,
        )
