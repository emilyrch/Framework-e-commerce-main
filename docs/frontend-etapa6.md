# Frontend compartilhado — 10/11/2026

Implementado no código; **build, lint, typecheck, inspeção visual no navegador e compra ponta a ponta ainda não verificados**. Não declarar o MVP aprovado.

## Interface

Uma base React/Next.js atende as duas configurações: identidade editorial “essencial” em roupas e “despensa” em alimentos. Fundo claro, cores de domínio, tipografia de sistema/serifada sem download de fontes, layouts responsivos, foco visível, diálogo nativo de produto e preferência de movimento reduzido. A marca visual não altera store_id/display_name dos manifestos.

Vitrine com busca e categorias; detalhe com combinações explícitas habilitadas, ou ingredientes/alergênicos/nutrição por porção; sacola editável; endereço; agenda de alimentos; revisão de preços pelo servidor; confirmação simulada; acompanhamento por tentativa/pedido. São integrações programadas com as APIs reais: não há catálogo fictício alternativo retornando sucesso quando o backend cai.

`components/product-art.tsx` fornece ilustrações SVG autorais no próprio código, sem rede ou imagens de terceiros. São representativas, não fotos exatas de cada produto. O fallback já existente em `/demo/catalog-fallback.svg` continua disponível no frontend para o caminho informado pela API. A UI atual escolhe a ilustração de domínio em vez de carregar imagens remotas.

Carrinho usa `lps:cart:<store_id>` no localStorage. Nome/preço locais são somente estimativas; comandos enviam apenas IDs e quantidades. Identidade de linha é produto+combinação em roupas e produto em alimentos. Limites de 50 linhas e 1–100 unidades; backend permanece autoridade. Endereço não é persistido no navegador.

## Sessão e intermediário

`src/lib/web-api.ts` implementa handlers padrão Request/Response; a rota Next `app/api/v1/[...path]/route.ts` os publica. Somente operações enumeradas são permitidas:

- POST session e GET store.
- GET products e products/{id}.
- GET delivery-slots.
- POST reviews/orders e GET orders/{id}/order-attempts/{key}.

Sem proxy de pagamentos ou resolução interna. Bearer, loja/hash e dono são reconstruídos no servidor; cabeçalhos de confiança do navegador são ignorados. Cada resposta interna exige identidade/hash correspondentes. Sem redirecionamentos ou repetição automática de mutações. Limites: corpo 64 KiB, resposta 1 MiB, timeout seis segundos (onze para admissão). Erros são projetados no envelope comum sem mensagens internas arbitrárias. Respostas usam no-store.

Cookie `lps_session_<store_id>`: SID aleatório, loja, emissão/expiração e HMAC-SHA256 com SESSION_SECRET estável. HttpOnly, SameSite=Lax, Path=/, 30 dias; Secure em origem HTTPS. HTTP permitido somente em loopback neste projeto. Dono = SHA-256(loja:SID). Contexto de continuidade usa HMAC com rótulo separado; nenhum SID/dono/token interno é retornado ao cliente. Cookie inválido em consulta privada resulta em 401; somente POST session cria/reutiliza sessão.

Mutações exigem Origin exatamente igual a WEB_ORIGIN e Content-Type application/json. Padrão: `http://127.0.0.1:3000`; acessar por localhost é outra origem e exige configuração explícita. SESSION_SECRET agora é passado apenas ao frontend pelo lançador e Compose; serviços não o recebem. Configuração de sessão/origem inválida impede bootstrap. Readiness informa disponibilidade do componente session_signing, sem certificar o fluxo no navegador.

## Retomada

Antes do POST orders, a UI persiste UUID da chave, review_id, contexto e fingerprint da seleção em `lps:purchase:<store_id>`. Se essa gravação falhar, não envia a compra. Botões compartilham trava local contra duplo envio. Resposta perdida conserva a chave e oferece consulta/reenvio da mesma tentativa. Não há polling ilimitado.

Contexto diferente bloqueia retomada; não interpretar 404 de nova sessão como inexistência da compra antiga. A sacola só é limpa quando uma resposta/consulta autenticada comprova pedido confirmado (`confirmed`) e sua seleção ainda corresponde à original. Conflito de revisão já consumida consulta o pedido indicado antes de limpar. Rejeição não limpa carrinho. Preço alterado/expiração exige nova revisão após consultar a tentativa rejeitada.

Referências dos últimos 20 pedidos concluídos podem ser guardadas localmente para consulta posterior na sessão original; não existe API de listagem geral de pedidos. Dados comerciais são obtidos novamente do backend. Perder cookie impede consulta mesmo preservando a referência. Tentativa pendente bloqueia início de outra compra na UI até resolução, evitando tratar incerteza como fracasso.

## Executar — PowerShell na raiz

Com dependências instaladas pelo lockfile:

```powershell
.\.venv\Scripts\python.exe tools/lps.py run clothing --dev
# Encerre com Ctrl+C e selecione a outra loja:
.\.venv\Scripts\python.exe tools/lps.py run food --dev
```

Abrir **http://127.0.0.1:3000**. Segredos continuam gerados/preservados por `tools/lps.py init clothing` ou `init food`, em `.local/<store_id>.env`. Não os substituir ao reiniciar. Para usar localhost em execução local: `$env:WEB_ORIGIN='http://localhost:3000'` antes do lançador. No Compose, WEB_ORIGIN pode ser informado pelo ambiente/arquivo --env-file. Compose não foi executado.

## Validação real

| Verificação | Resultado |
|---|---|
| `node --experimental-strip-types --test apps/store-ropa/scripts/test-web.ts` | 10 testes aprovados: sessão, adulteração/expiração/loja, cookie duplicado, origem, corpos, permissões/rotas, headers confiáveis, erros e projeção de alimentos |
| `node --experimental-strip-types apps/store-ropa/scripts/check-config.ts` | 24 vetores de identidade/hash aprovados |
| `python tools/test_backend.py --offline` | 31 testes aprovados, incluindo injeção de SESSION_SECRET somente no frontend |
| Compilação Python de tools/tests | Sem erros |
| npm run build / lint / typecheck | Tentados; next/eslint/tsc não encontrados na instalação incompleta |
| UI React no navegador, responsividade visual e integração real | Não verificados; Next indisponível |
| Backend HTTP/worker | 67 testes completos aprovados, com processos reais e reinício |
| Python limpo e containers | Bloqueados por acesso ao índice e ausência do Docker |

Os testes web executam código real de sessão/intermediário com Request/Response do Node e transporte controlado. Não importam substitutos de Next/React e não equivalem a renderização, typecheck ou E2E. Nesta execução, npm ci falhou com “Exit handler never called”; npm ping retornou EACCES. A regressão de carrinho preserva itens em estados incertos e edições feitas durante a confirmação.

## Próximo bloco

Prioridade: disponibilizar dependências reais, executar build/lint/typecheck, revisar visual em desktop/celular e corrigir achados. Depois, executar E2E Next.js nas duas lojas e Compose real. Compra, perda de resposta, reinício e isolamento já passaram no backend; isso não aprova a UI. Consolidar evidências acadêmicas após essas execuções. Não há implantação pública, conta, estoque, pagamento real, IA ou novas integrações.
