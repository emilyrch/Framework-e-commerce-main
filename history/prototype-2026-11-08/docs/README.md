# Documentação da LPS de e-commerce

Baseline da etapa 2 — 08/11/2026. **Somente documentação: arquitetura e comportamentos descritos ainda serão implementados.** As decisões do usuário para roupas/alimentos substituem as propostas da etapa 1; não alteram as exigências acadêmicas.

## Documentação de referência atual

| Documento | Responsabilidade |
|---|---|
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

O README da raiz ainda descreve a execução do protótipo existente; não foi modificado nesta etapa limitada a docs. Exemplos de manifestos neste diretório não criam configurações executáveis. Código, testes, dependências, Dockerfile e Compose permanecem intactos.
