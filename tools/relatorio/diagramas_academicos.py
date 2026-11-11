"""Vector academic diagrams. UML interfaces/realizations are distinct from FODA.

HTTP interface names are conceptual labels of implemented contracts, not extra
Python classes. Diagrams model source responsibilities; not runtime evidence.
"""
import math
from reportlab.graphics.shapes import Drawing,Rect,Line,String,Circle,Path,Polygon
from reportlab.lib.colors import HexColor,white

W=453.54
INK=HexColor('#263541');SOFT=HexColor('#edf2f5');GRAY=HexColor('#54616b');LIGHT=HexColor('#d0d8df')
FONT='Helvetica';BOLD='Helvetica-Bold'


def text(d,x,y,value,size=9,bold=False,anchor='start',color=INK):
    d.add(String(x,y,value,fontName=BOLD if bold else FONT,fontSize=size,textAnchor=anchor,fillColor=color))


def lines(d,points,dashed=False,arrow=None):
    p=Path(strokeColor=INK,strokeWidth=.9,fillColor=None,strokeDashArray=[4,3] if dashed else None)
    p.moveTo(*points[0])
    for point in points[1:]:p.lineTo(*point)
    d.add(p)
    if arrow:
        x,y=points[-1];a,b=points[-2];length=math.hypot(x-a,y-b);ux,uy=(x-a)/length,(y-b)/length
        back=8 if arrow=='triangle' else 5
        left=(x-back*ux-3.2*uy,y-back*uy+3.2*ux);right=(x-back*ux+3.2*uy,y-back*uy-3.2*ux)
        if arrow=='triangle':d.add(Polygon([x,y,*left,*right],fillColor=white,strokeColor=INK,strokeWidth=.9))
        else:lines(d,[left,(x,y),right])


def arc(d,cx,cy,r,start,extent,width=.9):
    p=Path(strokeColor=INK,strokeWidth=width,fillColor=None)
    count=max(1,math.ceil(abs(extent)/90));step=math.radians(extent/count);angle=math.radians(start)
    p.moveTo(cx+r*math.cos(angle),cy+r*math.sin(angle))
    for _ in range(count):
        end=angle+step;k=4/3*math.tan(step/4)
        p.curveTo(cx+r*(math.cos(angle)-k*math.sin(angle)),cy+r*(math.sin(angle)+k*math.cos(angle)),cx+r*(math.cos(end)+k*math.sin(end)),cy+r*(math.sin(end)-k*math.cos(end)),cx+r*math.cos(end),cy+r*math.sin(end))
        angle=end
    d.add(p)


def box(d,x,y,w,h,labels,fill=white,bold=False,size=9):
    d.add(Rect(x,y,w,h,fillColor=fill,strokeColor=INK,strokeWidth=.9))
    if isinstance(labels,str):labels=[labels]
    top=y+h/2+(len(labels)-1)*5.8-3
    for i,label in enumerate(labels):text(d,x+w/2,top-i*11.6,label,size,bold,anchor='middle')


def port(d,x,y):d.add(Rect(x-3,y-3,6,6,strokeColor=INK,strokeWidth=.8,fillColor=white))


def component(d,x,y,w,h,title,subtitle=None):
    d.add(Rect(x,y,w,h,strokeColor=INK,strokeWidth=.9,fillColor=white))
    text(d,x+10,y+h-12,'«component»',7.6)
    gx,gy=x+w-22,y+h-21
    d.add(Rect(gx,gy,12,13,strokeColor=INK,fillColor=white,strokeWidth=.75))
    for yy in [gy+2,gy+8]:d.add(Rect(gx-3,yy,6,3.2,strokeColor=INK,fillColor=white,strokeWidth=.75))
    text(d,x+w/2,y+h-30,title,9.2,True,'middle')
    if subtitle:text(d,x+w/2,y+10,subtitle,7.4,anchor='middle',color=GRAY)


def assembly_vertical(d,x,y,provider_y,required_points,label,label_x=None):
    # Provider below: ball on its stem. Consumer above: socket open downward.
    lines(d,[(x,provider_y),(x,y-3.8)]);d.add(Circle(x,y,3.8,fillColor=white,strokeColor=INK,strokeWidth=.9))
    lines(d,[*required_points,(x,y+8)]);arc(d,x,y,8,0,180)
    port(d,x,provider_y);port(d,*required_points[0])
    text(d,label_x if label_x is not None else x+12,y-2,label,7.8)


def features():
    d=Drawing(W,310)
    box(d,140,270,174,32,'E-commerce LPS',SOFT,True,10.5)
    box(d,5,213,215,30,'Núcleo comum',SOFT,True)
    box(d,254,213,195,30,'Domínio da loja',SOFT,True)
    lines(d,[(227,270),(227,253),(112.5,253),(112.5,246)])
    lines(d,[(227,253),(351.5,253),(351.5,246)])
    for x in [112.5,351.5]:d.add(Circle(x,246,3,fillColor=INK,strokeColor=INK))
    lines(d,[(112.5,213),(112.5,202),(20,202),(20,35)])
    for y,label in zip([174,149,124,99,74,49,24],['Catálogo','Carrinho','Checkout','Pedidos e consulta','Pix simulado','Endereço de entrega','Recomendações (extensão fixa)']):
        box(d,40,y,180,22,label,size=8.9)
        lines(d,[(20,y+11),(33,y+11)])
        d.add(Circle(36,y+11,3,strokeColor=INK,fillColor=INK))
    box(d,254,146,86,30,'Roupas',SOFT,True)
    box(d,363,146,86,30,'Alimentos',SOFT,True)
    parent=(351.5,213)
    for end in [(297,176),(406,176)]:lines(d,[parent,end])
    angle=math.degrees(math.atan2(176-213,297-351.5));angle2=math.degrees(math.atan2(176-213,406-351.5))
    arc(d,*parent,17,angle,angle2-angle)
    text(d,351.5,186,'[1..1]',7.5,anchor='middle')
    box(d,254,91,86,34,['Tamanho e cor','por combinação'],size=8.2)
    lines(d,[(297,146),(297,128)]);d.add(Circle(297,128,3,fillColor=INK,strokeColor=INK))
    lines(d,[(406,146),(406,136),(350,136),(350,54)])
    for y,label in [(91,['Informações','alimentares']),(37,['Agendamento','de entrega'])]:
        box(d,363,y,86,34,label,size=8.2)
        lines(d,[(350,y+17),(356,y+17)]);d.add(Circle(359,y+17,3,fillColor=INK,strokeColor=INK))
    d.add(Circle(10,15,3,fillColor=INK,strokeColor=INK));text(d,20,12,'Obrigatória',7.5)
    arc(d,134,20,9,215,110);text(d,149,12,'Arco vazio: alternativa XOR [1..1]',7.5)
    return d


def layers():
    d=Drawing(W,296)
    rows=[(238,'L1','Apresentação',['Storefront, ProductMedia e configuração visual']),(184,'L2','Fronteira web e API Gateway',['Route Handlers, sessão, Origin e validação HTTP']),(130,'L3','Aplicação dos serviços',['Catálogo, revisão, compra e recomendações']),(76,'L4','Domínio reutilizável',['Seleção, entrega, totais e contratos Protocol']),(22,'L5','Infraestrutura e adaptadores',['Clientes HTTP, repositórios privados, JSON e SQLite'])]
    for y,number,title,body in rows:
        d.add(Rect(5,y,443,44,fillColor=white,strokeColor=INK,strokeWidth=.85))
        d.add(Rect(5,y,49,44,fillColor=SOFT,strokeColor=INK,strokeWidth=.85))
        text(d,29.5,y+18,number,10,True,'middle')
        text(d,251,y+27,title,9.5,True,'middle')
        text(d,251,y+11,body[0],8.2,anchor='middle')
    for top,bottom in zip(rows,rows[1:]):lines(d,[(251,top[0]),(251,bottom[0]+44)],True,'open')
    text(d,7,5,'Dependência lógica permitida (tracejada). Camadas não são processos.',7.4)
    return d


def variability():
    d=Drawing(W,292)
    for x,name in [(20,'ProductSelectionValidator'),(245,'DeliveryPolicy')]:
        box(d,x,238,190,42,['«interface»',name],SOFT,size=9)
    component(d,20,154,190,48,'ClothingSelectionValidator')
    component(d,20,70,190,48,'FoodSelectionValidator')
    component(d,245,154,190,48,'UnscheduledDelivery')
    component(d,245,70,190,48,'ScheduledDelivery')
    lines(d,[(115,202),(115,238)],True,'triangle')
    lines(d,[(340,202),(340,238)],True,'triangle')
    lines(d,[(20,94),(5,94),(5,259),(20,259)],True,'triangle')
    lines(d,[(435,94),(449,94),(449,259),(435,259)],True,'triangle')
    d.add(Rect(5,2,443,49,strokeColor=LIGHT,fillColor=SOFT,strokeWidth=.8))
    text(d,14,38,'{xor} por ponto de variação; seleção na inicialização pelo manifesto.',8.1,True)
    text(d,14,24,'clothing: ClothingSelectionValidator + UnscheduledDelivery',8)
    text(d,14,10,'food: FoodSelectionValidator + ScheduledDelivery',8)
    return d


def node(d,x,y,w,h,title,subtitle,size=9):
    depth=5
    d.add(Polygon([x,y+h,x+depth,y+h+depth,x+w+depth,y+h+depth,x+w,y+h],fillColor=SOFT,strokeColor=INK,strokeWidth=.8))
    d.add(Polygon([x+w,y,x+w+depth,y+depth,x+w+depth,y+h+depth,x+w,y+h],fillColor=SOFT,strokeColor=INK,strokeWidth=.8))
    d.add(Rect(x,y,w,h,strokeColor=INK,fillColor=white,strokeWidth=.8))
    text(d,x+w/2,y+h-11,'«executionEnvironment»',6.7,anchor='middle',color=GRAY)
    text(d,x+w/2,y+h-26,title,size,True,'middle')
    if subtitle:text(d,x+w/2,y+9,subtitle,7.6,anchor='middle')


def artifact(d,x,y,w,h,title,subtitle):
    fold=8
    path=Path(strokeColor=INK,strokeWidth=.8,fillColor=white)
    path.moveTo(x,y);path.lineTo(x+w,y);path.lineTo(x+w,y+h-fold);path.lineTo(x+w-fold,y+h);path.lineTo(x,y+h);path.lineTo(x,y);d.add(path)
    lines(d,[(x+w-fold,y+h),(x+w-fold,y+h-fold),(x+w,y+h-fold)])
    text(d,x+w/2,y+h-11,'«artifact»',6.7,anchor='middle')
    text(d,x+w/2,y+h-23,title,8,True,'middle')
    text(d,x+w/2,y+7,subtitle,7,anchor='middle',color=GRAY)


def components():
    d=Drawing(W,425)
    component(d,115,335,224,58,'Web API e apresentação','Next.js / sessão / rotas fixas')
    component(d,15,205,180,62,'Catálogo','services/catalog')
    component(d,259,205,180,62,'Pedidos','services/orders')
    component(d,15,55,180,62,'Recomendações','services/recommendations')
    component(d,259,55,180,62,'Pagamentos simulados','services/payments')
    assembly_vertical(d,95,297,267,[(145,335),(145,320),(95,320)],'ICatalog',107)
    assembly_vertical(d,350,297,267,[(309,335),(309,320),(350,320)],'IOrders',361)
    # Catalog provides internal resolution to orders (horizontal assembly).
    port(d,195,235);port(d,259,235)
    lines(d,[(195,235),(223,235)]);d.add(Circle(227,235,4,fillColor=white,strokeColor=INK))
    lines(d,[(259,235),(235,235)]);arc(d,227,235,8,-90,180)
    text(d,227,250,'IResolve',7.2,anchor='middle')
    assembly_vertical(d,350,155,117,[(350,205)],'IPayment',362)
    # Recommendation service consumes catalog candidates (catalog provides downwards).
    port(d,95,205);port(d,95,117)
    lines(d,[(95,205),(95,169)]);d.add(Circle(95,165,4,fillColor=white,strokeColor=INK))
    lines(d,[(95,117),(95,157)]);arc(d,95,165,8,180,180)
    text(d,107,164,'ICandidates',7.4)
    # Gateway consumes recommendations via outer lane, without crossing components.
    assembly_vertical(d,42,147,117,[(115,364),(3,364),(3,178),(42,178)],'IRecommendations',54)
    text(d,10,30,'Círculo: fornecida; semicírculo: requerida; quadrado: porta UML.',7.2)
    text(d,10,16,'Interfaces conceituais dos contratos HTTP; porta UML não é porta TCP.',7.2)
    return d


def deployment():
    d=Drawing(W,380)
    node(d,145,330,163,38,'Navegador','Cliente web')
    node(d,100,248,253,52,'Next.js - interface e API Gateway',':3000 /api/v1')
    lines(d,[(227,330),(227,305)]);text(d,238,315,'HTTP mesma origem',7.2)
    entries=[(4,'Catálogo',':8001','products.json','JSON imutável'),(118,'Pedidos',':8002','orders.sqlite','revisão / pedido'),(232,'Pagamentos',':8003','payments.sqlite','autorização'),(346,'Recomendações',':8004','recommendations.sqlite','perfil / eventos')]
    for x,title,portno,filename,description in entries:
        node(d,x,119,102,54,title,'FastAPI '+portno,7.6)
        artifact(d,x,22,102,43,filename,description)
        lines(d,[(x+51,119),(x+51,65)],True,'open')
        text(d,x+51,82,'acesso privado',6.5,anchor='middle')
        lines(d,[(227,248),(227,220),(x+51,220),(x+51,178)])
    lines(d,[(169,119),(169,103),(55,103),(55,119)])
    text(d,112,91,'pedidos -> catálogo',6.4,anchor='middle')
    lines(d,[(220,146),(232,146)])
    lines(d,[(397,173),(397,193),(55,193),(55,173)])
    text(d,277,199,'recomendações -> catálogo',7.1,anchor='middle')
    text(d,5,5,'HTTP entre processos; tracejado: dependência de artefato. Não é captura de execução.',7)
    return d


DIAGRAMS={'01_features':features,'02_camadas':layers,'03_componentes_uml':components,'04_variabilidade_uml':variability,'05_implantacao':deployment}
