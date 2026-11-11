from pathlib import Path
import pypdfium2 as pdf
from pypdf import PdfReader
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[2]
path=root/'output/pdf/Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL.pdf'
out=root/'tmp/relatorio/render';out.mkdir(exist_ok=True)
d=pdf.PdfDocument(str(path));print('PAGES',len(d))
ims=[]
for i,p in enumerate(d):
    im=p.render(scale=1.3).to_pil().convert('RGB');im.save(out/f'page-{i+1:02d}.png');ims.append(im)
for group in range(0,len(ims),4):
    sheet=Image.new('RGB',(1200,1740),'#dddddd');draw=ImageDraw.Draw(sheet)
    for j,im in enumerate(ims[group:group+4]):
        copy=im.copy();copy.thumbnail((580,830));x=10+(j%2)*600;y=25+(j//2)*870
        sheet.paste(copy,(x,y));draw.text((x+5,y-18),f'Página {group+j+1}',fill='black')
    sheet.save(out/f'sheet-{group//4+1}.png')
r=PdfReader(path)
for i,p in enumerate(r.pages):
    t=p.extract_text();print(i+1,len(t),t.splitlines()[3:4])
    assert len(t)>200,'Unexpected empty page'
print('PDF readable; all pages rendered')
