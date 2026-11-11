# LPS de e-commerce — Essencial & Despensa

Repositório do projeto: [emilyrch/LPS-Ecommerce](https://github.com/emilyrch/LPS-Ecommerce). O código pode ser acompanhado pelo GitHub Desktop. Para envio pelo PowerShell, há também `& .\tools\publicar-github.ps1`: verifica arquivos, cria o commit e envia sem force push; requer Git e autenticação no GitHub.

Evidência posterior: [capturas reais de roupas e compra confirmada](docs/capturas-roupas-2026-11-10.md). A execução manual do navegador foi bem-sucedida para roupas; demais bloqueios e verificações anteriores mantêm seu alcance.

Estado atual: [estabilização da compra e entrega](docs/finalizacao-compra-e-entrega.md). Acompanhamento automático, sessão compartilhada, seletor visual em `/configurador` e painel de microsserviços implementados. 43 testes offline, 16 web e 24 vetores aprovados; lint/typecheck aprovados. Compra completa no navegador ainda não homologada por bloqueios de ambiente.

Atualização de 10/11/2026: roupas agora possui dez peças com imagens locais e recomendações por preferências/histórico. Há quatro microsserviços (incluindo recomendações em 8004) e cinco processos. Veja [implementação, execução e validação atuais](docs/recomendacoes-e-imagens.md). Os resultados de homologação anteriores abaixo são históricos; não certificam este incremento.

Projeto acadêmico de Linha de Produto de Software: **roupas** com tamanho/cor e **alimentos** com informações alimentares/agendamento. LPS, microsserviços e componentes são exigências do professor; tecnologias e recorte do MVP são escolhas do projeto. Sem agentes de IA.

**Implementação entregue, homologação incompleta.** Duas lojas do mesmo código, três microsserviços e frontend compartilhado. Há catálogo, carrinho, sessão, revisão, pedido, pagamento simulado durável e recuperação. Não há pagamento real.

**Estado atual:** 67 testes backend completos, 31 offline, 10 testes web e 24 vetores de configuração aprovados. HTTP/asyncio/worker e loopback funcionaram. Acesso aos registros de pacotes bloqueado pelo sistema operacional; Next.js/ESLint/TypeScript ausentes. Frontend, E2E Next.js, revisão visual e instalação Python limpa pendentes. Docker e Git não encontrados; esta pasta não contém `.git`. [Evidências e roteiro final](docs/entrega-final.md).

Validação consolidada: `.\.venv\Scripts\python.exe tools/validate.py`. Relatório em `.local/validation-latest.json`; validação bloqueada retorna código 2, sem indicar aprovação.

## Preparar — PowerShell, na raiz

Python 3.11, Node 24.15+ e npm. Instalação inicial requer acesso aos registros:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm.cmd --prefix apps/store-ropa ci --no-audit --no-fund
.\.venv\Scripts\python.exe tools/lps.py init clothing
.\.venv\Scripts\python.exe tools/lps.py init food
```

Segredos estáveis por loja são gerados em `.local`, ignorados pelo Git; nunca sobrescritos no reinício. Não publicar esses arquivos. Os manifestos ativos são `configurations/clothing.json` e `food.json`; o lançador não aceita Básica/Premium.

## Executar uma variante por vez

```powershell
.\.venv\Scripts\python.exe tools/lps.py run clothing --dev
# Encerre com Ctrl+C antes de executar a outra variante:
.\.venv\Scripts\python.exe tools/lps.py run food --dev
```

Frontend em **http://127.0.0.1:3000** quando suas dependências estiverem disponíveis (Origin validado; localhost exige WEB_ORIGIN explícito); serviços locais em loopback 8001/8002/8003/8004. Para o backend sem frontend, em quatro terminais:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
.\.venv\Scripts\python.exe tools/lps.py service clothing --service payments
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
.\.venv\Scripts\python.exe tools/lps.py service clothing --service recommendations
```

Troque clothing por food nos quatro terminais para alimentos. Pedidos/pagamentos têm persistência privada em `var/<store_id>/<service>/<service>.sqlite`; pagamentos autoriza somente operações simuladas vinculadas ao pedido. Reiniciar conserva dados/segredos; bancos legados/de outra loja são recusados.

O catálogo pode ser iniciado sozinho pelo primeiro comando. APIs: GET `/internal/v1/products`, GET `/internal/v1/products/{id}` (credencial web) e POST `/internal/v1/selections/resolve` (credencial orders). Ambas exigem identidade/hash; tokens não devem ir ao navegador. [Chamadas PowerShell completas e exemplos para cada loja](docs/catalogo-etapa4.md).

Pedidos agora oferece GET `/internal/v1/delivery-slots` e POST `/internal/v1/reviews` com credencial web→pedidos. O POST interno exige X-Session-Owner; o intermediário Next.js agora o deriva do cookie assinado, sem confiar nos cabeçalhos do navegador. A admissão consome a revisão uma única vez; não há GET de revisão. [Chamadas PowerShell, persistência e limites de confiança](docs/revisao-etapa5a.md).

Dados ativos em `demo-data/clothing/products.json` e `demo-data/food/products.json`, carregados e congelados no startup. Roupas usa dez imagens PNG locais geradas para o projeto, com fallback SVG autoral; alimentos mantém ilustrações locais. Revisão comercial ignora formatação/ordem de produtos e muda com preços, combinações ou informações alimentares.

Compose preparado, **ainda não executado** neste ambiente:

```powershell
docker compose --env-file .local/roupas-demo.env -p lps-roupas-demo up --build
# Para alimentos, após encerrar a primeira loja:
docker compose --env-file .local/alimentos-demo.env -p lps-alimentos-demo up --build
```

Só a porta do frontend é publicada. Não usar `down -v` no reinício normal. Instruções completas, armazenamento, Dockerfiles e alcance de saúde em [fundação da etapa 3](docs/fundacao-etapa3.md).

## Verificações

```powershell
node --experimental-strip-types --test apps/store-ropa/scripts/test-web.ts
```

```powershell
.\.venv\Scripts\python.exe tools/test_backend.py --offline
# Suíte completa requer loopback funcional:
.\.venv\Scripts\python.exe tools/test_backend.py
node --experimental-strip-types apps/store-ropa/scripts/check-config.ts
.\.venv\Scripts\python.exe tools/lps.py build-web clothing
npm.cmd --prefix apps/store-ropa run lint
npm.cmd --prefix apps/store-ropa run typecheck
```

Resultado atual: **67 testes backend completos + 31 offline + 10 testes web + 24 vetores aprovados**. A suíte completa inclui processos FastAPI reais, concorrência HTTP e recuperação após reinício, com bancos temporários. Testes web usam transporte controlado e não validam Next/React no navegador. Build/lint/typecheck foram tentados e bloqueados por executáveis ausentes. E2E Next.js, Python limpo e Compose pendentes. [Evidências e limitações](docs/entrega-final.md).

Histórico intacto em [history/prototype-2026-11-08](history/prototype-2026-11-08/HISTORY.md), com inventário. Teste legado separado em `tests/legacy`. Arquitetura, contratos, critérios e próximos passos no [índice de docs](docs/README.md).
