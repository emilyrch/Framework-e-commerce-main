# Contratos HTTP e modelos de dados

Contratos-alvo da etapa 2, atualizados na etapa 5A em 08/11/2026. **Implementados:** saúde, catálogo interno, janelas internas de pedidos e criação de revisão persistida. Sessão web, rotas /api/v1 do Next.js, criação de pedido, autorização e recuperação continuam futuras. Estado/comandos em [revisao-etapa5a.md](revisao-etapa5a.md); catálogo em [catalogo-etapa4.md](catalogo-etapa4.md). Exemplos de compra/admissão abaixo continuam ilustrativos, não funcionalidades executadas.

## Convenções e acesso

JSON UTF-8; campos desconhecidos rejeitados nos comandos. Identificadores externos de pedido, pagamento, revisão e tentativa são UUIDv4 gerados no servidor; chave do cliente é UUIDv4/CSPRNG. IDs de produto/combinação/janela podem ser legíveis: não são credenciais. Timestamps RFC3339 com offset; instantes de criação expostos em UTC e agenda com offset local e timezone IANA. Sem datas ingênuas. Todas as entidades incluem store_id.

| Navegador → Next.js, mesma origem | Interna destino | Acesso e finalidade |
|---|---|---|
| POST /api/v1/session | Não encaminha | Criar/reutilizar cookie de loja; Origin validado |
| GET /api/v1/store | Projeção local e verificação de identidade | Configuração pública sem segredos/caminhos |
| GET /api/v1/products | catálogo GET /internal/v1/products | Público, somente leitura via intermediário |
| GET /api/v1/products/{product_id} | catálogo GET /internal/v1/products/{id} | Detalhe da loja ativa |
| GET /api/v1/delivery-slots | pedidos GET /internal/v1/delivery-slots | Agenda da loja; sem sessão obrigatória |
| POST /api/v1/reviews | pedidos POST /internal/v1/reviews | Sessão; revisar seleção/endereço/preço |
| POST /api/v1/orders | pedidos POST /internal/v1/orders | Sessão e Idempotency-Key obrigatórias |
| GET /api/v1/orders/{order_id} | pedidos GET /internal/v1/orders/{id} | Só dono da sessão/loja |
| GET /api/v1/order-attempts/{key} | pedidos GET /internal/v1/order-attempts/{key} | Recuperar tentativa sem conhecer order_id; só dono |
| GET /api/health/live | Local | Processo web vivo, sem dados privados |
| GET /api/health/ready | Verificações internas | Estado agregado, identidade pública e nomes de componentes, sem URLs/segredos |

Somente internas: catálogo POST `/internal/v1/selections/resolve`; pagamentos PUT e GET `/internal/v1/payments/by-order/{order_id}`; todos os backends GET `/health/live` e GET `/health/ready`. Catálogo/pedidos não expõem rota genérica que permita ao navegador autorizar pagamento. Saúde ready exige credencial interna; live devolve apenas processo/estado. As credenciais por relação e os cabeçalhos confiáveis estão em [arquitetura-atual.md](arquitetura-atual.md).

Estado da etapa 4: rotas `/api/v1/*` na coluna navegador ainda **não** foram implementadas. Somente GETs `/internal/v1/products` e `/internal/v1/products/{id}` aceitam papel web; somente POST `/internal/v1/selections/resolve` aceita papel orders. Saúde aceita ambos. Papel válido fora da permissão retorna 403 INTERNAL_FORBIDDEN; token ausente/incorreto retorna 401. Tokens iguais para esses dois papéis impedem bootstrap. Pagamentos por pedido permanece contrato futuro, não endpoint implementado.

Etapa 5A acrescenta no serviço pedidos **GET /internal/v1/delivery-slots** e **POST /internal/v1/reviews**, ambos somente com credencial web→pedidos e loja/hash coerentes. O POST exige X-Session-Owner único em formato `[a-f0-9]{64}`; ausente/inválido retorna 401 SESSION_REQUIRED. Não há dono no corpo. O cabeçalho só é confiado junto à credencial correta; isso **não** implementa uma sessão anônima de navegador. O GET não exige dono. Não há GET de revisão, consumo ou pedido/autorização.

Internamente: Authorization Bearer, X-Store-Id, X-Config-Hash obrigatórios (exceto live); X-Session-Owner nas rotas privadas de pedidos. Respostas internas incluem X-Store-Id e X-Config-Hash; destinatário confere. Corpo store_id deve coincidir com configuração/cabeçalhos. Navegador recebe config_hash no store/revisões, mas não pode escolher cabeçalhos internos. Web valida cookie, Origin em mutações, Content-Type e corpo; remove cabeçalhos de confiança enviados pelo cliente e os recompõe.

Sem sessão válida, rotas privadas respondem 401. Recurso de outra sessão/loja é 404, sem informar se existe. Dados privados com `Cache-Control: no-store`. Erros em JSON usam envelope único, inclusive adaptação dos erros de validação FastAPI; não depender do corpo padrão do framework.

## Sessão e configuração pública

POST `/api/v1/session`, corpo `{}` e Origin da loja; 200 com Set-Cookie HttpOnly (token nunca no corpo):

```json
{"store_id":"roupas-demo","session_available":true,"session_context_id":"ctx_opaque_demo_1","expires_at":"2026-12-08T12:00:00Z"}
```

session_context_id é marcador opaco de continuidade, não token de autenticação, e permanece igual enquanto o cookie é válido. Sua derivação e o bloqueio de retomada sob outra sessão estão em [arquitetura-atual.md](arquitetura-atual.md). O literal do exemplo é ilustrativo; produção do marcador usará HMAC com rótulo separado. Não retornar session_owner ou SID.

GET `/api/v1/store`, 200 para roupas:

```json
{
  "schema_version": 1,
  "store_id": "roupas-demo",
  "display_name": "Loja de Roupas Demo",
  "domain": "clothing",
  "config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "currency": "BRL",
  "timezone": "America/Sao_Paulo",
  "features": ["catalog", "cart", "checkout", "orders", "simulated_pix", "address_delivery", "size_color_selection"],
  "payment": {"method":"simulated_pix","simulated":true},
  "delivery": {"scheduled":false,"shipping_cents":0},
  "limits": {"max_lines":50,"min_quantity":1,"max_quantity":100}
}
```

Para alimentos, store_id `alimentos-demo`, nome correspondente, domain `food`, features do manifesto de alimentos e delivery.scheduled true; mesmo schema público, método, moeda e limites. O hash acima é marcador de 64 hex, não cálculo real do exemplo de manifesto. Limite técnico proposto: 50 linhas e corpo até 64 KiB; não é feature nem exigência acadêmica. Não publicar dataset.source, bancos, tokens, segredo de sessão ou URLs internas.

## Catálogo e seleção de produto

GET `/api/v1/products`, resposta 200 (exemplo abreviado de conjunto, não exigência de apenas um produto):

```json
{
  "store_id":"roupas-demo",
  "catalog_revision":"catalog-clothing-1",
  "items":[
    {"id":"camiseta","name":"Camiseta demo","description":"Peça de demonstração","category":"Camisetas","price_cents":8990,"currency":"BRL","image_url":"/demo/catalog-fallback.svg","kind":"clothing"}
  ]
}
```

Sem paginação, até 100 produtos. Item listado contém os campos do exemplo; detalhe acrescenta metadados do domínio. Ajuste da etapa 4: category obrigatória foi acrescentada à listagem/detalhe (texto 1–60) para categorizar os produtos solicitados. Há seis produtos ativos por loja. image_url aponta para recurso local na origem do frontend futuro; não para arquivo servido pelo backend. `catalog_revision` agora é `sha256:<64 hex>` do conteúdo normalizado/validado; regras exatas de ordenação, Unicode e números em [catalogo-etapa4.md](catalogo-etapa4.md). Strings antigas catalog-clothing-1/catalog-food-1 nos exemplos são marcadores ilustrativos, não hashes reais.

GET `/api/v1/products/camiseta`, 200:

```json
{
  "store_id":"roupas-demo",
  "catalog_revision":"catalog-clothing-1",
  "product":{
    "id":"camiseta","kind":"clothing","name":"Camiseta demo",
    "description":"Peça de demonstração","category":"Camisetas","price_cents":8990,"currency":"BRL",
    "image_url":"/demo/catalog-fallback.svg",
    "combinations":[
      {"id":"camiseta-m-preta","size":"M","color":"preta","enabled":true},
      {"id":"camiseta-g-azul","size":"G","color":"azul","enabled":true}
    ]
  }
}
```

Preço é por produto neste MVP, não varia por combinação. ID da combinação é único no catálogo, pertence a um produto e não é derivado de texto digitado pelo cliente. Não construir produto cartesiano de listas de tamanhos/cores. Combinação desabilitada nunca é selecionável; enabled não implica estoque físico. Mensagem da UI deve dizer isso. Combinações repetidas/sem ID/sem tamanho ou cor impedem carga.

GET `/api/v1/products/biscoito`, em alimentos:

```json
{
  "store_id":"alimentos-demo",
  "catalog_revision":"catalog-food-1",
  "product":{
    "id":"biscoito","kind":"food","name":"Biscoito demo",
    "description":"Embalagem fictícia vendida por unidade","category":"Biscoitos","price_cents":2590,"currency":"BRL",
    "image_url":"/demo/catalog-fallback.svg","sale_unit":"unit",
    "food_information":{
      "fictional":true,
      "ingredients":["farinha de trigo","açúcar","óleo vegetal"],
      "allergens":{"status":"known","contains":["trigo"],"may_contain":["leite"]},
      "nutrition_per_serving":{
        "serving_amount":30,"serving_unit":"g","serving_description":"3 unidades",
        "energy_kcal":140,"carbohydrates_g":20,"total_sugars_g":6,
        "protein_g":2,"total_fat_g":6,"saturated_fat_g":2,
        "trans_fat_g":0,"fiber_g":1,"sodium_mg":90
      }
    }
  }
}
```

Metadados alimentares obrigatórios: fictional sempre true; ingredients lista não vazia de strings; nutrition_per_serving completo. Medida da porção: serving_amount número finito positivo, serving_unit `g` ou `ml`, serving_description texto não vazio. Nutrientes finitos não negativos com até duas casas decimais; nomes e unidades são exatamente os campos do exemplo: energia em kcal, sódio em mg, demais em g. Esses números não são dinheiro e podem ser decimais. Não calcular % diário nem alegar certificação, adequação dietética ou conformidade regulatória.

Alergênicos é união explícita:

- `{"status":"known","contains":[],"may_contain":[]}` = ausência **declarada nos dados fictícios**, não informação desconhecida nem garantia de ausência de risco.
- known com listas preenchidas = declaração conhecida; listas sem duplicatas, strings não vazias.
- `{"status":"unknown","contains":null,"may_contain":null}` = informação desconhecida; UI deve mostrar “Informação sobre alergênicos desconhecida”. Null não equivale a lista vazia.

Campo allergens ausente, unknown com listas vazias ou known com null são inválidos no catálogo. Produtos de roupas proíbem food_information; alimentos proíbem combinations. O catálogo valida store_id/domain no envelope do arquivo e o kind de cada produto antes de ficar pronto.

### Resolução interna usada por pedidos

POST catálogo `/internal/v1/selections/resolve` (credencial de pedidos), corpo:

```json
{"store_id":"roupas-demo","items":[{"product_id":"camiseta","combination_id":"camiseta-m-preta","quantity":2}]}
```

200:

```json
{
  "store_id":"roupas-demo","catalog_revision":"catalog-clothing-1",
  "items":[{"product_id":"camiseta","name":"Camiseta demo","kind":"clothing","quantity":2,"unit_price_cents":8990,"combination":{"id":"camiseta-m-preta","size":"M","color":"preta"}}]
}
```

Para alimento, entrada não contém combination_id e snapshot inclui sale_unit e food_information completo em vez de combination. Esta operação não escreve e pode ser repetida nas condições de timeout abaixo. Linha desconhecida ou combinação inválida retorna 422 SELECTION_INVALID, com índice/campo; resolução atômica da lista, sem resultados parciais. Duplicação de mesma seleção (product_id + combination_id ou product_id de alimento) é recusada com 422 DUPLICATE_LINE: carrinho deve consolidar e manter quantidade total 1–100. Linhas de combinações distintas do mesmo produto são permitidas.

## Endereço e entrega

Address contém recipient (1–80), street (1–120), number (1–20, string para permitir “s/n”), district (1–80), city (1–80), state (duas letras maiúsculas), postal_code (oito dígitos), complement opcional (até 120). Strings aparadas, sem vazios; não consultar CEP externo nem guardar telefone/CPF. Dados fictícios. Country é implicitamente BR no MVP.

GET `/api/v1/delivery-slots`, alimentos, 200:

```json
{
  "store_id":"alimentos-demo","timezone":"America/Sao_Paulo","server_now":"2026-11-08T12:00:00Z",
  "items":[
    {"id":"food-windows-v1:2026-11-09:morning","starts_at":"2026-11-09T09:00:00-03:00","ends_at":"2026-11-09T12:00:00-03:00","timezone":"America/Sao_Paulo","enabled":true},
    {"id":"food-windows-v1:2026-11-09:afternoon","starts_at":"2026-11-09T14:00:00-03:00","ends_at":"2026-11-09T17:00:00-03:00","timezone":"America/Sao_Paulo","enabled":true}
  ]
}
```

Retornar só janelas habilitadas cujo starts_at seja estritamente maior que o relógio do servidor, dentro do horizonte definido no manifesto. Roupas: 409 FEATURE_NOT_AVAILABLE. Lista vazia em alimentos é 200 com items []; UI bloqueia confirmação. Slot desconhecido/desabilitado é 422 DELIVERY_SLOT_INVALID; antes oferecido mas que já começou/horizonte expirado na confirmação é 409 DELIVERY_SLOT_EXPIRED. Revalidar na revisão e na admissão, não depois de pedido admitido. Validar timezone com base IANA, não subtrair três horas manualmente. Copiar id/starts_at/ends_at/timezone para o pedido.

## Revisão de preço antes da confirmação

POST futuro `/api/v1/reviews`; atualmente **POST /internal/v1/reviews** com credencial web→pedidos e X-Session-Owner validado. Exemplo roupas com duas linhas:

```json
{
  "store_id":"roupas-demo",
  "items":[
    {"product_id":"camiseta","combination_id":"camiseta-m-preta","quantity":1},
    {"product_id":"camiseta","combination_id":"camiseta-g-azul","quantity":2}
  ],
  "delivery":{"address":{"recipient":"Cliente Demo","street":"Rua Exemplo","number":"10","district":"Centro","city":"São Paulo","state":"SP","postal_code":"01001000"}},
  "payment_method":"simulated_pix"
}
```

Alimentos usa o mesmo contrato, com itens sem combination_id e delivery.slot_id obrigatório:

```json
{
  "store_id":"alimentos-demo",
  "items":[{"product_id":"biscoito","quantity":2},{"product_id":"suco","quantity":1}],
  "delivery":{"address":{"recipient":"Cliente Demo","street":"Rua Exemplo","number":"10","district":"Centro","city":"São Paulo","state":"SP","postal_code":"01001000"},"slot_id":"food-windows-v1:2026-11-09:morning"},
  "payment_method":"simulated_pix"
}
```

Não aceitar unit_price, total, horários, informações nutricionais ou rótulos da combinação como autoridade do cliente. Só IDs, quantidade, endereço e método. Ordem das linhas não muda o significado: servidor ordena por seleção ao normalizar. Roupas proíbe slot_id, inclusive null; alimentos proíbe combination_id, inclusive null. Quantidades estritamente inteiras 1–100 (não bool, string ou fração). Lista entre 1–50 seleções únicas; preço por unidade inteiro 1–10.000.000 centavos; total máximo 50.000.000.000, seguro para inteiro JS; excesso é 422 TOTAL_OUT_OF_RANGE. Limites técnicos do projeto, não requisitos do professor.

201 após persistir revisão no serviço de pedidos (exemplo roupas):

```json
{
  "store_id":"roupas-demo","review_id":"91323ddc-a37c-42a7-92b3-415c26304fe7",
  "config_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "catalog_revision":"catalog-clothing-1",
  "created_at":"2026-11-08T12:00:00Z","expires_at":"2026-11-08T12:10:00Z",
  "items":[
    {"product_id":"camiseta","name":"Camiseta demo","kind":"clothing","quantity":1,"unit_price_cents":8990,"line_total_cents":8990,"combination":{"id":"camiseta-m-preta","size":"M","color":"preta"}},
    {"product_id":"camiseta","name":"Camiseta demo","kind":"clothing","quantity":2,"unit_price_cents":8990,"line_total_cents":17980,"combination":{"id":"camiseta-g-azul","size":"G","color":"azul"}}
  ],
  "delivery":{"address":{"recipient":"Cliente Demo","street":"Rua Exemplo","number":"10","district":"Centro","city":"São Paulo","state":"SP","postal_code":"01001000"},"shipping_cents":0},
  "payment_method":"simulated_pix",
  "totals":{"currency":"BRL","subtotal_cents":26970,"shipping_cents":0,"discount_cents":0,"total_cents":26970}
}
```

Revisão é imutável, vinculada à sessão/loja/hash e dura 10 minutos para iniciar a admissão. Em alimentos, mesmo envelope, cada item preserva food_information completo; delivery acrescenta slot com snapshot da janela, além de address/shipping_cents. A revisão do exemplo de alimentos com suco a 1390 soma 6570 centavos. Não há preço travado no catálogo: revisão é a proposta exibida ao cliente.

Na etapa 5A, a resposta 201 só sai depois do INSERT/commit durável no schema 1 existente. Created_at é capturado após a resolução HTTP e expires_at soma exatamente dez minutos; endereço/itens/janela/totais são snapshots. Não se cria tentativa/pedido nem se chama pagamentos. Reenvios podem gerar revisões independentes; não existe idempotência de revisão ou endpoint de consulta. Seleções são ordenadas por produto/combinação na normalização. A semântica de sessão é a vinculação interna ao dono confiado, não proteção já validada no Next.js.

Na confirmação, pedidos resolve catálogo novamente. Compara snapshot comercial (produto, nome, combinação ou metadados alimentares e preços) e totais ao revisado; revisão global pode mudar por outro produto sem invalidar a compra. Se conteúdo relevante mudou, devolver 409 REVIEW_CHANGED; não autorizar, não criar pedido e não cobrar novo valor automaticamente. Cliente refaz revisão, apresenta diferenças e confirma com nova chave. Se revisão expirou → 409 REVIEW_EXPIRED. A última resolução válida imediatamente antes da gravação local define o ponto de aceitação do preço; não há bloqueio distribuído do arquivo do catálogo. Mudanças após esse ponto não alteram o pedido admitido.

## Criar, recuperar e consultar pedido

POST `/api/v1/orders`, cabeçalho `Idempotency-Key: 020bbd5d-7268-43aa-bf25-a8ee0919dc2a`, corpo:

```json
{"store_id":"roupas-demo","review_id":"91323ddc-a37c-42a7-92b3-415c26304fe7"}
```

Nenhum preço/seleção/endereço pode ser alterado nesta chamada. Consumir snapshot/entrada da revisão persistida. Novo pedido confirmado retorna 201 e Location `/api/v1/orders/<id>`; ainda em processamento retorna 202 e Retry-After: 2. Repetição retorna 200 se terminal ou 202 se intermediário, com o mesmo order_id quando já admitido. Mesma chave/conteúdo diferente → 409 IDEMPOTENCY_KEY_REUSED; outra chave para revisão já consumida → 409 REVIEW_ALREADY_USED (inclui order_id só para o mesmo dono). Contratos transacionais em [recuperacao.md](recuperacao.md).

Antes da admissão, 202 usa o modelo de tentativa (o mesmo do GET order-attempts), com status validating e order_id/order_status null. Depois da admissão, 202 usa o modelo de pedido com status payment_pending ou payment_unknown; payment_id null e payment.status not_observed. Assim o cliente não precisa inventar um pedido antes do commit. Exemplo 202 de validação concorrente:

```json
{"store_id":"roupas-demo","attempt_id":"14432c8c-9de1-441c-b9ba-a3fb9af2cb82","status":"validating","order_id":null,"order_status":null,"recovery":{"action":"wait","next_retry_at":"2026-11-08T12:01:02Z"},"error":null}
```

Resposta comum 201/200 de pedido confirmado; GET `/api/v1/orders/{id}` usa o mesmo modelo:

```json
{
  "store_id":"roupas-demo","order_id":"5ebc2180-2610-4f37-b050-ec070847b041",
  "review_id":"91323ddc-a37c-42a7-92b3-415c26304fe7","status":"confirmed",
  "created_at":"2026-11-08T12:01:00Z","updated_at":"2026-11-08T12:01:01Z",
  "items":[
    {"product_id":"camiseta","name":"Camiseta demo","kind":"clothing","quantity":1,"unit_price_cents":8990,"line_total_cents":8990,"combination":{"id":"camiseta-m-preta","size":"M","color":"preta"}},
    {"product_id":"camiseta","name":"Camiseta demo","kind":"clothing","quantity":2,"unit_price_cents":8990,"line_total_cents":17980,"combination":{"id":"camiseta-g-azul","size":"G","color":"azul"}}
  ],
  "delivery":{"address":{"recipient":"Cliente Demo","street":"Rua Exemplo","number":"10","district":"Centro","city":"São Paulo","state":"SP","postal_code":"01001000"},"shipping_cents":0},
  "totals":{"currency":"BRL","subtotal_cents":26970,"shipping_cents":0,"discount_cents":0,"total_cents":26970},
  "payment":{"payment_id":"741ce1ae-a941-4bee-8bf8-0d1785373182","method":"simulated_pix","simulated":true,"status":"approved","amount_cents":26970},
  "recovery":{"action":"none","next_retry_at":null}
}
```

Alimentos: mesmo modelo com snapshot alimentar por item e delivery.slot completo. Pedido não é enriquecido consultando catálogo no GET: leitura vem do snapshot persistido, inclusive depois de reinício ou remoção do produto. Não retornar session_owner, idempotency_key ou endereço em logs.

Estados de pedido: `payment_pending` (admitido e gravado, ainda sem resultado), `payment_unknown` (timeout/falha com resultado não confirmado localmente), `confirmed` (autorização aprovada e confirmação gravada) e `payment_conflict` (violação persistida de invariantes/valor, requer investigação, sem nova autorização). Pending/unknown têm payment com payment_id null, status `not_observed`; isso é observação do pedido, não um estado durável do serviço pagamentos. recovery.action é `wait`, `retry_same_key`, `investigate` ou `none`; não expirar pedido automaticamente por tempo. Não há cancelamento/estorno/finalização logística no MVP.

GET `/api/v1/order-attempts/{key}` quando já existe tentativa, 200:

```json
{
  "store_id":"roupas-demo","attempt_id":"14432c8c-9de1-441c-b9ba-a3fb9af2cb82",
  "status":"accepted","order_id":"5ebc2180-2610-4f37-b050-ec070847b041",
  "order_status":"payment_unknown","recovery":{"action":"retry_same_key","next_retry_at":"2026-11-08T12:02:00Z"},
  "error":null
}
```

Tentativa pode ser `validating` (order_id null), `rejected` (order_id null, error com rejeição persistida) ou `accepted` (order_id fixo, consultar pedido). Ausente/loja ou dono diferente → 404. Um 404 depois de timeout **não** autoriza trocar chave: repetir o mesmo POST/corpo, pois o primeiro pode ainda estar em trânsito. GET não dispara efeito de pagamento; worker/POST de retomada com mesma chave executam recuperação.

## Pagamentos simulados: APIs exclusivamente internas

PUT `/internal/v1/payments/by-order/5ebc2180-2610-4f37-b050-ec070847b041`, credencial pedidos→pagamentos:

```json
{"store_id":"roupas-demo","order_id":"5ebc2180-2610-4f37-b050-ec070847b041","method":"simulated_pix","currency":"BRL","amount_cents":26970}
```

201 na primeira gravação, 200 na repetição idêntica:

```json
{
  "store_id":"roupas-demo","order_id":"5ebc2180-2610-4f37-b050-ec070847b041",
  "payment_id":"741ce1ae-a941-4bee-8bf8-0d1785373182","method":"simulated_pix",
  "simulated":true,"status":"approved","currency":"BRL","amount_cents":26970,
  "created_at":"2026-11-08T12:01:01Z"
}
```

GET na mesma URL retorna 200 com o mesmo modelo ou 404 PAYMENT_NOT_FOUND. Estado persistido de pagamento no MVP é apenas `approved`: a autorização simulada é uma decisão local determinística gravada atomicamente com o registro, sem chamada bancária. `absent` é ausência de linha/404 e `unknown` é incerteza do chamador, não novas linhas ou estados de autorização. Não há recusa de negócio, dados bancários ou estado pendente remoto inventado. Falha de armazenamento → 503 PAYMENT_STORAGE_UNAVAILABLE, sem afirmar se houve commit; consultar/repetir pela mesma ordem resolve. Conteúdo diferente para mesmo (store,order) → 409 PAYMENT_CONFLICT, nunca sobrescrever aprovação.

## Erros, saúde, prontidão e tempos

Envelope de erro (código estável, mensagem localizada, lista de campos sem valores privados):

```json
{"error":{"code":"SELECTION_INVALID","message":"Combinação não permitida para este produto","fields":[{"path":"items.0.combination_id","code":"invalid_combination"}],"retryable":false},"request_id":"afc9236e-1b63-40f8-8804-268db48ab891"}
```

| HTTP | Exemplos / significado |
|---|---|
| 400 | MALFORMED_JSON, IDEMPOTENCY_KEY_REQUIRED/INVALID |
| 401 / 403 | SESSION_REQUIRED ou INTERNAL_UNAUTHORIZED / ORIGIN_FORBIDDEN |
| 404 | PRODUCT_NOT_FOUND, ORDER_NOT_FOUND, REVIEW_NOT_FOUND, ATTEMPT_NOT_FOUND, PAYMENT_NOT_FOUND; sem revelar outro dono |
| 409 | REVIEW_CHANGED/EXPIRED/ALREADY_USED, IDEMPOTENCY_KEY_REUSED, CONFIG_MISMATCH, DELIVERY_SLOT_EXPIRED, FEATURE_NOT_AVAILABLE, PAYMENT_CONFLICT |
| 413 / 415 | BODY_TOO_LARGE (64 KiB) / UNSUPPORTED_MEDIA_TYPE |
| 422 | INPUT_INVALID, SELECTION_INVALID, DELIVERY_SLOT_INVALID, DUPLICATE_LINE, TOTAL_OUT_OF_RANGE |
| 503 | DEPENDENCY_UNAVAILABLE, CATALOG_RESPONSE_INVALID, NOT_READY, ORDER_STORAGE_UNAVAILABLE, PAYMENT_STORAGE_UNAVAILABLE; retryable true. Para futura criação de pedido, preservar a chave; revisão 5A ainda não é idempotente |
| 500 | INTERNAL_ERROR inesperado, sem stack trace público; nunca traduzir em sucesso |

Erro retryable não permite criar nova chave. Em criação, se a admissão foi persistida e o serviço ainda consegue ler/escrever estado, preferir 202 ao erro de dependência. Se não consegue confirmar o próprio commit/responder, 503/timeout e recuperação pela chave. Não enviar pagamento antes de commit do pedido.

GET backend `/health/live`: 200 `{"service":"orders","status":"alive"}`. Sem banco/dependências, apenas vida do processo. Web usa service `web` no mesmo modelo.

GET `/health/ready` interno: exemplo **alvo de etapas futuras**, não resposta da fundação atual (que não possui worker):

```json
{"service":"orders","status":"ready","store_id":"roupas-demo","config_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","checks":{"schema":"ok","storage":"ok","catalog_identity":"ok","payments_identity":"ok","recovery_worker":"ok"}}
```

503 no mesmo envelope de readiness com status `not_ready` e check `unavailable`/`mismatch`; não incluir caminhos/segredos. Catálogo valida manifesto/dados e informa catalog_revision. Pagamentos verifica manifesto, schema e acesso ao banco, sem consultar pedidos. Pedidos verifica banco/worker e identidade/readiness de catálogo/pagamentos; web verifica os três. Sem ciclos de health. Readiness web só publica service/status/store_id/config_hash e checks por nome, sem detalhes internos. Processo com dependência indisponível continua capaz de servir leitura de pedido persistido; readiness degradada não bloqueia automaticamente todas as rotas. Configuração estrutural inválida impede inicialização.

Esse parágrafo é o alvo futuro completo. **Prontidão atual 5A de pedidos:** banco/schema, review_repository, instância review_service e catálogo apenas. Não depende de pagamentos nem marca worker/sessão web prontos. Scope foundation permanece; liveness não faz I/O de dependência. O cliente de catálogo valida resposta tipada e cabeçalhos, rejeita redirecionamento, limita resposta a 1 MiB e trata identidade explícita divergente como 409 e ausência/má-formação como 503. Sem transação SQLite durante HTTP. Detalhes de retry e limites em [revisao-etapa5a.md](revisao-etapa5a.md).

Política técnica inicial, a validar em testes de falha:

- Navegador: timeout 15 s por chamada; Next.js: orçamento 12 s; fluxo de criação em pedidos: 8 s antes de responder 202 se já admitido. Timeouts não cancelam commits já iniciados.
- Pedido→catálogo: 1,5 s total por tentativa, no máximo duas tentativas (uma repetição após 100 ms) só em indisponibilidade/transporte, inclusive resolve que não escreve. GETs de readiness: 1 s, uma tentativa por verificação; readiness pode usar resultado recente de até 5 s.
- Pedido→pagamento: PUT 2 s, sem repetição imediata; se timeout e houver orçamento, um GET de 1 s para observar. Worker usa recuperação limitada de [recuperacao.md](recuperacao.md). Nunca repetir um pagamento com outro order_id.
- Next.js não repete automaticamente POST de revisão/criação. Para GETs, até duas tentativas de 2 s se couber em 12 s, com 100 ms de intervalo; endpoints ready usam 1 s por destino. Serviços sem resposta dentro do orçamento → 503 do intermediário, sem inventar resultado.
- Cliente acompanha tentativa/pedido com no máximo seis GETs, separados por pelo menos 2 s; após isso mostra estado e opção de retomar com mesma chave. Retry-After prevalece. Erros 4xx de validação/conflito não têm repetição automática.

Não há SLA produtivo nem garantia de processamento exatamente uma vez. Contadores, transações, limites e janela de retry são decisões técnicas, não novas features comerciais.
