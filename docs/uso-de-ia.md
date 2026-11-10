# Uso de IA

Registro de como a IA foi utilizada no desenvolvimento deste case.

## Ferramenta

Usei o **Claude Code** como auxiliar no desenvolvimento. O Claude Code é uma ferramenta da Anthropic que roda no terminal: ele lê os arquivos do projeto, escreve e altera código, roda comandos (como o `pytest`) e explica o que fez.

A IA foi usada como apoio, não como piloto automático. As decisões de projeto foram minhas: eu definia o que devia ser feito, revisava o que a IA produzia e pedia mudanças quando algo não fazia sentido para o case.

## O `CLAUDE.md`: como a IA foi guiada

O Claude Code lê automaticamente o arquivo [`CLAUDE.md`](../CLAUDE.md), na raiz do repositório, no começo de cada sessão. Usei esse arquivo para passar à IA, de uma vez só, tudo o que ela precisava saber sobre o projeto, em vez de repetir as mesmas instruções em cada conversa.

O `CLAUDE.md` define:

- **Contexto:** o que é o case e o que o avaliador valoriza (simplicidade bem estruturada em vez de complexidade).
- **Stack:** Python, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest e Angular, além do que **não** usar (outras ferramentas, bibliotecas ou camadas não previstas).
- **Arquitetura:** as camadas `domain/`, `application/`, `infra/` e `api/`, o que cada uma pode importar e o que é proibido. Por exemplo, nada de FastAPI ou SQLAlchemy dentro do domínio, e nenhuma regra de negócio nas rotas ou no frontend.
- **Modelo de domínio e regras de negócio:** o `Produto`, a `Reserva` e o `Bloqueio`, como os saldos são calculados e cada regra com a exceção correspondente.
- **API:** as rotas, os códigos HTTP de sucesso e o mapeamento de cada exceção para um código de erro.
- **Testes:** o que testar em cada nível (unitário, integração e sequências de operações) e como nomear os testes.
- **Forma de trabalho:** a ordem dos passos (domínio → casos de uso → infra → API → testes de sequência → seed → frontend → README), sem adiantar etapas futuras, rodando o `pytest` ao fim de cada passo e só seguindo com todos os testes passando.
- **Registro de decisões:** toda decisão não coberta pelo `CLAUDE.md` devia ser anotada com o motivo.

Com isso, a IA trabalhava sempre dentro dos mesmos limites. Quando eu mudava de ideia sobre alguma coisa, atualizava o `CLAUDE.md`, e as sessões seguintes já seguiam a regra nova. Foi o caso, por exemplo, da troca do `pedido_id` da reserva por um `motivo` opcional e da remoção do controle de concorrência.
