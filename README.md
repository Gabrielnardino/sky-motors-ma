# Sky Motors SDR Bot - Camila 🚁💭

Este projeto é uma implementação PROFISSIONAL de um bot de SDR para a concessioncária **Sky Motors**.

## 🚹 Tecnologias

- **Python 3.12+**
- **FastAPI**
- **OpenAI API** (gpt-4o-mini)
- **Redis**: Gerento de estado, histórico e deduplicação.
- **PostgreSQL:** Armazenamento persistente de leads qualificados.
- **SQLAlchemy (Async)**: ORM para interac�ão com banco.

## �SI Arquitetura

- _src/database/db_client.py_: Conexões e modelos.
- _src/core/agent.py_: Engenharia de prompt e extração de dados.
- _src/main.py_: Orquestração assíncrona.

## ⚙ Pré-requisitos

- Redis rodando
  / PostgreSQL rodando

## ?fnf Configuração

1. `uv sync`
2. Configure o `.env` (REDIS_URL, DATABASE_URL)
3. `uv run python src/main.py`

Os leads qualificados são salvos automaticamente no Postgres asós a identificação pela Camila.
