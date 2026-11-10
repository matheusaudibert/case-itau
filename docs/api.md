# API de Controle de Estoque

Este documento explica todas as rotas da API, o que cada uma recebe e devolve, e todos os erros que podem acontecer.

## Sumário

- [Visão geral](#visão-geral)
- [Conceitos](#conceitos)
- [Objetos devolvidos](#objetos-devolvidos)
- [Erros](#erros)
- [Rotas](#rotas)
  - [Produtos](#produtos)
  - [Entrada e saída](#entrada-e-saída)
  - [Reservas](#reservas)
  - [Bloqueios](#bloqueios)
- [Exemplo de uso completo](#exemplo-de-uso-completo)

## Visão geral

| | |
|---|---|
| Endereço local | `http://localhost:8000` |
| Formato | JSON, no corpo da requisição e da resposta |
| Autenticação | Nenhuma (a API é aberta) |
| Documentação interativa | Swagger em `/docs` (dá para testar as rotas pelo navegador) |

Resumo das rotas:

| Método | Rota | O que faz | Sucesso |
|---|---|---|---|
| `POST` | `/produtos` | Cadastra um produto | 201 |
| `GET` | `/produtos` | Lista todos os produtos | 200 |
| `GET` | `/produtos/{produto_id}` | Consulta um produto e seus saldos | 200 |
| `POST` | `/produtos/{produto_id}/entradas` | Adiciona unidades ao estoque | 200 |
| `POST` | `/produtos/{produto_id}/saidas` | Retira unidades do estoque | 200 |
| `POST` | `/produtos/{produto_id}/reservas` | Cria uma reserva | 201 |
| `GET` | `/produtos/{produto_id}/reservas` | Lista as reservas do produto | 200 |
| `GET` | `/reservas/{reserva_id}` | Consulta uma reserva | 200 |
| `POST` | `/reservas/{reserva_id}/liberar` | Libera uma reserva | 200 |
| `POST` | `/produtos/{produto_id}/bloqueios` | Cria um bloqueio | 201 |
| `GET` | `/produtos/{produto_id}/bloqueios` | Lista os bloqueios do produto | 200 |
| `GET` | `/bloqueios/{bloqueio_id}` | Consulta um bloqueio | 200 |
| `POST` | `/bloqueios/{bloqueio_id}/liberar` | Libera um bloqueio | 200 |

## Conceitos

- **Produto:** item do estoque. O id é escolhido por quem cadastra e segue o formato `P` + 3 números (ex.: `P001`).
- **Total:** quantas unidades existem no estoque.
- **Reservado:** soma das reservas **ativas**. São unidades separadas para algum pedido.
- **Bloqueado:** soma dos bloqueios **ativos**. São unidades que não podem ser usadas (ex.: com defeito).
- **Disponível:** o que sobra para usar: `total − reservado − bloqueado`.
- **Reserva e bloqueio:** registros com id próprio (UUID, gerado pela API). Começam com status `ATIVO` e, quando liberados, passam para `LIBERADO`. Nunca são apagados.

Regra que vale sempre:

```
total = disponível + reservado + bloqueado      (nenhum valor fica negativo)
```

## Objetos devolvidos

### Produto

```json
{
  "id": "P001",
  "nome": "Teclado mecânico",
  "total": 100,
  "disponivel": 77,
  "reservado": 15,
  "bloqueado": 8
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | texto | Id do produto (`P000` a `P999`) |
| `nome` | texto | Nome do produto |
| `total` | número | Unidades no estoque |
| `disponivel` | número | Unidades que podem ser usadas |
| `reservado` | número | Soma das reservas ativas |
| `bloqueado` | número | Soma dos bloqueios ativos |

### Reserva e bloqueio

Os dois têm exatamente os mesmos campos:

```json
{
  "id": "88a25a22-3370-4c8e-895f-5ee2ec36da79",
  "produto_id": "P001",
  "quantidade": 10,
  "motivo": "Reserva para Matheus",
  "status": "ATIVO",
  "criado_em": "2026-11-09T23:30:52.931908Z",
  "liberado_em": null
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | UUID | Id gerado pela API |
| `produto_id` | texto | Produto ao qual pertence |
| `quantidade` | número | Unidades reservadas ou bloqueadas |
| `motivo` | texto ou `null` | Motivo informado na criação (opcional) |
| `status` | `ATIVO` ou `LIBERADO` | Situação atual |
| `criado_em` | data e hora (UTC) | Quando foi criado |
| `liberado_em` | data e hora (UTC) ou `null` | Quando foi liberado; `null` enquanto estiver ativo |

## Erros

### Formato

Todo erro, em qualquer rota, volta no mesmo formato:

```json
{
  "erro": "ESTOQUE_INSUFICIENTE",
  "mensagem": "Estoque insuficiente: foram solicitadas 100 unidades, mas só há 77 disponíveis."
}
```

- `erro`: um código fixo, para o programa que chama a API saber qual erro aconteceu.
- `mensagem`: um texto em português para mostrar ao usuário. O frontend mostra exatamente essa mensagem.

**Uma operação que dá erro não muda nada no estoque.**

### Códigos HTTP

| Código | Quando acontece |
|---|---|
| **404** | Algo não foi encontrado (produto, reserva, bloqueio ou rota) |
| **405** | A rota existe, mas não aceita esse método (ex.: `DELETE /produtos/P001`) |
| **409** | A operação não pode ser feita no estado atual (ex.: falta estoque, reserva já liberada) |
| **422** | Os dados enviados são inválidos |
| **500** | Erro inesperado no servidor |

### Exceções de negócio

Cada regra de negócio quebrada gera uma exceção na camada `domain/`. O código do `erro` é o nome da exceção em maiúsculas, separado por `_`.

| Exceção | Código do erro | HTTP | Quando acontece | Mensagem |
|---|---|---|---|---|
| `ProdutoNaoEncontrado` | `PRODUTO_NAO_ENCONTRADO` | 404 | O produto informado não existe | Produto P999 não encontrado. |
| `ReservaNaoEncontrada` | `RESERVA_NAO_ENCONTRADA` | 404 | A reserva informada não existe | Reserva {id} não encontrada. |
| `BloqueioNaoEncontrado` | `BLOQUEIO_NAO_ENCONTRADO` | 404 | O bloqueio informado não existe | Bloqueio {id} não encontrado. |
| `ProdutoJaExiste` | `PRODUTO_JA_EXISTE` | 409 | Já existe um produto com esse id | Já existe um produto com o id P001. |
| `EstoqueInsuficiente` | `ESTOQUE_INSUFICIENTE` | 409 | Saída, reserva ou bloqueio maior que o disponível | Estoque insuficiente: foram solicitadas 100 unidades, mas só há 77 disponíveis. |
| `ReservaJaLiberada` | `RESERVA_JA_LIBERADA` | 409 | A reserva já tinha sido liberada | Reserva {id} já foi liberada. |
| `BloqueioJaLiberado` | `BLOQUEIO_JA_LIBERADO` | 409 | O bloqueio já tinha sido liberado | Bloqueio {id} já foi liberado. |
| `IdProdutoInvalido` | `ID_PRODUTO_INVALIDO` | 422 | O id não segue o formato `P000` | O id deve seguir o formato "P000": letra P maiúscula seguida de 3 dígitos (ex.: P001). |
| `NomeProdutoInvalido` | `NOME_PRODUTO_INVALIDO` | 422 | O nome está vazio ou só tem espaços | O nome do produto é obrigatório. |
| `QuantidadeInvalida` | `QUANTIDADE_INVALIDA` | 422 | A quantidade não é um inteiro maior que zero | A quantidade deve ser um número inteiro maior que zero. |

Os ids e números da mensagem são sempre os da requisição.

**Por que alguns erros quase nunca aparecem?** A API valida os dados em duas etapas:

1. Primeiro, o FastAPI confere o formato dos dados recebidos (ex.: a quantidade é um número inteiro maior que zero?). Se algo estiver errado, a resposta é `VALIDACAO` (veja abaixo).
2. Depois, as regras de negócio do domínio conferem de novo.

Por isso, na prática, a API devolve `VALIDACAO` em vez de `QUANTIDADE_INVALIDA`, porque a quantidade errada é barrada já na primeira etapa. A regra continua no domínio para que ele nunca aceite um valor inválido, mesmo se for chamado de outro lugar (pelo seed ou pelos testes, por exemplo).

`ID_PRODUTO_INVALIDO` e `NOME_PRODUTO_INVALIDO` só aparecem em casos que passam pela primeira etapa mas não pela segunda:
- um nome só com espaços (`"   "`);
- um id com números que não são de 0 a 9, como `"P١٢٣"` (algarismos arábicos).

### Erros de validação (`VALIDACAO`, 422)

Acontecem quando os dados enviados estão no formato errado. A mensagem depende do campo:

| Situação | Mensagem |
|---|---|
| `id` fora do formato (ex.: `p001`, `P01`, `P0001`) | O id deve seguir o formato "P000": letra P maiúscula seguida de 3 dígitos (ex.: P001). |
| `nome` vazio ou com mais de 200 caracteres | O nome é obrigatório e deve ter no máximo 200 caracteres. |
| `quantidade` zero, negativa, decimal ou em texto (ex.: `0`, `-1`, `5.0`, `"5"`) | A quantidade deve ser um número inteiro maior que zero. |
| `motivo` com mais de 200 caracteres ou que não é texto | O motivo deve ser um texto de no máximo 200 caracteres. |
| `?status=` diferente de `ATIVO` ou `LIBERADO` | O status deve ser ATIVO ou LIBERADO. |
| Id de reserva na URL que não é um UUID | O id da reserva deve ser um UUID válido. |
| Id de bloqueio na URL que não é um UUID | O id do bloqueio deve ser um UUID válido. |
| Campo obrigatório que não foi enviado | O campo "quantidade" é obrigatório. (com o nome do campo) |
| Corpo vazio, JSON quebrado ou que não é um objeto | O corpo da requisição deve ser um JSON válido com os campos esperados. |

Se houver mais de um problema, as mensagens vêm juntas na mesma resposta:

```json
{
  "erro": "VALIDACAO",
  "mensagem": "O campo \"id\" é obrigatório. O campo \"nome\" é obrigatório."
}
```

### Erros gerais

Podem acontecer em qualquer rota:

| Código do erro | HTTP | Quando acontece | Mensagem |
|---|---|---|---|
| `HTTP_404` | 404 | A rota não existe | Rota não encontrada. |
| `HTTP_405` | 405 | A rota não aceita esse método | Método não permitido nesta rota. |
| `ERRO_INTERNO` | 500 | Erro inesperado (um bug, por exemplo). Os detalhes vão para o log do servidor, não para o cliente. | Erro interno inesperado. |

## Rotas

### Produtos

#### `POST /produtos` — cadastrar produto

Cria um produto com todos os saldos zerados. Para ter estoque, depois é preciso fazer uma entrada.

Corpo:

```json
{ "id": "P003", "nome": "Monitor 27" }
```

| Campo | Obrigatório | Regras |
|---|---|---|
| `id` | sim | `P` maiúsculo + exatamente 3 números. `p001`, `P01`, `P0001` e `P 001` são recusados. |
| `nome` | sim | De 1 a 200 caracteres, sem ser só espaços. Os espaços do começo e do fim são removidos. |

Resposta **201**:

```json
{ "id": "P003", "nome": "Monitor 27", "total": 0, "disponivel": 0, "reservado": 0, "bloqueado": 0 }
```

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_JA_EXISTE` | 409 | Já existe um produto com esse id |
| `ID_PRODUTO_INVALIDO` | 422 | Id com números fora de 0–9 (ex.: `"P١٢٣"`) |
| `NOME_PRODUTO_INVALIDO` | 422 | Nome só com espaços |
| `VALIDACAO` | 422 | Id fora do formato, nome vazio ou longo demais, campo faltando |

#### `GET /produtos` — listar produtos

Devolve todos os produtos, ordenados pelo id. Se não houver nenhum, devolve `[]`.

Resposta **200**:

```json
[
  { "id": "P001", "nome": "Teclado mecânico", "total": 100, "disponivel": 77, "reservado": 15, "bloqueado": 8 },
  { "id": "P002", "nome": "Mouse sem fio", "total": 50, "disponivel": 50, "reservado": 0, "bloqueado": 0 }
]
```

Esta rota não tem erros específicos.

#### `GET /produtos/{produto_id}` — consultar produto

Devolve o produto com os saldos atuais.

Resposta **200**:

```json
{ "id": "P001", "nome": "Teclado mecânico", "total": 100, "disponivel": 77, "reservado": 15, "bloqueado": 8 }
```

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe. Um id fora do formato (ex.: `/produtos/abc`) também cai aqui, porque simplesmente não existe. |

### Entrada e saída

#### `POST /produtos/{produto_id}/entradas` — entrada

Adiciona unidades ao `total` do produto. Devolve o produto atualizado.

Corpo:

```json
{ "quantidade": 10 }
```

| Campo | Obrigatório | Regras |
|---|---|---|
| `quantidade` | sim | Número inteiro maior que zero. `"5"`, `5.0` e `true` são recusados. |

Resposta **200** (P001 tinha 100):

```json
{ "id": "P001", "nome": "Teclado mecânico", "total": 110, "disponivel": 87, "reservado": 15, "bloqueado": 8 }
```

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe (a entrada não cria o produto) |
| `VALIDACAO` | 422 | Quantidade inválida ou ausente |

#### `POST /produtos/{produto_id}/saidas` — saída

Retira unidades do `total`. Só pode usar o **disponível**: unidades reservadas ou bloqueadas não saem.

Corpo:

```json
{ "quantidade": 7 }
```

Resposta **200** (P001 tinha 100 no total e 77 disponíveis):

```json
{ "id": "P001", "nome": "Teclado mecânico", "total": 93, "disponivel": 70, "reservado": 15, "bloqueado": 8 }
```

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe |
| `ESTOQUE_INSUFICIENTE` | 409 | A quantidade é maior que o disponível (ex.: pedir 78 com 77 disponíveis, mesmo havendo 100 no total) |
| `VALIDACAO` | 422 | Quantidade inválida ou ausente |

### Reservas

#### `POST /produtos/{produto_id}/reservas` — reservar

Separa unidades disponíveis para um pedido. O `total` não muda; o `disponivel` diminui e o `reservado` aumenta.

Corpo:

```json
{ "quantidade": 10, "motivo": "Reserva para Matheus" }
```

| Campo | Obrigatório | Regras |
|---|---|---|
| `quantidade` | sim | Número inteiro maior que zero |
| `motivo` | não | Texto de até 200 caracteres. Se não for enviado, fica `null`. |

Resposta **201**: a reserva criada, com status `ATIVO`.

```json
{
  "id": "88a25a22-3370-4c8e-895f-5ee2ec36da79",
  "produto_id": "P001",
  "quantidade": 10,
  "motivo": "Reserva para Matheus",
  "status": "ATIVO",
  "criado_em": "2026-11-09T23:30:52.931908Z",
  "liberado_em": null
}
```

Guarde o `id`: ele é usado para consultar e liberar a reserva.

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe |
| `ESTOQUE_INSUFICIENTE` | 409 | A quantidade é maior que o disponível |
| `VALIDACAO` | 422 | Quantidade inválida ou ausente, motivo longo demais |

#### `GET /produtos/{produto_id}/reservas` — listar reservas do produto

Devolve as reservas do produto, da mais antiga para a mais nova. Sem filtro, devolve todas (ativas e liberadas).

Filtro opcional:

| Parâmetro | Valores | Exemplo |
|---|---|---|
| `status` | `ATIVO` ou `LIBERADO` | `/produtos/P001/reservas?status=ATIVO` |

Resposta **200**: uma lista de reservas (pode ser `[]`).

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe |
| `VALIDACAO` | 422 | `status` diferente de `ATIVO` ou `LIBERADO` |

#### `GET /reservas/{reserva_id}` — consultar reserva

Devolve uma reserva pelo id, esteja ela ativa ou liberada.

Resposta **200**: a reserva.

| Erro | HTTP | Quando |
|---|---|---|
| `RESERVA_NAO_ENCONTRADA` | 404 | Não existe reserva com esse id |
| `VALIDACAO` | 422 | O id na URL não é um UUID |

#### `POST /reservas/{reserva_id}/liberar` — liberar reserva

Cancela a reserva: as unidades voltam para o disponível. A reserva **não é apagada**: o status muda para `LIBERADO` e `liberado_em` recebe a data e a hora.

Não tem corpo.

Resposta **200**: a reserva atualizada.

```json
{
  "id": "88a25a22-3370-4c8e-895f-5ee2ec36da79",
  "produto_id": "P001",
  "quantidade": 10,
  "motivo": "Reserva para Matheus",
  "status": "LIBERADO",
  "criado_em": "2026-11-09T23:30:52.931908Z",
  "liberado_em": "2026-11-09T23:35:10.112233Z"
}
```

| Erro | HTTP | Quando |
|---|---|---|
| `RESERVA_NAO_ENCONTRADA` | 404 | Não existe reserva com esse id |
| `RESERVA_JA_LIBERADA` | 409 | A reserva já tinha sido liberada. Liberar duas vezes dá erro, para quem chamou saber que a segunda vez não fez nada. |
| `VALIDACAO` | 422 | O id na URL não é um UUID |

### Bloqueios

Os bloqueios funcionam exatamente como as reservas. A diferença é o significado: o bloqueio deixa unidades indisponíveis, por exemplo por defeito ou conferência.

#### `POST /produtos/{produto_id}/bloqueios` — bloquear

Corpo:

```json
{ "quantidade": 8, "motivo": "Avaria" }
```

| Campo | Obrigatório | Regras |
|---|---|---|
| `quantidade` | sim | Número inteiro maior que zero |
| `motivo` | não | Texto de até 200 caracteres |

Resposta **201**: o bloqueio criado, com status `ATIVO` (mesmos campos da reserva).

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe |
| `ESTOQUE_INSUFICIENTE` | 409 | A quantidade é maior que o disponível |
| `VALIDACAO` | 422 | Quantidade inválida ou ausente, motivo longo demais |

#### `GET /produtos/{produto_id}/bloqueios` — listar bloqueios do produto

Mesmo funcionamento da lista de reservas, inclusive o filtro `?status=ATIVO` ou `?status=LIBERADO`.

| Erro | HTTP | Quando |
|---|---|---|
| `PRODUTO_NAO_ENCONTRADO` | 404 | O produto não existe |
| `VALIDACAO` | 422 | `status` diferente de `ATIVO` ou `LIBERADO` |

#### `GET /bloqueios/{bloqueio_id}` — consultar bloqueio

| Erro | HTTP | Quando |
|---|---|---|
| `BLOQUEIO_NAO_ENCONTRADO` | 404 | Não existe bloqueio com esse id |
| `VALIDACAO` | 422 | O id na URL não é um UUID |

#### `POST /bloqueios/{bloqueio_id}/liberar` — liberar bloqueio

As unidades voltam para o disponível; o bloqueio passa para `LIBERADO`.

| Erro | HTTP | Quando |
|---|---|---|
| `BLOQUEIO_NAO_ENCONTRADO` | 404 | Não existe bloqueio com esse id |
| `BLOQUEIO_JA_LIBERADO` | 409 | O bloqueio já tinha sido liberado |
| `VALIDACAO` | 422 | O id na URL não é um UUID |

## Exemplo de uso completo

Um fluxo do começo ao fim usando `curl`, com a API rodando em `localhost:8000`:

```bash
# 1. Cadastrar o produto (começa com tudo zerado)
curl -X POST localhost:8000/produtos -H "Content-Type: application/json" \
  -d '{"id": "P003", "nome": "Monitor 27"}'
# 201 → total 0, disponível 0

# 2. Dar entrada de 20 unidades
curl -X POST localhost:8000/produtos/P003/entradas -H "Content-Type: application/json" \
  -d '{"quantidade": 20}'
# 200 → total 20, disponível 20

# 3. Reservar 5 para um pedido (guarde o "id" da resposta)
curl -X POST localhost:8000/produtos/P003/reservas -H "Content-Type: application/json" \
  -d '{"quantidade": 5, "motivo": "Pedido 123"}'
# 201 → reserva ATIVO; o produto fica com disponível 15 e reservado 5

# 4. Bloquear 3 com defeito
curl -X POST localhost:8000/produtos/P003/bloqueios -H "Content-Type: application/json" \
  -d '{"quantidade": 3, "motivo": "Avaria"}'
# 201 → o produto fica com disponível 12, reservado 5 e bloqueado 3

# 5. Tentar tirar 15 (só há 12 disponíveis)
curl -X POST localhost:8000/produtos/P003/saidas -H "Content-Type: application/json" \
  -d '{"quantidade": 15}'
# 409 ESTOQUE_INSUFICIENTE → nada muda

# 6. Liberar a reserva
curl -X POST localhost:8000/reservas/<id-da-reserva>/liberar
# 200 → reserva LIBERADO; o produto volta a ter disponível 17

# 7. Consultar o produto
curl localhost:8000/produtos/P003
# 200 → total 20, disponível 17, reservado 0, bloqueado 3
```

## Observações

- **Campos a mais no corpo são ignorados.** Por exemplo, `{"quantidade": 5, "outro": 1}` funciona como `{"quantidade": 5}`.
- **Datas sempre em UTC**, no formato ISO 8601 (o `Z` no fim indica UTC).
- **Não existe rota para editar ou excluir produtos**, nem para editar reservas ou bloqueios. Uma reserva errada deve ser liberada e criada de novo.
