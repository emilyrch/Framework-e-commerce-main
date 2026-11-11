# Backend da compra — etapa 5B

> Registro histórico do incremento. Resultados e limitações abaixo se referem àquela etapa; o estado atual está em [entrega-final.md](entrega-final.md). A homologação posterior aprovou 67 testes backend completos, 31 offline e 10 web; frontend e containers permanecem pendentes.

Registro de 10/11/2026. Implementado no código; integração HTTP e execução do worker **não verificadas neste ambiente**. Frontend permanece sem integração, carrinho, checkout ou sessão de navegador. O MVP não está pronto.

## Operações implementadas

Todas as rotas abaixo são internas, com Bearer e X-Store-Id/X-Config-Hash. Não publicar os serviços diretamente. A futura camada Next.js mapeará as operações de pedidos para `/api/v1` e gerará o dono de sessão; essa camada ainda não existe.

| Serviço | Operação | Permissão |
|---|---|---|
| Pedidos | POST `/internal/v1/orders` | web + X-Session-Owner + Idempotency-Key UUIDv4 |
| Pedidos | GET `/internal/v1/orders/{order_id}` | web + mesmo dono |
| Pedidos | GET `/internal/v1/order-attempts/{key}` | web + mesmo dono |
| Pagamentos | PUT `/internal/v1/payments/by-order/{order_id}` | orders |
| Pagamentos | GET `/internal/v1/payments/by-order/{order_id}` | orders |

Revisões e janelas da etapa 5A permanecem. Não foi criado GET de revisão. Dono é uma asserção interna de 64 caracteres hexadecimais, não uma sessão web implementada. Consultas de outra sessão retornam recurso inexistente. Respostas privadas usam no-store.

Criação recebe somente store_id/review_id. Revalida validade de dez minutos, configuração, seleções, preços, endereço e janela antes de admitir. Mudança comercial exige nova revisão; mudança isolada da revisão global do catálogo não invalida itens inalterados. Pedido preserva o snapshot original. Revisão consumida não admite outro pedido. Admissão e vínculo da tentativa são gravados atomicamente antes de qualquer pagamento.

## Reenvios e recuperação

Chave escopada por loja e dono, com hash do comando normalizado: mesmo comando recupera a tentativa; conteúdo diferente retorna 409. Restrições únicas arbitram concorrência. Tentativa passa de validating para rejected ou accepted; pedido usa payment_pending, payment_unknown, confirmed ou payment_conflict. Pagamento simulado só possui approved e nunca solicita dados financeiros.

Pagamentos persiste uma autorização por loja/pedido e compara o comando em reenvios. Pedidos consulta primeiro: somente 404 explícito PAYMENT_NOT_FOUND permite PUT. Timeout/resposta inválida mantém incerteza e recuperação posterior; não cria outra identidade de pagamento. Valor/identidade divergente produz conflito, nunca confirmação.

Worker usa leases persistidos de 15 segundos e versão para impedir gravação por execução vencida. Cada fase tem até cinco execuções, com esperas 2/4/8/16 segundos; esgotamento exige reenvio explícito da mesma chave após cooldown de pelo menos 30 segundos. A quinta aquisição já persiste cooldown conservador caso o processo caia. Leituras não reiniciam contadores. Reinício mantém estados, contadores e leases. Pedido admitido não volta a validar expiração ou catálogo.

Orçamento operacional do envio: oito segundos, além de reserva/leitura local; não é garantia de latência. GET de pagamento tem limite de um segundo e PUT dois, sem repetição imediata. Recuperação faz novas observações limitadas. Nenhuma transação SQLite atravessa HTTP. Não há transação distribuída nem promessa de processamento exatamente uma vez.

201 indica nova confirmação; replay confirmado retorna 200; trabalho pendente retorna 202 e Retry-After. Cliente deve conservar chave e revisão, consultar tentativa/pedido e reenviar a mesma chave quando necessário. Futuro frontend só deve limpar o carrinho após conhecer a admissão do pedido, preservando referência para consultar seu resultado; nunca apenas por iniciar o envio.

## Estrutura e persistência

- `services/orders/checkout.py`: orquestração; `checkout_models.py` e `checkout_routes.py`: contratos e transporte.
- `services/orders/order_repository.py`: reserva, admissão, leases e transições condicionais; `worker.py`: recuperação periódica.
- `services/orders/payment_client.py`: cliente tipado, sem redirecionamento ou proxy de ambiente.
- `services/payments/models.py`, `repository.py`, `routes.py`: autorização simulada durável.
- `foundation/storage.py`: transações locais curtas com conferência da identidade.

Schema continua na versão 1: tabelas previstas de tentativas/pedidos/autorizações foram aproveitadas, sem migração ou limpeza. Bancos privados continuam em `var/<store_id>/<service>/<service>.sqlite`. Falha de persistência não retorna sucesso fictício. Snapshot, pedido e pagamento sobrevivem ao reinício pelo armazenamento existente.

Readiness de pedidos agora verifica catálogo, pagamentos, repositório e worker realmente iniciado; liveness continua independente. Scope foundation é mantido por compatibilidade e não certifica compra completa ou sessão web. Compose e lançador voltam a fornecer token/URL de pagamentos ao serviço de pedidos. Não há montagem de bancos privados entre serviços.

## Execução — PowerShell

Na raiz, usando ambiente já preparado. Para roupas, três terminais:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
.\.venv\Scripts\python.exe tools/lps.py service clothing --service payments
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
```

Encerre os três e substitua clothing por food para alimentos. Não apague bancos ou segredos. `run clothing --dev` e `run food --dev` incluem frontend, cuja instalação continua pendente.

Prepare `$headers`, `$store` e `$review` com os exemplos de [revisão](revisao-etapa5a.md); alimentos exige uma janela futura obtida do servidor. Após receber a revisão:

```powershell
$key = [guid]::NewGuid().ToString()
$headers['Idempotency-Key'] = $key
$command = @{store_id=$store; review_id=$review.review_id} | ConvertTo-Json
$result = Invoke-RestMethod 'http://127.0.0.1:8002/internal/v1/orders' -Method Post -Headers $headers -ContentType 'application/json' -Body $command
Invoke-RestMethod "http://127.0.0.1:8002/internal/v1/order-attempts/$key" -Headers $headers
if ($result.order_id) { Invoke-RestMethod "http://127.0.0.1:8002/internal/v1/orders/$($result.order_id)" -Headers $headers }
# Se a resposta se perder, conservar $key e $command; não gerar outra chave.
```

Os comandos são instruções reproduzíveis; não foram executados por HTTP nesta etapa devido ao bloqueio abaixo.

## Evidências e limitações

`python tools/test_backend.py --offline`: **30 testes aprovados**. Exercitam modelos/componentes/fundação e fluxos com SQLite temporário real: variantes, totais/snapshots, expiração controlada, conflitos, reenvios, resposta perdida, reinício do orquestrador, falhas de armazenamento, limites de recuperação, fencing e concorrência por threads. Respostas de pagamento incompletas/divergentes são rejeitadas.

Os testes offline de fluxo usam adaptadores assíncronos imediatos explicitamente locais. Não validam escalonamento asyncio, timeout real, sockets, HTTP entre processos ou worker em execução. Suítes correspondentes foram preparadas em `tests/checkout/test_workflow.py` e `test_http.py`, sem declaração de aprovação.

Compilação Python (`compileall`) concluída sem erros. Coleta estática encontrou 66 testes ativos, sem executá-los integralmente. Conferência do inventário pré-5B aprovou os 68 hashes preservados. Essas verificações não substituem os testes pendentes de integração.

`python tools/test_backend.py` verifica socketpair antes da suíte integral: neste ambiente, o accept interno do Python expira ao criar o loop assíncrono. Runner encerra com código 2 e informa que a suíte não executou, em vez de travar ou aprovar por omissão. Os 48 testes da etapa 5A são evidência histórica, não regressão integral executada agora.

Pendências: executar suíte integral em ambiente com loopback funcional; instalação Python limpa; Compose real; dependências/build/lint/typecheck do frontend. Não houve nova tentativa npm equivalente, instalação de Docker ou alteração global. Protótipo anterior e cópia pré-5B com inventário estão em history; nenhum segredo/banco foi copiado para o histórico.

Próximo bloco recomendado: intermediário Next.js com sessão anônima, catálogo/carrinho/checkout e consulta de pedidos. Antes de declarar integração aprovada, resolver o bloqueio de execução e rodar a suíte HTTP/worker. Bloco final: validação ponta a ponta das duas lojas, ambiente reproduzível e documentação acadêmica consolidada.
