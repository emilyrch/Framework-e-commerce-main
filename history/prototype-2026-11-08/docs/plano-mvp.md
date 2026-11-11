# Plano do MVP — baseline da etapa 2

Atualizado em 08/11/2026 após as decisões do usuário. Modelagem detalhada concluída em documentação; implementação ainda não iniciada. Este plano substitui as propostas pendentes da etapa 1, sem transformar escolhas do projeto em obrigações acadêmicas.

## Origem e escopo

Professor: LPS modelada e implementada, microsserviços e componentes obrigatórios. Python sugerido; agentes de IA opcionais. Não foram informados número de serviços, framework, quantidade de diagramas, rubrica, prazo ou implantação em cloud.

Projeto: duas lojas derivadas do mesmo núcleo/frontend — roupas com tamanho/cor por combinação e alimentos com informações alimentares/agendamento. Uma loja por implantação com dados separados; execução sequencial suficiente. Next.js/React/TypeScript/Tailwind; Python/FastAPI em três serviços; pagamento Pix inteiramente simulado. Sem IA inicialmente.

O [modelo de features](modelo-lps.md) é a fonte da variabilidade/configuração. A [arquitetura-alvo](arquitetura-atual.md) é a fonte dos componentes, serviços e armazenamento. Os [contratos](contratos-api.md), o [fluxo de recuperação](recuperacao.md) e a [matriz de validação](validacao.md) são as fontes dos detalhes técnicos/aceitação. Não repetir versões alternativas desses contratos neste plano.

## MVP demonstrável

Núcleo obrigatório: catálogo/detalhe, carrinho com vários itens persistido no navegador por loja, checkout sem cadastro com endereço simples, revisão dos valores, Pix simulado, criação e consulta do pedido pela sessão anônima. Quantidades inteiras 1–100; valores em centavos; totais no backend; sem frete e sem desconto.

Roupas: selecionar combination_id válido do produto, com tamanho/cor. Backend revalida; sem estoque/reserva nem garantia de disponibilidade física. Sem janela de entrega ou promessa de prazo.

Alimentos: embalados por unidade, ingredientes/alergênicos/nutrição por porção definidos no contrato. Distinguir ausência declarada de alergênicos de informação desconhecida. Dados fictícios, sem certificação. Endereço mais janela habilitada e futura do servidor em America/Sao_Paulo; sem capacidade/reserva. Salvar snapshot da janela.

Operação: catálogo local validado; pedidos e autorizações simuladas em bancos privados duráveis. Intermediário Next.js com mesma origem, identidade/configuração coerente e sessão anônima assinada. Chave idempotente de pedido e autorização única por pedido, com recuperação limitada após falhas. Compose futuro inclui frontend e serviços; execução sem Docker também documentada.

## Fluxos do cliente

**Roupas:** abrir catálogo → detalhe → escolher combinação cadastrada → adicionar/editar carrinho → informar endereço → revisar preços atuais → confirmar simulação → acompanhar se houver processamento → observar confirmação durável → consultar pedido com a mesma sessão. Combinação inválida bloqueia revisão/admissão.

**Alimentos:** catálogo → detalhe com ingredientes, alergênicos e nutrição → carrinho → endereço → consultar/escolher janela futura → revisar → confirmar simulação → acompanhar → consultar pedido e janela preservados. Sem janela válida, não confirmar.

**Variações comuns do fluxo:** preço relevante mudou ou revisão expirou antes da admissão → mostrar conflito e exigir nova revisão/confirmação; resposta perdida → consultar tentativa e reenviar mesma chave/corpo, mantendo carrinho; confirmar somente após observar pedido confirmed. Mudança de catálogo após admissão não altera snapshot. Consulta por outra sessão é recusada, mesmo conhecendo o ID.

## Fora do escopo

IA; autenticação por conta/login; recuperação de conta; pagamento/banco/cartão reais; painel administrativo; cupons/desconto; estoque; reserva/capacidade de janela; frete; transportadora/rastreamento; venda por peso; lotes/validade; multitenancy e implantação pública. Consulta anônima é vinculada ao cookie, não pública por ID. Perder a sessão elimina o acesso do usuário aos pedidos anteriores no MVP.

## Aceitação e dados da demonstração

Critérios RF01–RF13 e RNF01–RNF09, origem acadêmica e evidências futuras estão em [validacao.md](validacao.md). Incluem positivos/negativos de ambas as lojas, isolamento, restart, concorrência, preços alterados e dependências indisponíveis.

Dados futuros: ≥2 produtos de cada loja; roupas com duas combinações válidas e uma tentativa de combinação não cadastrada; alimentos com exemplos conhecidos/ausência declarada e desconhecidos de alergênicos; pelo menos duas janelas futuras de exemplo e cenários de janela desabilitada/passada em teste. Usar relógio controlável em testes e geração relativa na demonstração. Não afirmar que esses dados já existem.

## Sequência de trabalho

Etapa 1: diagnóstico registrado. Etapa 2: esta especificação documental. Etapa 3 recomendada: estrutura executável e ambiente, descrita em [decisoes-e-etapas.md](decisoes-e-etapas.md). Depois: catálogo/componentes; pedidos/revisões/agenda/pagamentos e recuperação; UI compartilhada; checkout/consulta; demonstração e evidências. Cada incremento registra validações reais; não confundir esqueleto pronto com MVP entregue.
