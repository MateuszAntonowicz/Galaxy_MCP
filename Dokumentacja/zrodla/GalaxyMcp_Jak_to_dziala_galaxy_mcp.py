"""Poprawki GalaxyMcp_Jak_to_dziala.pdf (2026-11-18): nazwa wtyczki „GalaxyMCP” zamiast „AVEVA Galaxy (GalaxyMcp)”/„GalaxyMcp”
(nazwy plików GalaxyMcp.exe/.log/.mcpb bez zmian) oraz potwierdzenie działania na AVEVA System Platform 2026.
PDF nie ma źródła reportlab - zmiany nakładane PyMuPDF (redakcja spanu + wstawienie tekstu tą samą czcionką).
Użycie: python GalaxyMcp_Jak_to_dziala_galaxy_mcp.py WEJSCIE.pdf WYJSCIE.pdf"""
import pymupdf as fitz, re, sys
SRC, DST = sys.argv[1], sys.argv[2]
D = '/usr/share/fonts/truetype/dejavu/'
FONTS = {'DejaVuSans': D + 'DejaVuSans.ttf', 'DejaVuSans-Bold': D + 'DejaVuSans-Bold.ttf',
         'DejaVuSansMono': D + 'DejaVuSansMono.ttf'}
SUBS = [('AVEVA_Galaxy__GalaxyMcp___', 'GalaxyMCP__'), ('AVEVA_Galaxy__GalaxyMcp', 'GalaxyMCP'),
        ('AVEVA Galaxy (GalaxyMcp)', 'GalaxyMCP')]
BARE = re.compile(r'GalaxyMcp(?![.\w])')
CENTERED = {(1, 'ładowana DO procesu GalaxyMcp')}

def new_text(t):
    for a, b in SUBS: t = t.replace(a, b)
    return BARE.sub('GalaxyMCP', t)

def col(c): return ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255

def put(page, x, y, txt, font, size, color):
    fn = font.split('+')[-1]
    page.insert_text((x, y), txt, fontsize=size, fontname='GM' + fn.replace('-', ''), fontfile=FONTS[fn], color=color)
    return fitz.get_text_length(txt, fontname='helv', fontsize=size) if False else \
        fitz.Font(fontfile=FONTS[fn]).text_length(txt, fontsize=size)

d = fitz.open(SRC)
for pno, page in enumerate(d, 1):
    jobs = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = l['spans']
            idx = [i for i, s in enumerate(sp) if new_text(s['text']) != s['text']]
            if not idx: continue
            first = idx[0]; rest = sp[first:]
            line_txt = ''.join(s['text'] for s in sp)
            jobs.append((rest, (pno, line_txt) in CENTERED))
    if not jobs: continue
    for rest, _ in jobs:
        for s in rest:
            r = fitz.Rect(s['bbox']); r.y0 += s['size'] * 0.25; r.y1 -= s['size'] * 0.1
            page.add_redact_annot(r)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    for rest, centered in jobs:
        x, y = rest[0]['origin']
        if centered:
            old_w = sum(fitz.Font(fontfile=FONTS[s['font'].split('+')[-1]]).text_length(s['text'], fontsize=s['size']) for s in rest)
            new_w = sum(fitz.Font(fontfile=FONTS[s['font'].split('+')[-1]]).text_length(new_text(s['text']), fontsize=s['size']) for s in rest)
            x -= (new_w - old_w) / 2
        for s in rest:
            x += put(page, x, y, new_text(s['text']), s['font'], s['size'], col(s['color']))

INK = col(1909808)
# str. 1, „W skrócie”: nowy punkt o zgodności
p1 = d[0]
# ramka „W skrócie” kończy się na y=692.8 - przedłużenie tła i paska o jeden wiersz
BOX = (0.9098, 0.9451, 0.9843); BAR = (0.1843, 0.4353, 0.7098)
p1.draw_rect(fitz.Rect(56.69, 692.0, 538.58, 712.5), color=None, fill=BOX, width=0)
p1.draw_line((56.69, 692.0), (56.69, 712.5), color=BAR, width=3)
put(p1, 69.7, 701.1, '•', 'DejaVuSans', 10, INK)
x = 80.7
x += put(p1, x, 701.1, 'Działa na AVEVA System Platform 2026', 'DejaVuSans-Bold', 9.8, INK)
put(p1, x, 701.1, ' – sprawdzone na galaktykach testowych.', 'DejaVuSans', 9.8, INK)
# str. 8, przykład zabezpieczeń: dopisek po dacie testu
p8 = d[7]
x = 66.7 + fitz.Font(fontfile=FONTS['DejaVuSans']).text_length('2026-09-17. ', fontsize=9.8)
put(p8, x, 688.2, 'Wtyczka działa na AVEVA System Platform 2026.', 'DejaVuSans-Bold', 9.8, INK)

m = d.metadata
m['title'] = 'Jak działa wtyczka GalaxyMCP'
m['subject'] = 'Architektura GalaxyMCP: Claude, Claude Desktop, GRAccess, galaktyka (AVEVA System Platform 2026)'
d.set_metadata(m)
d.subset_fonts()
d.save(DST, garbage=3, deflate=True)
print('ok')
