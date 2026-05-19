import asyncpg
from loguru import logger

from src.core.config import settings

_pool: asyncpg.Pool | None = None

_INIT_SQL = """
CREATE SCHEMA IF NOT EXISTS skymotors;

CREATE TABLE IF NOT EXISTS skymotors.leads (
    id                 BIGSERIAL     PRIMARY KEY,
    telefone           VARCHAR(20)   NOT NULL,
    nome               VARCHAR(200),
    idioma             VARCHAR(5)    DEFAULT 'EN',
    interesse          VARCHAR(100),
    veiculo_interesse  VARCHAR(200),
    budget             VARCHAR(100),
    tem_trade_in       BOOLEAN       DEFAULT FALSE,
    trade_in_details   JSONB,
    precisa_financing  BOOLEAN       DEFAULT FALSE,
    down_payment       VARCHAR(100),
    credit_score_range VARCHAR(50),
    pre_aprovado       BOOLEAN,
    contato_preferido  VARCHAR(100),
    status             VARCHAR(50)   DEFAULT 'New Lead',
    link_whatsapp      TEXT,
    observacoes        TEXT,
    criado_em          TIMESTAMPTZ   DEFAULT NOW(),
    atualizado_em      TIMESTAMPTZ   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skymotors.mensagens (
    id        BIGSERIAL    PRIMARY KEY,
    telefone  VARCHAR(20)  NOT NULL,
    direcao   VARCHAR(10)  NOT NULL,
    texto     TEXT,
    etapa     VARCHAR(50),
    idioma    VARCHAR(5),
    criado_em TIMESTAMPTZ  DEFAULT NOW()
);

-- Migrations: add columns that may be missing from older table versions
ALTER TABLE skymotors.mensagens ADD COLUMN IF NOT EXISTS idioma VARCHAR(5);
"""


async def init_pool() -> None:
    global _pool
    # asyncpg doesn't accept the +asyncpg driver prefix
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute(_INIT_SQL)
    logger.info("Database pool ready")


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call init_pool() first")
    return _pool
