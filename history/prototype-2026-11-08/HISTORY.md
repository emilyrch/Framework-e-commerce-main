# Protótipo preservado antes da etapa 3

Não havia Git disponível no PATH ou nos caminhos usuais, nem diretório `.git` na raiz. Este snapshot preserva 41 arquivos preexistentes, sem alterar o conteúdo. `inventory.json` contém os caminhos relativos e SHA256. Não foram copiados bancos, segredos, dependências instaladas ou caches. Bancos antigos, se presentes na área de trabalho, devem permanecer lá e nunca ser abertos pelo novo runtime.

Para reproduzir o backend legado, em um terminal nesta pasta: `python -m services.server catalog --port 8001`; outros terminais executam payments/8003 e orders/8002. Os comandos legados usam localhost e não possuem a fronteira de autenticação do novo sistema; somente demonstração histórica. Testes: `python -m unittest discover -s tests -v`. Frontend: `cd apps/store-ropa`, `npm ci`, `npm run dev`. Dependências e problemas originais foram preservados, não corrigidos neste snapshot.

Este diretório não é uma entrada ativa do MVP. Básica/Premium, cartão, desconto e endpoints de compra legados não são oferecidos pelo novo lançador. A suíte ativa usa exclusivamente `tests/foundation`; a suíte legada é a deste snapshot. Não executar descoberta recursiva na raiz misturando os dois sistemas.
