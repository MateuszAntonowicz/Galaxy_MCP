"""Poprawka GalaxyMcp_Jak_to_dziala.pdf pod wersję 0.2.6: serverInfo na rys. 2 (strona 4). PDF nie ma źródła reportlab - zmiany nakładane PyMuPDF (redakcja spanu + wstawienie tekstu tą samą czcionką).
Użycie: python GalaxyMcp_Jak_to_dziala_wersja_0_2_6.py WEJSCIE.pdf WYJSCIE.pdf"""
import pymupdf as fitz, sys
SRC, DST = sys.argv[1], sys.argv[2]
D = '/usr/share/fonts/truetype/dejavu/'
FONTS = {'DejaVuSans': D + 'DejaVuSans.ttf', 'DejaVu Sans Book': D + 'DejaVuSans.ttf', 'DejaVu Sans Bold': D + 'DejaVuSans-Bold.ttf'}
# (strona, dokładny tekst spanu, nowy tekst, nowe x albo None = bez zmiany)
R = [(4, 'serverInfo galaxy-mcp 0.2.5 + instructions', 'serverInfo galaxy-mcp 0.2.6 + instructions', None)]

d = fitz.open(SRC)
todo = {}
for pg, old, new, x in R:
    hit = None
    for b in d[pg - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'] == old and hit is None:
                    hit = s
    assert hit, (pg, old)
    todo.setdefault(pg, []).append((hit, new, x))
for pg, items in todo.items():
    page = d[pg - 1]
    for s, _, _ in items:
        r = fitz.Rect(s['bbox']); r.y0 += s['size'] * 0.25; r.y1 -= s['size'] * 0.1
        page.add_redact_annot(r)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    for s, txt, x in items:
        if not txt:
            continue
        fn = s['font'].split('+')[-1]
        c = s['color']; col = ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255
        ox, oy = s['origin']
        page.insert_text((x if x is not None else ox, oy), txt, fontsize=s['size'],
                         fontname='V' + fn.replace(' ', '').replace('-', ''), fontfile=FONTS[fn], color=col)
d.subset_fonts()
d.save(DST, garbage=3, deflate=True)
print('ok')
