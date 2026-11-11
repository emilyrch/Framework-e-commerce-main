# Estabilização da compra e preparação da entrega — 10/11/2026

Evidência posterior: [capturas reais de roupas e compra confirmada](capturas-roupas-2026-11-10.md). A execução manual do navegador foi bem-sucedida para roupas; demais bloqueios e verificações anteriores mantêm seu alcance.

Este documento prevalece sobre contagens e pendências dos registros anteriores. Implementação disponível não equivale a compra homologada em navegador. O relato de que a compra não finaliza não pôde ser reproduzido por HTTP neste ambiente; portanto não há diagnóstico definitivo de sua causa.

## Correções e incrementos realizados

- A tela acompanha tentativas pendentes com até doze consultas, com pausa de dois segundos entre leituras. Consulta o pedido quando existe um ID, atualiza o snapshot e limpa a sacola somente após confirmação e correspondência da seleção original. Nunca cria chave nem reenvia compra automaticamente.
- Ao sair da tela, respostas atrasadas são ignoradas. Falhas transitórias não apagam a tentativa; ao atingir o limite, a interface orienta a consulta ou reenvio com a mesma chave. Estados confirmado, rejeitado e conflito encerram o acompanhamento.
- Recomendações e checkout compartilham a requisição em andamento de inicialização da sessão. Isso evita criar dois cookies/donos por chamadas simultâneas sem cookie. Falha libera a requisição para uma nova tentativa. Não foi acrescentado login: a sessão anônima continua sendo a decisão de escopo.
- O campo UF transforma letras em maiúsculas; CEP remove caracteres não numéricos. Validação autoritativa continua no backend.
- `/configurador` oferece escolha exclusiva roupas/alimentos, lista as features efetivas, gera download do manifesto validado e fornece comandos para construir e executar a variante. Features obrigatórias não podem ser desligadas. Não cria um terceiro domínio, não muda uma loja durante uma compra e não executa shell pelo navegador.
- A página principal identifica os quatro microsserviços, suas portas configuradas e permite consultar prontidão. Antes da consulta, mostra “não verificado”. Prontidão não é prova da compra completa. Nenhum token, hostname privado ou caminho de armazenamento é enviado nesse painel.
- A imagem Docker do frontend inclui os dois manifestos versionados necessários ao configurador; o manifesto selecionado permanece montado somente para leitura. Dados privados continuam separados.

## Exigências acadêmicas conferidas

O PDF `Elementos do Relatorio do Projeto -2026-2.pdf` foi lido novamente. Além das três exigências inicialmente transcritas, o roteiro exige seletor visual e construção do produto (5.4), recomendação por histórico em microsserviço próprio (6.1), captura das portas em execução (6.4), destaque dos microsserviços na interface (8) e URL do projeto na capa (9). A recomendação não depende de agentes de IA.

Seletor, recomendação e painel de serviços estão implementados. Capturas de execução, homologação completa e URL específico do repositório não foram inventados. O requisito de vídeo do item 11 é condicional a jogos e não se aplica a este e-commerce. O relatório atualizado permanece até a seção 10.

## Evidências atuais

| Verificação | Resultado |
|---|---|
| Backend offline com SQLite real e componentes | 43 testes aprovados; adaptadores inline não certificam HTTP/worker |
| Fronteira web, sessão e acompanhamento | 16 testes Node aprovados |
| Configuração Python/TypeScript | 24 vetores aprovados |
| TypeScript e lint | Aprovados após correções |
| Sintaxe Python e versões fixadas | Aprovadas |
| Backend HTTP/async/worker e E2E Next | Não executados: preflight de loopback falhou |
| Build Next.js | Tentativa real falhou: SWC não consegue resolver jsc.baseUrl por acesso negado |
| Consistência do ambiente Python | pip check identifica conflito preexistente de setuptools/streamlit-vis-network |
| Instalação Python limpa, containers Compose e navegador | Não verificados |

O relatório automatizado é `.local/validation-latest.json`; o comando é `python tools/validate.py`. Não foram instalados stubs, desativados testes ou alteradas configurações globais. Recursos de demonstração não foram usados pelos testes. As fontes anteriores do checkout foram preservadas em `history/before-checkout-stabilization-2026-11-10/`.

## Execução e diagnóstico da demonstração

Em PowerShell, na raiz do repositório, com dependências já instaladas:

```powershell
.\.venv\Scripts\python.exe tools/lps.py init clothing
.\.venv\Scripts\python.exe tools/lps.py run clothing --dev
```

Abra **http://127.0.0.1:3000**, evitando `localhost` quando a origem configurada é `127.0.0.1`. Não inicie somente `npm run dev`: a compra depende dos serviços. Para alimentos, encerre os processos com Ctrl+C e substitua `clothing` por `food`. Preserve `.local`, `var` e o cookie para consultar compras após reinício.

Em outro terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:3000/health/ready
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 3000,8001,8002,8003,8004 } |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

Se houver serviço indisponível, confira o erro de inicialização no terminal e as verificações de prontidão. Não apague bancos, não gere outra chave para compra incerta e não trate falha de recomendação como motivo para autorizar novamente pagamento.

## Relatório e apresentação

O PDF e o HTML editável atualizados estão em `output`, com diagramas SVG revisados para quatro microsserviços. Os documentos anteriores foram preservados. Fontes de geração em `tools/relatorio/`; utilizam bibliotecas de documentos, não são dependências do backend. Falta nome do professor, link específico do repositório e brasão oficial obtido de fonte institucional. Não se inventou identificação nem certificação de execução.

Veja [roteiro de apresentação e coleta de evidências](preparacao-apresentacao.md). A entrega está preparada no código e na documentação, mas ainda depende das verificações bloqueadas e dos dados de identificação. Não declarar o MVP homologado.
