# Documentação da LPS de e-commerce

Evidência posterior: [capturas reais de roupas e compra confirmada](capturas-roupas-2026-11-10.md). A execução manual do navegador foi bem-sucedida para roupas; demais bloqueios e verificações anteriores mantêm seu alcance.

Referência mais recente: [finalização da compra e entrega](finalizacao-compra-e-entrega.md), [roteiro de apresentação](preparacao-apresentacao.md). Relatório atualizado em `output/pdf/Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_atualizado.pdf`, versão editável em `output/Relatorio_LPS_Emily_Rocha_atualizado_editavel.html`.

Referência mais recente: [Imagens e recomendações](recomendacoes-e-imagens.md). Atualiza arquitetura para quatro microsserviços, catálogo de roupas para dez peças e evidências atuais; resultados anteriores abaixo são históricos.

Atualizado em 10/11/2026 após homologação real: **67 testes backend completos (HTTP/asyncio/worker), 31 offline, 10 testes web e 24 vetores de configuração aprovados**. Frontend build/lint/typecheck, E2E Next.js, navegador, instalação Python limpa e Compose continuam bloqueados. O loopback funcionou nesta execução. [Estado final e roteiro](entrega-final.md).

## Documentação de referência atual

| Documento | Responsabilidade |
|---|---|
| [homologacao-2026-11-10.md](homologacao-2026-11-10.md) | Comandos executados nesta sessão, correções, resultados e impedimentos concretos |
| [entrega-final.md](entrega-final.md) | Estado atual, evidências, bloqueios, comando único e roteiro acadêmico |
| [frontend-etapa6.md](frontend-etapa6.md) | Interface compartilhada, sessão, intermediário e evidências atuais |
| [backend-etapa5b.md](backend-etapa5b.md) | Backend atual, reenvios, execução e validação limitada |
| [revisao-etapa5a.md](revisao-etapa5a.md) | Revisão durável, janelas, cliente HTTP, dono interno, testes e preparo de 5B |
| [catalogo-etapa4.md](catalogo-etapa4.md) | Estado atual do catálogo, revisão, componentes, permissões, imagens e testes |
| [fundacao-etapa3.md](fundacao-etapa3.md) | Implementação real, versões, comandos, resultados e limitações |
| [plano-mvp.md](plano-mvp.md) | Escopo, origem das exigências e fluxos do cliente |
| [modelo-lps.md](modelo-lps.md) | Features, matriz, restrições, exemplos completos de configuração e derivação |
| [arquitetura-atual.md](arquitetura-atual.md) | Arquitetura-alvo, armazenamento, migração e contratos de componentes |
| [contratos-api.md](contratos-api.md) | Fronteiras HTTP, sessão, modelos, exemplos, erros, saúde e tempos |
| [recuperacao.md](recuperacao.md) | Reenvios, estados, persistência, concorrência e diagramas de sequência |
| [validacao.md](validacao.md) | Requisitos com origem e matriz de cenários/evidências futuras |
| [decisoes-e-etapas.md](decisoes-e-etapas.md) | Decisões confirmadas, resoluções e recorte da etapa 3 |

Não há features opcionais desligáveis nesta versão: o núcleo é obrigatório e o domínio é uma alternativa exclusiva. FastAPI, três serviços, SQLite e estratégias de sessão/idempotência são escolhas do projeto, não exigências adicionais do professor.

## Registros históricos

- [diagnostico.md](diagnostico.md): estado analisado na etapa 1, preservado com nota datada da etapa 2. Execução histórica dos testes do protótipo não valida o novo MVP.
- [arquitetura.md](arquitetura.md): modelo do protótipo Básica/Premium; **não é a arquitetura de referência atual**.
- [historico-original.md](historico-original.md): README original e galeria.

O README da raiz orienta o runtime ativo. O protótipo anterior permanece em [history](../history/prototype-2026-11-08/HISTORY.md), com inventário; não é produto ativo do lançador. Suítes ativas: `tests/foundation`, `tests/catalog`, `tests/reviews` e `tests/checkout`; legado separado em `tests/legacy`. Nenhuma validação histórica equivale a aprovar recursos ainda não implementados.
