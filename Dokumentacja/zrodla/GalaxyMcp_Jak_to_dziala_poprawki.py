import pymupdf as fitz, sys
SRC,DST=sys.argv[1],sys.argv[2]
FONTS={'DejaVuSans':'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
       'DejaVuSans-Bold':'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'}
# (strona, stary fragment, nowy fragment) - zamiana w obrębie jednego spanu
R=[(1,'Obszar roboczy sesji','Obszar roboczy wątku'),
   (1,'host MCP – most sesji do komputera','host MCP – most wątku do komputera'),
   (3,'okno czatu','projekt i jego wątki'),
   (3,'roboczy sesji','roboczy wątku'),
   (3,'(kontener tej','(kontener tego'),
   (3,'rozmowy)','wątku)'),
   (3,'wywołania narzędzi z sesji i odsyła','wywołania narzędzi z wątku i odsyła'),
   (3,'wiadomość w czacie, załączniki','wiadomość w wątku, pliki'),
   (3,'sesji','wątku'),               # "polecenia powłoki w kontenerze / sesji"
   (3,'przez połączenie sesji z','przez połączenie wątku z'),
   (4,'narzędzia widoczne dla Claude w nowej rozmowie','narzędzia widoczne dla Claude w nowym wątku'),
   (5,'W sesji narzędzia mają długie nazwy, np.','W wątku narzędzia mają długie nazwy, np.'),
   (5,'przez połączenie sesji z komputerem','przez połączenie wątku z komputerem'),
   (9,'czat → chmura; specyfikacja chmura →','wątek/Library → chmura; specyfikacja →'),
   (9,'obszar roboczy sesji; wtyczka','Library projektu i wątek; wtyczka'),
   (9,'Claude czyta je i streszcza w czacie','Claude czyta je i streszcza w wątku'),
   (9,'Jeden proces wtyczki obsługuje wszystkie rozmowy prowadzone przez tę instancję Claude',
      'Jeden proces wtyczki obsługuje wszystkie wątki połączone z tą instancją Claude'),
   (9,'Desktop. Przełączenie galaktyki w jednej rozmowie jest więc widoczne także w innej – dlatego',
      'Desktop. Przełączenie galaktyki w jednym wątku jest więc widoczne także w innym – dlatego'),
]
d=fitz.open(SRC)
todo={}
for pg,old,new in R:
    page=d[pg-1]; hit=None
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if old in s['text'] and (old!='sesji' or s['text'].strip()=='sesji'):
                    hit=s; break
            if hit: break
        if hit: break
    assert hit, (pg,old)
    todo.setdefault(pg,[]).append((hit,hit['text'].replace(old,new)))
for pg,items in todo.items():
    page=d[pg-1]
    for s,_ in items:
        r=fitz.Rect(s['bbox']); r.y0+=s['size']*0.25; r.y1-=s['size']*0.1
        page.add_redact_annot(r)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    for s,txt in items:
        fn=s['font'].split('+')[-1]
        c=s['color']; col=((c>>16)&255)/255,((c>>8)&255)/255,(c&255)/255
        page.insert_text(s['origin'],txt,fontsize=s['size'],fontname=fn.replace('-','_'),fontfile=FONTS[fn],color=col)
p9=d[8]
p9.insert_textbox(fitz.Rect(62.7,622,532,700),
  "Uzupełnienie do rozdziału 8: pliki dodane do projektu (załączniki w rozmowie projektu i w wątkach "
  "oraz pliki w Library) zostają w Bibliotece projektu i są dostępne dla kolejnych wątków, dopóki ich nie "
  "usuniesz. Tam trafiają też wyniki wątków, np. pliki CSV i Spec_<UDT>.json.",
  fontsize=9.8,fontname='DejaVuSans',fontfile=FONTS['DejaVuSans'],color=(0x1d/255,0x24/255,0x30/255),lineheight=1.45)
d.subset_fonts()
d.set_metadata(d.metadata)
d.save(DST,garbage=3,deflate=True)
print('ok')
