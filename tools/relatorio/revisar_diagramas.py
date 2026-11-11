from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdf
from PIL import Image,ImageDraw
import zipfile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[2]
path=root/'output/pdf/Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_diagramas_revisados.pdf'
r=PdfReader(path);d=pdf.PdfDocument(str(path));out=root/'tmp/relatorio/diagramas_render';out.mkdir(exist_ok=True)
print('PAGES',len(r.pages));ims=[]
for i,(page,p) in enumerate(zip(d,r.pages)):
    im=page.render(scale=1.4).to_pil().convert('RGB');im.save(out/f'page-{i+1:02d}.png');ims.append(im)
    content=p.extract_text();print(i+1,len(content),' | '.join(content.splitlines()[3:4]))
    assert '11 Aplicabilidade do vídeo e conclusão' not in content
    assert len(content)>350,'Page fragment requires layout review'
for group in range(0,len(ims),4):
    sheet=Image.new('RGB',(1200,1740),'#dddddd');draw=ImageDraw.Draw(sheet)
    for j,im in enumerate(ims[group:group+4]):
        copy=im.copy();copy.thumbnail((580,830));x=10+(j%2)*600;y=25+(j//2)*870
        sheet.paste(copy,(x,y));draw.text((x,y-18),f'Página {group+j+1}',fill='black')
    sheet.save(out/f'sheet-{group//4+1}.png')
all_text='\n'.join(p.extract_text() for p in r.pages)
assert '10 Referências bibliográficas' in r.pages[-1].extract_text()
assert 'OBJECT MANAGEMENT GROUP' in r.pages[-1].extract_text()
assert 'serviço ativo na Figura 4' not in all_text
for name in ['Figura 1','Figura 2','Figura 3','Figura 4','Figura 5']:assert name in all_text,name
for path in (root/'output/diagramas_academicos').glob('*.svg'):ET.parse(path)
with zipfile.ZipFile(root/'output/Diagramas_LPS_editaveis.zip') as archive:assert archive.testzip() is None
html=(root/'output/Relatorio_LPS_Emily_Rocha_diagramas_revisados_editavel.html').read_text(encoding='utf-8')
assert html.count('<svg')==5
assert '11 Aplicabilidade do vídeo e conclusão' not in html
print('PDF, HTML, 5 SVGs and ZIP structurally verified; all PDF pages rendered.')
