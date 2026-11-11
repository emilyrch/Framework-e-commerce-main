# Estabilização e entrega — 10/11/2026

Atualização posterior: [estabilização da compra e entrega](finalizacao-compra-e-entrega.md) prevalece sobre o estado registrado abaixo. Frontend tem dependências, lint/typecheck passaram; build e homologação continuam impedidos. Há quatro microsserviços e seletor visual. Resultados antigos são históricos.

**Implementação entregue; homologação incompleta por bloqueios do ambiente.** Não declarar o MVP pronto ou a demonstração aprovada. Este documento é a referência atual de execução e evidências; os registros por etapa descrevem o estado de cada incremento.

## O que está no código

LPS com manifestos estritos roupas/alimentos, identidade/hash compartilhados, três aplicações FastAPI, componentes de domínio, catálogos fictícios, agenda de alimentos, revisão persistida, admissão de pedido, Pix simulado durável, idempotência e recuperação limitada. Frontend Next.js compartilhado, sessão anônima assinada, intermediário de APIs, catálogo, carrinho por loja, entrega/revisão e consulta do pedido. Consulta mostra os dados preservados de entrega, janela e informações de roupa/alimento; não depende do catálogo atual.

Neste fechamento foi acrescentada validação defensiva das respostas de sucesso no intermediário: estrutura mínima, domínio, limites monetários, soma de linhas/totais e confirmação com ID/valor de pagamento coerentes. Resposta incompleta não vira confirmação. Informações alimentares foram extraídas para componente visual reutilizado no produto e no snapshot do pedido.

Não foram incluídos estoque, conta/login, painel administrativo, frete calculado, cartão, pagamento real, IA ou implantação pública.

## Evidências executadas

| Verificação | Resultado real |
|---|---|
| Backend offline | **31 testes aprovados**, com SQLite real, modelos/componentes, concorrência por threads e adaptadores imediatos explicitamente limitados |
| Camada web Node | **10 testes aprovados**, incluindo rejeição de sucesso malformado/inconsistência monetária |
| Configuração Python/TypeScript | **24 vetores aprovados** pelo verificador TypeScript; suíte Python correspondente aprovada |
| Compatibilidade de respostas Python → TypeScript | Incluída nos 31 testes: **21 DTOs reais** das duas variantes aceitos pela fronteira web, sem HTTP |
| Sintaxe Python | compileall sem erros |
| Versões Python do projeto | Pacotes instalados correspondem às versões fixadas em requirements.txt |
| Inventários históricos | 41 arquivos do protótipo e 68 do pré-5B com hashes preservados |
| Acesso ao registro npm | npm ci pelo lockfile falhou com “Exit handler never called”; npm ping confirmou EACCES |
| Backend HTTP, asyncio e worker | **67 testes aprovados em 78,608 s**, com processos FastAPI, HTTP, concorrência e reinício reais |
| Frontend build/lint/typecheck | Bloqueados: Next.js/ESLint/TypeScript ausentes na instalação incompleta |
| HTTP Next.js → backend + reinício | Teste preparado, não executado por ausência do build |
| Inspeção visual desktop/celular | Não executada: frontend ainda não inicia |
| Instalação Python limpa | Venv criado sem pacotes globais; instalação falhou em annotated-doc==0.0.5; HTTPS PyPI confirmou WinError 10013 |
| pip check do ambiente atual | Conflito externo: streamlit-vis-network exige setuptools >=75.8.0; instalado 65.5.0. O venv herda pacotes do sistema. Nenhum pacote global foi alterado |
| Docker Compose real | Não executado: Docker não instalado; nenhum container foi validado |

A suíte completa agora cobre backend HTTP/asyncio/worker; os testes offline/DTO isoladamente não seriam suficientes. Next/React, navegador e containers continuam pendentes. Resultados dos incrementos anteriores permanecem registros históricos.

## Um comando de validação

PowerShell, na raiz:

```powershell
.\.venv\Scripts\python.exe tools/validate.py
```

Gera `.local/validation-latest.json`, ignorado pelo versionamento, com status passed/failed/blocked por verificação. Código 0 indica aprovação de todas as verificações; 1 indica falha; 2 indica validação incompleta/bloqueada. O script não instala pacotes nem modifica bancos/segredos da demonstração. O build, quando disponível, usa credenciais efêmeras apenas no ambiente do subprocesso. Inspeção visual, instalação limpa e Compose exigem execução/evidência específica e permanecem bloqueados nesse relatório automático.

Comandos individuais:

```powershell
.\.venv\Scripts\python.exe tools/test_backend.py --offline
.\.venv\Scripts\python.exe tools/test_backend.py
node --experimental-strip-types --test apps/store-ropa/scripts/test-web.ts
node --experimental-strip-types apps/store-ropa/scripts/check-config.ts
.\.venv\Scripts\python.exe tools/e2e.py
```

`tools/e2e.py` exige build de produção e loopback. Inicia Next.js e os três serviços em processos próprios, com portas/bancos/tokens temporários, percorre ambas as variantes sequencialmente, descarta deliberadamente a primeira resposta de compra, recupera pela chave, testa sessão distinta, reinicia pedidos/pagamentos e confere um pedido/uma autorização nos bancos. O descarte não simula todos os tipos de timeout. Usa relógio controlado pela fábrica de teste; não altera relógio/configuração do runtime normal. Isso é E2E HTTP, ainda sem renderização ou automação de navegador.

## Preparação quando o acesso aos registros estiver disponível

Nesta execução, npm ci pelo lockfile terminou com “Exit handler never called”. npm ping retornou EACCES. DNS do PyPI resolveu, mas HTTPS falhou com WinError 10013. O venv isolado `.local/venv-homologacao-20261110` foi criado com include-system-site-packages=false; a instalação não foi concluída. Nenhum pacote global foi alterado.

O loopback agora funcionou. A primeira suíte completa revelou configuração desatualizada em tests/foundation/test_processes.py: faltava SESSION_SECRET para a prontidão web. O teste passou a fornecer segredo efêmero exclusivamente ao subprocesso web. Na repetição, os 67 testes passaram. O carrinho foi corrigido para limpar somente após confirmação, preservando alterações durante a chamada; os 10 testes Node passaram.

Build, lint e typecheck foram chamados pelos scripts npm reais e falharam porque next/eslint/tsc não estão instalados. O lançador recusou iniciar a aplicação; tools/e2e.py retornou bloqueio por falta de Next/build. Não houve inspeção no navegador. Docker não encontrado no PATH nem no caminho padrão; Compose não executado. Git indisponível e sem `.git`; nenhum histórico foi recriado. Inventários históricos de 41 e 68 arquivos conferidos por SHA-256 sem divergência.

Validação consolidada repetida: nenhum check failed; release_ready=false pelas verificações bloqueadas. “No installation attempted” refere-se ao verificador; a tentativa npm ocorreu separadamente. [Registro detalhado desta execução](homologacao-2026-11-10.md).

Não repetir estes comandos enquanto o mesmo bloqueio persistir. Em ambiente funcional, instalar pelo lockfile e verificar Python em venv isolado, sem pacotes globais:

```powershell
npm.cmd --prefix apps/store-ropa ci --no-audit --no-fund
python -m venv .local/venv-verificacao
.\.local\venv-verificacao\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.local\venv-verificacao\Scripts\python.exe -m pip check
.\.local\venv-verificacao\Scripts\python.exe tools/validate.py
```

Verifique os resultados; existir código de teste não significa aprovação. Build/lint/typecheck ou testes podem revelar correções adicionais. Não modificar versões apenas para ocultar falhas, usar stubs ou desabilitar testes.

## Roteiro de demonstração acadêmica

Pré-condição: build, testes HTTP/worker, E2E e revisão visual efetivamente aprovados. Sem essa pré-condição, apresentar o código/modelagem e a tabela de limitações, sem afirmar demonstração pronta.

1. Mostrar modelo de features e manifestos; domínio XOR, núcleo obrigatório e escolha de componentes no ponto de composição.
2. Iniciar roupas: `python tools/lps.py run clothing --dev`; abrir **http://127.0.0.1:3000**. Mostrar processos separados e prontidão.
3. Buscar/filtrar, abrir produto, selecionar combinação habilitada e adicionar duas combinações distintas. Mostrar que combinação desabilitada não é selecionável e não há promessa de estoque.
4. Editar quantidades, preencher endereço fictício e revisar. Mostrar preços/totais do servidor e Pix simulado sem dados bancários.
5. Confirmar, consultar pedido e reenviar a mesma tentativa quando apropriado. Demonstrar ID preservado e uma autorização; não criar nova chave para uma resposta perdida.
6. Encerrar/reiniciar a mesma loja, conservando `.local`, volumes/bancos e cookie. Consultar o pedido preservado.
7. Encerrar os processos e iniciar alimentos: `python tools/lps.py run food --dev`. Conferir sacola/dados separados.
8. Mostrar ingredientes, alergênicos conhecidos, ausência declarada e informação desconhecida; nutrição por porção e caráter fictício.
9. Comprar com janela futura obrigatória de São Paulo. Consultar snapshot da janela, endereço e informações alimentares preservadas.
10. Mostrar evidências dos cenários negativos: sessão distinta sem acesso, dados inválidos, preço alterado, indisponibilidade, reenvios e reinício. Distinguir teste executado de cenário somente preparado.

Para verificar Compose quando Docker estiver disponível, usar projetos isolados, uma variante por vez, com porta 3000 livre:

```powershell
docker compose --env-file .local/roupas-demo.env -p lps-verificacao-roupas up --build -d
docker compose --env-file .local/roupas-demo.env -p lps-verificacao-roupas ps
Invoke-RestMethod http://127.0.0.1:3000/health/ready
# Exercitar a interface e registrar os resultados antes de encerrar:
docker compose --env-file .local/roupas-demo.env -p lps-verificacao-roupas down
# Repetir com alimentos-demo.env e projeto lps-verificacao-alimentos.
```

Não usar down -v para reinício normal. Subir containers ou analisar YAML, isoladamente, não aprova a compra. Preserve os segredos de cada loja.

## Entrega acadêmica e origem

| Origem | Evidência de implementação/modelagem |
|---|---|
| Professor: LPS modelada e implementada | modelo-lps.md, configurações reais, validadores e derivação por manifesto |
| Professor: microsserviços | catálogo/pedidos/pagamentos em processos próprios, contratos HTTP e dados privados |
| Professor: componentes de software | contratos/implementações de seleção, entrega, totais e pagamento; componentes visuais distintos dos serviços |
| Projeto: duas variantes e tecnologias | manifesto roupas/alimentos, frontend comum, FastAPI/SQLite/Compose; não são exigências extras do professor |

Diagramas existentes em modelo-lps.md, arquitetura-atual.md e recuperacao.md. Contratos em contratos-api.md; matriz de origem/aceitação em validacao.md. Não foram inventados rubrica, prazo, número obrigatório de serviços ou implantação pública.

**Pendências reais para aprovação:** acesso aos registros/dependências frontend, instalação Python limpa, E2E Next.js, revisão visual desktop/celular e containers. O trabalho de estabilização possível nesta sessão foi concluído; aprovação final permanece condicionada às execuções faltantes.
