# Tutorial de execução no Windows

Agora há `/configurador` e painel de microsserviços na loja. Siga [execução e diagnóstico atual](finalizacao-compra-e-entrega.md#execução-e-diagnóstico-da-demonstração); iniciar somente o Next.js não inicia os serviços necessários à compra.

Atualização 10/11/2026: `tools/lps.py run clothing --dev` inicia cinco processos, incluindo recomendações em 8004. Execute `init clothing`/`init food` para acrescentar os novos segredos preservando os anteriores. [Comandos e estado atual](recomendacoes-e-imagens.md#executar).

Este guia usa PowerShell e os comandos atuais do projeto. As instruções não significam que a execução completa já foi homologada. A última checagem encontrou lint/typecheck aprovados, mas o build do Next.js falhou por acesso negado no SWC no ambiente do agente.

## 1 Abrir a pasta no VS Code

Abra um PowerShell normal do Windows:

```powershell
cd "C:\Users\M\Downloads\Framework-e-commerce-main\Framework-e-commerce-main"
code .
```

Se `code` não estiver disponível, abra o VS Code e escolha **Arquivo > Abrir Pasta**, selecionando esse mesmo diretório. No VS Code, escolha **Terminal > Novo Terminal** e use PowerShell. Os comandos seguintes devem ser executados na raiz do projeto, onde estão `tools`, `apps` e `requirements-dev.txt`.

## 2 Conferir os pré-requisitos

```powershell
python --version
node --version
npm.cmd --version
```

O projeto foi preparado com Python 3.11 e Node 24.15.0. O fluxo abaixo não exige Docker. Se algum comando não for reconhecido, o programa correspondente precisa estar instalado e disponível no terminal; reabra o terminal após uma instalação feita por você.

## 3 Preparar as dependências

Faça esta preparação na primeira execução, ou ao atualizar dependências. Não precisa repeti-la sempre que abrir a loja.

```powershell
# Cria o ambiente somente se ainda não existir:
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm.cmd --prefix apps/store-ropa ci --no-audit --no-fund
```

O uso do executável completo dispensa ativar o venv e não exige alterar a política de execução do PowerShell. O npm instala pelo package-lock.json. As instalações precisam de acesso aos registros de pacotes e devem terminar sem erro antes de seguir. Se a instalação atual já está completa, avance para o próximo passo.

## 4 Inicializar as configurações das lojas

```powershell
.\.venv\Scripts\python.exe tools/lps.py init clothing
.\.venv\Scripts\python.exe tools/lps.py init food
```

O lançador gera ou preserva segredos em `.local/roupas-demo.env` e `.local/alimentos-demo.env`. Não é necessário copiar seus valores para o navegador ou editar variáveis NEXT_PUBLIC. Reiniciar não exige apagar ou regenerar esses arquivos.

## 5 Iniciar a loja de roupas

```powershell
.\.venv\Scripts\python.exe tools/lps.py run clothing --dev
```

Um comando inicia catálogo, pagamentos, pedidos e frontend como quatro processos separados. Mantenha esse terminal aberto. O comando permanece em execução e exibe os logs; isso é esperado. Aguarde o Next.js anunciar que está pronto antes de abrir a interface. O modo `--dev` dispensa um build de produção anterior, mas ainda depende do compilador e das dependências reais do Next.js.

Abra no navegador:

```text
http://127.0.0.1:3000
```

Use **127.0.0.1**, conforme a origem configurada. `localhost` é uma origem diferente e pode impedir operações de sessão/compra com a configuração padrão.

## 6 Abrir a interface e as APIs

| O que abrir | Endereço |
|---|---|
| Loja e fluxo de compra | http://127.0.0.1:3000 |
| Configuração pública da loja ativa | http://127.0.0.1:3000/api/v1/store |
| Catálogo via intermediário | http://127.0.0.1:3000/api/v1/products |
| Prontidão agregada | http://127.0.0.1:3000/health/ready |
| Swagger do catálogo | http://127.0.0.1:8001/docs |
| Swagger de pedidos | http://127.0.0.1:8002/docs |
| Swagger de pagamentos | http://127.0.0.1:8003/docs |
| Liveness do catálogo | http://127.0.0.1:8001/health/live |
| Liveness de pedidos | http://127.0.0.1:8002/health/live |
| Liveness de pagamentos | http://127.0.0.1:8003/health/live |

Swagger documenta as operações existentes. Os endpoints internos exigem credencial e identidade/hash da configuração; operações privadas de pedidos também exigem dono de sessão. Um 401 ao chamar uma API interna sem esses cabeçalhos é esperado. Para demonstrar compra, utilize a loja: o Next.js trata sessão e credenciais internamente. Não tente autorizar pagamentos pelo navegador.

Prontidão pode ficar degradada durante a inicialização ou se alguma dependência cair. Liveness indica processo vivo e não comprova compra completa.

## 7 Percorrer a loja de roupas

1. Abra a coleção, busque ou filtre por categoria.
2. Abra um produto e escolha uma combinação habilitada de tamanho/cor.
3. Adicione à sacola e confira quantidades.
4. Continue para entrega e preencha endereço fictício; CEP tem oito números e UF duas letras maiúsculas.
5. Clique em revisar e confira o total calculado pelo servidor.
6. Confirme a compra simulada e consulte seu resultado.

Não há transferência financeira real, QR Code de Pix ou solicitação de dados bancários. Se a resposta se perder, consulte o resultado ou reenvie a mesma tentativa pela interface; não comece outra compra para resolver a incerteza. Preserve cookies para consultar o pedido depois.

## 8 Encerrar roupas e abrir alimentos

No terminal do lançador, pressione **Ctrl+C** para encerrar os quatro processos. Depois:

```powershell
.\.venv\Scripts\python.exe tools/lps.py run food --dev
```

Abra/recarregue http://127.0.0.1:3000. A implantação ativa agora usa o manifesto de alimentos. Não execute as duas variantes simultaneamente nas portas padrão.

Na variante de alimentos:

1. Abra os produtos e confira ingredientes, alergênicos e nutrição por porção.
2. Adicione produtos por unidade à sacola.
3. Preencha endereço fictício.
4. Escolha uma janela futura de entrega; os horários são de São Paulo.
5. Revise, confirme a compra simulada e consulte o pedido.

As lojas têm dados, cookies e sacolas separados. Para retornar à loja de roupas, encerre alimentos com Ctrl+C e execute novamente `run clothing --dev`.

## 9 Mostrar cada processo em um terminal

Alternativa ao comando `run`: abra **quatro terminais**, todos na raiz do projeto. Não use esta opção ao mesmo tempo que `run`.

Terminal 1 — catálogo:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service catalog
```

Terminal 2 — pagamentos:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service payments
```

Terminal 3 — pedidos:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service orders
```

Terminal 4 — frontend:

```powershell
.\.venv\Scripts\python.exe tools/lps.py service clothing --service web --dev
```

Para alimentos, substitua `clothing` por `food` nos quatro terminais. Para encerrar esta opção, use Ctrl+C em cada terminal.

Para mostrar as portas num quinto terminal:

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object { $_.LocalPort -in 3000,8001,8002,8003 } |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

## 10 Rodar verificações e modo de produção

Em outro terminal na raiz:

```powershell
npm.cmd --prefix apps/store-ropa run typecheck
npm.cmd --prefix apps/store-ropa run lint
.\.venv\Scripts\python.exe tools/validate.py
```

O relatório consolidado é salvo em `.local/validation-latest.json`. Verificação bloqueada não é aprovação.

Para testar o modo de produção, encerre a execução dev, gere o build e só depois inicie sem `--dev`:

```powershell
.\.venv\Scripts\python.exe tools/lps.py build-web clothing
# Só prossiga se o build terminar com sucesso:
.\.venv\Scripts\python.exe tools/lps.py run clothing
```

O teste HTTP ponta a ponta isolado requer build e loopback funcionais:

```powershell
.\.venv\Scripts\python.exe tools/e2e.py
```

Esse teste usa recursos temporários; não substitui inspeção visual da interface.

## 11 Problemas comuns

| Mensagem ou sintoma | Verificação |
|---|---|
| python/node/npm não reconhecido | Verifique instalação e disponibilidade no terminal; use npm.cmd no PowerShell |
| Frontend dependencies missing | Execute npm ci na etapa 3 e confira se terminou com sucesso |
| ENOTFOUND, EACCES ou falha de download | Registro de pacotes inacessível; instalação não concluída. Não trate a pasta node_modules parcial como instalação válida |
| SWC, failed to canonicalize ou acesso negado | O compilador não conseguiu acessar o projeto. Guarde a mensagem completa; é necessário resolver a permissão/ambiente antes de considerar o frontend aprovado |
| EADDRINUSE ou address already in use | Já existe um processo usando a porta. Encerre a execução anterior; não inicie ambas as variantes nas mesmas portas |
| ORIGIN_FORBIDDEN | Abra http://127.0.0.1:3000, sem trocar por localhost na configuração padrão |
| Serviço indisponível na vitrine | Verifique os logs dos processos e health/live; aguarde inicialização e consulte health/ready |
| SESSION_REQUIRED ou pedido inacessível | Preserve a sessão original. Limpar/trocar cookies pode impedir consultar compras anteriores |
| Erro de configuração ou banco incompatível | Não apague o banco para contornar. Confira variante, caminhos e mensagens; o sistema recusa dados de outra loja/schema |

Não apague `.local` ou `var` para reiniciar. Os bancos de demonstração ficam em `var/<store_id>/orders/orders.sqlite` e `var/<store_id>/payments/payments.sqlite`. Capturas para apresentação não devem expor arquivos de segredos.
