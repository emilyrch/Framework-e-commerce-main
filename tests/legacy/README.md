# Suíte legada

O teste original foi movido sem alterações para este diretório após cópia histórica verificada em `history/prototype-2026-11-08/tests`. Usa o código stdlib e as configurações Básica/Premium ainda preservados na raiz; não testa o novo MVP.

Executar separadamente, a partir da raiz: `python -m unittest discover -s tests/legacy -v`. As suítes ativas são tests/foundation, tests/catalog e tests/reviews: `python -m unittest discover -s tests -t . -v`. Não misturar seus resultados com o legado.
