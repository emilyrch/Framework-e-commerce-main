"""Export the same report elements to a self-contained, editable HTML document."""
from pathlib import Path
from html import escape
import re
import base64
from reportlab.platypus import Image as ReportImage
from reportlab.platypus import Paragraph, Table, Preformatted, PageBreak, Spacer
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderSVG


def markup(paragraph):
    text=paragraph.text
    text=re.sub(r'<link\s', '<a ', text)
    return text.replace('</link>','</a>')


def export_html(story, destination):
    headings=[];seen=set()
    for item in story:
        if isinstance(item,Paragraph) and item.style.name in ('H1','H2'):
            text=item.getPlainText();match=re.match(r'^(\d+(?:\.\d+)?)\s',text)
            if match and match[1] not in seen:
                seen.add(match[1]);headings.append((match[1],text))
    blocks=['<article class="paper cover" contenteditable="true" spellcheck="true">'];assigned=set()
    for item in story:
        if isinstance(item,PageBreak):blocks.append('</article><article class="paper" contenteditable="true" spellcheck="true">')
        elif isinstance(item,Paragraph):
            style=item.style.name
            tag='h1' if style=='H1' else 'h2' if style=='H2' else 'p'
            anchor='';match=re.match(r'^(\d+(?:\.\d+)?)\s',item.getPlainText())
            if style in ('H1','H2') and match and match[1] not in assigned:
                assigned.add(match[1]);anchor=f' id="sec-{match[1].replace(".","-")}"'
            blocks.append(f'<{tag}{anchor} class="{style.lower()}">{markup(item)}</{tag}>')
        elif isinstance(item,TableOfContents):
            blocks.append('<nav class="toc" aria-label="Sumário"><ol>')
            for number,title in headings:
                blocks.append(f'<li class="{"sub" if "." in number else "main"}"><a href="#sec-{number.replace(".","-")}">{escape(title)}</a></li>')
            blocks.append('</ol></nav>')
        elif isinstance(item,Table):
            blocks.append('<table>')
            for i,row in enumerate(item._cellvalues):
                blocks.append('<tr>');tag='th' if i==0 else 'td'
                for cell in row:
                    text=markup(cell) if isinstance(cell,Paragraph) else escape(str(cell))
                    blocks.append(f'<{tag}>{text}</{tag}>')
                blocks.append('</tr>')
            blocks.append('</table>')
        elif isinstance(item,Preformatted):blocks.append('<pre>'+escape('\n'.join(item.lines))+'</pre>')
        elif isinstance(item,ReportImage):
            filename=Path(item.filename)
            encoded=base64.b64encode(filename.read_bytes()).decode('ascii')
            mime='image/jpeg' if filename.suffix.lower() in ('.jpg','.jpeg') else 'image/png'
            blocks.append(f'<figure contenteditable="false" style="margin:8pt auto;text-align:center"><img alt="Captura real do sistema de roupas" src="data:{mime};base64,{encoded}" style="max-width:100%;width:{item.drawWidth}pt;height:auto;max-height:530pt;object-fit:contain"></figure>')
        elif isinstance(item,Drawing):
            svg=renderSVG.drawToString(item)
            svg=svg[svg.index('<svg'):]
            blocks.append('<div class="figure" contenteditable="false">'+svg+'</div>')
        elif isinstance(item,Spacer):blocks.append(f'<div class="space" style="height:{min(item.height,70)}pt"></div>')
    blocks.append('</article>')
    html='''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório LPS de comércio eletrônico até a seção 10</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#e6e7e9;color:#171717;font-family:'Times New Roman',serif}
.toolbar{position:sticky;top:0;z-index:10;background:#173b55;color:white;padding:12px 24px;display:flex;gap:20px;align-items:center;justify-content:space-between;font:14px Arial,sans-serif}.toolbar button{padding:10px 16px;cursor:pointer;border:0;background:white;color:#173b55;font-weight:bold}.toolbar small{display:block;margin-top:5px;font-size:12px}
.paper{background:white;max-width:21cm;min-height:29.7cm;margin:24px auto;padding:2.5cm 2cm 2cm 3cm;box-shadow:0 2px 8px #0002;outline:none}.cover{text-align:center}.cover .small{text-align:left}p{font-size:11.4pt;line-height:1.4;margin:0 0 9pt;text-align:justify;text-indent:18pt}.lead{text-indent:0}.cover p{text-align:center;text-indent:0;font-size:12pt;line-height:1.6}.cover .title{font-size:19pt;font-weight:bold;line-height:1.4}.small{font-size:9.5pt;line-height:1.4;text-indent:0}.caption{text-align:center;font-size:9pt;line-height:1.35;text-indent:0;margin:7pt 0 10pt}h1{font-size:14pt;margin:0 0 15pt;line-height:1.3}h2{font-size:12pt;margin:12pt 0 9pt;line-height:1.35}table{border-collapse:collapse;width:100%;font-size:9.1pt;line-height:1.35;margin:0 0 12pt}th,td{padding:7pt;vertical-align:top;text-align:left;border-bottom:1px solid #ccc;overflow-wrap:anywhere}th{background:#edf1f4;border-bottom-color:#777}pre{font:7.7pt/1.35 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f4;padding:9pt;margin:8pt 0 10pt}.figure{margin:8pt 0}.figure svg{width:100%;height:auto;display:block}.figure text{font-family:'Times New Roman',serif}.toc ol{list-style:none;padding:0}.toc li{margin:11pt 0;font-size:10.3pt}.toc .sub{padding-left:15pt;font-size:9.5pt}.toc a{text-decoration:none;color:inherit}a{color:#193c57}.space{max-height:70pt}
@media(max-width:800px){.paper{margin:12px;padding:32px;min-height:auto}.toolbar{position:static;flex-wrap:wrap}table{font-size:10pt}.cover .title{font-size:18pt}}
@media print{@page{size:A4;margin:2.5cm 2cm 2cm 3cm}body{background:white}.toolbar{display:none}.paper{margin:0;padding:0;box-shadow:none;max-width:none;min-height:0;break-after:page}.paper:last-child{break-after:auto}h1,h2{break-after:avoid}tr,pre,.figure{break-inside:avoid}}
</style></head><body>
<aside class="toolbar"><div><b>Relatório editável</b><small>Clique no texto para editar. Use Salvar versão editada para conservar as alterações.</small></div><button type="button" onclick="saveReport()">Salvar versão editada</button><button type="button" onclick="window.print()">Imprimir ou salvar PDF</button></aside>
'''+''.join(blocks)+'''
<script>
function saveReport(){const file=new Blob(['<!DOCTYPE html>\\n'+document.documentElement.outerHTML],{type:'text/html;charset=utf-8'});const url=URL.createObjectURL(file);const a=document.createElement('a');a.href=url;a.download='Relatorio_LPS_Emily_Rocha_editado.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
</script></body></html>'''
    if 'diagramas_revisados' in str(destination) or 'atualizado' in str(destination):
        html=html.replace(".figure text{font-family:'Times New Roman',serif}",'.figure text{font-family:Arial,Helvetica,sans-serif}')
    Path(destination).write_text(html,encoding='utf-8')
