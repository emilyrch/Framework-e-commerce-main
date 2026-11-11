# Apresentação acadêmica — roteiro de 10 a 12 minutos

## Preparação

Executar `python tools/validate.py` em ambiente que permita loopback e build. Conferir resultados, sem interpretar checks bloqueados como aprovação. Iniciar a família com o lançador, não apenas o frontend. As capturas devem ser de execução real, sem segredos, e devem ser acrescentadas ao relatório após a homologação.

## Sequência sugerida

1. **Objetivo (1 min):** mesma base de e-commerce, duas variantes configuradas, diferenças previstas e reutilização.
2. **Features (2 min):** mostrar diagrama e `/configurador`; domínio XOR, núcleo obrigatório, tamanho/cor ou informações alimentares/agendamento. Baixar manifesto e mostrar o comando de derivação; recomendações é extensão comum fixa.
3. **Arquitetura (2 min):** quatro processos FastAPI e frontend/gateway. Mostrar portas reais no terminal e painel da interface. Distinguir microsserviço, componente de domínio e componente visual. Mostrar bancos privados sem expor conteúdo de compras ou chaves.
4. **Roupas (2 min):** abrir produto com combinações não cartesianas, adicionar duas seleções e finalizar com endereço fictício. Mostrar total do servidor, Pix simulado, confirmação e consulta. Não prometer estoque físico.
5. **Persistência (1 min):** anotar o ID do pedido, reiniciar a mesma loja conservando bancos/cookie e consultá-lo. Mostrar evidência automatizada de reenvio sem pedido/pagamento duplicado.
6. **Alimentos (2 min):** encerrar roupas, iniciar food e mostrar metadados, ausência de tamanho/cor e agenda obrigatória. Concluir compra com janela futura e consultar snapshot.
7. **Recomendações e conclusão (1–2 min):** demonstrar preferências, explicações e limpeza/pausa do histórico. Relacionar features, microsserviços, componentes e evidências às exigências do roteiro.

## Capturas necessárias para o relatório

| Evidência | O que deve aparecer |
|---|---|
| Configuração — item 5.4 | Domínio escolhido, features, identidade/hash e comandos de derivação |
| Processos — item 6.4 | Portas 3000/8001/8002/8003/8004 e processos efetivamente ativos |
| Interface principal — item 8 | Loja, catálogo e painel identificando os microsserviços |
| Compra roupas | Combinações, revisão, confirmação e consulta de pedido |
| Compra alimentos | Informações alimentares, agenda e pedido com janela preservada |
| Recomendações — item 6.1 | Preferências, sugestões explicadas e efeito de histórico |
| Reinício e isolamento | Mesmo pedido após reinício e dados separados ao trocar loja |

As capturas ainda não foram realizadas neste ambiente. Diagrama arquitetural não é evidência de serviços executando. Um vídeo de apoio só deve mostrar execução real já verificada. Login não foi exigido pelo roteiro fornecido; checkout anônimo continua no escopo.
