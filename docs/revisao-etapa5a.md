# Revisão persistida e janelas de entrega — etapa 5A

> Registro histórico do incremento. Resultados e limitações abaixo se referem àquela etapa; o estado atual está em [entrega-final.md](entrega-final.md). A homologação posterior aprovou 67 testes backend completos, 31 offline e 10 web; frontend e containers permanecem pendentes.

> Atualização 10/11/2026 — Registro histórico da etapa 5A. Desde 5B, pedidos consome revisões, chama pagamentos e inicia recuperação; readiness depende novamente de pagamentos. As afirmações de ausência dessas operações abaixo descrevem apenas 5A. Ver [estado atual](backend-etapa5b.md).

Estado: implementado no backend em 08/11/2026. Catálogo e pedidos se comunicam por HTTP. **Não há criação de pedidos, tentativas, autorização, consumo de revisão ou recuperação.** O frontend continua legado e sem integração. A sessão de navegador/Next.js não foi implementada nem declarada protegida.

## Operações implementadas

| Backend de pedidos agora | Papel e cabeçalhos | Futuro intermediário Next.js |
|---|---|---|
| GET /internal/v1/delivery-slots | web→pedidos + loja/hash; não exige dono | GET /api/v1/delivery-slots |
| POST /internal/v1/reviews | web→pedidos + loja/hash + X-Session-Owner | POST /api/v1/reviews |

As rotas /api/v1 acima continuam **futuras**. Não foi criado endpoint de consulta de revisão: não é necessário para esta etapa. A resposta 201 fornece o review_id para a futura confirmação; a futura admissão fará a leitura privada no repositório e verificará loja/dono/configuração/expiração.

GET janelas reutiliza a política do domínio: alimentos retorna somente janelas habilitadas e futuras dentro do horizonte, timezone America/Sao_Paulo e server_now em UTC. O mesmo instante capturado alimenta server_now e a política, evitando divergência no limite de início. Roupas retorna 409 FEATURE_NOT_AVAILABLE. Sem capacidade, reserva, banco de agenda ou chamada de pagamento.

POST revisão valida corpo fechado, domínio, seleção/endereço/método, resolve todos os itens pela API do catálogo, valida a entrega, calcula os totais e grava o snapshot antes de retornar 201. Não aceita preço, total ou metadados do cliente. Roupas exige combination_id válido/habilitado; alimentos proíbe combination_id inclusive null. Endereço é comum; alimentos exige slot_id não nulo e roupas proíbe esse campo inclusive null. Entre 1–50 seleções únicas, quantidade estritamente int 1–100, dinheiro em centavos, frete/desconto zero e método simulado somente como metadado da revisão.

## Fronteira de confiança e erros

Authorization Bearer deve ser a credencial **WEB_ORDERS_TOKEN**. Nenhuma credencial de catálogo/pagamento concede acesso a pedidos. Ausente/incorreta/de outro serviço: 401 INTERNAL_UNAUTHORIZED. Loja/hash divergentes: 409 CONFIG_MISMATCH. O corpo store_id também precisa corresponder à configuração ativa.

Na criação, X-Session-Owner precisa ser exatamente um cabeçalho com 64 caracteres hexadecimais minúsculos, formato do hash previsto para o intermediário. Ausente/inválido/repetido: 401 SESSION_REQUIRED. Sua validação ocorre depois da credencial interna. Dono no corpo é campo extra e resulta em 422. Este valor é uma **asserção confiada ao chamador interno**, não uma prova de identidade do usuário final. Conhecer/enviar um hash sem credencial não permite gravar; quem tem a credencial web pode representar um dono. Até implementar e validar o intermediário, não há cookie, sessão anônima de navegador, proteção Origin ou garantia de identidade do cliente final.

Corpos limitados a 64 KiB e JSON. Envelope comum com request_id/fields sanitizados, sem valores privados, paths internos, tokens ou traceback. Respostas usam Cache-Control: no-store. Exemplos:

- 400 MALFORMED_JSON; 413 BODY_TOO_LARGE; 415 UNSUPPORTED_MEDIA_TYPE.
- 422 INPUT_INVALID, SELECTION_INVALID, DUPLICATE_LINE, DELIVERY_SLOT_INVALID ou TOTAL_OUT_OF_RANGE.
- 409 CONFIG_MISMATCH ou DELIVERY_SLOT_EXPIRED (inclui início exatamente igual a now).
- 503 DEPENDENCY_UNAVAILABLE, CATALOG_RESPONSE_INVALID ou ORDER_STORAGE_UNAVAILABLE.

O OpenAPI de pedidos mostra somente saúde, janelas e criação de revisão; não contém dados reais de sessão/endereço ou operações futuras.

## Cliente tipado de catálogo

`services/orders/catalog_client.py` implementa CatalogResolver com transporte HTTP da biblioteca padrão. Pedidos **não carrega JSON comercial** nem abre banco do catálogo. Envia apenas store_id/items, token orders→catálogo e X-Store-Id/X-Config-Hash: endereço e X-Session-Owner não saem de pedidos.

Cada resolução tem orçamento de 1,5 s por tentativa, no máximo duas tentativas; espera 100 ms entre elas. Repetir somente falha de transporte/timeout ou HTTP 500/502/503/504. Não repetir validação 4xx, divergência ou resposta inválida. A operação de resolução é somente leitura, portanto pode ser repetida com o mesmo conteúdo. Não seguir redirecionamentos nem usar proxies de ambiente que encaminhem credenciais.

Cliente limita resposta a 1 MiB, valida Content-Type, cabeçalhos de identidade/hash, corpo/modelos estritos, revisão sha256 e correspondência exata entre seleções e resposta (domínio, produto, combinação, quantidade, completude/unicidade). Aceita resposta ordenada diferentemente, mas recompõe a ordem normalizada da solicitação. Nunca aceita preço fora dos limites ou resposta parcial. Erros de seleção conhecidos são propagados com campos permitidos, sem mensagem/conteúdo remoto arbitrário. Resposta sem identidade é inválida (503); identidade explicitamente divergente é conflito (409).

O orçamento do chamador usa asyncio.wait_for; trabalho bloqueante roda em thread, sem transações SQLite. Cancelar a espera não garante cancelamento instantâneo de DNS/socket do sistema: o transporte também tem timeout e deadline de leitura e fecha a resposta. Resolução tardia não grava nada; somente a sequência que recebeu resultado válido pode prosseguir para persistência. Não se adicionou dependência Python para esse cliente.

## Componentes reutilizados e estrutura

| Arquivo/componente | Uso nesta etapa |
|---|---|
| domain.models / ClothingSelection / FoodSelection | Tipos estritos e seleções |
| domain.delivery / Address / ScheduledDelivery / UnscheduledDelivery | Endereço, janela e snapshot; componentes da etapa 4 preservados |
| domain.pricing / IntegerTotalsCalculator | Linhas e totais sem I/O |
| domain.composition | Seleção da política por domínio e captura de relógio único por operação |
| services/orders/models.py | DTOs fechados por variante, resposta de revisão/janelas e resposta tipada do catálogo |
| services/orders/catalog_client.py | Cliente/porta de resolução e transporte com limites |
| services/orders/service.py | Orquestração da revisão, sem regras nos handlers |
| services/orders/repository.py | INSERT transacional de revisão, sem atualização/consumo |
| services/orders/routes.py | Autorização/dono de sessão e duas rotas implementadas |
| foundation/application.py / auth.py / errors.py / health.py | Bootstrap, limite de corpo, erros e prontidão comuns |

`create_app(..., clock=...)` permite relógio injetável. Somente a fábrica de teste `tests/reviews/server.py` lê TEST_CLOCK; o runtime normal não expõe um relógio controlável por cabeçalho/corpo/ambiente. O instante da revisão é capturado depois da resolução HTTP e usado para validar entrega e calcular a expiração.

## Persistência e expiração

Reutiliza `reviews` no schema **1**, sem alterar DDL, migração, limpeza ou recriação de bancos existentes. Caminho local: `var/<store_id>/orders/orders.sqlite`; volume privado de pedidos no Compose. Permanecem a identidade/schema compatíveis e a recusa a banco legado/de outra loja.

Grava review_id UUIDv4 aleatório, loja, session_owner, config_hash, entrada normalizada, snapshot JSON completo, catalog_revision, created_at e expires_at. Ordena seleções por product_id/combination_id na entrada persistida e no resultado, preservando quantidade/endereço e demais campos validados. O dono não entra na entrada pública nem na resposta; fica em coluna privada.

Snapshot contém nome, tipo, quantidade, preço unitário e linha; combinação (id/tamanho/cor) ou informações alimentares completas; endereço e janela quando aplicável; método e totais. Unknown de alergênicos preserva os dois null. Modelos são imutáveis, gravação é INSERT sem UPSERT/UPDATE e não há endpoint para modificar/consumir. Mudanças de catálogo/configuração não reescrevem snapshots antigos.

BEGIN IMMEDIATE, conferência do schema/identidade, INSERT e commit são locais/curtos; conexão fecha por operação. Todo HTTP acontece **antes** da transação. Bloqueio/erro de gravação/commit produz 503, nunca confirmação fictícia. Não há INSERT em orders/attempts ou acesso a pagamentos. Os testes de falha de commit verificam rollback; uma falha real com resultado de commit incerto não autoriza afirmar que nunca houve gravação, apenas que não houve sucesso confirmado ao chamador.

expires_at = created_at UTC + exatamente 10 minutos. Não há espera por expiração, consumo ou limpeza automática. Revisão não reserva estoque, não trava preço, não reserva janela e não representa pedido confirmado. Janela pode começar antes do fim dos dez minutos: a futura admissão deverá revalidá-la e conferir preços/configuração/expiração. Reenviar POST agora pode criar outra revisão independente; não há idempotência de revisão nem cobrança. Perda da resposta pode deixar uma revisão sem referência no cliente, sem efeito financeiro/pedido.

## Prontidão e dependências

Pedidos verifica schema/acesso do banco, review_repository, instância review_service e identidade/prontidão do catálogo, mantendo scope foundation. **Não verifica nem chama pagamentos** nesta etapa: readiness de pedidos não depende mais dele. O token orders→pagamentos deixou de ser injetado em pedidos pelo lançador/Compose; segredos existentes são preservados para o incremento 5B. Compose orders depende de catalog, não de payments. O serviço pagamentos continua apenas com sua fundação; não há autorização.

A prontidão agregada preexistente do frontend ainda verifica infraestrutura dos três serviços, mas não valida sessão web, UI ou pagamento de negócio. Nenhum indicador recovery_worker/session_web/payment_authorization foi marcado pronto. Liveness de pedidos não depende do catálogo.

## Executar e chamar — PowerShell

Usar Python/ambiente da fundação, na raiz. Sem frontend ou serviço de pagamentos para estas operações. Em dois terminais:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
```

Em outro terminal, preparar chamada interna (dono **fictício**, simulando o intermediário; não usar como sessão real):

```powershell
$variant = 'clothing'
$store = 'roupas-demo'
$secrets = Get-Content ".local/$store.env" -Raw | ConvertFrom-StringData
$hash = & .\.venv\Scripts\python.exe -c "from foundation.config import load; print(load('configurations/$variant.json').config_hash)"
$headers = @{ Authorization = "Bearer $($secrets.WEB_ORDERS_TOKEN)"; 'X-Store-Id' = $store; 'X-Config-Hash' = $hash; 'X-Session-Owner' = ('a' * 64) }
$address = @{ recipient = 'Cliente Fictício'; street = 'Rua Exemplo'; number = '10'; district = 'Centro'; city = 'São Paulo'; state = 'SP'; postal_code = '01001000' }
$body = @{ store_id = $store; items = @(@{ product_id = 'camiseta'; combination_id = 'camiseta-m-preta'; quantity = 1 }, @{ product_id = 'camiseta'; combination_id = 'camiseta-g-azul'; quantity = 2 }); delivery = @{ address = $address }; payment_method = 'simulated_pix' } | ConvertTo-Json -Depth 8
$review = Invoke-RestMethod http://127.0.0.1:8002/internal/v1/reviews -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
$review
```

Total esperado de roupas: 26970 centavos. GET delivery-slots dessa loja retorna 409 FEATURE_NOT_AVAILABLE.

Para alimentos, encerrar ambos os processos e iniciar os mesmos comandos com **food**. Reexecutar a preparação dos cabeçalhos com `$variant = 'food'` e `$store = 'alimentos-demo'`, lendo o arquivo de segredos correspondente; não reutilizar o token de roupas. Reutilizar apenas o endereço fictício:

```powershell
$variant = 'food'
$store = 'alimentos-demo'
$secrets = Get-Content ".local/$store.env" -Raw | ConvertFrom-StringData
$hash = & .\.venv\Scripts\python.exe -c "from foundation.config import load; print(load('configurations/$variant.json').config_hash)"
$headers = @{ Authorization = "Bearer $($secrets.WEB_ORDERS_TOKEN)"; 'X-Store-Id' = $store; 'X-Config-Hash' = $hash; 'X-Session-Owner' = ('a' * 64) }
$address = @{ recipient = 'Cliente Fictício'; street = 'Rua Exemplo'; number = '10'; district = 'Centro'; city = 'São Paulo'; state = 'SP'; postal_code = '01001000' }
$slots = Invoke-RestMethod http://127.0.0.1:8002/internal/v1/delivery-slots -Headers $headers
if (-not $slots.items) { throw 'Nenhuma janela disponível' }
$body = @{ store_id = $store; items = @(@{ product_id = 'granola'; quantity = 1 }, @{ product_id = 'suco'; quantity = 2 }); delivery = @{ address = $address; slot_id = $slots.items[0].id }; payment_method = 'simulated_pix' } | ConvertTo-Json -Depth 8
$review = Invoke-RestMethod http://127.0.0.1:8002/internal/v1/reviews -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
$review
```

Total esperado de alimentos: 4970 centavos; granola preserva alergênicos unknown/null. O exemplo busca janela atual do servidor, sem data fixa que envelheça. Segredos não devem ser impressos, copiados ao navegador ou versionados.

## Validação realizada

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/reviews -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Resultado: **16 testes novos e 48 testes ativos no total**, com regressão das 32 verificações das etapas anteriores. Suíte legada separada. Inclui:

- Revisões de roupas com combinações distintas e alimentos com janela; valores, linhas, metadados/snapshots e UUIDv4.
- Tipos/campos incompatíveis, null proibido, seleção duplicada, endereço, sessão interna e identidade/configuração inválidos.
- Janelas ausentes/passadas/desabilitadas/desconhecidas, timezone e instante coerente com relógio controlado.
- Cliente tipado, resposta parcial/malformada/divergente, retry limitado e timeout com teste curto; HTTP negativo sem redirecionar credenciais.
- HTTP real entre processos catálogo/pedidos para ambas as variantes, com relógio de teste e bancos/portas/segredos temporários.
- Falha de commit e bloqueio SQLite sem sucesso falso; possibilidade de outro writer durante a resolução prova ausência de transação longa no HTTP.
- Persistência após reinicialização de repositório e processo; owner/config_hash vinculados; orders/attempts vazios e sem pagamento.
- OpenAPI apenas das operações implementadas, resposta privada no-store e ausência de consulta de revisão por conveniência.

Nenhum banco/segredo/dataset da demonstração foi alterado pelos testes; só fixtures temporárias e dados fictícios. Não houve espera de dez minutos para provar expiração.

## Pendências e preparação da etapa 5B

Mantidas: frontend sem integração, sessão web ausente, build/lint/typecheck pendentes, instalação Python limpa pendente e Compose não executado. Nenhuma nova tentativa npm foi feita sem evidência de mudança do ambiente. Sem stubs para declarar frontend validado; sem instalação automática do Docker. Dependências/versões fixadas existentes foram reutilizadas.

Para 5B: leitura privada de revisão por loja/dono; validação de expiração/configuração e re-resolução de preço/entrega na admissão; tentativa com chave/hash e UNIQUE por loja/sessão; consumo único de revisão/pedido gravado antes de pagamento; API de autorização/consulta durável e idempotente por pedido; estados, leases, contadores e retomada conforme recuperacao.md. Reintroduzir explicitamente credencial/dependência orders→pagamentos somente com esse uso real. Não usar a revisão como prova de compra confirmada. O intermediário Next.js terá incremento próprio antes de afirmar proteção da sessão do usuário final.
