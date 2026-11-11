# Diagnóstico do repositório

> Nota de 08/11/2026 — etapa 2: diagnóstico da etapa 1 preservado como registro do código analisado, não da arquitetura-alvo. A conferência documental/código desta etapa confirma servidor stdlib, configurações Básica/Premium, ausência dos novos campos e frontend estático. FastAPI, sessão, novas variantes e recuperação são planos em [arquitetura-atual.md](arquitetura-atual.md), não implementações. Nenhum teste funcional foi repetido nesta etapa; o resultado abaixo pertence à etapa 1. As propostas e pendências históricas deste diagnóstico são substituídas pelas decisões atuais em [decisoes-e-etapas.md](decisoes-e-etapas.md).

## Base analisada e método

Análise local em 08/11/2026 dos arquivos de aplicação, configuração, dependências, documentação e testes. Não foram instaladas dependências nem modificados código, configurações de produto ou infraestrutura. Não houve auditoria de vulnerabilidades ou consulta a versões mais recentes das bibliotecas.

## Estrutura e dependências

| Área | Evidência | Situação |
|---|---|---|
| Vitrine | `apps/store-ropa/src/app/page.tsx` | Uma página cliente que importa catálogo TypeScript e renderiza imagens, descrição e preço |
| Dados da vitrine | `packages/catalog-module/products.ts` | Tipo Product e 28 itens de exemplo; sem tamanho, cor ou informações alimentares |
| Frontend | `apps/store-ropa/package.json` e `package-lock.json` | Next 15.3.1; React/React DOM ^19; TypeScript ^5; Tailwind ^4; ESLint ^9. Há lockfile local |
| Configuração web | `tsconfig.json`, `next.config.ts`, `layout.tsx`, CSS e ESLint | Alias para packages; strict desativado; metadados padrão; idioma en; fontes Google e imagens remotas |
| Backend | `services/server.py` | Biblioteca padrão Python; servidor HTTP parametrizado para catalog, orders ou payments |
| Componentes | `lps/components.py` | Protocols Pricing e Payment; preço regular/desconto Pix; Pix/cartão simulados; fábricas |
| Variabilidade | `lps/features.py`, `configurations/basic.json` e `premium.json` | Seleção em inicialização, features obrigatórias, meios de pagamento e dependência desconto → Pix |
| Dados backend | Lista PRODUCTS e SQLite de pedidos | Dois produtos fixos; pedidos armazenados como JSON, sem esquema de domínio versionado |
| Implantação | `Dockerfile` e `compose.yaml` | Uma imagem Python 3.11-slim; três containers/portas; dependências HTTP e volume exclusivo de pedidos; frontend fora do Compose |
| Testes | `tests/test_lps.py` | unittest sem dependências adicionais; dois métodos com cenários de ambas as configurações |
| Documentação | README raiz, README Next.js e docs anteriores | Orientada a Básica/Premium; README raiz contém caracteres substituídos por `?`; README da aplicação é genérico |

Não há manifesto de dependências Python porque o backend usa apenas biblioteca padrão. Não há workspace JavaScript na raiz nem pacote independente configurado para catalog-module: o reaproveitamento atual é por importação de arquivo via alias.

## O que foi verificado

Comando: `python -m unittest discover -s tests -v` → **2 testes aprovados**, com subcenários. Confirma regras inválidas selecionadas, cálculo Pix para Básica/Premium, cartão recusado/aceito, criação e leitura em SQLite, quantidade negativa rejeitada e HTTP 503 quando catálogo fica indisponível.

Os testes iniciam servidores HTTP em threads no mesmo processo. Verificam comunicação real por sockets, mas não validam implantação em processos separados, Docker, frontend ou reinício do serviço preservando pedidos. A consulta ao banco é verificada durante a execução, não após reinicialização.

Ambiente: Python 3.11.0, Node 24.15.0 e npm 11.12.1 disponíveis. `node_modules` ausente. Docker e Git não foram encontrados pelo shell. Build, lint e navegação do frontend e subida do Compose **não foram executados**. A compatibilidade do script `next lint` com as dependências deve ser verificada na etapa de preparação; não há resultado de lint nesta análise.

## O que pode ser reaproveitado

- Estrutura Next.js, grade de produtos, estilos e alias de componentes compartilhados como ponto de partida visual.
- Comunicação HTTP entre catálogo, pedidos e pagamentos; timeout e resposta de indisponibilidade.
- Valores inteiros em centavos e cálculo de preço no servidor.
- Componentes com contratos explícitos e fábricas; padrão de validação de configuração antes de iniciar os serviços.
- Persistência SQLite, containers e testes como base de evolução, sem assumir que já atendem aos novos contratos.

O frontend e o backend têm catálogos diferentes e desconectados. O tipo Product pode orientar a apresentação, mas o backend deve ser a fonte de preço e de combinações permitidas. Reaproveitar não significa manter dados duplicados como fontes de verdade.

## Lacunas para roupas e alimentos

| Lacuna | Impacto | Tratamento proposto |
|---|---|---|
| Apenas Básica/Premium | Variabilidade atual não demonstra os dois domínios solicitados | Configurações roupas/alimentos e novas restrições |
| Sem tamanho/cor e SKU | Não identifica a combinação comprada | Variantes explícitas no catálogo e no pedido |
| Sem dados alimentares | Loja de alimentos não se diferencia | Metadados alimentares e apresentação específica |
| Sem agenda | Não há escolha/validação de entrega | Janelas oferecidas pelo servidor, obrigatórias em alimentos |
| Sem detalhe, carrinho e checkout | Fluxo do cliente termina na vitrine | Fluxo compartilhado com pontos de extensão |
| Pedido aceita um produto por requisição | Não atende ao carrinho proposto | Lista de itens e totalização; preservar snapshot |
| Sem consulta visual de pedido | Apenas endpoint por ID | Tela de confirmação e consulta |
| Validação parcial | JSON/configuração fora do formato esperado e erros de banco não têm tratamento completo | Contratos e erros previsíveis; testes de entradas inválidas |
| Sem identificação da loja nos dados | Alternar configuração reutiliza banco e catálogo | Isolar implantação/dados por loja e persistir identificação no pedido |
| Sem autenticação, idempotência ou recuperação distribuída | Protótipo não serve como loja real | Ambiente demonstrativo e escopo explícito; revisar falhas antes de integrar pagamento real |

Não existe estoque por combinação. O comentário anterior de conversa sobre estoque próprio foi uma proposta, não uma implementação nem uma exigência do professor. Controle de estoque será decisão explícita de escopo.

## Limitações relevantes

Pagamentos sempre simulam aprovação. Autorizar antes de gravar o pedido pode deixar inconsistência se a gravação falhar. Não há estados de falha persistidos, reconciliação ou transação distribuída. Health informa identidade/configuração, mas não verifica prontidão das dependências. Compose declara ordem de início, sem verificação de prontidão. Não há isolamento atual de lojas no mesmo banco.

Imagens externas e fontes podem depender de rede; a demonstração precisa de dados e recursos visuais locais ou de um procedimento que declare essa dependência. Não há evidência de acessibilidade, desempenho ou funcionamento completo no navegador. Esses itens serão verificados na implementação, sem supor que já funcionam.
