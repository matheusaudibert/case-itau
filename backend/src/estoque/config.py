import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    cors_origins: list[str]
    seed_on_startup: bool


def carregar_config() -> Config:
    return Config(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/estoque.db"),
        cors_origins=lista(os.getenv("CORS_ORIGINS", "http://localhost:4200")),
        seed_on_startup=booleano("SEED_ON_STARTUP", os.getenv("SEED_ON_STARTUP", "true")),
    )


def lista(valor: str) -> list[str]:
    return [item.strip() for item in valor.split(",") if item.strip()]


def booleano(nome: str, valor: str) -> bool:
    normalizado = valor.strip().lower()
    if normalizado == "true":
        return True
    if normalizado == "false":
        return False
    raise ValueError(f"{nome} deve ser true ou false (recebido: {valor!r}).")
