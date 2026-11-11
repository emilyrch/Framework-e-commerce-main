from pathlib import Path
import zipfile
from reportlab.graphics import renderSVG
from diagramas_academicos import DIAGRAMS

HERE=Path(__file__).resolve().parent
source=(HERE/'gerar_relatorio.py').read_text(encoding='utf-8')
start=source.index("page('11 Aplicabilidade do vídeo e conclusão')")
end=source.index('\ndoc=Report(',start)
source=source[:start]+source[end:]
source=source.replace('Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL.pdf','Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_atualizado.pdf')
source=source.replace('from pathlib import Path','from pathlib import Path\nfrom diagramas_academicos import features,layers,components,variability,deployment',1)
source=source.replace("('TOPPADDING',(0,0),(-1,-1),7)","('TOPPADDING',(0,0),(-1,-1),4 if headers==['Feature','Roupas','Alimentos'] else 7)")
source=source.replace("('BOTTOMPADDING',(0,0),(-1,-1),7)","('BOTTOMPADDING',(0,0),(-1,-1),4 if headers==['Feature','Roupas','Alimentos'] else 7)")


def replace_diagram(section,function,caption):
    global source
    section_start=source.index(section)
    first=source.index('\ndiagram(',section_start)
    last=source.index('\ncaption(',first)
    source=source[:first]+f'\nstory.append({function}())'+source[last:]
    caption_start=source.index('\ncaption(',first)
    caption_end=source.index('\n',caption_start+1)
    source=source[:caption_start]+f'\ncaption({caption!r})'+source[caption_end:]


replace_diagram("page('5.1 Diagrama de features')",'features','Figura 1 — Modelo de features com obrigatoriedade e grupo alternativo XOR [1..1]. Notação de features, distinta da UML. Fonte: elaboração própria a partir de docs/modelo-lps.md.')
replace_diagram("page('5.2 Arquitetura em camadas e variabilidade')",'layers','Figura 2 — Visão lógica em camadas e direção de dependência. Não representa sequência temporal nem processos distintos. No MVP, PaymentsRepository reúne autorização simulada e adaptação ao SQLite.')
replace_diagram("page('5.3 Componentes de software e variabilidade')",'components','Figura 3 — Diagrama UML de componentes e interfaces HTTP da aplicação. Ícone de componente, portas e conectores de montagem com interfaces fornecidas/requeridas. Fonte: elaboração própria; convenções UML 2.5.1 (OMG, 2017).')

# Keep the original contracts table and explanatory paragraphs, separating the
# two abstraction levels instead of claiming that boxes alone form a UML model.
point=source.index("table(['Contrato','Entradas e saídas','Uso e seleção']",source.index("page('5.3 Componentes"))
addition="""p('Os nomes IPublicCatalog, IResolve, IOrders e IPayment identificam interfaces conceituais dos contratos HTTP já implementados; não representam classes ou serviços novos. Cada retângulo denota uma unidade modular. Nesta visão, as unidades de backend também correspondem aos serviços implantáveis, mas componente lógico e microsserviço não são sinônimos.','Small')
p('O círculo representa uma interface fornecida; o semicírculo, uma interface requerida. O conector de montagem indica que o contrato requerido é satisfeito. Quadrados na borda são portas UML de interação, sem relação com os números TCP da implantação.','Small')
page('5.3 Variabilidade dos componentes de domínio')
story.append(variability())
caption('Figura 4 — Realização dos contratos e alternativas dos componentes de domínio. Linha tracejada e triângulo vazio indicam realização conceitual dos Protocols por tipagem estrutural, não herança explícita. A restrição {xor} seleciona uma alternativa por ponto de variação.')
"""
source=source[:point]+addition+source[point:]
replace_diagram("page('6 Arquitetura baseada em microsserviços')",'deployment','Figura 5 — Visão de implantação local com ambientes de execução, comunicação HTTP e artefatos privados. Linhas contínuas: comunicação entre processos; tracejadas: dependência de artefato. Checagens de prontidão foram omitidas para legibilidade. Diagrama arquitetural, não captura de execução.')
source=source.replace('Essa extensão não aparece como serviço ativo na Figura 4','Essa extensão não aparece como serviço ativo na Figura 5')
source=source.replace("('FASTAPI.','Documentação oficial do FastAPI'","('OBJECT MANAGEMENT GROUP.','OMG Unified Modeling Language Version 2.5.1','2017','https://www.omg.org/spec/UML/2.5.1/'),\n ('FASTAPI.','Documentação oficial do FastAPI'")
source=source.replace('\ndoc=Report(',"\nfrom exportar_editavel import export_html\nexport_html(story,ROOT/'output/Relatorio_LPS_Emily_Rocha_atualizado_editavel.html')\ndoc=Report(")
exec(compile(source,str(HERE/'gerar_relatorio.py'),'exec'))

root=HERE.parents[1]
assets=root/'output/diagramas_atualizados';assets.mkdir(exist_ok=True)
for name,factory in DIAGRAMS.items():
    svg=renderSVG.drawToString(factory())
    (assets/(name+'.svg')).write_text(svg,encoding='utf-8')
(assets/'LEIA-ME.txt').write_text('''DIAGRAMAS ACADÊMICOS DA LPS

Arquivos SVG vetoriais: textos e formas podem ser editados no Inkscape ou outro editor vetorial.

01_features: árvore de features, obrigatoriedade e escolha exclusiva XOR.
02_camadas: arquitetura lógica e dependências entre camadas; não é fluxo temporal.
03_componentes_uml: componentes, portas, interfaces fornecidas/requeridas e montagem.
04_variabilidade_uml: realização conceitual dos Protocols e restrições por configuração.
05_implantacao: processos, comunicação HTTP e artefatos privados; não comprova execução.

Interfaces I* são rótulos conceituais para APIs existentes. Portas UML são pontos de interação, não números TCP. Componentes concretos de domínio realizam Protocols por tipagem estrutural. Alternativas não estão todas ativas simultaneamente.

Fontes: código de domain/, foundation/, services/ e apps/store-ropa/src/; docs/modelo-lps.md; OMG UML 2.5.1, https://www.omg.org/spec/UML/2.5.1/ (2017).
''',encoding='utf-8')
with zipfile.ZipFile(root/'output/Diagramas_LPS_atualizados_editaveis.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(assets.iterdir()):archive.write(path,path.name)
print('HTML editável e SVGs vetoriais exportados.')
