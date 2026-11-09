# CLAUDE.md

Guia para o Claude Code neste repositório. Leia antes de qualquer alteração e siga as decisões abaixo; se algo aqui parecer errado ou insuficiente, pergunte antes de divergir.

## Contexto

Case técnico de **controle de estoque**. Para cada produto: quantidade total, disponível, reservada e bloqueada. Um produto pode ter várias reservas e bloqueios ativos ao mesmo tempo, de solicitações diferentes.

Operações: **entrada, saída, reservar, bloquear, liberar (reserva ou bloqueio) e consultar**.

O avaliador valoriza: modelagem, correção das regras, consistência, testes, tratamento de erros e decisões justificadas. **Simplicidade bem estruturada > complexidade.** Não adicione tecnologias ou camadas que não estejam descritas aqui.

## Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (estilo 2.0, tipado), SQLite
- **Dependências**: `venv` + `pip` com `requirements.txt` (sem uv, poetry ou similares)
- **Testes**: apenas pytest (o `httpx` entra só como dependência do `TestClient` do FastAPI)
- Não usar Hypothesis, ruff, mypy, black, flake8 ou outras ferramentas além das listadas
- **Frontend**: Angular (standalone components, HttpClient), sem NgRx
- **Docker**: só no final do projeto (Dockerfile por app + docker-compose). Não criar antes de ser pedido.

## Arquitetura

Monólito modular em camadas (Clean/Hexagonal leve). **Regra de dependência: tudo aponta para o domínio; o domínio não importa nada externo.**

```
api/  →  application/  →  domain/
              ↓
           infra/  (implementa as interfaces de application/)
```

| Camada | Responsabilidade | Pode importar |
|---|---|---|
| `domain/` | Entidades, regras, invariantes, exceções de domínio. Python puro. | Apenas stdlib |
| `application/` | Casos de uso; define interfaces (`Protocol`) de repositório e Unit of Work | `domain` |
| `infra/` | Modelos SQLAlchemy, repositório, Unit of Work, seed, config do banco | `domain`, `application` |
| `api/` | Rotas FastAPI, schemas Pydantic, tradução de exceções em HTTP | `application`, `domain` (exceções e tipos) |

Proibido: FastAPI, Pydantic ou SQLAlchemy dentro de `domain/`; regra de negócio em rotas, schemas ou repositórios; o frontend replicar regra de negócio (ele só exibe o resultado ou o erro da API).

## Modelo de domínio

- **`Produto`** é a raiz do agregado. Toda alteração de estoque passa por métodos dele:
  `entrada(qtd)`, `saida(qtd)`, `reservar(qtd, motivo) -> Reserva`, `bloquear(qtd, motivo) -> Bloqueio`, `liberar_reserva(reserva_id)`, `liberar_bloqueio(bloqueio_id)`.
- **`Reserva`** e **`Bloqueio`**: id (UUID), produto_id, quantidade, status (`ATIVO` | `LIBERADO`), criado_em, liberado_em. Reserva e bloqueio têm `motivo` (opcional).
- **Saldos — fonte única da verdade:**
  - persistido: `total`
  - derivados: `reservado` = soma das reservas ATIVAS; `bloqueado` = soma dos bloqueios ATIVOS; `disponivel` = total − reservado − bloqueado
  - Não criar colunas contadoras de reservado/bloqueado/disponível.
- **Liberar não apaga**: muda status para `LIBERADO` e grava `liberado_em` (mantém histórico).

### Regras de negócio

1. Toda quantidade deve ser **inteira e > 0** → senão `QuantidadeInvalida`.
2. `saida`, `reservar` e `bloquear` exigem `qtd <= disponivel` → senão `EstoqueInsuficiente`.
3. `saida` reduz o `total` e consome **apenas do disponível** (não consome reservas nem bloqueios).
4. Liberar reserva/bloqueio inexistente → `ReservaNaoEncontrada` / `BloqueioNaoEncontrado`.
5. Liberar reserva/bloqueio já liberado → `ReservaJaLiberada` / `BloqueioJaLiberado` (não é idempotente; decisão documentada).
6. Operação inválida **não altera nada**: validar tudo antes de mutar o estado.
7. Invariantes que devem valer sempre: `total = disponivel + reservado + bloqueado` e nenhum saldo negativo.

Produtos são criados pelo seed ou por `POST /produtos`. Entrada em produto inexistente → `ProdutoNaoEncontrado` (não cria automaticamente).

### Identificação do produto

- O `id` do produto é **informado pelo cliente** e deve seguir o formato **`P` maiúsculo + exatamente 3 dígitos** (regex `^P\d{3}$`, ex.: `P001`) → senão `IdProdutoInvalido`.
- Sem normalização: `p001`, `P01`, `P0001` e `P 001` são rejeitados.
- `nome` é obrigatório e não pode ser vazio ou só espaços → senão `NomeProdutoInvalido`.
- Id já existente → `ProdutoJaExiste`.
- A validação do formato é regra de domínio (fica em `domain/`); o schema Pydantic repete o `pattern` apenas para documentar no Swagger.
- Limitação conhecida (documentar no README): o formato comporta no máximo 1000 produtos (`P000` a `P999`).
- Ids de reservas e bloqueios são UUIDs gerados pelo servidor e devolvidos na resposta de criação.

## Consistência e concorrência

- Cada caso de uso roda em **uma única transação** via Unit of Work: carrega o agregado → chama o domínio → persiste → commit. Qualquer exceção → rollback.
- **Lock otimista**: coluna `version` no produto usando `version_id_col` do SQLAlchemy. Toda operação que altera reservas/bloqueios também incrementa a versão do produto.
- Em conflito de versão (`StaleDataError`): o caso de uso tenta de novo até 3 vezes; persistindo, levanta `ConflitoDeConcorrencia`.
- SQLite: habilitar `PRAGMA foreign_keys=ON`.

## API

| Operação | Rota | Sucesso |
|---|---|---|
| Criar produto | `POST /produtos` (`id`, `nome`) | 201 |
| Listar | `GET /produtos` | 200 |
| Consultar | `GET /produtos/{id}` | 200 (total, disponivel, reservado, bloqueado) |
| Entrada | `POST /produtos/{id}/entradas` (`quantidade`) | 200 |
| Saída | `POST /produtos/{id}/saidas` (`quantidade`) | 200 |
| Reservar | `POST /produtos/{id}/reservas` (`quantidade`, `motivo` opcional) | 201 com a reserva |
| Listar reservas do produto | `GET /produtos/{id}/reservas?status=ATIVO` | 200 |
| Consultar reserva | `GET /reservas/{id}` | 200 |
| Liberar reserva | `POST /reservas/{id}/liberar` | 200 |
| Bloqueios | mesmo padrão: `POST /produtos/{id}/bloqueios`, `GET /produtos/{id}/bloqueios`, `GET /bloqueios/{id}`, `POST /bloqueios/{id}/liberar` | — |

**Mapeamento de erros** (exception handler central em `api/errors.py`, resposta `{"erro": "<codigo>", "mensagem": "<texto>"}`):

| Exceção | HTTP |
|---|---|
| `*NaoEncontrado` / `*NaoEncontrada` | 404 |
| `EstoqueInsuficiente`, `*JaLiberada`/`*JaLiberado`, `ConflitoDeConcorrencia`, `ProdutoJaExiste` | 409 |
| `QuantidadeInvalida`, `IdProdutoInvalido`, `NomeProdutoInvalido` e validação do Pydantic | 422 |

## Estrutura

```
backend/
  src/estoque/
    domain/        produto.py, exceptions.py
    application/   services.py, ports.py
    infra/         models.py, repository.py, uow.py, database.py, seed.py
    api/           main.py, routes.py, schemas.py, errors.py
    config.py
  tests/
    unit/          domínio puro (maioria dos testes)
    integration/   API + SQLite em memória
  data/            arquivo do SQLite (no .gitignore)
  requirements.txt
  pytest.ini
frontend/          Angular
docs/              decisoes.md, uso-de-ia.md
```

## Configuração

Tudo por variável de ambiente (lido em `config.py`), com padrão para rodar localmente:

- `DATABASE_URL` (padrão `sqlite:///./data/estoque.db`)
- `CORS_ORIGINS` (padrão `http://localhost:4200`)
- `SEED_ON_STARTUP` (padrão `true`)

No startup: cria as tabelas se não existirem e roda o seed **somente se o banco estiver vazio**. Seed com **dados fixos** (não aleatórios), com 2 produtos:

| Produto | Total | Reservas ativas | Bloqueios ativos | Saldos esperados |
|---|---|---|---|---|
| `P001` — Teclado mecânico | 100 | 10 (motivo "Reserva para Matheus") e 5 (motivo "Reserva de pré-venda para Julia") | 8 (motivo "Avaria") | reservado 15, bloqueado 8, disponível 77 |
| `P002` — Mouse sem fio | 50 | — | — | reservado 0, bloqueado 0, disponível 50 |

O seed deve criar esses dados pelos próprios casos de uso (entrada, reservar, bloquear), não inserindo direto nas tabelas, para passar pelas mesmas regras.

No Angular, a URL da API fica em `environment.ts`, nunca fixa no código.

## Testes

- **Unitários** (`tests/unit`): cada regra e cada exceção do domínio, sem banco.
- **Integração** (`tests/integration`): endpoints via `TestClient` com SQLite em memória; verificar status HTTP, corpo e que o estado não muda após operação inválida.
- **Invariantes**: testes com sequências de operações (usando `pytest.mark.parametrize`) verificando após cada passo que `total = disponivel + reservado + bloqueado` e que nenhum saldo fica negativo.
- Testes não dependem do seed; cada teste monta seus próprios dados. Nomes descritivos em português (`test_reservar_mais_que_disponivel_levanta_estoque_insuficiente`).

## Convenções de código

- Type hints em funções e atributos públicos.
- Seguir a PEP 8.
- Nomes de domínio em português (produto, reserva, bloqueio, entrada, saida), como no enunciado.
- Funções pequenas, sem comentários óbvios; docstring apenas onde a regra não for evidente.
- Não adicionar dependências sem necessidade clara.

## Comandos

```bash
# backend (dentro de backend/)
python -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn estoque.api.main:app --reload --app-dir src   # API em http://localhost:8000, Swagger em /docs
pytest

# frontend (dentro de frontend/)
npm install
npm start                                      # http://localhost:4200
```

## Forma de trabalho

- Trabalhar em **passos pequenos**, nesta ordem: domínio + testes unitários → casos de uso → infra → API + testes de integração → testes de invariantes → seed → frontend → Docker → README.
- Ao fim de cada passo: rodar `pytest` e só seguir com todos os testes passando.
- Não implementar etapas futuras antecipadamente.
- Ao tomar uma decisão não coberta aqui, registrá-la em `docs/decisoes.md` com o motivo.