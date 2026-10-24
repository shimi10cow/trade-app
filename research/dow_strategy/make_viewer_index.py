"""Write a viewer page from the template for one instrument.
Usage: python make_viewer_index.py <built index.html (for the YEARS/ALLTR line)> <out index.html> <name or EUR>"""
import sys
from pathlib import Path
T = (Path(__file__).parent / 'stage_viewer_template.html').read_text(encoding='utf-8')
src, out, name = sys.argv[1], sys.argv[2], sys.argv[3]
key = 'let DATA=null;const ALLTR=/*ALLTR*/null;const YEARS=/*YEARS*/null;let year=YEARS[YEARS.length-1];'
line = [l for l in Path(src).read_text(encoding='utf-8').split('\n') if l.startswith('let DATA=null;const ALLTR=')][0]
new = T.replace(key, line)
if name != 'EUR':
    line2 = line.split('const ALLTR=')[0] + 'const ALLTR=[];const YEARS=' + line.split('const YEARS=')[1]
    new = T.replace(key, line2)
    for a, b in [('<title>トレンド段階ビューア</title>', f'<title>{name} EAビューア</title>'),
                 ('<h1>既存EAのエントリー（色＝H4ダウの段階）</h1>', f'<h1>{name} EAのエントリー</h1>'),
                 ('<option value="ea">既存EA</option>', ''),
                 ('EAごとの成績（ユーロドル・全年、コスト込み）', f'EAごとの成績（{name}・全年、コスト込み）')]:
        assert new.count(a) == 1, a
        new = new.replace(a, b)
Path(out).write_text(new, encoding='utf-8'); print('wrote', out)
