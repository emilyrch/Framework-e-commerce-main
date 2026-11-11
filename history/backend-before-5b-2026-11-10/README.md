# LPS de e-commerce — catálogo e revisão persistida

Projeto acadêmico de Linha de Produto de Software: **roupas** com tamanho/cor e **alimentos** com informações alimentares/agendamento. LPS, microsserviços e componentes são exigências do professor; tecnologias e recorte do MVP são escolhas do projeto. Sem agentes de IA.

**Etapa 5A:** catálogo funcional das duas lojas, janelas internas de entrega e revisão persistida da compra. A revisão resolve produtos por HTTP, valida entrega, calcula e grava snapshots com expiração de dez minutos. **Não é pedido confirmado.** Sem sessão de navegador, frontend integrado, carrinho, checkout, admissão/pedido, autorização ou recuperação. O MVP não está pronto.

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

Frontend em http://127.0.0.1:3000 quando suas dependências estiverem disponíveis; serviços locais em loopback 8001/8002/8003. Para catálogo/revisões sem frontend ou pagamentos, em dois terminais:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
```

Troque clothing por food nos dois terminais para alimentos. Pedidos/pagamentos têm persistência privada em `var/<store_id>/<service>/<service>.sqlite`; pagamentos segue somente como infraestrutura e não é chamado por 5A. Reiniciar conserva dados/segredos; bancos legados/de outra loja são recusados.

O catálogo pode ser iniciado sozinho pelo primeiro comando. APIs: GET `/internal/v1/products`, GET `/internal/v1/products/{id}` (credencial web) e POST `/internal/v1/selections/resolve` (credencial orders). Ambas exigem identidade/hash; tokens não devem ir ao navegador. [Chamadas PowerShell completas e exemplos para cada loja](docs/catalogo-etapa4.md).

Pedidos agora oferece GET `/internal/v1/delivery-slots` e POST `/internal/v1/reviews` com credencial web→pedidos. O POST exige dono interno X-Session-Owner validado, **simulando** o futuro intermediário; isso não implementa sessão de navegador. Não há consulta/consumo de revisão. [Chamadas PowerShell, persistência e limites de confiança](docs/revisao-etapa5a.md).

Dados ativos em `demo-data/clothing/products.json` e `demo-data/food/products.json`, carregados e congelados no startup. Imagens usam um fallback SVG local existente, sem fotos de terceiros. Revisão comercial ignora formatação/ordem de produtos e muda com preços, combinações ou informações alimentares.

Compose preparado, **ainda não executado** neste ambiente:

```powershell
docker compose --env-file .local/roupas-demo.env -p lps-roupas-demo up --build
# Para alimentos, após encerrar a primeira loja:
docker compose --env-file .local/alimentos-demo.env -p lps-alimentos-demo up --build
```

Só a porta do frontend é publicada. Não usar `down -v` no reinício normal. Instruções completas, armazenamento, Dockerfiles e alcance de saúde em [fundação da etapa 3](docs/fundacao-etapa3.md).

## Verificações

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
node --experimental-strip-types apps/store-ropa/scripts/check-config.ts
.\.venv\Scripts\python.exe tools/lps.py build-web clothing
npm.cmd --prefix apps/store-ropa run lint
npm.cmd --prefix apps/store-ropa run typecheck
```

Resultado local: **48 testes ativos aprovados**, incluindo 16 novos de revisão/cliente HTTP e regressão dos 32 anteriores. Testados snapshots, TTL controlado, janelas, autenticação/dono interno, falhas de rede/armazenamento e reinício. Readiness `scope: foundation` inclui carga do catálogo e repositório/serviço de revisão em pedidos; não depende de pagamentos em 5A nem declara sessão web/recuperação.

Limitações mantidas: frontend sem integração e build/lint/typecheck pendentes; instalação Python limpa e Compose não executados. Não houve nova tentativa npm sem evidência de mudança do bloqueio, nem stubs ou instalação automática do Docker. Backend validado com versões fixadas/preexistentes. Evidências atuais em [revisao-etapa5a.md](docs/revisao-etapa5a.md); registros anteriores em docs.

Histórico intacto em [history/prototype-2026-11-08](history/prototype-2026-11-08/HISTORY.md), com inventário. Teste legado separado em `tests/legacy`. Arquitetura, contratos, critérios e próximos passos no [índice de docs](docs/README.md).
