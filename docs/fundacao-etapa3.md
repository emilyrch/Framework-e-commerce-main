# Fundação executável — etapa 3

> Registro histórico do incremento. Resultados e limitações abaixo se referem àquela etapa; o estado atual está em [entrega-final.md](entrega-final.md). A homologação posterior aprovou 67 testes backend completos, 31 offline e 10 web; frontend e containers permanecem pendentes.

> Registro histórico da etapa 3. Em 08/11/2026, a etapa 4 implementou catálogo e componentes internos; veja [catalogo-etapa4.md](catalogo-etapa4.md) para o estado atual. As limitações de instalação/frontend/Compose persistem. O conteúdo abaixo preserva o que foi entregue/verificado na fundação, inclusive a ausência de catálogo naquele momento.

Registro em 08/11/2026. Backend/configuração/persistência da fundação implementados e verificados localmente. Frontend/Compose preparados; build e execução do servidor Next.js e containers **não verificados** devido às limitações descritas abaixo. O MVP e o fluxo de compra não estão prontos.

## Estrutura real

| Caminho | Responsabilidade / estado |
|---|---|
| `history/prototype-2026-11-08/` | Snapshot de 41 arquivos preexistentes, inventário SHA256 e HISTORY.md; sem segredos, bancos, node_modules ou caches |
| `configurations/clothing.json`, `food.json` | Manifestos ativos implementados; Básica/Premium preservados apenas para reprodução histórica |
| `shared/config.schema.json` | Schema fechado Draft-7 versão 1; dependências/exclusões e conjuntos exatos de features |
| `shared/config-vectors.json` | 24 vetores válidos/inválidos comuns a Python e TypeScript |
| `foundation/config.py` | Validação estrutural/semântica, normalização e hash SHA256 |
| `foundation/settings.py`, `application.py`, `health.py`, `errors.py`, `contracts.py` | Bootstrap, credenciais, lifespan, prontidão, erros e portas de infraestrutura |
| `services/catalog/app.py`, `orders/app.py`, `payments/app.py` | Três apps FastAPI independentes; somente saúde, prontidão e OpenAPI |
| `services/orders/repository.py`, `payments/repository.py`, `foundation/storage.py` | Repositórios de cada dono; schema e transações locais; sem operações de compra |
| `apps/store-ropa/src/lib/` e `src/instrumentation.ts` | Configuração no servidor, validação/hash e readiness agregada; startup valida antes de disponibilizar o servidor |
| `apps/store-ropa/src/app/api/health/` e `src/app/health/` | Rotas web de saúde; aliases /health e /api/health; handlers escritos, execução Next.js pendente |
| `tools/lps.py` | Geração estável de segredos, seleção estrita clothing/food e lançador local em loopback |
| `tests/foundation/`, `tests/legacy/` | Suíte ativa separada da legada, cujo teste original foi movido sem alterações |
| `requirements.txt`, `requirements-dev.txt`, lockfile npm | Dependências Python fixadas e lockfile frontend preexistente preservado |

`lps/`, `services/server.py` e os manifestos basic/premium ainda existem para reprodução legada. Não são importados pelas novas entradas ou oferecidos pelo lançador. Nenhum banco antigo foi encontrado na raiz durante a preservação; não há importação automática, exclusão ou reutilização do caminho legado `orders.db`.

## Pré-requisitos e instalação reproduzível

Python 3.11 e Node.js 24.15.0+ para os testes TypeScript com type stripping, npm, e acesso aos registros para instalação inicial. Docker/Compose são opcionais para o caminho local. Não instalar Docker nem alterar configuração global como parte deste projeto.

Na raiz, em PowerShell (sem ativação de script ou mudança de ExecutionPolicy):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm.cmd --prefix apps/store-ropa ci --no-audit --no-fund
.\.venv\Scripts\python.exe tools/lps.py init clothing
.\.venv\Scripts\python.exe tools/lps.py init food
```

Para backend/runtime somente, `requirements.txt` basta. O arquivo dev acrescenta apenas PyYAML para verificação estática do Compose; os testes usam unittest da biblioteca padrão. Não é necessário pytest/httpx. Linux/macOS: `.venv/bin/python` e `npm` nos mesmos comandos, com execução a partir da raiz.

Versões **realmente disponíveis e utilizadas** nesta validação: Python 3.11.0, FastAPI 0.141.1, Uvicorn 0.49.0, Pydantic 2.13.4, Starlette 1.3.1, jsonschema 4.25.1, Node 24.15.0 e npm 11.12.1. `requirements.txt` fixa também o fechamento transitivo instalado. Compatibilidade das dependências foi conferida por metadados e execução dos testes, não por instalação limpa.

Frontend: package.json mantém Next 15.3.1, React/React DOM ^19, TypeScript ^5, Tailwind ^4, ESLint ^9. O lockfile existente resolve React 19.1.0, TypeScript 5.8.3 e ESLint 9.25.1. Esses pacotes **não foram instalados com sucesso nem executados aqui**; não confundir versões do lock com versões validadas em build. Não houve atualização ampla de dependências.

Neste ambiente, tentativas pip/npm online falharam por bloqueio de socket/acesso (WinError 10013/EACCES). `npm ci --offline` também falhou: cache incompleto, inclusive unrs-resolver 1.7.2. Nenhuma instalação global foi feita. Os testes usaram os pacotes Python já disponíveis, inclusive uma venv local com `include-system-site-packages=true` para acesso a esse ambiente. Isso é uma alternativa local de validação, **não prova de instalação limpa reprodutível**. O procedimento normal acima precisa de acesso aos pacotes. Não desativar verificações nem contornar restrições da máquina.

## Segredos e seleção da loja

`tools/lps.py init clothing` gera `.local/roupas-demo.env`; `init food` gera `.local/alimentos-demo.env`. Cada arquivo contém seis segredos aleatórios por loja, manifesto e nome do projeto Compose. Chamadas repetidas preservam os mesmos bytes; arquivos incompatíveis são recusados, nunca sobrescritos. Não imprimir esses valores. SESSION_SECRET é reservado para a futura sessão anônima e ainda não é passado/usado pelo runtime.

No local, o lançador injeta somente credenciais das relações usadas por cada processo. O frontend recebe Web→catálogo/pedidos/pagamentos; pedidos recebe seu token Web e as duas credenciais de saída; catálogo/pagamentos recebem apenas suas duas credenciais de entrada. Não existe segredo em NEXT_PUBLIC_*, nos manifestos ou nos vetores. `.env.example` contém somente placeholders que não são aceitos pelo runtime. Não versionar `.local`, `.env` reais ou bancos; preservar esses arquivos para reiniciar a mesma loja.

## Executar localmente

Depois de instalar as dependências, uma variante por vez:

```powershell
.\.venv\Scripts\python.exe tools/lps.py run clothing --dev
```

Encerre com Ctrl+C, sem apagar dados; depois:

```powershell
.\.venv\Scripts\python.exe tools/lps.py run food --dev
```

Esse comando inicia três processos Uvicorn e o Next.js em loopback, nas portas 8001/8002/8003 e 3000. Falha de um filho encerra os outros; preflight de dependências evita subida parcial se Next estiver ausente. Na validação atual, esse comando completo não foi executado com sucesso porque o frontend não tem dependências instaladas.

Para executar somente os backends, use três terminais na raiz, com a mesma variante:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
.\.venv\Scripts\python.exe tools/lps.py service clothing --service payments
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
```

Troque clothing por food nos três comandos para alimentos. Para frontend individual: `tools/lps.py service clothing --service web --dev`, com o mesmo Python/raiz. Basic/premium não são escolhas válidas do CLI.

Build e validação web, após instalação:

```powershell
.\.venv\Scripts\python.exe tools/lps.py build-web clothing
npm.cmd --prefix apps/store-ropa run lint
npm.cmd --prefix apps/store-ropa run typecheck
npm.cmd --prefix apps/store-ropa run test:config
```

O wrapper build-web fornece manifesto/credenciais de servidor também para eventuais validações de instrumentação durante o build. Após build válido, `tools/lps.py run clothing` usa Next start. Não selecionar loja no build: manifesto e identidade usados pelo servidor vêm do ambiente de runtime. O teste de configuração TS não depende de instalar Next, apenas Node 24.15+.

## Compose

Os dois Dockerfiles e o Compose foram escritos, mas **containers não foram executados**: Docker não está disponível. Verificação de YAML é somente estática.

```powershell
docker compose --env-file .local/roupas-demo.env -p lps-roupas-demo up --build
# Depois de encerrar a loja de roupas:
docker compose --env-file .local/roupas-demo.env -p lps-roupas-demo down
docker compose --env-file .local/alimentos-demo.env -p lps-alimentos-demo up --build
```

Não usar `down -v` no reinício normal. Projetos distintos separam volumes orders-data/payments-data. Só 127.0.0.1:3000 é publicada; backends ficam na rede interna. Manifesto selecionado é montado read-only nos quatro processos. Nenhum container monta o banco do outro. Catálogo não monta dados de negócio nesta etapa, pois a carga do catálogo virá na etapa 4. As imagens contêm somente o código ativo necessário; `.dockerignore` exclui segredos, histórico, caches e bancos.

Os healthchecks do Compose medem **liveness** e não devem ser interpretados como prontidão de negócio ou substitutos da readiness agregada. A ordem depends_on não garante prontidão; as rotas degradas suportam dependências iniciando/fora do ar.

## Persistência preparada

Local: `var/roupas-demo/orders/orders.sqlite` e `var/roupas-demo/payments/payments.sqlite`; alimentos usa `var/alimentos-demo/...`. Compose: `/data/orders.sqlite` e `/data/payments.sqlite` em volumes privados distintos.

Schema 1: metadata com loja/domínio/serviço/versão, reviews, attempts e orders no dono pedidos; authorizations no dono pagamentos. UNIQUE cobre chave loja/sessão, revisão consumida, vínculo de tentativa e autorização por loja/pedido. FKs locais associam revisão/tentativa/dono do pedido. O order_id da tentativa é obtido pela relação única de orders.attempt_id, sem duplicar ponteiro em attempts. Não existe FK entre serviços.

Inicialização cria schema apenas em banco vazio e confirma atomicamente metadata/DDL; banco legado, outra loja/serviço, versão desconhecida ou DDL divergente são recusados sem migração/limpeza. PRAGMA foreign_keys ON, busy_timeout 500 ms, synchronous FULL; transações curtas e conexões fechadas por operação. Readiness testa schema/identidade e obtenção de transação de escrita, revertida sem mudanças. Nenhuma conexão/transação permanece aberta durante HTTP.

As tabelas contêm campos/constraints para estados futuros, mas não há métodos de criar pedido, autorizar pagamento, consumir revisão, adquirir lease ou executar recuperação. Fixtures SQL dos testes não são endpoints de negócio. Mudança de manifesto com trabalho intermediário de hash anterior é recusada; processos atuais não geram esse trabalho.

## Saúde e prontidão implementadas

Backends: GET `/health/live` público; GET `/health/ready` com Bearer, X-Store-Id e X-Config-Hash. Sem credencial: 401; loja/hash diferentes: 409. OpenAPI expõe somente essas duas operações. Não há /products, /orders ou /payments novos.

Frontend: `/health/live`, `/health/ready` e aliases `/api/health/live`, `/api/health/ready`. Liveness só processo; readiness pública sanitizada, sem cabeçalhos privados do navegador encaminhados. Código dos handlers está preparado; a lógica agregadora foi executada diretamente pelo Node nos testes, mas **os handlers em um servidor Next.js não foram executados**.

Todos os resultados de readiness usam `scope: foundation`. Verificações reais:

- Catálogo: manifesto/configuração e schema do manifesto. **Não verifica catálogo ou seleção de produto ainda.**
- Pagamentos: configuração e schema/acesso do banco. **Não autoriza pagamentos.**
- Pedidos: configuração, schema/acesso do banco e identidade/prontidão de catálogo/pagamentos. **Não verifica worker, sessão ou compras.**
- Web: configuração no servidor e identidade/prontidão dos três serviços. **Não verifica fluxo de cliente.**

Sem `recovery_worker: ok`, sem ciclo de dependências. Chamadas de prontidão usam timeout de 1 s, sem repetição e em paralelo por destino; pedidos não chama frontend. Não há proxy de ambiente/redirecionamento de credenciais no cliente Python; o cliente HTTP nativo Node da prontidão tem deadline total e limite de resposta de 16 KiB, sem seguir redirecionamentos. Dependência fora → 503 readiness, liveness continua 200. HTTP de erro não contém caminho, segredo ou stack trace.

Manifesto inválido falha antes de servir no lifespan FastAPI; Next tem validação no register da instrumentação, cuja execução real ainda depende da instalação web. Configuração é aplicada no bootstrap, não por parâmetro do navegador. Componentes de domínio e dados de catálogo ainda são os especificados na etapa 2.

## Evidências desta etapa

| Verificação | Resultado / limite |
|---|---|
| Suíte ativa unittest | 11 testes aprovados; inclui subcenários dos dois domínios |
| Paridade Python/TS | 24 vetores: Unicode, ordem das features, configs válidas/inválidas, janelas e tipos |
| Processos | Três PIDs Uvicorn por variante; roupas e alimentos sequenciais, diretórios isolados |
| HTTP/identidade | live/ready, 401 sem credencial, 409 divergente, 503 com dependência fora e live 200 |
| Lógica web de prontidão | Executada pelo Node contra os processos reais; pronto e degradado; não equivale a executar Next.js |
| SQLite | Reinicialização conserva fixtures, constraints e FKs; outra loja/serviço/schema/legado rejeitados; restart dos processos |
| Segredos | Geração por loja, estabilidade e injeção limitada testadas, sem exposição de valores |
| Python | Compilação das novas entradas e metadados de dependências conferidos |
| Build/lint/typecheck Next.js | Tentados, não concluídos: next/eslint/tsc ausentes após falha na instalação; não aprovados |
| Compose | YAML/topologia conferidos; Docker indisponível, build/containers não executados |

Comandos de testes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/foundation -v
node --experimental-strip-types apps/store-ropa/scripts/check-config.ts
# Histórico, separado; não usado para afirmar cobertura do novo sistema:
python -m unittest discover -s tests/legacy -v
```

Os novos testes de processo usam portas temporárias e bancos temporários; não alteram bancos da demonstração. Nenhum resultado da suíte histórica foi reutilizado como evidência da fundação.

## Pendências reais e próximo incremento

Instalar frontend a partir do lockfile quando houver acesso aos pacotes; então executar build/lint/typecheck e smoke das rotas Next.js. Validar imagens e Compose em ambiente com Docker, sem instalá-lo automaticamente aqui. Instalação Python limpa a partir dos pins também precisa de validação com acesso ao registro. Esses itens permanecem **não verificados**, não erros mascarados como aprovação.

Etapa 4 recomendada: dados reais de demonstração por loja, schemas de produto/metadados, carga validada e revisão do catálogo, listagem/detalhe/seleção por combination_id, validadores de roupas/alimentos e política de entrega/totais testáveis. Não avançar para carrinho/checkout/criação/autorização/worker como parte desta fundação.

Referências técnicas consultadas para a implementação: [execução Uvicorn/FastAPI](https://fastapi.tiangolo.com/deployment/manually/), [instrumentação do Next.js 15](https://nextjs.org/docs/15/app/api-reference/file-conventions/instrumentation) e [ESLint no Next.js 15](https://nextjs.org/docs/15/app/api-reference/config/eslint). As referências não substituem os resultados locais e não tornam o frontend verificado.
