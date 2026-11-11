from pathlib import Path
import json
import re
import math
from html import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether, Preformatted
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/pdf/Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
for name,file in [('TNR','times.ttf'),('TNR-Bold','timesbd.ttf'),('TNR-Italic','timesi.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNR-Bold',italic='TNR-Italic',boldItalic='TNR-Bold')
W,H=595.276,841.89
LEFT,RIGHT,TOP,BOTTOM=3*cm,2*cm,2.5*cm,2*cm
CW=W-LEFT-RIGHT
ink=colors.HexColor('#171717'); gray=colors.HexColor('#555555'); pale=colors.HexColor('#edf1f4'); blue=colors.HexColor('#193c57')
styles={
 'Body':ParagraphStyle('Body',fontName='TNR',fontSize=11.4,leading=16,alignment=TA_JUSTIFY,spaceAfter=9,firstLineIndent=18,textColor=ink),
 'Lead':ParagraphStyle('Lead',fontName='TNR',fontSize=11.2,leading=16,alignment=TA_JUSTIFY,spaceAfter=10),
 'H1':ParagraphStyle('H1',fontName='TNR-Bold',fontSize=14,leading=18,spaceAfter=15,keepWithNext=True),
 'H2':ParagraphStyle('H2',fontName='TNR-Bold',fontSize=12,leading=16,spaceBefore=9,spaceAfter=9,keepWithNext=True),
 'Cell':ParagraphStyle('Cell',fontName='TNR',fontSize=9.1,leading=12,spaceAfter=0),
 'HeadCell':ParagraphStyle('HeadCell',fontName='TNR-Bold',fontSize=9.1,leading=12,spaceAfter=0),
 'Caption':ParagraphStyle('Caption',fontName='TNR',fontSize=9,leading=12,spaceBefore=7,spaceAfter=10,alignment=TA_CENTER),
 'Small':ParagraphStyle('Small',fontName='TNR',fontSize=9.5,leading=13,spaceAfter=8),
 'Code':ParagraphStyle('Code',fontName='Mono',fontSize=7.7,leading=10.4,spaceAfter=10,backColor=colors.HexColor('#f4f4f4'),borderPadding=9),
 'Cover':ParagraphStyle('Cover',fontName='TNR',fontSize=12,leading=19,alignment=TA_CENTER,spaceAfter=4),
 'Title':ParagraphStyle('Title',fontName='TNR-Bold',fontSize=19,leading=26,alignment=TA_CENTER,spaceAfter=12),
}
story=[]
def p(text,style='Body'):story.append(Paragraph(text,styles[style]))
def h(text,level=1):p(text,'H1' if level==1 else 'H2')
def page(title=None):
    if story:story.append(PageBreak())
    if title:h(title)
def table(headers,rows,widths=None):
    data=[[Paragraph(escape(str(x)),styles['HeadCell']) for x in headers]]+[[Paragraph(escape(str(x)).replace('\n','<br/>'),styles['Cell']) for x in row] for row in rows]
    t=Table(data,colWidths=[CW*v for v in widths] if widths else [CW/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,gray),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#cccccc')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t);story.append(Spacer(1,10))
def code(text):story.append(Preformatted(text.strip('\n'),styles['Code'],maxLineLength=88,splitChars=' ,',newLineChars=''))
def caption(text):p(text,'Caption')
def note(text):p('<b>Nota de evidência.</b> '+text,'Small')
def diagram(height,boxes,edges):
    d=Drawing(CW,height)
    for a,b in edges:
        x1,y1,x2,y2=a[0],a[1],b[0],b[1]
        d.add(Line(x1,y1,x2,y2,strokeColor=gray,strokeWidth=.8))
        length=math.hypot(x2-x1,y2-y1);ux,uy=(x2-x1)/length,(y2-y1)/length
        pts=[x2,y2,x2-5*ux-2.5*uy,y2-5*uy+2.5*ux,x2-5*ux+2.5*uy,y2-5*uy-2.5*ux]
        d.add(Polygon(pts,fillColor=gray,strokeColor=gray))
    for x,y,w,hh,lines,fill in boxes:
        d.add(Rect(x,y,w,hh,fillColor=fill or colors.white,strokeColor=gray,strokeWidth=.65,rx=3,ry=3))
        if isinstance(lines,str):lines=[lines]
        baseline=y+hh/2+(len(lines)-1)*6-3
        for i,line in enumerate(lines):d.add(String(x+w/2,baseline-i*12,line,fontName='TNR',fontSize=9,textAnchor='middle',fillColor=ink))
    story.append(d)

class Report(BaseDocTemplate):
    def beforeDocument(self):
        self._toc_seen=set()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name in ('H1','H2'):
            text=f.getPlainText();level=0 if f.style.name=='H1' else 1
            key='s'+str(self.seq.nextf('heading'))
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,level=level,closed=False)
            number=re.match(r'^(\d+(?:\.\d+)?)\s',text)
            if number and number.group(1) not in self._toc_seen:
                self._toc_seen.add(number.group(1))
                self.notify('TOCEntry',(1 if '.' in number.group(1) else 0,text,self.page,key))
def header(c,doc):
    if doc.page>1:
        c.setFont('TNR',8);c.setFillColor(gray)
        c.drawString(LEFT,H-37,'UFAL  |  Engenharia da Computação')
        c.drawRightString(W-RIGHT,H-37,'LPS de comércio eletrônico  |  2026.2')
        c.drawRightString(W-RIGHT,31,str(doc.page))
    c.setTitle('Linha de Produto de Software para Comércio Eletrônico')
    c.setAuthor('Emily Vitória de Jesus Rocha')
    c.setSubject('Relatório acadêmico da disciplina Tópico em Engenharia de Software')

# Capa: identificação confirmada pela autora; nenhuma identidade visual reconstruída.
story.append(Spacer(1,12))
p('UNIVERSIDADE FEDERAL DE ALAGOAS','Cover')
p('Campus A. C. Simões','Cover');p('Engenharia da Computação','Cover')
story.append(Spacer(1,48));p('EMILY VITÓRIA DE JESUS ROCHA','Cover')
story.append(Spacer(1,70));p('Linha de Produto de Software<br/>para Comércio Eletrônico','Title')
p('Modelagem e implementação das variantes de roupas e alimentos','Cover')
story.append(Spacer(1,38));p('Tópico em Engenharia de Software','Cover')
p('Projetando Linhas de Produto de Software','Cover');p('Relatório do projeto  |  Semestre 2026.2','Cover')
story.append(Spacer(1,28));p('Perfil GitHub informado pela autora<br/><link href="https://github.com/emilyrch" color="#193c57">https://github.com/emilyrch</link>','Cover')
p('Endereço específico do repositório ainda não informado','Small')
story.append(Spacer(1,45));p('Maceió<br/>2026','Cover')

page('Resumo')
p('Este relatório apresenta a modelagem e a implementação de uma Linha de Produto de Software (LPS) para comércio eletrônico, derivada em duas variantes: uma loja de roupas com combinações explícitas de tamanho e cor e uma loja de alimentos embalados, com informações alimentares e entrega agendada. A solução compartilha o núcleo de catálogo, carrinho, revisão da compra, pedidos e pagamento Pix inteiramente simulado. A variabilidade é declarada em manifestos estritos, interpretados na inicialização, e vinculada a componentes de domínio selecionados no ponto de composição.')
p('A arquitetura compreende um frontend Next.js, que também atua como intermediário de APIs, e quatro aplicações FastAPI independentes: catálogo, pedidos, pagamentos e recomendações. Catálogos fictícios são validados em memória; pedidos, pagamentos e recomendações utilizam bancos SQLite privados. A criação de pedidos emprega revisões persistidas, chaves de idempotência, restrições de unicidade e recuperação limitada de estados intermediários, sem transação distribuída.')
p('O registro histórico anterior contém 67 testes completos de backend. No incremento atual, passaram 43 testes offline, 16 testes web e 24 vetores de configuração; esses resultados não substituem testes HTTP completos. Na verificação posterior, lint e typecheck passaram, mas o build do frontend foi impedido por acesso negado no compilador SWC. Assim, a execução visual, o fluxo completo pelo Next.js e os containers não são apresentados como homologados. O microsserviço de recomendação por preferências e histórico foi acrescentado, com imagens locais de dez peças, seletor visual da LPS e identificação dos serviços na interface.')
p('<b>Palavras-chave:</b> linha de produto de software; reuso; variabilidade; microsserviços; componentes; comércio eletrônico.','Lead')
h('Delimitação e identificação documental',2)
p('O texto segue os itens do documento “Elementos do Relatório do Projeto -2026-2”, entregue pela autora. A análise considera o código e os registros locais disponíveis em 10 de novembro de 2026. Nomes de cerimônias, durações de sprint, resultados de telas e publicação em GitHub não foram presumidos. Os backlogs são uma organização retrospectiva dos incrementos registrados.','Lead')
note('O brasão oficial da UFAL não foi incorporado: o acesso ao arquivo institucional foi bloqueado no ambiente de produção do relatório. O nome do docente e o URL específico do repositório não foram informados. Não se utilizou um logotipo redesenhado ou uma URL de projeto inventada.')

page('Sumário')
toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC0',fontName='TNR',fontSize=10.3,leading=14,spaceBefore=4),ParagraphStyle('TOC1',fontName='TNR',fontSize=9.5,leading=12,leftIndent=15,spaceBefore=2)]
story.append(toc)

page('1 Enunciado do projeto')
p('O projeto consiste em desenvolver uma família de aplicações de comércio eletrônico com ativos compartilhados e variabilidade explícita. Em vez de manter duas aplicações copiadas, a LPS deve derivar produtos a partir do mesmo código e de uma configuração válida. Roupas e alimentos diferem nas regras de seleção e de entrega, preservando a experiência básica de compra e os serviços comuns.')
p('As exigências inicialmente fornecidas foram a modelagem e a implementação de uma LPS, o uso de microsserviços e o uso de componentes de software. Python foi sugerido e agentes de inteligência artificial foram considerados opcionais. As escolhas de Next.js, FastAPI, SQLite, inicialmente três serviços e demonstração local foram decisões de projeto. A leitura posterior do roteiro de relatório acrescentou evidências e um requisito funcional de recomendação que não podem ser considerados atendidos apenas pelo escopo anterior.')
table(['Produto','Variabilidade obrigatória','Núcleo reutilizado'],[
 ('Roupas — essencial','Combinações válidas de tamanho/cor; sem agendamento ou promessa de prazo','Catálogo, carrinho, endereço, revisão, pedidos, Pix simulado e consulta'),
 ('Alimentos — despensa','Ingredientes, alergênicos, nutrição por porção; janela futura obrigatória','Mesmo frontend e serviços, com políticas selecionadas pelo manifesto')],[.22,.39,.39])
p('Cada implantação representa uma loja, com dados e segredos separados. A demonstração sequencial das variantes é suficiente para o escopo adotado. Não há estoque, reserva física, login, cartão, desconto, capacidade de agenda ou transferência financeira real. Produtos e informações alimentares são exclusivamente fictícios, sem alegação de certificação regulatória.')
h('2 Metodologia ágil escolhida')
p('A organização observada é iterativa e incremental, orientada por backlog e revisão de entregas. Cada incremento delimita um objetivo verificável, depende dos anteriores e registra decisões e limitações. O relatório utiliza práticas de priorização e inspeção de incrementos associadas ao desenvolvimento ágil (Beck et al., 2001), sem afirmar a realização de eventos ou papéis para os quais não há evidência.')
p('Para apresentar o Product Backlog e o Sprint Backlog pedidos no roteiro, os incrementos foram agrupados retrospectivamente em sete sprints documentais. Não há registro de timeboxes, Daily Scrum, Product Owner ou Scrum Master; portanto, não se declara conformidade integral ao Scrum definido por Schwaber e Sutherland (2020).')

page('3 Técnicas de reuso de software utilizadas')
p('A LPS concentra o reuso no domínio do comércio eletrônico: as duas variantes compartilham contratos, infraestrutura de configuração, interface, cálculo em centavos e fluxo de compra. A derivação ocorre por ativos comuns e regras de variabilidade, coerentemente com o desenvolvimento a partir de ativos compartilhados descrito por Northrop et al. (2012). O domínio é uma alternativa exclusiva; não existem features opcionais desligáveis no MVP.')
table(['Técnica','Aplicação concreta','Benefício e limite'],[
 ('Linha de Produto de Software','Manifestos clothing/food, modelo de features, schemas e composição de domínio','Uma base para dois produtos; novas variantes exigem regras e configuração explícitas'),
 ('Microsserviços','Catálogo, pedidos, pagamentos e recomendações com processos, APIs e armazenamento privados','Responsabilidades independentes; comunicação sujeita a falhas e timeouts'),
 ('Componentes de domínio','CatalogLoader, ProductSelectionValidator, DeliveryPolicy, TotalsCalculator e gateway de pagamento','Substituição por contrato; seleção concentrada no bootstrap'),
 ('Componentes visuais','Storefront, ProductMedia e FoodInformation','Interface comum com extensões do domínio; não são microsserviços')],[.24,.39,.37])
p('As camadas compartilhadas não permitem que um serviço abra o banco privado de outro. Pedidos resolve seleções por HTTP no catálogo e observa/autoriza pagamentos pela API interna. Compartilhar tipos e bibliotecas não significa compartilhar propriedade dos dados. O catálogo não consulta banco de pedidos, e o navegador não acessa diretamente a resolução interna ou a autorização de pagamentos.')
h('4 Desenvolvimento segundo a metodologia e o reuso')
p('O desenvolvimento partiu do diagnóstico do protótipo Básica/Premium, preservado como histórico. Em seguida, foram definidos o núcleo, o domínio exclusivo, os contratos e os componentes. A fundação materializou manifestos, processos, persistência e ambiente; os incrementos seguintes implementaram catálogo, revisão, admissão e pagamento recuperável. Por último, o frontend foi integrado no código e submetido à estabilização possível no ambiente.')
p('A inspeção de cada incremento orientou o próximo: validações de identidade precederam o catálogo; catálogos e políticas de entrega precederam revisões; revisões duráveis precederam pedidos; a admissão local precedeu a autorização simulada. Essa ordem reduziu o acoplamento entre evolução visual e regras de compra. A documentação diferencia artefato implementado, teste executado e evidência ainda pendente.')

page('5 Product Backlog e Sprint Backlogs')
p('O Product Backlog abaixo foi reconstruído a partir do escopo e dos arquivos do projeto. A prioridade representa dependência técnica e importância para a demonstração, não uma estimativa histórica de esforço. “Implementado” refere-se ao código; a homologação é informada separadamente.','Lead')
table(['ID','Item de backlog e aceitação resumida','Situação'],[
 ('PB01','Modelar núcleo, domínio XOR, dependências e configurações válidas','Documentado e implementado'),
 ('PB02','Validar manifestos e produzir identidade/hash iguais em Python/TypeScript','Implementado; vetores aprovados'),
 ('PB03','Iniciar os serviços com saúde, credenciais e dados privados','Implementado; suíte backend aprovada'),
 ('PB04','Disponibilizar catálogo estrito: dez roupas e seis alimentos','Implementado; testado'),
 ('PB05','Validar combinações de roupa e metadados alimentares','Implementado; testado'),
 ('PB06','Gerar janelas futuras de alimentos e rejeitar agenda em roupas','Implementado; testado'),
 ('PB07','Persistir revisão imutável por dez minutos, com total do servidor','Implementado; testado'),
 ('PB08','Admitir pedidos idempotentes e consumir cada revisão uma única vez','Implementado; testado'),
 ('PB09','Autorizar Pix simulado durável e recuperar incertezas sem duplicação','Implementado; suíte aprovada'),
 ('PB10','Oferecer sessão anônima, intermediário e carrinho por loja','Implementado; testes web aprovados'),
 ('PB11','Exibir catálogo, checkout e consulta nas duas identidades visuais','Implementado; validação visual pendente'),
 ('PB12','Validar build, fluxo Next→backend, instalação limpa e Compose','Parcial; bloqueios do ambiente'),
 ('PB13','Atender recomendação por histórico em serviço próprio — item 6.1 do roteiro','Implementado; testes offline e de fronteira aprovados; HTTP atual pendente'),
 ('PB14','Entregar seletor visual, capturas de telas/portas e URL do projeto','Seletor visual implementado; capturas e URL pendentes')],[.11,.63,.26])
note('PB13 e parte de PB14 não integravam o escopo inicialmente aprovado. A recomendação e o seletor visual foram implementados em incremento posterior. Capturas reais e URL específico continuam pendentes; código não substitui homologação.')

page('5 Continuação dos Sprint Backlogs')
p('Cada sprint documental reúne objetivo, seleção do backlog, tarefas e evidência. A numeração descreve a sequência dos incrementos; não se atribuem datas, reuniões ou duração inexistentes.','Lead')
for title,goal,ids,tasks,evidence in [
 ('Sprint 1 — Diagnóstico e modelagem','Definir a família e preservar o protótipo.','PB01','Analisar estrutura/dependências; distinguir exigências e decisões; definir features, contratos, componentes e limites.','docs/diagnostico.md, modelo-lps.md e arquitetura-atual.md; histórico Básica/Premium separado.'),
 ('Sprint 2 — Fundação executável','Derivar configurações e iniciar a arquitetura.','PB02, PB03','Criar manifestos estritos; hash comum; três apps FastAPI; schema privado; saúde e lançador; preparar Compose.','foundation/, services/*/app.py, configurations/, tools/lps.py e testes de fundação.'),
 ('Sprint 3 — Catálogo e domínio','Oferecer dados próprios e regras reutilizáveis.','PB04, PB05, PB06','Carregar catálogos imutáveis; validar seleções; implementar totais e políticas de entrega com relógio injetável.','demo-data/, domain/, services/catalog/ e testes de catálogo; APIs internas implementadas.'),
 ('Sprint 4 — Revisão persistida','Preparar a confirmação sem criar pedido prematuramente.','PB07','Resolver produtos por HTTP; validar endereço/janela; calcular total; persistir snapshot e TTL de dez minutos.','services/orders/service.py, repository.py e rotas de revisão; cenários positivos/negativos testados.')]:
 h(title,2);p('<b>Objetivo:</b> '+goal+' <b>Backlog:</b> '+ids+'.','Small');p('<b>Tarefas:</b> '+tasks,'Small');p('<b>Incremento e evidência:</b> '+evidence,'Small')

page('5 Conclusão dos Sprint Backlogs')
for title,goal,ids,tasks,evidence in [
 ('Sprint 5 — Pedido e pagamento recuperável','Admitir e confirmar compras com persistência.','PB08, PB09','Reservar chave; revalidar revisão; admitir em transação curta; observar/autorizar Pix; recuperar com leases e tentativas limitadas.','services/orders/checkout.py, order_repository.py, worker.py e services/payments/. A suíte completa registrada aprovou 67 testes de backend.'),
 ('Sprint 6 — Interface compartilhada','Expor o fluxo das duas variantes sem divulgar credenciais.','PB10, PB11','Construir identidade visual, catálogo, detalhe, carrinho, checkout e consulta; implementar cookie assinado, contexto e gateway por rotas fixas.','apps/store-ropa/src/. Registro anterior: dez testes da camada web aprovados; não comprovam renderização ou E2E.'),
 ('Sprint 7 — Estabilização e evidências','Conferir implementação e tornar bloqueios explícitos.','PB12 e levantamento de PB13/PB14','Corrigir reconciliação do carrinho e validação de respostas; executar verificações; preparar E2E isolado; registrar limitações e roteiro.','tools/validate.py, tools/e2e.py e docs/homologacao-2026-11-10.md. Lint/typecheck passaram em checagem posterior; build falhou por acesso negado no SWC.')]:
 h(title,2);p('<b>Objetivo:</b> '+goal+' <b>Backlog:</b> '+ids+'.','Small');p('<b>Tarefas:</b> '+tasks,'Small');p('<b>Incremento e evidência:</b> '+evidence,'Small')
h('Critérios de conclusão e tratamento das pendências',2)
p('Uma tarefa não é considerada homologada apenas porque o código existe. Para regras de domínio, exige-se validação de cenários pertinentes; para a aplicação completa, exige-se build, execução da interface e fluxo entre Next.js e serviços. Na estabilização, bloqueios externos foram mantidos no relatório, em vez de substituir ferramentas reais por simulações ou alterar pacotes globais.')
p('O incremento adicional implementou recomendações por preferências e histórico, dez imagens locais, seletor visual em /configurador e painel de microsserviços. A coleta de capturas de execução continua pendente; não há evidência de homologação visual. O projeto não é uma LPS de jogos; o vídeo específico pedido no item 11 não se aplica.')

page('5.1 Diagrama de features')
diagram(275,[
 (145,229,165,38,'LPS de comércio eletrônico',pale),
 (8,153,205,44,['Núcleo obrigatório','Catálogo, carrinho e checkout'],None),
 (246,153,196,44,['Domínio exclusivo XOR','Escolher exatamente uma variante'],None),
 (8,78,205,50,['Pedidos e consulta da sessão','Endereço e Pix simulado'],None),
 (235,78,96,44,'Roupas',pale),(344,78,98,44,'Alimentos',pale),
 (232,7,102,48,['Tamanho e cor','por combinação'],None),(340,7,106,48,['Info. alimentar','Agenda obrigatória'],None)
],[((175,229),(110,197)),((280,229),(344,197)),((110,153),(110,128)),((298,153),(283,122)),((390,153),(392,122)),((283,78),(283,55)),((392,78),(392,55))])
caption('Figura 1 — Modelo de features da família. Fonte: elaboração própria a partir de docs/modelo-lps.md.')
p('O núcleo é obrigatório nos dois produtos. O grupo de domínio tem cardinalidade 1..1: roupas ou alimentos. Seleção de tamanho/cor exige roupas; informação alimentar e agendamento exigem alimentos e são inseparáveis nesta versão. Não se classifica como opcional uma capacidade que o projeto não permite desligar.')
table(['Feature','Roupas','Alimentos'],[('Catálogo, carrinho, checkout e pedidos','Obrigatória','Obrigatória'),('Endereço e Pix simulado','Obrigatória','Obrigatória'),('size_color_selection','Obrigatória','Excluída'),('food_information','Excluída','Obrigatória'),('delivery_scheduling','Excluída','Obrigatória'),('Features opcionais desligáveis','Nenhuma','Nenhuma')],[.6,.2,.2])
p('Seja K o conjunto {catalog, cart, checkout, orders, simulated_pix, address_delivery}. As configurações válidas são K acrescido de size_color_selection para roupas, ou K acrescido de food_information e delivery_scheduling para alimentos. Exemplos inválidos incluem features duplicadas, domínio food com size_color_selection, roupas com entrega scheduled ou ausência de componente obrigatório.')

page('5.2 Arquitetura em camadas e variabilidade')
diagram(286,[(25,237,400,40,['Apresentação','Storefront, ProductMedia e FoodInformation'],pale),(25,179,400,40,['Fronteira web','Route Handlers, sessão, Origin e projeção pública'],None),(25,121,400,40,['Aplicação em cada microsserviço','CatalogService, ReviewService e Checkout'],None),(25,63,400,40,['Domínio reutilizável','Seleção, entrega, totais e contratos'],None),(25,5,400,40,['Infraestrutura privada por serviço','HTTP, arquivos validados, SQLite e repositórios'],pale)],[((225,237),(225,219)),((225,179),(225,161)),((225,121),(225,103)),((225,63),(225,45))])
caption('Figura 2 — Visão lógica em camadas. Cada serviço preserva sua própria fronteira de aplicação e dados.')
p('A apresentação coleta escolhas, mas não define o preço final. O intermediário autentica a sessão e recompõe cabeçalhos internos. A aplicação coordena casos de uso; o domínio valida seleções, entrega e totais; a infraestrutura executa I/O. O diagrama de camadas complementa a implantação em microsserviços: não representa um único banco ou um processo monolítico.')
table(['Ponto de variação','Variante roupas','Variante alimentos','Vinculação'],[('Domínio da loja','clothing','food','Bootstrap pelo manifesto'),('Seleção','ClothingSelectionValidator','FoodSelectionValidator','Registro em compose'),('Entrega','UnscheduledDelivery','ScheduledDelivery','Registro em compose'),('Apresentação','Tamanho/cor e identidade essencial','Metadados, agenda e identidade despensa','Configuração pública'),('Dados de catálogo','clothing-demo-v1','food-demo-v1','Carga inicial validada')],[.2,.29,.29,.22])

page('5.3 Componentes de software e variabilidade')
diagram(260,[(150,222,150,38,['Configuração validada','Domínio e identidade'],pale),(5,154,300,44,['Domínio compartilhado','compose(config, clock)'],pale),(320,154,130,44,['Aplicação de pedidos','Bootstrap e Checkout'],pale),(0,65,95,55,['Catálogo e totais','Implementações','comuns'],None),(104,65,95,55,['Seleção de produto','Clothing ou Food','Ponto de variação'],None),(208,65,95,55,['Política de entrega','Agendada ou não','Ponto de variação'],None),(320,65,130,55,['Gateway de pagamento','Cliente tipado de','Pix simulado'],None)],[((210,222),(155,198)),((285,222),(385,198)),((55,154),(47,120)),((155,154),(151,120)),((255,154),(255,120)),((385,154),(385,120))])
caption('Figura 3 — Composição de componentes comuns e alternativos. O domínio é composto em domain/composition.py; o gateway de pagamentos é instanciado no bootstrap de pedidos.')
table(['Contrato','Entradas e saídas','Uso e seleção'],[
 ('CatalogLoader','Manifesto e fonte → snapshot validado ou erro','Catálogo; JsonCatalogLoader compartilhado'),
 ('ProductSelectionValidator','Produto e seleção → item resolvido ou erro','Catálogo; Clothing/Food pelo domínio'),
 ('DeliveryPolicy','Endereço, slot e relógio → snapshot; list_slots → janelas','Pedidos; agendada ou não agendada'),
 ('TotalsCalculator','Itens resolvidos → linhas, subtotal e total em centavos','Pedidos; cálculo puro, sem I/O'),
 ('SimulatedPaymentGateway','Pedido/valor persistidos → autorização observada ou erro','Pedidos; cliente de API interna de pagamentos')],[.27,.4,.33])
p('Os contratos de domínio usam Protocol em domain/contracts.py. O registro em domain/composition.py seleciona estratégias no início, evitando espalhar condicionais pelos handlers. O gateway de pagamento é uma fronteira de aplicação implementada em services/orders/payment_client.py; sua autorização durável pertence ao serviço de pagamentos. Componentes visuais são unidades React e não substituem os contratos de domínio.')

page('5.4 Configuração e construção de produtos')
p('A configuração real é declarativa e versionada. Os arquivos configurations/clothing.json e configurations/food.json incluem schema_version, store_id, domínio, features, fonte de catálogo, entrega e pagamento. Schemas fechados rejeitam propriedades desconhecidas, features duplicadas e combinações de domínio incompatíveis. O hash SHA-256 determinístico considera a normalização documentada e é comparado nas chamadas entre processos.')
table(['Propriedade','Roupas','Alimentos'],[('store_id','roupas-demo','alimentos-demo'),('domain','clothing','food'),('features de domínio','size_color_selection','food_information, delivery_scheduling'),('delivery.policy','unscheduled','scheduled'),('Horizonte e janelas','Não aplicável','7 dias; 09h–12h e 14h–17h'),('payment.provider','simulated_pix','simulated_pix'),('discount_cents / shipping_cents','0 / 0','0 / 0')],[.32,.3,.38])
h('Seleção efetivamente implementada',2)
code('python tools/lps.py init clothing\npython tools/lps.py run clothing --dev\n\n# Após encerrar a primeira variante:\npython tools/lps.py init food\npython tools/lps.py run food --dev')
p('O lançador seleciona o manifesto e inicia o mesmo frontend e os mesmos quatro serviços. A derivação utiliza infraestrutura, contratos e políticas comuns; não cria uma cópia independente do código. Os dados privados ficam em var/&lt;store_id&gt;/orders e var/&lt;store_id&gt;/payments. Recomendações possui seu banco em var/&lt;store_id&gt;/recommendations. A sacola é separada por loja no navegador. Ao reiniciar a mesma loja, devem ser preservados bancos, segredos e cookie da sessão.')
p('A tela /configurador permite escolher exclusivamente roupas ou alimentos, visualizar as features obrigatórias, baixar o manifesto validado e obter os comandos de construção e execução. A troca de processo é explícita pelo lançador; a tela não modifica a loja ativa nem executa shell no servidor. O download corresponde ao manifesto versionado da variante. A captura dessa tela em execução ainda depende do ambiente.')

page('6 Arquitetura baseada em microsserviços')
diagram(320,[(137,273,176,36,['Navegador','mesma origem'],pale),(104,207,242,43,['Next.js  :3000','Interface, sessão e API Gateway'],pale),(0,111,137,51,['Catálogo  :8001','FastAPI'],None),(157,111,137,51,['Pedidos  :8002','FastAPI + recuperação'],None),(314,111,137,51,['Pagamentos  :8003','FastAPI — Pix simulado'],None),(0,20,137,43,['JSON próprio','snapshot em memória'],pale),(157,20,137,43,['SQLite privado','revisões e pedidos'],pale),(314,20,137,43,['SQLite privado','autorizações'],pale)],[((225,273),(225,250)),((149,207),(68,162)),((225,207),(225,162)),((157,135),(137,135)),((294,135),(314,135)),((68,111),(68,63)),((225,111),(225,63)),((382,111),(382,63))])
caption('Figura 4 — Arquitetura implementada e armazenamento privado. A checagem de prontidão do frontend também consulta pagamentos; autorização de negócio não é exposta ao navegador.')
p('Cada microsserviço executa em processo próprio. Pedidos consulta o catálogo por API e acessa pagamentos por credencial exclusiva. Catálogo mantém arquivos fictícios validados e congelados durante execução. SQLite é utilizado somente no serviço proprietário dos dados. O Compose prevê somente a porta 3000 publicada; no modo local, os serviços usam loopback e credenciais internas.')
h('6.1 Recomendação considerando o histórico',2)
p('O serviço services/recommendations executa em processo próprio na porta 8004. Obtém candidatos por API autenticada do catálogo, persiste preferências e até cem eventos por sessão/loja em SQLite privado e retorna até seis sugestões explicadas. Não lê bancos de outros serviços. O algoritmo é determinístico, sem IA em execução.')
p('Categorias e histórico orientam a pontuação; orçamento limita o preço e tamanho/cor devem corresponder à mesma combinação habilitada. O usuário pode limpar preferências e pausar a coleta. Há testes de modelos, ranking, isolamento e persistência, além de contratos web; os testes HTTP novos aguardam ambiente funcional.')

page('6.2 Especificação documentada do API Gateway')
p('O Next.js atua como Backend for Frontend e gateway de rotas fixas. A entrada está em src/app/api/v1/[...path]/route.ts e delega à função createWebApi de src/lib/web-api.ts. O intermediário valida método, origem e JSON, aplica limites e timeouts, autentica cookie e recompõe os cabeçalhos de serviço. Route Handlers utilizam Request/Response e constituem a fronteira HTTP da aplicação (Vercel, documentação Next.js 15).')
code("// src/app/api/v1/[...path]/route.ts\nimport { createWebApi } from '@/lib/web-api';\nexport const runtime='nodejs';\nexport const dynamic='force-dynamic';\nexport const GET=createWebApi();\nexport const POST=GET;")
table(['Rota pública','Destino e finalidade'],[('POST /api/v1/session','Local; cria/reutiliza cookie assinado'),('GET /api/v1/store','Local; projeção pública, sem segredos'),('GET /api/v1/products[/{id}]','Catálogo; listagem/detalhe'),('GET /api/v1/delivery-slots','Pedidos; janelas de alimentos'),('POST /api/v1/reviews','Pedidos; revisão com sessão'),('POST /api/v1/orders','Pedidos; admissão com Idempotency-Key'),('GET /api/v1/orders/{id}','Pedidos; snapshot do dono'),('GET /api/v1/order-attempts/{key}','Pedidos; retomada por chave'),('GET/POST /api/v1/preferences','Recomendações; preferências da sessão'),('GET /api/v1/recommendations','Recomendações; sugestões explicadas'),('POST /api/v1/recommendation-events','Recomendações; histórico limitado'),('POST /api/v1/recommendation-reset','Recomendações; limpar e pausar')],[.45,.55])
p('O cookie tem SID aleatório, loja, emissão/expiração e HMAC-SHA256; HttpOnly, SameSite=Lax e duração de 30 dias. Secure é usado em HTTPS. O intermediário deriva session_owner e transmite X-Session-Owner somente em chamadas privadas autenticadas. SID e credenciais não são enviados no JSON nem persistidos em localStorage.')
p('O limite do corpo é 64 KiB; respostas internas são limitadas a 1 MiB. O timeout é de seis segundos, ou onze para admissão; o cliente usa quinze segundos. Não são seguidos redirecionamentos nem repetidas mutações automaticamente. Respostas privadas usam no-store; identidade/hash e coerência comercial são conferidos antes de responder.')

page('6.3 Especificação dos microsserviços')
h('Serviço de catálogo',2)
p('A entrada services/catalog/app.py utiliza o bootstrap comum. services/catalog/routes.py mantém handlers pequenos e delega à aplicação CatalogService. Os modelos são estritos e discriminados por kind. A seleção de roupas exige combination_id habilitado e pertencente ao produto; alimentos proíbe esse campo, inclusive null. Não são aceitos preços do cliente. O catálogo não possui banco relacional.')
table(['Método e rota interna','Permissão','Resposta ou erro'],[('GET /internal/v1/products','web','200; store_id, catalog_revision, items'),('GET /internal/v1/products/{id}','web','200 produto; 404 desconhecido'),('POST /internal/v1/selections/resolve','orders','Lista integral resolvida; sem resultado parcial'),('GET /health/live','Pública','Vida do processo'),('GET /health/ready','Interna','Identidade, configuração e catálogo carregado')],[.48,.15,.37])
code("# services/catalog/routes.py — excerto real\nasync def products(request: Request):\n    return request.app.state.catalog.list_products()\n\nasync def product(product_id: str, request: Request):\n    return request.app.state.catalog.detail(product_id)\n\nasync def resolve(body: ResolveRequest, request: Request):\n    return request.app.state.catalog.resolve(body)")
caption('Listagem 1 — Delegação dos handlers. Os decorators e dependências de permissão estão no arquivo integral.')
p('A resolução recebe entre uma e cinquenta seleções únicas, com quantidades estritamente inteiras de 1 a 100. Dois tamanhos/cores do mesmo produto podem ocupar linhas distintas; repetir a mesma identidade de seleção é inválido. O catálogo ativo contém dez roupas com imagens locais e seis alimentos, com preços em centavos e IDs estáveis.')
p('A revisão comercial é determinística: alterações relevantes de preço, combinação ou informação alimentar mudam catalog_revision; formatação JSON e reordenação de produtos/combinações não mudam o conteúdo normalizado. Ausência ou inconsistência do catálogo impede a inicialização, sem expor caminhos privados nas respostas.')

page('6.3 Serviço de pedidos')
p('Pedidos coordena os casos de uso em ReviewService e Checkout. Seu banco privado conserva reviews, attempts e orders no schema 1. Revisões contêm entrada normalizada, itens e valores resolvidos, entrega, identidade/config_hash e expiração de dez minutos. A revisão não reserva estoque ou preço e não representa pedido confirmado.')
table(['Rota interna','Contrato e comportamento'],[('GET /internal/v1/delivery-slots','200 com server_now/timezone/items em alimentos; roupas retorna FEATURE_NOT_AVAILABLE'),('POST /internal/v1/reviews','web + dono; 201 somente após persistir snapshot'),('POST /internal/v1/orders','web + dono + chave UUIDv4; recebe store_id/review_id'),('GET /internal/v1/orders/{id}','Snapshot persistido; recurso de outro dono retorna 404'),('GET /internal/v1/order-attempts/{key}','Consulta sem criar nova tentativa ou reiniciar contadores')],[.48,.52])
code("# services/orders/checkout_models.py\nclass OrderCommand(FrozenModel):\n    store_id: Identifier\n    review_id: UUID4 = Field(strict=False)\n\n# services/orders/checkout_routes.py — excerto\nasync def get_order(order_id: UUID4, request: Request,\n                    owner=Depends(trusted_session)):\n    return await request.app.state.checkout.get_order(\n        owner, order_id)")
p('Antes da admissão, pedidos revalida configuração, validade da revisão, seleções, preços e janela. Mudança relevante produz REVIEW_CHANGED; não se aceita automaticamente um novo total. A chave de idempotência é única por loja e dono: mesmo comando recupera o resultado; conteúdo diferente gera 409. Cada revisão pode originar no máximo um pedido, por restrição local.')
p('A reserva/admissão e o vínculo entre tentativa e pedido são locais e duráveis. Estados de tentativa: validating, accepted e rejected. Estados de pedido: payment_pending, payment_unknown, confirmed e payment_conflict. Nenhuma transação SQLite é mantida aberta durante HTTP. Consultas leem snapshots, mesmo após alteração do catálogo ou reinício.')

page('6.3 Serviço de pagamentos e recuperação')
p('Pagamentos implementa somente Pix simulado, sem desconto, QR Code ou dados bancários. O banco authorizations é privado e mantém unicidade por loja/pedido. O valor é recebido de pedidos já admitidos, nunca diretamente do navegador. O único estado de autorização simulada é approved; incerteza é um estado observado em pedidos, não uma segunda decisão financeira.')
table(['Rota interna','Permissão','Semântica'],[('PUT /internal/v1/payments/by-order/{id}','orders','201 na primeira autorização; 200 no replay; 409 se valor/comando divergir'),('GET /internal/v1/payments/by-order/{id}','orders','200 na autorização encontrada; 404 explícito se ausente')],[.47,.15,.38])
code("# services/payments/routes.py — excerto com quebras visuais\n@router.get('/by-order/{order_id}',\n            response_model=AuthorizationResponse)\nasync def lookup(order_id: UUID4, request: Request):\n    try:\n        result = await asyncio.to_thread(\n            request.app.state.repository.lookup, order_id)\n    except StorageError:\n        raise DomainError(\n            'PAYMENT_STORAGE_UNAVAILABLE') from None\n    if result is None:\n        raise DomainError('PAYMENT_NOT_FOUND')\n    return result")
h('Sequência normal e falhas',2)
p('A sequência é: persistir revisão; reservar chave; revalidar; admitir pedido em transação local; consultar autorização; somente diante de 404, autorizar com o mesmo order_id; persistir confirmação. Perda de resposta após aprovação é tratada por nova observação da autorização existente. A semântica de métodos e códigos HTTP é apoiada na RFC 9110 (Fielding; Nottingham; Reschke, 2022), mas a deduplicação é garantida pelas regras e restrições da aplicação.')
p('O worker usa leases persistidos de quinze segundos, versão e gravação condicional. Há até cinco execuções por ciclo, com intervalos 2/4/8/16 segundos e retomada manual após cooldown de pelo menos trinta segundos. GET não reinicia contador. Reinício conserva estados e não cria outra autorização. Não se promete processamento exatamente uma vez nem transação distribuída.')

page('6.3 Serviço de recomendações')
p('GET /internal/v1/preferences e GET /internal/v1/recommendations consultam o perfil e as sugestões. POST /internal/v1/preferences salva escolhas; POST /internal/v1/recommendation-events registra view ou add_to_cart com UUID v4 idempotente; POST /internal/v1/recommendation-reset limpa e pausa o histórico. Todas exigem credencial exclusiva web e dono derivado da sessão. O gateway expõe os mesmos sufixos em /api/v1, com no-store e validação de origem nas mutações.')
code("# services/recommendations/routes.py - excerto\n@router.get('/recommendations',\n            response_model=RecommendationResponse)\nasync def recommendations(request: Request,\n                          owner=Depends(trusted_session)):\n    return await request.app.state.recommendations.recommend(owner)")
p('O componente puro ranking.py pontua categoria (+6), cor (+3), tamanho (+2) e categoria do histórico (até +6). Produtos já vistos recebem -2. Empates usam ID. O repositório privado impõe unicidade de eventos e limite de cem eventos por perfil. Sem transações abertas durante HTTP; respostas do catálogo são validadas e usam timeout e repetição limitada.')

page('6.4 Portas e evidência dos serviços em execução')
table(['Processo','Porta local','Responsabilidade'],[('Frontend Next.js','3000','Interface e intermediário de APIs'),('Catálogo FastAPI','8001','Consulta e resolução interna de seleções'),('Pedidos FastAPI','8002','Agenda, revisão, pedido e recuperação'),('Pagamentos FastAPI','8003','Autorização e consulta simuladas'),('Recomendações FastAPI','8004','Preferências, histórico e sugestões')],[.3,.19,.51])
p('As portas acima são definidas em tools/lps.py e Compose. Os testes de integração utilizam portas temporárias, o que permite executar serviços em processos independentes sem modificar recursos de demonstração. A aprovação da suíte comprova os cenários testados, mas não substitui a captura das portas exigida pelo item 6.4.')
code("# PowerShell — serviços em terminais separados\n.\\.venv\\Scripts\\python.exe tools/lps.py service clothing `\n  --service catalog\n.\\.venv\\Scripts\\python.exe tools/lps.py service clothing `\n  --service payments\n.\\.venv\\Scripts\\python.exe tools/lps.py service clothing `\n  --service orders\n.\\.venv\\Scripts\\python.exe tools/lps.py service clothing `\n  --service recommendations\n\n# Após iniciar o frontend, conferir as cinco portas:\nGet-NetTCPConnection -State Listen |\n  Where-Object { $_.LocalPort -in 3000,8001,8002,8003,8004 } |\n  Select-Object LocalAddress,LocalPort,OwningProcess")
p('Uma captura válida deve mostrar data/contexto da execução e processos/portas efetivamente ativos, ocultando credenciais. Também se deve registrar o estado agregado em http://127.0.0.1:3000/health/ready e distinguir liveness de readiness. Dependência indisponível degrada prontidão sem afirmar que o processo morreu.')
note('Não foi obtida captura verificável das quatro portas durante a elaboração. Não se apresenta tabela, comando ou saída fabricada como uma tela de processos em execução. O build do frontend permaneceu bloqueado por acesso negado no SWC; portanto, a evidência visual do item 6.4 precisa ser anexada em ambiente funcional.')

page('6.5 Construção de um produto a partir da LPS')
p('A engenharia de aplicação instancia ativos comuns conforme a configuração. A derivação de roupas/alimentos já está representada pelos manifestos e pelo registro de componentes. Os passos abaixo constituem o procedimento executável documentado, sem confundir instrução de execução com execução aprovada.')
table(['Passo','Procedimento e verificação'],[('1 — Preparar','Usar Python 3.11, Node/npm e dependências reais. Instalar requirements-dev.txt e npm ci pelo lockfile em ambiente com acesso aos índices.'),('2 — Configurar','Selecionar configurations/clothing.json ou food.json. Não incluir segredos no manifesto; bootstrap rejeita configuração inválida.'),('3 — Inicializar','Executar tools/lps.py init <variante>; preservar .local/<store_id>.env e SESSION_SECRET entre reinícios.'),('4 — Iniciar','Executar tools/lps.py run <variante> --dev ou iniciar os serviços por --service. Todos recebem a mesma identidade/hash.'),('5 — Conferir','Verificar prontidão, origem http://127.0.0.1:3000, catálogo correspondente e bancos privados por loja.'),('6 — Demonstrar','Roupas: combinações; alimentos: metadados e janela futura. Revisar e confirmar sem dados financeiros reais.'),('7 — Reiniciar','Conservar bancos/segredos/cookie; consultar pedido da sessão original. Não usar down -v no reinício normal.'),('8 — Trocar variante','Encerrar a implantação; executar a outra variante. Conferir isolamento de dados e sacola.')],[.24,.76])
code("# Execução local na raiz do projeto\n.\\.venv\\Scripts\\python.exe tools/lps.py init clothing\n.\\.venv\\Scripts\\python.exe tools/lps.py run clothing --dev\n\n# Alimentos, após Ctrl+C na execução anterior\n.\\.venv\\Scripts\\python.exe tools/lps.py init food\n.\\.venv\\Scripts\\python.exe tools/lps.py run food --dev")
p('Um novo produto concreto pode ser derivado de uma configuração válida dentro do domínio suportado; a inclusão de um terceiro domínio demanda novos componentes e regras no schema, e não somente alteração de nome. O relatório demonstra a derivação documental das duas variantes existentes, sem afirmar que uma terceira aplicação foi construída ou testada.')

page('7 Tecnologias utilizadas na implementação')
table(['Unidade','Tecnologias e linguagem','Dados e estado'],[('Frontend e gateway','Next.js 15.3.1, React 19, TypeScript e Tailwind CSS 4; Node.js','Carrinho/referências no navegador; cookie assinado; sem banco próprio'),('Catálogo','Python 3.11, FastAPI 0.141.1, Pydantic 2.13.4 e Uvicorn 0.49.0','JSON fictício validado; snapshot imutável em memória'),('Pedidos','Python/FastAPI; Protocol, componentes e cliente HTTP tipado','SQLite privado; schema 1; revisões, tentativas e pedidos'),('Pagamentos','Python/FastAPI; repositório de autorização simulada','SQLite privado; authorizations e metadata'),('Recomendações','Python/FastAPI; ranking determinístico e cliente do catálogo','SQLite privado; profiles, events e metadata'),('Ambiente','Dockerfiles, Docker Compose e lançador Python/PowerShell','Volumes por serviço e projeto; arquivos de configuração somente leitura'),('Validação','unittest, Node test runner, vetores e testes HTTP','Recursos temporários; relatório local de resultados')],[.23,.43,.34])
p('Os números de versão são os fixados/registrados no projeto; React, TypeScript e Tailwind possuem faixas no package.json, com resolução no package-lock.json. O SQLite é acessado pela biblioteca padrão do Python, com transações curtas, chaves estrangeiras e inicialização compatível e repetível. O framework não transforma validação de schema em garantia de negócio: invariantes de revisão, pagamento e propriedade são implementadas pela aplicação (Python Software Foundation, documentação sqlite3; FastAPI, documentação oficial).')
h('Validação e reprodutibilidade',2)
table(['Verificação','Evidência disponível'],[('Backend completo','Histórico anterior: 67 testes aprovados. Incremento atual bloqueado pelo preflight de loopback'),('Offline atual','43 testes aprovados; não certificam HTTP/asyncio/worker'),('Fronteira web e configuração','16 testes Node e 24 vetores aprovados; sem comprovação de renderização'),('Checagem posterior do frontend','Lint e typecheck passaram; build falhou ao carregar next.config.ts por acesso negado no SWC'),('E2E visual, instalação limpa e Compose','Não aprovados; sem evidência de execução completa')],[.37,.63])
note('A validação atual aprovou lint/typecheck e testes offline/web. Build falhou por acesso negado no SWC; HTTP completo/E2E foram bloqueados pelo preflight de loopback. pip check apontou conflito preexistente de setuptools/streamlit-vis-network; instalação limpa e Compose permanecem pendentes.')

page('8 Funcionamento do produto e telas')
p('A interface possui duas identidades visuais da mesma aplicação: “essencial” para roupas e “despensa” para alimentos. O layout usa tipografia de sistema, fotos ilustrativas locais e fallback SVG, busca, categorias, diálogo de produto, fluxo de compra e consulta. Não depende de fotografias remotas. A descrição abaixo está baseada no código de Storefront, ProductMedia e FoodInformation; não substitui a sequência de capturas reais exigida pelo roteiro.')
table(['Tela ou estado','Ação do usuário e comportamento','Microsserviço relacionado'],[('Vitrine','Buscar/filtrar; consultar listagem real; backend indisponível mostra erro, sem catálogo de sucesso fictício','Catálogo, via Next.js'),('Detalhe de roupas','Selecionar combinação explícita habilitada e quantidade; desabilitada não representa estoque','Catálogo'),('Detalhe de alimentos','Ver ingredientes, alergênicos conhecidos/ausência declarada/desconhecidos e nutrição por porção','Catálogo'),('Sacola','Editar/remover linhas; persistência separada por loja; valores apenas estimados','Estado local; backend confere depois'),('Entrega','Informar endereço fictício; em alimentos escolher janela futura de São Paulo','Pedidos'),('Revisão','Receber snapshot e total do servidor; validade de dez minutos; sem reserva','Pedidos consulta catálogo'),('Confirmação','Enviar review_id e chave preservada; nenhum dado bancário/cartão','Pedidos e pagamentos simulados'),('Consulta','Ver estado, valores e entrega preservados; recuperar por tentativa com a sessão original','Pedidos; pagamento observado por pedidos')],[.24,.55,.21])
p('A sacola só é limpa após confirmação e se a seleção atual ainda corresponde à tentativa, preservando edições feitas enquanto a chamada estava em andamento. Estado incerto não significa compra fracassada. A interface acompanha automaticamente estados intermediários com até doze consultas, a cada dois segundos, sem reenviar mutações. O bootstrap de sessão é compartilhado entre recomendações e checkout para evitar cookies concorrentes. A interface permite consultar e reenviar a mesma chave, e bloqueia retomada com contexto de sessão diferente. Não há recuperação de pedido apenas por nome ou ID sem o cookie original.')
note('Capturas de desktop/celular, de cada etapa da compra e da identidade dos serviços na interface principal não foram produzidas. A página principal possui painel de microsserviços com portas configuradas e consulta real de prontidão. A tela de configuração fica em /configurador. Esses componentes aguardam captura em execução. Nenhuma imagem esquemática foi apresentada como execução real.')

page('9 Código do projeto e disponibilização no GitHub')
p('A autora informou o identificador público emilyrch. O endereço https://github.com/emilyrch corresponde ao perfil informado, não identifica o repositório do projeto e não comprova publicação ou versão disponível. Não foi encontrado um diretório .git na cópia analisada. Portanto, o URL específico solicitado na capa pelo item 9 permanece pendente.')
table(['Diretório ou arquivo','Conteúdo a disponibilizar'],[('apps/store-ropa/src/','Frontend, sessão, gateway e componentes visuais'),('services/catalog/','APIs e aplicação de catálogo'),('services/orders/','Revisão, admissão, consultas, cliente de pagamento e worker'),('services/payments/','Autorização simulada durável'),('domain/ e foundation/','Contratos/componentes e infraestrutura comum'),('configurations/, shared/ e demo-data/','Manifestos, schemas/vetores e catálogos fictícios'),('tests/ e tools/','Validações, lançador e teste E2E preparado'),('README.md, docs/, Dockerfiles e Compose','Instalação, arquitetura, contratos, evidências e execução')],[.4,.6])
p('O repositório deve excluir .local, bancos privados, segredos, node_modules, .venv e artefatos de build. O .gitignore contém essas exclusões, mas sua presença não comprova que uma publicação anterior esteja livre desses arquivos. Antes de publicar, devem ser revisados os arquivos efetivamente incluídos e o README com os passos reproduzíveis.')
h('Limites da entrega verificada',2)
p('O relatório não certifica funcionamento integral do código no GitHub: a publicação não foi demonstrada e a homologação do frontend não foi concluída. O backend possui evidências de testes completos, e as verificações posteriores de lint/typecheck não apresentaram erros. O build permanece impedido por permissão no ambiente. A causa ambiental não autoriza afirmar que o fluxo visual completo já foi aprovado.')
p('Para reprodução e atualização das evidências, executar tools/validate.py em ambiente funcional e conservar o relatório gerado em .local/validation-latest.json como evidência local, sem publicar credenciais. O teste tools/e2e.py utiliza portas, bancos e tokens temporários; mesmo quando aprovado, ainda deve ser complementado por inspeção do navegador.')

page('10 Referências bibliográficas')
refs=[
 ('BECK, Kent et al.','Manifesto para Desenvolvimento Ágil de Software','2001','https://agilemanifesto.org/iso/ptbr/manifesto.html'),
 ('SCHWABER, Ken; SUTHERLAND, Jeff.','The Scrum Guide','2020','https://scrumguides.org/scrum-guide.html'),
 ('NORTHROP, Linda M. et al.','A Framework for Software Product Line Practice Version 5.0','Pittsburgh: Software Engineering Institute, Carnegie Mellon University, 2012','https://www.sei.cmu.edu/library/a-framework-for-software-product-line-practice-version-50/'),
 ('FASTAPI.','Documentação oficial do FastAPI','s.d.','https://fastapi.tiangolo.com/'),
 ('VERCEL.','Next.js 15 Route Handlers and Middleware','s.d.','https://nextjs.org/docs/15/app/getting-started/route-handlers-and-middleware'),
 ('PYTHON SOFTWARE FOUNDATION.','sqlite3 DB API 2.0 interface for SQLite databases','Documentação Python 3.11, s.d.','https://docs.python.org/3.11/library/sqlite3.html'),
 ('FIELDING, Roy; NOTTINGHAM, Mark; RESCHKE, Julian.','HTTP Semantics RFC 9110','Internet Engineering Task Force, 2022','https://www.rfc-editor.org/rfc/rfc9110.html'),
 ('UNIVERSIDADE FEDERAL DE ALAGOAS.','Identidade Visual','s.d.','https://ufal.br/ufal/comunicacao/manuais/identidade-visual')]
for author,title,year,url in refs:p(f'{escape(author)} <b>{escape(title)}</b>. {escape(year)}. Disponível em: <link href="{url}" color="#193c57">{url}</link>. Acesso em: 10 nov. 2026.','Lead')
p('UNIVERSIDADE FEDERAL DE ALAGOAS. <b>Elementos do Relatório do Projeto 2026 2</b>. Disciplina Tópico em Engenharia de Software, “Projetando Linhas de Produto de Software”. Material de orientação fornecido pela autora, 2 p., 2026. Nome do docente não informado.','Lead')
p('ROCHA, Emily Vitória de Jesus. <b>Documentação técnica e código da LPS de comércio eletrônico</b>. Arquivos locais: docs/modelo-lps.md, arquitetura-atual.md, contratos-api.md, recuperacao.md, entrega-final.md e homologacao-2026-11-10.md; código de domain/, foundation/, services/ e apps/store-ropa/src/. Versão analisada em 10 nov. 2026. Repositório específico ainda não informado.','Lead')

page('11 Aplicabilidade do vídeo e conclusão')
p('O item 11 do roteiro solicita vídeo para uma Linha de Produto de Jogos. A família desenvolvida é de comércio eletrônico, portanto esse requisito condicional não se aplica. Não foi informado link de vídeo e não se afirma existir uma gravação da aplicação.')
p('O trabalho evidencia reuso de ativos por uma LPS com núcleo comum e variabilidade restrita, decomposição em microsserviços e componentes substituíveis por contrato. A integração comercial preserva preços e entrega no pedido, mantém dados privados por serviço e trata repetição/indisponibilidade com persistência e recuperação limitada. Essas decisões são sustentadas por evidências de backend e testes da fronteira web, dentro de seus respectivos alcances.')
p('A recomendação em serviço próprio, o seletor visual e a identificação dos serviços na interface foram implementados. A entrega integral ainda exige captura real das portas e das telas, URL específico do projeto na capa e homologação do frontend em ambiente funcional. O relatório torna essas diferenças explícitas, sem converter itens planejados em resultados realizados.')
h('Matriz final de atendimento ao roteiro',2)
table(['Item','Atendimento documental e pendência'],[('1 a 4','Enunciado, método, reuso e evolução descritos; backlogs retrospectivos sem cerimônias inventadas'),('5 e 5.1 a 5.3','Product/Sprint Backlogs, features, camadas, componentes e variabilidade apresentados'),('5.4','Seletor visual /configurador gera manifesto validado e comandos; derivação usa o lançador'),('6 e 6.1','Quatro microsserviços implementados, incluindo recomendações por perfil/histórico'),('6.2 e 6.3','Gateway e serviços especificados com rotas, modelos e excertos reais comentados no texto'),('6.4','Portas e comandos definidos; captura de execução pendente'),('6.5 e 7','Derivação passo a passo, tecnologias, linguagem e dados de cada serviço apresentados'),('8','Fluxo e painel de serviços implementados; capturas reais e homologação visual pendentes'),('9','Perfil informado na capa; URL do repositório/publicação funcional não comprovados'),('10 e 11','Referências apresentadas; vídeo condicional de jogos não aplicável'),('Identificação e marca','Autora, curso, campus e disciplina preenchidos; docente e brasão oficial pendentes')],[.24,.76])

doc=Report(str(OUT),pagesize=(W,H),leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,allowSplitting=True)
doc.addPageTemplates([PageTemplate(id='academic',frames=[Frame(LEFT,BOTTOM,CW,H-TOP-BOTTOM,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=header)])
doc.multiBuild(story)
print(OUT)
