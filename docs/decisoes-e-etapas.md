# Decisões, migração e próximas etapas

Estabilização adicional: [compra e entrega](finalizacao-compra-e-entrega.md). Sessão inicial compartilhada, consultas automáticas limitadas, configurador visual e painel de serviços implementados. O roteiro do professor, itens 5.4/6.1/6.4/8, foi conferido no PDF; capturas e homologação permanecem pendentes.

Decisão adicional 10/11/2026: dez peças com imagens locais; recomendações determinísticas sem IA em microsserviço privado dedicado. Manifesto v1 mantido, extensão fixa comum. [Escopo, justificativa e limitações](recomendacoes-e-imagens.md).

Atualizado em 10/11/2026 após homologação real: **67 testes backend completos (HTTP/asyncio/worker), 31 offline, 10 testes web e 24 vetores de configuração aprovados**. Frontend build/lint/typecheck, E2E Next.js, navegador, instalação Python limpa e Compose continuam bloqueados. O loopback funcionou nesta execução. [Estado final e roteiro](entrega-final.md).

## Registro de decisões

| ID | Decisão | Estado / justificativa |
|---|---|---|
| D01 | Sem agentes de IA inicialmente | Confirmada; opcionais no enunciado |
| D02 | Produtos roupas e alimentos, mesmo núcleo/frontend | Confirmada; variabilidade de domínio explícita |
| D03 | Etapa 2 somente documentação; etapa 3 autorizada para fundação | Etapa 2 preservada como histórico; etapa 3 altera infraestrutura sem avançar para compra |
| D04 | Roupas/alimentos como único eixo ativo do MVP | Confirmada e detalhada; Básica/Premium vira histórico, não combinações comerciais ativas |
| D05 | Next.js/React/TS/Tailwind e backend Python/FastAPI | Implementada; migração para FastAPI realizada, instalação Python limpa pendente |
| D06 | Três serviços: catálogo, pedidos, pagamentos; agenda em pedidos | Confirmada; manter ownership e evitar serviço extra sem necessidade |
| D07 | Pix simulado, sem desconto ou dados bancários | Confirmada; preservar histórico de cartão/desconto fora do registro ativo |
| D08 | Uma loja por implantação, dados/segredos separados, demonstração sequencial | Confirmada; sem multitenancy nem mistura de bancos/carrinhos |
| D09 | Carrinho local persistente por loja; checkout sem login | Confirmada; revisão e tentativa preservadas em locais apropriados |
| D10 | Sem estoque/reserva nem capacidade de agenda | Confirmada; habilitação de combinação/janela não é estoque |
| D11 | Ingredientes/alergênicos/nutrição por porção, dados fictícios | Confirmada; campos e união known/unknown detalhados em contratos |
| D12 | Endereço comum; alimentos agenda futura em America/Sao_Paulo; roupas sem prazo | Confirmada; janelas fornecidas e validadas no servidor, snapshot no pedido |
| D13 | Consulta por sessão anônima, IDs imprevisíveis, intermediário Next.js | Confirmada; cookie assinado estável, filtro loja/dono; proteger fronteira interna |
| D14 | SQLite separado e durável em pedidos e pagamentos | Detalhamento escolhido; idempotência precisa sobreviver a restart, sem transação distribuída |
| D15 | Manifesto comum fechado/versionado e config_hash | Detalhamento escolhido; seleção no bootstrap e detecção de divergência em chamadas/readiness |
| D16 | Revisão durável, nova confirmação se preço/metadado relevante mudar | Detalhamento escolhido; evitar aceitar valor diferente sem consentimento |
| D17 | Idempotência por loja/sessão/chave e pagamento por loja/pedido | Detalhamento escolhido; UNIQUE, estados, leases, contador e retomada limitada |
| D18 | Ambiente local e Compose com os quatro processos | Confirmada; backends privados em Compose, execução sem Docker documentada |
| D19 | Catálogo validado/imutável e revisão comercial normalizada | Implementada na etapa 4; ordem de produtos/combinações e formatação não alteram revisão; conteúdo comercial altera |
| D20 | category obrigatória e imagens por fallback local próprio | Ajuste de contrato desta etapa; seis produtos por loja, sem fotos de terceiros nem rede obrigatória nos novos ativos |
| D21 | Permissões distintas de leitura e resolução | Web só lista/detalha; orders só resolve; ambos podem consultar prontidão. Não expor resolução no navegador |
| D22 | Revisão vinculada ao dono interno e persistida no schema 1 existente | Etapa 5A: credencial web→pedidos + cabeçalho hex64; TTL dez minutos; sem consulta/consumo ou migração |
| D23 | Histórico: pedidos não dependia de pagamento na etapa 5A | Revisão só usa catálogo; removidas dependência de prontidão e injeção de token de saída não utilizado. Reintroduzidas em 5B com autorização/recuperação reais do simulador |

| D24 | Fronteira web valida sucesso comercial e totais | Fechamento: respostas incompletas/inconsistentes viram 503; DTOs reais das variantes cobertos por teste Python→Node |
| D25 | Homologação não aprovada enquanto houver bloqueios | Comando tools/validate.py registra passed/failed/blocked; não substituir runtime ausente por stubs |

Fonte dos detalhes por assunto: [modelo-lps.md](modelo-lps.md), [arquitetura-atual.md](arquitetura-atual.md), [contratos-api.md](contratos-api.md), [recuperacao.md](recuperacao.md). Prazos e rubrica não fornecidos; não inventar requisitos acadêmicos.

## Destino das pendências da etapa 1

| Pendência antiga | Resolução nesta etapa |
|---|---|
| P01 — Básica/Premium | Histórico de níveis comerciais; migração planejada sem produtos legados ativos nem importação automática do banco antigo |
| P02 — Campos alimentares | Definidos explicitamente em contratos; known vazio ≠ unknown; sem conformidade regulatória declarada |
| P03 — Agenda | Política em pedidos, janelas habilitadas/futuras, sem capacidade, timezone definido |
| P04 — Estoque | Fora do MVP, inclusive por tamanho/cor |
| P05 — Compra | Carrinho persistido, endereço, Pix simulado e consulta vinculada à sessão; não consulta pública por ID |
| P06 — Pilha/serviços | FastAPI confirmado; três serviços e frontend atual preservados |
| P07 — Demonstração | Sequencial, com persistência separada por loja |
| P08 — Reenvio/falhas | Fluxo concreto em recuperacao.md, incluindo concorrência e reinício |
| P09 — Rubrica/prazo | Não informados; não bloqueiam estrutura executável, ajustar caso sejam fornecidos |

## Etapas e dependências

| Etapa | Depende de | Escopo/entrega | Critério de saída futuro |
|---|---|---|---|
| 1 — Diagnóstico | — | Registro da base e limitações | Concluído documentalmente; resultados históricos identificados |
| 2 — Modelagem/arquitetura | 1 + decisões do usuário | Features, derivação, contratos, componentes, falhas e aceitação | Esta documentação; não confundir com funcionalidades prontas |
| 3 — Estrutura executável e ambiente | 2 + solicitação futura de implementação | Bootstrap, apps FastAPI, schemas iniciais, health/ready, identidade/isolamento, frontend no Compose e caminho local | Mesma configuração nos processos, smoke de saúde, bancos corretos e comandos reproduzíveis; ainda sem compra completa |
| 4 — Catálogo e componentes de domínio | 3 | Carga/validação, DTOs e seleção de roupas/alimentos, entrega e totais | T01–T04/T06/T07 unitários e APIs de leitura/seleção |
| 5 — Revisão, pedidos e pagamentos recuperáveis | 4 | Persistência, sessão de ponta a ponta, revisão, admissão, autorização, worker e APIs de consulta | T07–T16 de integração pertinentes, com falhas e restart |
| 6 — UI compartilhada, carrinho e checkout | 4; confirmação depende de 5 | Extensões de domínio, persistência do carrinho, revisão, estados, retomada e consulta | Fluxos das duas lojas T05/T08/T13/T17 |
| 7 — Validação e demonstração | 5 + 6 | Testes consolidados, Compose/local e roteiro acadêmico | Matriz T01–T18 com resultados reais, limites e rastreabilidade |

As dependências indicam ordem técnica. A etapa 3 foi autorizada e implementada somente no recorte da fundação; próximas funcionalidades exigem o incremento posterior solicitado pelo usuário.

## Recorte adotado da etapa 3

Lista de escopo aprovada abaixo; implementação e verificação efetivas estão no guia da fundação. A instalação limpa, o frontend em execução e os containers ainda precisam de validação; não marcar estes itens como concluídos apenas por estarem no escopo.

1. Preservar explicitamente o protótipo antes da migração; separar entrada legada da entrada ativa, sem dados antigos no novo runtime.
2. Fixar versões compatíveis de Python/FastAPI/Pydantic/Uvicorn e registrar instalação/reprodução; conservar o lockfile frontend, avaliar build/lint sem atualização ampla não justificada.
3. Criar esqueleto dos três apps e infraestrutura compartilhada de configuração/erros/identidade. Materializar manifestos e schemas **somente quando a implementação for solicitada**.
4. Preparar SQLite privados com metadata/versionamento, tabelas/invariantes definidas e recusa de banco legado/outra loja; não implementar autorização/compra apenas para provar tabelas.
5. Fornecer frontend servidor capaz de ler configuração em runtime e conferir prontidão; preparar fronteira de credenciais e segredo estável de sessão, sem antecipar checkout completo.
6. Incluir frontend e serviços no Compose, volumes privados e manifesto somente leitura; definir launcher/guia local com quatro terminais e execução sequencial isolada.
7. Fazer smoke tests reais de inicialização, config inválida, hash divergente, banco errado, health/ready e persistência de metadata; atualizar docs com resultados e separar estes dos testes funcionais ainda futuros.

## Bloqueios reais e pontos a acompanhar

**Pendências reais após 5A:** frontend sem integração e sessão web inexistente; build/lint/typecheck, instalação Python limpa e Compose pendentes. Nenhuma tentativa npm repetida sem evidência de mudança do ambiente. Não há decisão funcional pendente para este escopo. 5B requer admissão por revisão/dono/loja, unicidade/idempotência, pagamento durável e recuperação, sem assumir que uma revisão já seja pedido.

Docker/Git foram novamente procurados na etapa 3 e não encontrados; `.git` ausente. Histórico por arquivo foi criado antes de substituir arquivos. Acesso online a pacotes falhou por restrições de rede e cache npm incompleto; não foi instalado Docker nem alterada configuração global. Conferência de YAML não é validação de containers. O guia da fundação registra o que foi realmente executado.

Pontos de atenção já resolvidos como limites, não novas perguntas: sessão perdida não tem recuperação; idempotência não deduplica novas compras de sessões distintas; configurações não trocam com transações intermediárias; não há garantia de entrega física nem processamento exatamente uma vez; ambiente não será publicado. Uma futura rubrica poderá exigir ajuste de evidências, sem bloquear este planejamento.
