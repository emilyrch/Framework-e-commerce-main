# Requisitos, rastreabilidade e validação futura

Evidência posterior: [capturas reais de roupas e compra confirmada](capturas-roupas-2026-11-10.md). A execução manual do navegador foi bem-sucedida para roupas; demais bloqueios e verificações anteriores mantêm seu alcance.

Última rodada: [finalização](finalizacao-compra-e-entrega.md#evidências-atuais), com 43 testes offline, 16 web e 24 vetores aprovados. Typecheck/lint aprovados; HTTP/E2E bloqueados e build falhou por acesso negado. Os resultados antigos abaixo não certificam o incremento atual.

Evidência mais recente em [imagens e recomendações](recomendacoes-e-imagens.md#validação-e-limites): 43 offline, 13 web, 24 vetores, typecheck e lint aprovados. HTTP completo/E2E bloqueados nesta sessão; build falhou por acesso negado no SWC. Resultados anteriores não validam as novas mudanças.

Atualizado em 10/11/2026 após homologação real: **67 testes backend completos (HTTP/asyncio/worker), 31 offline, 10 testes web e 24 vetores de configuração aprovados**. Frontend build/lint/typecheck, E2E Next.js, navegador, instalação Python limpa e Compose continuam bloqueados. O loopback funcionou nesta execução. [Estado final e roteiro](entrega-final.md).

## Exigências e escolhas

| ID / requisito | Origem | Implementação planejada | Evidência futura de validação |
|---|---|---|---|
| AC01 — Modelar e implementar LPS | Professor — obrigatório | Núcleo compartilhado, domínio XOR, configurações validadas e componentes selecionados | Modelo, matriz de features, T01 e demonstração derivando duas lojas do mesmo código |
| AC02 — Usar microsserviços | Professor — obrigatório | Catálogo/pedidos/pagamentos em três processos com APIs e dados privados | Diagrama e execução por processos, chamadas HTTP, testes T08/T11/T16/T18 |
| AC03 — Usar componentes de software | Professor — obrigatório | Contratos de configuração, seleção, entrega, totais e pagamento; componentes visuais | Diagrama/contratos, testes unitários e integração T01–T12/T17 |
| CT01 — Python sugerido | Professor — sugestão | Escolha do projeto: backend Python/FastAPI | Manifesto e ambiente verificável em T18; não tratar a linguagem como obrigação |
| CT02 — Agentes opcionais | Professor — opcional; exclusão decidida pelo projeto | Nenhum agente/serviço/modelo de IA | Inventário de dependências/processos do MVP, sem inventar critério acadêmico de ausência |

## Requisitos funcionais e critérios de aceitação

Os RFs abaixo são decisões do projeto confirmadas pelo usuário e detalhamentos técnicos adotados nesta etapa. Não são requisitos adicionais atribuídos ao professor.

| ID / requisito | Origem | Implementação planejada | Critério de aceitação / evidência futura |
|---|---|---|---|
| RF01 — Derivar roupas/alimentos | Decisão do projeto | Manifesto fechado, hash comum, bootstrap/registro de componentes | T01/T14/T16: duas lojas do mesmo código; configurações inválidas/identidade divergente não ficam prontas; basic/premium não selecionáveis pelo MVP |
| RF02 — Catálogo e detalhe da loja | Decisão do projeto | Catálogo como fonte única; API implementada, UI futura | T02: ≥6 produtos por loja na etapa 4, com categorias; lista/detalhe HTTP e 404 verificados; arquivo de outra loja impede startup. Estados visuais continuam pendentes |
| RF03 — Combinação de tamanho/cor | Decisão do projeto | combination_id pertencente ao produto e habilitado | T03: aceitar M/preta e G/azul; recusar M/azul não cadastrado, outra roupa, ausente ou desabilitado; UI não promete estoque |
| RF04 — Informações alimentares | Decisão do projeto | Ingredientes, união de alergênicos e nutrição com campos/unidades do contrato | T04: exibir dados fictícios, diferenciar known vazio de unknown; recusar catálogo incompleto/inconsistente; sem tamanho/cor |
| RF05 — Carrinho persistente por loja | Decisão do projeto | CartStore no navegador, namespace e versão, seleções normalizadas | T05/T14: adicionar/alterar/remover múltiplos itens, sobreviver a reload, não misturar lojas; sem endereço/segredo no localStorage; vazio bloqueia checkout |
| RF06 — Agenda obrigatória em alimentos | Decisão do projeto | ScheduledDelivery e GET interno implementados; snapshot na revisão 5A | T06: futuros/habilitados e timezone testados; ausente/desconhecido/desabilitado/passado recusados. Componentes mantêm teste no limite exato; admissão/UI/recuperação ainda futuros |
| RF07 — Checkout/endereço e validação estrita | Decisão do projeto | Sem login, endereço comum, itens únicos 1–50, quantidade 1–100 | T07: aceitar quantidades 1/100; rejeitar 0/101/fração/bool, campos incompatíveis/null, duplicados, endereço inválido e corpo excessivo; roupas sem prazo/frete |
| RF08 — Revisão de valores e Pix simulado | Decisão do projeto | Revisão durável/totalização implementadas; método é apenas metadado, sem autorização | 5A: HTTP real do catálogo, rejeição de preço do cliente, snapshot/TTL de dez minutos/rollback/restart. Revalidação de preço na admissão e pagamento ainda futuros |
| RF09 — Pedido com snapshot e estados | Decisão do projeto | Admitir antes do pagamento; múltiplos itens, endereço, seleção/agenda e valores preservados | T08/T11/T15: 201 somente após confirmed durável; 202 quando intermediário; GET não depende de catálogo atual; carrinho só removido após confirmação observada |
| RF10 — Consulta vinculada à sessão | Decisão do projeto | Cookie assinado, IDs aleatórios, filtro por loja/dono | T13/T15: dono consulta após restart com cookie/segredo estável; outra sessão/loja/ID inexistente → 404; sem cookie → 401; sem exposição de token |
| RF11 — Estados de UI e falhas | Decisão do projeto | Carregamento/vazio/validação/processamento/recuperação/erro | T11/T17: falhas mantêm carrinho e tentativa, sem sucesso falso; seis consultas automáticas no máximo; campos com rótulos e mensagens úteis |
| RF12 — Reenvio sem pedido duplicado | Decisão do projeto | Chave por loja/sessão, hash, transações UNIQUE e revisão consumida uma vez | T09/T11: mesma chave/corpo retorna mesmo pedido; diferente → 409; concorrentes convergem; duas chaves/mesma revisão não duplicam; GET chave recupera resultado |
| RF13 — Pagamento durável por pedido | Decisão do projeto | SQLite privado, UNIQUE loja/order_id, PUT idempotente e GET interno | T10/T12/T15: repetição/concorrência devolvem mesmo payment_id; valor divergente → 409; restart preserva aprovação; não expor API ao navegador |

## Requisitos não funcionais

| ID / requisito | Origem | Implementação planejada | Critério de aceitação / evidência futura |
|---|---|---|---|
| RNF01 — Separação e comunicação | Decisão do projeto para atender AC02 | FastAPI em processos próprios; apenas HTTP entre donos | T16/T18: processo de catálogo pode parar sem derrubar leitura local de pedido; nenhum serviço abre banco alheio |
| RNF02 — Reuso e composição | Decisão do projeto para atender AC01/AC03 | Bootstrap e registro único de componentes/DTOs e UI | T01/T03/T04/T06: contratos testados por implementação; fluxo comum sem duplicar aplicação; revisão de código futura |
| RNF03 — Ambiente reproduzível | Decisão do projeto | Dependências fixadas, Compose com frontend e três serviços e execução local documentada | T18: derivar sequencialmente ambas as lojas por ambos os caminhos; registrar comandos/versões e limitações reais |
| RNF04 — Durabilidade e isolamento | Decisão do projeto | SQLite separados, metadata e schemas, volumes/diretórios por loja | T14/T15: reiniciar sem perder revisão/tentativa/pedido/autorização; banco antigo/outra loja recusado; nenhuma limpeza automática |
| RNF05 — Robustez e limites | Decisão do projeto | Timeouts/orçamentos, retries limitados, CAS/leases e erros comuns | T07/T09–T12: falhas injetadas em cada fronteira, sem sucesso/recusa inventados e sem transação aberta em HTTP; contadores sobrevivem a restart |
| RNF06 — Usabilidade básica | Decisão do projeto | Componentes com labels/foco e layout responsivo | T17: fluxo por teclado, indicação de simulação/fictício, tela de 360 px sem rolagem horizontal principal |
| RNF07 — Testabilidade | Decisão do projeto | Relógio e gateways substituíveis, testes de contrato, integração/processos e navegador | T01–T18: positivos/negativos; cenários legados separados; resultados só marcados executados após execução real |
| RNF08 — Fronteira anônima local | Decisão do projeto | Cookie HttpOnly/SameSite, Origin, segredos por loja, no-store e cabeçalhos recompostos | T13/T14: tentativa de forjar sessão/header/origem recusada; resposta/cache/logs sem credenciais/endereço completo; uso local, sem alegação de segurança pública |
| RNF09 — Identidade/prontidão | Decisão do projeto | Store/hash em chamadas e verificações; liveness independente | T16: divergência de hash/banco/dataset → not_ready; dependência indisponível → 503; leitura persistida continua possível com identidade válida |

Sem SLA de latência/carga/alta disponibilidade. Os timeouts e limites são políticas de operação/teste do MVP, não metas de performance nem garantias de conclusão. Consulta sem login continua protegida pela sessão anônima; identificadores aleatórios não substituem esse filtro.

## Catálogo de cenários futuros

| ID | Cenário positivo | Cenários negativos/de falha | Nível/evidência futura |
|---|---|---|---|
| T01 | Validar dois manifestos e mesmos vetores de hash Python/TS | Domínio duplo, feature faltante/extra/duplicada, campo desconhecido, hash divergente | Unitário/contrato + bootstrap |
| T02 | Listar/detalhar duas lojas com fonte única | Produto desconhecido, catálogo vazio, IDs repetidos, kind/dataset/loja errados | Catálogo + UI |
| T03 | Selecionar duas combinações cadastradas da roupa | Combinação inexistente, de outro produto, desabilitada ou ausente | Componente + API + navegador |
| T04 | Alimentos com ingredientes e medidas; known vazio e unknown distintos | Nutriente negativo/NaN, unidade inválida, metadado ausente, allergens inconsistente, combination_id em alimento | Carga + DTO + UI |
| T05 | Carrinho com dois itens persiste no reload e permite edição | Vazio, limite excedido, schema/hash incompatível, aba altera carrinho antes da confirmação | Unidade CartStore + navegador |
| T06 | Janela futura do servidor e snapshot no pedido | Janela ausente/desabilitada/desconhecida/passada; igualdade com agora; roupas envia slot; nenhuma disponível | Política com relógio + API |
| T07 | Endereço e quantidades limites válidos; revisão de total | Campos extras, preço enviado, quantidade 0/101/bool/fração, soma excessiva; preço muda, revisão expira ou pertence a outra sessão | Schema + totais + integração |
| T08 | Compra normal de cada loja com vários itens; consulta de snapshot | Não limpar carrinho ao receber 202; mudança de preço exige nova revisão; valores não vêm do cliente | Processos HTTP + navegador |
| T09 | Mesmo K/corpo retorna mesmo pedido | Mesmo K/outro review; simultâneos com K igual; chaves distintas para mesma revisão; rejeição persistida repetida | Integração concorrente + contagem de linhas |
| T10 | Mesmo order_id autoriza uma vez e repete payment_id | PUTs concorrentes; outro valor/moeda/método; resposta perdida depois do commit | Pagamento + banco + injeção de falha |
| T11 | Recuperar validating/pending/unknown com mesma identidade | Falha antes/depois de cada commit, catálogo fora, pagamento fora, GET 404 com PUT atrasado, queda após confirmed, agenda passa após admissão | Integração com interrupção/restart; inspecionar pedidos/pagamentos por APIs e contagens do dono |
| T12 | Recuperação respeita lease/CAS e cinco tentativas | Lease expirado/requisições concorrentes, cooldown, retorno conflitante; reinício não zera contador nem regride confirmed | Unitário de estados + integração |
| T13 | Sessão dona recupera por chave/ID após reinício | Outra sessão, cookie ausente/adulterado/expirado, Origin externo, header interno forjado e acesso direto sem credencial | Integração de fronteira + navegador |
| T14 | Alternar lojas sequencialmente mantém dados e carrinhos próprios | Store_id no corpo forjado, volume de outra loja, mesmo ID/key em contextos distintos, configuração troca com trabalho pendente | Isolamento de processos/dados/browser |
| T15 | Reiniciar cada serviço preserva revisão/tentativa/pedido/autorização e acesso | Abrir orders.db legado, schema desconhecido, segredo perdido; catálogo muda após confirmação sem mudar snapshot | Teste de reinício com diretório durável |
| T16 | live/ready e configuração coerentes nos quatro processos | Config/hash diferente, banco sem acesso, dependências fora, worker inativo; ready não veda GET de pedido já persistido | Smoke/integração de readiness |
| T17 | Fluxos completos e consulta por teclado/tela estreita | Vazio, carregamento lento, erro, pending, preço alterado e alergênicos desconhecidos | Teste manual documentado e navegador automatizado conforme ambiente |
| T18 | Subir ambas as lojas local e Compose a partir do mesmo código | Variáveis ausentes, portas ocupadas, volume/schema errado, legado ativo por engano | Ambiente limpo + guia de reprodução e logs sanitizados |

Comprovar ausência de duplicação por IDs retornados **e** contagem de registros em testes do respectivo serviço. A aplicação normal nunca lê banco de outro dono; os testes podem usar repositórios/fixtures isolados para verificar invariantes. Simulações de falha são infraestrutura de teste, não botões de recusa/pagamento extra no produto.

## Histórico da validação documental da etapa 2

Conferência documental executada nesta etapa: 21 blocos JSON parseados; duas configurações verificadas quanto a conjuntos de features, identidade distinta, moeda/política de pagamento e fuso; links locais e delimitadores Markdown conferidos; IDs RF01–RF13, RNF01–RNF09 e T01–T18 presentes. Comparação SHA256 dos 30 arquivos inventariados fora de docs confirmou conteúdo intacto. Essas verificações são da documentação, não testes da futura implementação.

Foram escritos cinco diagramas Mermaid atuais (features, arquitetura, componentes e duas sequências), além do diagrama histórico preservado. Os blocos foram contabilizados, mas não renderizados. Não se executaram testes funcionais nesta etapa, não se subiu FastAPI/Compose e não se verificou a futura UI. Renderização dos diagramas e execução dos cenários continuam pendentes de validação real.

## Validação da fundação na etapa 3

Resultados executados e limitações em [fundacao-etapa3.md](fundacao-etapa3.md): 11 testes ativos (configuração, 24 vetores Python/TS, bancos, launcher e processos), prontidão/autenticação/isolamento/restart e lógica de prontidão web via Node. Os cenários de compra continuam não implementados. Build/lint/typecheck web foram tentados mas não concluídos por falta de pacotes; Compose não executado por ausência de Docker. Esses resultados não significam aprovação integral de T01–T18.

## Evidência da etapa 4

`python -m unittest discover -s tests -t . -v`: **32 testes aprovados**, 21 em tests/catalog e 11 em tests/foundation. Cobre catálogo carregado/imutável, revisão comercial, tipos/uniões/limites/duplicações, alergênicos, permissões por papel, HTTP real nas duas lojas, totais internos e janela IANA com relógio fixo. Os casos são subcenários de T02/T03/T04/T06/T07/T16; partes de navegador/compra desses IDs não estão aprovadas. Testes usam somente temporários para bancos/segredos/dados alterados.

Uma nova instalação npm pelo lockfile falhou com EACCES e erro de encerramento npm. Nenhuma repetição equivalente; Next.js/build/lint/typecheck continuam não verificados. Instalação Python limpa e Compose permanecem pendentes. Não houve mudança nas exigências do professor nem declaração de MVP pronto.

## Evidência da etapa 5A

`python -m unittest discover -s tests -t . -v`: **48 testes ativos**, 16 novos em tests/reviews e regressão dos 32 anteriores. Comunicação real catálogo→pedidos nas duas variantes; DTOs, papéis/dono interno/loja/hash, TTL com relógio fixo, snapshots, janelas e persistência/restart; catálogo malformado/indisponível/redirecionamento, retries e falha de commit/bloqueio de banco. Pedidos/attempts permanecem vazios e não há pagamento. Os testes usam apenas temporários, não a demonstração.

Isso cobre partes de T06/T07/T13/T15/T16 e RF08; **não** aprova proteção de sessão web, T08 de compra, T09/T10 de idempotência/pagamento ou T11/T12 de recuperação. A alteração da regressão de readiness é intencional: pedidos não depende de pagamentos em 5A; o agregador web continua uma verificação de infraestrutura, não de negócio. Frontend/build/lint/typecheck, instalação Python limpa e Compose seguem pendentes. Nenhuma nova tentativa npm nesta etapa.
