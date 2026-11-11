# Catálogo funcional e componentes de domínio — etapa 4

> Registro histórico do incremento. Resultados e limitações abaixo se referem àquela etapa; o estado atual está em [entrega-final.md](entrega-final.md). A homologação posterior aprovou 67 testes backend completos, 31 offline e 10 web; frontend e containers permanecem pendentes.

> Registro da etapa 4. Na etapa 5A foram implementadas janelas internas e revisão persistida em pedidos, reutilizando estes componentes. Veja [revisao-etapa5a.md](revisao-etapa5a.md) para o estado atual; as menções abaixo à ausência desses endpoints descrevem o fechamento da etapa 4.

Registro em 08/11/2026. **Implementado e verificado no backend.** Dois catálogos fictícios, APIs internas, validação de seleção e componentes puros de totais/entrega. Frontend continua legado, sem integração de catálogo e sem redesenho. Não há carrinho, checkout, revisão de compra, criação de pedido, autorização ou recuperação. Agenda ainda não tem endpoint.

## Dados e modelos

| Fonte | Loja / dataset | Produtos |
|---|---|---|
| `demo-data/clothing/products.json` | roupas-demo / clothing-demo-v1 | Camiseta, calça de sarja, jaqueta leve, vestido midi, bermuda de moletom e moletom com capuz |
| `demo-data/food/products.json` | alimentos-demo / food-demo-v1 | Biscoito, suco, arroz, granola, geleia e chocolate |

Envelope fechado: schema_version 1, store_id, domain, dataset_id, fictional true e products. Entre 1 e 100 produtos no schema; os catálogos ativos têm seis cada. ID estável em slug, nome 1–100 caracteres, descrição 1–600, **category obrigatória** 1–60, preço inteiro positivo até 10.000.000 centavos, BRL, image_url local e kind discriminador. Valores/nomes/informações são exclusivamente fictícios. Nenhum dado inválido foi inserido no catálogo ativo; fixtures inválidas são construídas nos testes.

Roupas acrescenta combinações explícitas (ID globalmente único, tamanho, cor, enabled booleano). Produto camiseta possui M/preta, G/preta e G/azul habilitadas; **não** possui M/azul. P/branca existe desabilitada: isso é um estado válido do catálogo, não uma linha inválida. Nem enabled true nem a existência da combinação representam estoque físico. Sem campo, controle ou reserva de estoque. Rejeitar pares tamanho/cor duplicados, mesmo com diferenças de capitalização.

Alimentos acrescenta sale_unit unit e food_information completo: fictional true, ingredientes, união known/unknown de alergênicos e nutrição por porção. Biscoito/chocolate têm declaração conhecida; arroz/suco/geleia têm ausência declarada (known, duas listas vazias); granola tem informação desconhecida (unknown, dois null). Não confundir esses casos com garantia de segurança alimentar. Listas de alergênicos não podem repetir termos nem declarar o mesmo termo em contains e may_contain. Sem alegações de certificação, saúde ou conformidade regulatória.

Nutrição segue os campos/unidades de [contratos-api.md](contratos-api.md): porção positiva em g/ml; energia kcal; sódio mg; demais nutrientes g. Números finitos, não negativos, no máximo duas casas decimais; bool/string não são números. Ingredientes precisam ser não vazios. Dados incompatíveis com kind são proibidos. Preços e quantidades são estritamente int: inclusive 1.0 é recusado como quantidade. Este contrato de negócio é mais estrito que a notação de inteiro matemático usada pelo schema do manifesto.

## Código e composição

| Arquivo | Responsabilidade |
|---|---|
| `domain/models.py` | Modelos Pydantic estritos, congelados, tuplas aninhadas e uniões por kind/status |
| `domain/catalog.py` | JsonCatalogLoader, validação de identidade/dataset, limite de 1 MiB, snapshot imutável e revisão |
| `domain/selection.py` | ClothingSelectionValidator e FoodSelectionValidator |
| `domain/pricing.py` | IntegerTotalsCalculator, linhas e totais imutáveis, sem I/O |
| `domain/delivery.py` | Address, política sem agenda, política agendada, relógio/ZoneInfo e snapshot da janela |
| `domain/contracts.py` | Portas CatalogLoader, ProductSelectionValidator, TotalsCalculator, DeliveryPolicy e Clock |
| `domain/composition.py` | Registro único por domínio e criação dos componentes |
| `services/catalog/service.py` | Listagem/detalhe/resolução integral usando o snapshot e a abstração de seleção |
| `services/catalog/routes.py` | Três handlers HTTP finos, modelos e permissões |
| `foundation/auth.py` | Credenciais por papel e identidade/hash, reutilizados por prontidão e catálogo |

Bootstrap de catálogo seleciona componentes, carrega/valida o arquivo e guarda um snapshot. Falta do arquivo, JSON inválido, chaves JSON repetidas, limites, identidade ou dados inválidos impedem startup. Diagnóstico contém código CATALOG_INVALID, caminho lógico do campo e categoria da falha, sem incluir conteúdo bruto ou arquivo privado nas respostas HTTP. O processo não fica disponível após startup inválido.

Modelos congelados e coleções em tuplas/mapping read-only impedem alterações acidentais. Métodos de API criam DTOs/serializações separados. Alterar o arquivo em disco com o processo rodando não troca os dados: é necessário reiniciar o catálogo. Outros serviços não abrem esses arquivos.

## Normalização e catalog_revision

Formato: `sha256:<64 hex>`, calculado uma vez sobre JSON UTF-8 do **conteúdo validado**. Independente de config_hash, que identifica o manifesto e não contém preços.

1. Strings comerciais normalizam Unicode NFC e removem espaços externos; caracteres de controle/surrogates isolados são recusados. IDs são slugs; não reescrever case de IDs.
2. Produtos ordenados por id e combinações por id apenas para o hash. Listagem também tem ordem estável por ID; ordem de combinações apresentada no detalhe não é uma capacidade comercial.
3. Contains/may_contain conhecidos são conjuntos sem duplicação, ordenados no hash. Ingredientes preservam a ordem declarada, assim como os demais campos textuais de apresentação.
4. Inteiros/decimais nutricionais matematicamente equivalentes (30/30.0) têm representação canônica igual; dinheiro continua int estrito. Chaves JSON ordenadas, sem espaços, sem NaN/Infinity.
5. Inclui envelope validado de identidade/schema/dataset/fictional, produtos e seus campos completos, inclusive descrição, categoria, preço, habilitação, image_url e metadados. Não inclui caminho do arquivo, timestamps de carga ou bytes da imagem.

| Mudança | Revisão |
|---|---|
| Preço, rótulo/habilitação de combinação, descrição/categoria | Muda |
| Informação alimentar, porção/nutriente ou ordem dos ingredientes | Muda |
| Indentação, espaços entre tokens, ordem das chaves JSON | Não muda |
| Ordem dos produtos ou das combinações | Não muda |
| Ordem de termos em contains/may_contain | Não muda |
| Unicode equivalente, espaços externos em texto, 30 vs 30.0 em medida | Não muda |
| Conteúdo da imagem mantendo o mesmo image_url | Não muda; limitação explícita, imagens não são versionadas por este hash |

As revisões não são travas de preço nem revisões de compra. Não se implementou nenhuma confirmação de preço nesta etapa.

## APIs implementadas e permissões

Rotas do **serviço catálogo**, não do navegador:

| Método/rota | Papel permitido | Resultado |
|---|---|---|
| GET /internal/v1/products | web | store_id, catalog_revision, items resumidos, incluindo category |
| GET /internal/v1/products/{product_id} | web | store_id, catalog_revision, product discriminado completo; 404 PRODUCT_NOT_FOUND |
| POST /internal/v1/selections/resolve | orders | store_id, catalog_revision, items resolvidos; sem calcular total nem gravar |
| GET /health/ready | web ou orders | Configuração/schema e catalog_loaded, com catalog_revision |
| GET /health/live | Sem credencial | Somente vida do processo |

Sem credencial ou token incorreto: 401 INTERNAL_UNAUTHORIZED. Papel conhecido fora da permissão: 403 INTERNAL_FORBIDDEN (por exemplo, web tentando resolver ou orders tentando listar). Credenciais dos dois papéis precisam ser distintas no bootstrap. Store/hash divergentes: 409 CONFIG_MISMATCH; corpo store_id também deve coincidir. Não há seleção de outra loja por parâmetro do cliente.

Resolução recebe apenas store_id e 1–50 linhas únicas, produto, quantity int 1–100 e combination_id obrigatório em roupas. Em alimentos, combination_id é proibido, inclusive null. Mesmo produto com combinações diferentes pode ocupar duas linhas; seleção repetida retorna 422 DUPLICATE_LINE. Produto/combinação inexistente, combinação de outra roupa ou desabilitada: 422 SELECTION_INVALID. Campos extras/preços/tipos inválidos: 422 INPUT_INVALID. Lista inválida não devolve items parciais nem altera o snapshot.

Respostas preservam os envelopes do contrato. Ajuste necessário: **category foi acrescentada à listagem/detalhe**, por exigência desta etapa, e o exemplo de imagem foi trocado pelo fallback existente. A seleção resolvida mantém o contrato anterior: produto/nome/kind/quantidade/preço unitário, combinação ou informações alimentares; não recebe categoria, imagem ou total como novos campos.

Erros usam envelope comum com request_id e fields sanitizados, sem input bruto ou traceback. JSON malformado é 400; corpo acima de 64 KiB é 413; Content-Type incompatível é 415. Sem rota de resolução no Next.js, sem CORS liberado, sem endpoints de agenda/revisão/pedido/pagamento. OpenAPI contém somente saúde e as três operações reais do catálogo.

## Totais e entrega — componentes internos

IntegerTotalsCalculator recebe itens resolvidos e devolve linhas, subtotal/total BRL, frete/desconto zero. Entre 1–50 seleções únicas, preço até 10.000.000 e quantidade 1–100; total até 50.000.000.000 centavos. Não consulta catálogo/API, não grava e não autoriza. Pode ser usado futuramente pelo serviço de pedidos; **não possui endpoint**.

UnscheduledDelivery aceita Address validado e nenhuma janela (até null explícito é rejeitado); sem promessa de prazo. ScheduledDelivery usa templates do manifesto e Clock injetável, com datetime aware e ZoneInfo America/Sao_Paulo. Horizon days_ahead inclui hoje; só retorna starts_at estritamente maior que now, habilitado e dentro do horizonte. ID contém policy_id, data local ISO e nome do template. Sem datas fixas na implementação e sem controle/reserva de capacidade.

Validação recusa janela desconhecida/desabilitada, data fora do horizonte e início passado ou exatamente igual a now; preserva id, início/fim com offset e timezone em snapshot imutável. Relógio é consultado uma vez por operação. ZoneInfo determina offsets, inclusive históricos; não subtrair três horas manualmente. Instantes locais inexistentes em transições históricas não são oferecidos. As políticas não persistem agenda nem criam pedidos e não estão expostas por HTTP.

## Imagens locais

Todos os produtos usam `/demo/catalog-fallback.svg`. Arquivo real em `apps/store-ropa/public/demo/catalog-fallback.svg`: ilustração vetorial genérica original criada neste repositório para demonstração, sem imagem/elemento de terceiro copiado e sem dependência de rede. Não são fotografias dos produtos; só há fallback nesta entrega.

Futuramente, o navegador receberá o mesmo image_url da API intermediada e resolverá o caminho na origem do **frontend**; Next.js serve arquivos public/ sob a raiz, portanto frontend/demo/catalog-fallback.svg. O serviço de catálogo não serve o SVG e não deve receber a pasta public privada do frontend. Hoje o arquivo existe e foi conferido em teste; sua entrega pelo Next.js ainda depende da instalação/execução pendente. A vitrine legada não foi alterada para consumir esses caminhos nem as novas APIs; suas imagens remotas antigas continuam transitórias.

## Execução e chamadas — PowerShell

Os pins/ambiente são os da fundação. Na raiz, terminal 1:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
```

Terminal 2: credencial lida do arquivo local, nunca impressa:

```powershell
$variant = 'clothing'
$store = 'roupas-demo'
$secrets = Get-Content ".local/$store.env" -Raw | ConvertFrom-StringData
$hash = & .\.venv\Scripts\python.exe -c "from foundation.config import load; print(load('configurations/$variant.json').config_hash)"
$headers = @{ Authorization = "Bearer $($secrets.WEB_CATALOG_TOKEN)"; 'X-Store-Id' = $store; 'X-Config-Hash' = $hash }
Invoke-RestMethod http://127.0.0.1:8001/internal/v1/products -Headers $headers
Invoke-RestMethod http://127.0.0.1:8001/internal/v1/products/camiseta -Headers $headers
$headers.Authorization = "Bearer $($secrets.ORDERS_CATALOG_TOKEN)"
$body = @{ store_id = $store; items = @(@{ product_id = 'camiseta'; combination_id = 'camiseta-m-preta'; quantity = 2 }) } | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8001/internal/v1/selections/resolve -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

Para alimentos: encerrar roupas com Ctrl+C e iniciar `tools/lps.py service food --service catalog`. No terminal 2, refazer as variáveis com `$variant = 'food'` e `$store = 'alimentos-demo'`; listar e consultar `/internal/v1/products/biscoito`. Resolução usa o token orders de alimentos e este corpo **sem combination_id**:

```powershell
$headers.Authorization = "Bearer $($secrets.ORDERS_CATALOG_TOKEN)"
$body = @{ store_id = $store; items = @(@{ product_id = 'biscoito'; quantity = 2 }, @{ product_id = 'suco'; quantity = 1 }) } | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8001/internal/v1/selections/resolve -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

O lançador gera segredos apenas se ausentes e conserva os existentes. Para levantar a família local, comandos da fundação continuam válidos, sujeitos à instalação do frontend. Não enviar esses tokens ao navegador.

## Docker e isolamento

Dockerfile backend agora inclui domain/; os JSON comerciais **não entram na imagem comum**. Compose monta `./demo-data:/app/demo-data:ro` somente em catalog; `CATALOG_DATA_ROOT` só é configurado nesse serviço. A pasta contém ambos os datasets do mesmo dono; o manifesto seleciona e a carga confere loja/domínio/dataset/schema. Pedidos/pagamentos/frontend não montam demo-data. Pedidos/pagamentos preservam seus volumes privados. No caminho local, o lançador fornece CATALOG_DATA_ROOT apenas ao processo catálogo.

Prontidão mantém `scope: foundation` para compatibilidade com os verificadores existentes, mas catálogo agora exige catalog_loaded e informa catalog_revision. Isso não declara prontidão de compra, pagamento ou worker. Liveness continua independente. Somente porta do frontend publicada no Compose; para chamadas diretas de diagnóstico, usar caminho local acima. YAML conferido não equivale a executar containers.

## Verificação real e pendências

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
# Ou separadamente:
.\.venv\Scripts\python.exe -m unittest discover -s tests/catalog -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/foundation -v
```

Resultado final: **32 testes ativos aprovados**, sendo 21 de catálogo/componentes e 11 de regressão da fundação, com subcenários. A suíte legada está fora da descoberta ativa acima. Dois processos catálogo simultâneos para as variantes nos testes HTTP; três serviços por variante sequenciais na regressão. Portas temporárias, relógio fixo e arquivos/bancos/segredos temporários: testes não alteram recursos da demonstração.

Cobertos: carga, campos/tipos/limites, unicidade, exclusões de domínio, combinações/duplicação de linhas, alergênicos, normalização/revisão, imutabilidade em execução, resolução HTTP integral, permissões, identidade/hash, 404/400/413/415/422, bootstrap com catálogo inválido, totais e fronteiras de tempo. Regression mantém saúde, isolamento/storage/restart e 24 vetores Python/TS. Testes de agenda não usam a data real nem esperas por janela.

Frontend: feita uma tentativa nova `npm ci` pelo lockfile, sem retry de rede e com timeout. Falhou; log registra EACCES ao buscar react/next e encerramento npm “Exit handler never called”. Não repetir tentativas equivalentes. Build/lint/typecheck e execução Next.js continuam **não verificados**, sem stubs. Não houve redesign ou integração visual. Instalação Python limpa e containers/Compose continuam pendentes; não foram instalados Docker nem pacotes globais, e os pins existentes foram preservados.

Próximo incremento recomendado: serviço de pedidos com sessão anônima/intermediário, revisão/admissão e persistência, conectando os componentes definidos; só então pagamentos simulados duráveis e recuperação no recorte aprovado. Se a próxima prioridade for visual, integrar primeiro somente leitura do catálogo pelo Next.js após resolver a instalação, sem misturar isso com checkout. Nenhuma dessas funcionalidades foi antecipada nesta entrega.

Referência técnica para os modelos: [uniões discriminadas Pydantic](https://pydantic.dev/docs/validation/latest/concepts/unions/) e [validação estrita](https://github.com/pydantic/pydantic/blob/main/docs/concepts/strict_mode.md); versões efetivas permanecem as fixadas na fundação.
