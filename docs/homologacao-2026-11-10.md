# Homologação executada em 10/11/2026

Estado final: backend homologado pela suíte existente; demonstração completa ainda não aprovada. Evidência local detalhada em `.local/validation-latest.json`, gerada por `tools/validate.py` depois das correções. Recursos de teste usam bancos, portas e credenciais temporários; bancos e segredos de demonstração não foram substituídos.

## Correções

- `storefront.tsx` limpava a sacola assim que recebia um order_id, inclusive em payment_pending/payment_unknown. Os três caminhos de resposta agora usam `reconcileConfirmedCart`: exige confirmed e compara a seleção atual com a tentativa. Atualização funcional do estado preserva edições feitas durante a chamada. Regressão cobre estados incertos, rejeição, ausência de ID e alteração de quantidade.
- O teste de processos não fornecia SESSION_SECRET à prontidão web. Agora fornece segredo efêmero e origem de loopback somente ao subprocesso Node. Nenhuma validação de runtime foi removida. A primeira execução completa teve três falhas decorrentes desse preparo; após a correção, passou integralmente.
- README, arquitetura, contratos, recuperação e frontend foram alinhados ao código e às evidências. Registros por etapa permanecem identificados como históricos.

## Execuções e resultados

| Execução | Resultado |
|---|---|
| `tools/validate.py`, repetido após correções | Nenhum check failed; release_ready=false por bloqueios |
| `tools/test_backend.py`, pela validação | 67 testes em 78,608 s, OK; HTTP, asyncio e worker reais |
| `tools/test_backend.py --offline` | 31 testes, OK; subconjunto da suíte completa |
| Node `scripts/test-web.ts` | 10 testes, OK; funções e fronteira web sem renderização |
| Node `scripts/check-config.ts` | 24 vetores, OK |
| compileall | Aprovado |
| Versões Python instaladas | Correspondem a requirements.txt no ambiente existente |
| Inventários history SHA-256 | 41 + 68 arquivos, nenhuma divergência |
| npm ci pelo package-lock | Falhou: Exit handler never called; dependências continuam ausentes |
| npm ping | EACCES no acesso ao registro |
| npm run build / lint / typecheck | Executados; next/eslint/tsc não encontrados |
| Venv isolado | Criado em .local/venv-homologacao-20261110, include-system-site-packages=false |
| pip install -r requirements-dev.txt no venv isolado | Falhou: nenhuma distribuição disponível de annotated-doc==0.0.5 no acesso permitido |
| Diagnóstico PyPI | DNS resolve; HTTPS falha com WinError 10013, acesso a socket proibido |
| pip check do ambiente existente | Conflito externo streamlit-vis-network/setuptools; globais preservados |
| Início via lançador | Recusado no preflight pela ausência do Next.js |
| tools/e2e.py | Chamado diretamente e pela validação; bloqueado por ausência de Next/build |
| Desktop/celular, navegação e console | Não executados; frontend não inicia |
| Docker/Compose | Docker não encontrado no PATH ou caminho padrão; não instalado automaticamente |
| Git/AGENTS.md | Git e .git ausentes; nenhum AGENTS.md encontrado na árvore ou ancestrais aplicáveis |

Os testes completos exercitam catálogo, seleções, endereço, revisão, janelas alimentares, confirmação e consulta nas duas variantes. Também exercitam preços alterados, campos inválidos, dono/loja incorretos, reenvios concorrentes, autorização com resposta perdida, persistência e recuperação após reinício. Parte desses cenários usa serviços de domínio com transporte controlado; os testes HTTP iniciam processos FastAPI reais. Isso não comprova o caminho Next/React nem o comportamento visual do navegador.

## Reprodução e demonstração

Preparação, comandos das duas variantes e roteiro acadêmico em [entrega-final.md](entrega-final.md) e [README](../README.md). Os bloqueios antigos de socketpair/DNS não descrevem esta execução: loopback funcionou e o bloqueio atual de rede é de permissão de conexão externa.

Pendências concretas: concluir npm ci e a instalação Python isolada em ambiente com acesso aos índices; executar build/lint/typecheck, tools/e2e.py e inspeção desktop/celular; executar Compose em máquina com Docker. Não há aprovação de containers ou da demonstração completa.
