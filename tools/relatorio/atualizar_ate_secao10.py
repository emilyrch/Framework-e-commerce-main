from pathlib import Path
source=Path(__file__).with_name('gerar_relatorio.py').read_text(encoding='utf-8')
start=source.index("page('11 Aplicabilidade do vídeo e conclusão')")
end=source.index('\ndoc=Report(',start)
source=source[:start]+source[end:]
source=source.replace('Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL.pdf','Relatorio_LPS_Ecommerce_Emily_Rocha_UFAL_ate_secao10.pdf')
source=source.replace('\ndoc=Report(',"\nfrom exportar_editavel import export_html\nexport_html(story,ROOT/'output/Relatorio_LPS_Emily_Rocha_editavel.html')\ndoc=Report(")
exec(compile(source,str(Path(__file__).with_name('gerar_relatorio.py')),'exec'))
