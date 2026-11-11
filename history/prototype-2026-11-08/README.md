# LPS de e-commerce

Agentes de IA são opcionais e ficam fora do escopo da implementação inicial. O foco é a modelagem e implementação da LPS com microsserviços e componentes de software.

Prot?tipo acad?mico de Linha de Produto de Software com microsservi?os Python e componentes reutiliz?veis. A vitrine Next.js original est? preservada em `apps/store-ropa`.

## Evid?ncias dos requisitos

| Requisito | Implementa??o |
|---|---|
| Modelagem da LPS | [Features, restri??es, arquitetura e rastreabilidade](docs/arquitetura.md) |
| Implementa??o da LPS | Configura??es B?sica e Premium em `configurations` e valida??o em `lps/features.py` |
| Microsservi?os | Cat?logo, pedidos e pagamentos com comunica??o HTTP e processos independentes |
| Componentes | Contratos de pre?o e pagamento com implementa??es substitu?veis em `lps/components.py` |
| Python sugerido | Backend Python 3.11+, sem depend?ncias externas |

## Executar localmente

Na raiz do reposit?rio, execute em tr?s terminais separados:

```powershell
python -m services.server catalog --port 8001 --config configurations/basic.json
python -m services.server payments --port 8003 --config configurations/basic.json
python -m services.server orders --port 8002 --config configurations/basic.json
```

Para derivar a Premium, encerre os tr?s processos e substitua `basic.json` por `premium.json` em todos os comandos. Todos os servi?os devem usar a mesma configura??o.

Com Docker Compose:

```powershell
$env:PRODUCT_VARIANT = "premium"
docker compose up --build
```

Use `basic` para a loja b?sica. O volume `orders-data` preserva os pedidos. Use volumes distintos para lojas independentes.

## Roteiro de demonstra??o

```powershell
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8001/products
$pedido = Invoke-RestMethod http://localhost:8002/orders -Method Post -ContentType 'application/json' -Body '{"product_id":"1","quantity":1,"payment_method":"pix"}'
$pedido
Invoke-RestMethod "http://localhost:8002/orders/$($pedido.id)"
```

Na B?sica o pedido custa 8990 centavos e cart?o ? rejeitado. Na Premium o mesmo pedido Pix custa 8541 centavos; cart?o ? aceito e custa 8990. Troque `payment_method` por `card` para demonstrar. Remover Pix de uma configura??o com desconto impede a inicializa??o e demonstra a restri??o de features.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Cobrem configura??es inv?lidas, fluxo HTTP das duas variantes, persist?ncia e consulta, rejei??o de cart?o na B?sica, quantidade inv?lida e falha de depend?ncia.

Pagamentos s?o simulados. A vitrine original ainda usa dados TypeScript locais e n?o est? integrada ?s APIs. Veja limites e pr?ximos incrementos em [docs/arquitetura.md](docs/arquitetura.md). O README anterior foi preservado em [docs/historico-original.md](docs/historico-original.md).
