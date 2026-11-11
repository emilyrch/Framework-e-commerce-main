# Documentação da LPS de e-commerce

Atualização da etapa 5A — 08/11/2026. **Revisão persistida e janelas internas implementadas**, sobre a fundação/catálogos existentes. Sem sessão de navegador, integração visual, carrinho, checkout, admissão de pedido, autorização ou recuperação. Frontend/build/lint/typecheck, instalação Python limpa e Compose continuam pendentes.

Comece por [revisão e janelas da etapa 5A](revisao-etapa5a.md), com chamadas PowerShell, resultados e limites de confiança. Guias das etapas anteriores registram o que foi implementado naquele momento; suas afirmações de ausência de revisão/agenda não descrevem mais o backend atual.

## Documentação de referência atual

| Documento | Responsabilidade |
|---|---|
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

O README da raiz orienta o runtime ativo. O protótipo anterior permanece em [history](../history/prototype-2026-11-08/HISTORY.md), com inventário; não é produto ativo do lançador. Suítes ativas: `tests/foundation`, `tests/catalog` e `tests/reviews`; legado separado em `tests/legacy`. Nenhuma validação histórica equivale a aprovar recursos ainda não implementados.
