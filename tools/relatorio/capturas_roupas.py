"""Insert real, observed clothing UI evidence without certifying unrelated checks."""

def update_source(source):
    source=source.replace('TableStyle, KeepTogether, Preformatted','TableStyle, KeepTogether, Preformatted, Image as ReportImage')
    helper='''
def screenshot(filename,title,description):
    page(title)
    image=ReportImage(str(ROOT/'output/capturas-roupas'/filename))
    factor=min(CW/image.imageWidth,470/image.imageHeight)
    image.drawWidth=image.imageWidth*factor
    image.drawHeight=image.imageHeight*factor
    image.hAlign='CENTER'
    story.append(image)
    caption(title+'. Fonte: captura real do sistema pela autora, assistida por ferramenta de automação (10 nov. 2026).')
    p(description)

'''
    source=source.replace("page('Resumo')",helper+"page('Resumo')",1)
    source=source.replace('Assim, a execução visual, o fluxo completo pelo Next.js e os containers não são apresentados como homologados.',
        'Posteriormente, uma execução manual da variante de roupas pelo navegador concluiu revisão, pagamento simulado e consulta do pedido, com capturas reais. Isso não homologa alimentos, reinício, build de produção, toda a suíte E2E ou containers.')
    source=source.replace('A captura dessa tela em execução ainda depende do ambiente.','A Figura 5 registra a tela de configuração efetivamente aberta, com roupas selecionada.')
    source=source.replace("page('6 Arquitetura baseada em microsserviços')",'''screenshot('09-configurador.jpg','Figura 5 - Configuração visual da variante de roupas','A escolha exclusiva roupas está ativa. A tela apresenta identidade, hash, features e comandos de derivação. A presença da alternativa alimentos não representa execução ou captura dessa variante.')

page('6 Arquitetura baseada em microsserviços')''')
    source=source.replace("page('6.5 Construção de um produto a partir da LPS')",'''screenshot('08-microsservicos.jpg','Figura 7 - Serviços e portas da loja de roupas','O painel da interface consultou a prontidão e apresentou catalog 8001, orders 8002, payments 8003 e recommendations 8004 como prontos. Trata-se da observação do painel, não de captura de terminal nem comprovação de isolamento ou reinício.')

page('6.5 Construção de um produto a partir da LPS')''')
    source=source.replace('Não foi obtida captura verificável das quatro portas durante a elaboração.','Nesta execução foram capturados os quatro serviços e suas portas no painel da interface, todos prontos. Não houve captura de terminal com processos/PIDs.')
    source=source.replace('Nesta etapa, capturas de desktop/celular e do fluxo de compra não foram obtidas.','Foram obtidas capturas reais da variante de roupas, no viewport disponível do navegador.')
    # Replace only the outdated section-8 capture note; older test evidence remains scoped.
    lines=source.splitlines()
    for index,line in enumerate(lines):
        if line.startswith("note('Capturas de desktop/celular"):
            lines[index]="note('As Figuras 8 a 16 apresentam execução real de roupas: vitrine, seleção, sacola, entrega, revisão, confirmação, consulta e recomendações. O pedido 6d252cef-57c0-4ba0-b5d9-cf4621427109 foi confirmado por R$ 89,90, com pagamento fictício. Foram usados nome e endereço fictícios. Alimentos, reinício, build de produção e Compose não foram validados nesta sessão.')"
    source='\n'.join(lines)+'\n'
    captures=[
        ('01-vitrine.jpg','Figura 8 - Vitrine da loja de roupas','A vitrine utiliza imagem local da camiseta e apresenta a identidade essencial. Os produtos e valores são fictícios; a captura registra a execução no navegador, não uma maquete.'),
        ('02-produto-combinacoes.jpg','Figura 9 - Combinações de tamanho e cor','A camiseta foi selecionada em M e preta. As demais combinações aparecem explicitamente, incluindo a opção desabilitada. A imagem não constitui garantia de estoque físico.'),
        ('03-sacola.jpg','Figura 10 - Sacola com uma seleção','A sacola contém uma camiseta M/preta, por R$ 89,90 estimados. A revisão subsequente confirma o valor no backend; o frontend não determina o preço final.'),
        ('04-entrega.jpg','Figura 11 - Endereço fictício para entrega','O checkout sem cadastro recebeu Cliente de Demonstração, Rua Fictícia, 100, Centro, Maceió/AL e CEP 57000000. Roupas não exige agendamento nem promete prazo de entrega.'),
        ('05-revisao.jpg','Figura 12 - Revisão da compra pelo servidor','O serviço de pedidos persistiu a revisão e retornou total de R$ 89,90, expiração e possibilidade de confirmar. O Pix é inteiramente simulado, sem transferência ou dados bancários.'),
        ('06-pedido-confirmado.jpg','Figura 13 - Confirmação da compra simulada','A interface apresentou Pedido confirmado e Pagamento fictício aprovado. O identificador aleatório permite acompanhar o pedido na sessão original. Nenhum pagamento real foi realizado.'),
        ('13-consulta-completa.jpg','Figura 14 - Consulta posterior do pedido','Após voltar à coleção e abrir Meu pedido, foi consultado novamente o mesmo identificador, com valor, combinação e endereço preservados. A navegação recarregou a página ao visitar o configurador; os processos de backend não foram reiniciados.'),
        ('10-preferencias.jpg','Figura 15 - Preferências de demonstração','Foram salvas a categoria Camisetas e camisas e o limite de R$ 150,00 por peça. O histórico desta sessão registrou duas interações: visualização e adição à sacola.'),
        ('14-recomendacoes-recorte.jpg','Figura 16 - Recomendações por preferências e histórico','As sugestões mostram motivos como categoria escolhida e categoria do histórico. Este recorte retangular da captura integral 12-pagina-completa.jpg preserva o conteúdo original, sem alterar textos ou resultados.'),
    ]
    addition='\n'.join(f'screenshot({filename!r},{title!r},{description!r})' for filename,title,description in captures)
    source=source.replace("page('9 Código do projeto e disponibilização no GitHub')",addition+"\n\npage('9 Código do projeto e disponibilização no GitHub')")
    source=source.replace('captura real das portas e das telas, URL específico do projeto na capa e homologação do frontend em ambiente funcional.',
        'complementação das capturas de terminal/portas, evidências da variante de alimentos, URL específico do projeto na capa e demais verificações técnicas. A compra de roupas foi observada nesta sessão, com confirmação e consulta registradas.')
    source=source.replace('Portas e comandos definidos; captura de execução pendente','Painel real mostra serviços prontos e portas; captura de terminal/PIDs pendente')
    source=source.replace('Fluxo e painel de serviços implementados; capturas reais e homologação visual pendentes','Capturas e compra de roupas registradas; alimentos e demais verificações pendentes')
    source=source.replace('A coleta de capturas de execução continua pendente; não há evidência de homologação visual.',
        'Posteriormente, foram coletadas capturas de roupas e observada uma compra confirmada. A homologação completa de ambas as variantes permanece pendente.')
    source=source.replace('A causa ambiental não autoriza afirmar que o fluxo visual completo já foi aprovado.',
        'A execução manual de roupas registrada nas figuras é uma evidência específica; não aprova toda a suíte de integração nem a variante de alimentos.')
    return source


if __name__=='__main__':
    from pathlib import Path
    here=Path(__file__).resolve().parent
    entry=here/'atualizar_diagramas.py'
    code=entry.read_text(encoding='utf-8')
    marker='source=source[:start]+source[end:]'
    code=code.replace(marker,marker+'\nfrom capturas_roupas import update_source\nsource=update_source(source)')
    code=code.replace('Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_atualizado.pdf','Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_capturas_roupas.pdf')
    code=code.replace('Relatorio_LPS_Emily_Rocha_atualizado_editavel.html','Relatorio_LPS_Emily_Rocha_capturas_roupas_editavel.html')
    code=code.replace('Figura 5 — Visão de implantação','Figura 6 — Visão de implantação')
    exec(compile(code,str(entry),'exec'),{'__file__':str(entry),'__name__':'__main__'})
