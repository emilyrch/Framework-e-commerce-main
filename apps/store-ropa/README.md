# Frontend compartilhado da LPS

Next.js/React/TypeScript/Tailwind preservados. A página existente é uma vitrine estática de roupas com aviso de transição, **não integrada** aos novos serviços. Não há carrinho, checkout, sessão ou proxy de negócio nesta etapa.

Etapa 4: o backend agora possui catálogos funcionais. O fallback original local em `public/demo/catalog-fallback.svg` está pronto para uso futuro via `/demo/catalog-fallback.svg`, mas a página legada não foi redesenhada ou conectada às APIs. Há somente essa imagem genérica para os novos dados; não há fotos de produtos. Consulte [catalogo-etapa4.md](../../docs/catalogo-etapa4.md).

Configuração server-side em `src/lib/store-config.ts` e `server-runtime.ts`, validada no startup por `src/instrumentation.ts`. Saúde em `/health/live` e `/health/ready`, também sob `/api/health/`. Nenhum segredo em NEXT_PUBLIC_*.

Execute a partir da raiz pelo lançador documentado no [README principal](../../README.md). Instalação: `npm.cmd --prefix apps/store-ropa ci`. Build com manifesto/credenciais no servidor: `python tools/lps.py build-web clothing`. Desenvolvimento: `python tools/lps.py service clothing --service web --dev`.

`npm run lint` usa ESLint diretamente; `npm run typecheck` usa TypeScript; `npm run test:config` usa Node 24.15+ sem depender do Next instalado. Fontes Google foram removidas para evitar acesso de rede no build; imagens remotas da vitrine legada permanecem por enquanto.

No ambiente desta entrega, instalação npm falhou por rede bloqueada/cache incompleto: build, lint, typecheck e execução Next.js **não foram validados**. Apenas validação/hash e lógica de prontidão do módulo servidor foram exercitados pelo Node. Estado e evidências em [docs/fundacao-etapa3.md](../../docs/fundacao-etapa3.md).
