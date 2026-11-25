#!/usr/bin/env python3
"""
Generuje Instrukcja_UDT_CSV.pdf - instrukcję działania projektu UDT->CSV (TIA Portal -> AVEVA System Platform)
w projektach Claude (Claude Desktop, lewe menu -> Projects; rozmowa projektu + wątki).

Użycie:  python Instrukcja_UDT_CSV_pdf.py [--out Instrukcja_UDT_CSV.pdf]
Wymaga:  reportlab; czcionki z polskimi znakami (Carlito/Liberation/DejaVu albo Calibri/Arial/Consolas na Windows).
Treść jest w tym pliku - zmiana projektu = aktualizacja tekstu poniżej i ponowne wygenerowanie PDF.
"""
import argparse, os, sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

DOC_YEAR = "2026"
AUTHOR = "Mateusz Antonowicz"
AUTHOR_NOTE = "z pomocą Claude AI"
PLUGIN_VERSION = "0.2.7"

# ------------------------------------------------------------------ czcionki
FONT_SETS = [
    {"Body": "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
     "Body-Bold": "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
     "Head": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
     "Mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"},
    {"Body": r"C:\Windows\Fonts\calibri.ttf", "Body-Bold": r"C:\Windows\Fonts\calibrib.ttf",
     "Head": r"C:\Windows\Fonts\arialbd.ttf", "Mono": r"C:\Windows\Fonts\consola.ttf"},
    {"Body": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "Body-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "Head": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "Mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"},
]
for fs in FONT_SETS:
    if all(os.path.exists(p) for p in fs.values()):
        for name, path in fs.items():
            pdfmetrics.registerFont(TTFont(name, path))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")
        break
else:
    sys.exit("Brak czcionek TTF z polskimi znakami (Carlito/Calibri/DejaVu).")

# ------------------------------------------------------------------ kolory i style
HEAD = colors.HexColor("#1F4E79")
GREY = colors.HexColor("#808080")
LINE = colors.HexColor("#A6A6A6")
ZEBRA = colors.HexColor("#F2F6FA")
CODEBG = colors.HexColor("#F2F2F2")
NOTE_BG = colors.HexColor("#EAF1F8")
WARN_BG = colors.HexColor("#FFF4DB")
WARN_LINE = colors.HexColor("#E0A526")
TEXT = colors.black

S = {
    "title": ParagraphStyle("title", fontName="Head", fontSize=20, leading=25, textColor=HEAD, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=10.5, leading=14, textColor=GREY, spaceAfter=4),
    "tochead": ParagraphStyle("tochead", fontName="Head", fontSize=17, leading=22, textColor=HEAD,
                              spaceBefore=18, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=15, leading=19, textColor=HEAD, spaceBefore=12,
                         spaceAfter=7, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=12, leading=15, textColor=HEAD, spaceBefore=9,
                         spaceAfter=5, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10.5, leading=13.6, textColor=TEXT, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=10, leading=12.6, textColor=TEXT),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=10, leading=12.6, textColor=colors.white),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=10.5, leading=13.6, textColor=TEXT,
                             leftIndent=16, bulletIndent=5, spaceAfter=2.5),
    "step": ParagraphStyle("step", fontName="Body", fontSize=10.5, leading=13.6, textColor=TEXT, leftIndent=18,
                           bulletIndent=2, spaceAfter=3),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.8, leading=11.8, textColor=TEXT),
    "small": ParagraphStyle("small", fontName="Body", fontSize=9.5, leading=12, textColor=GREY),
}


def P(t, st="body"):
    return Paragraph(t, S[st])


def H1(t):
    h = Paragraph(t, S["h1"])
    h.toc_level = 0
    return h


def H2(t):
    h = Paragraph(t, S["h2"])
    h.toc_level = 1
    return h


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        lvl = getattr(f, "toc_level", None)
        if lvl is not None:
            text = f.getPlainText()
            key = "k%d" % id(f)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=lvl, closed=False)
            if lvl == 0:
                self.notify("TOCEntry", (0, text, self.page, key))


def c(t):
    return f'<font name="Mono" size="9.5">{t}</font>'


def ui(t):
    """Nazwa przycisku / pola w aplikacji (pogrubiona)."""
    return f"<b>{t}</b>"


def bullets(items):
    return [Paragraph(i, S["bullet"], bulletText="•") for i in items]


def steps(items, start=1):
    return [Paragraph(t, S["step"], bulletText=f"{n}.") for n, t in enumerate(items, start)]


def table(rows, widths, zebra=True):
    data = [[x if not isinstance(x, str) else Paragraph(x, S["cellb" if r == 0 else "cell"]) for x in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), HEAD),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("GRID", (0, 0), (-1, -1), 0.5, LINE)]
    if zebra:
        for r in range(2, len(rows), 2):
            st.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(st))
    return t


def codeblock(lines):
    t = Table([[Paragraph("<br/>".join(lines), S["code"])]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CODEBG), ("LEFTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return KeepTogether([t, Spacer(1, 6)])


def note(content, kind="info", title=None):
    bg, line = {"info": (NOTE_BG, HEAD), "warn": (WARN_BG, WARN_LINE)}[kind]
    inner = [P(f"<b>{title}</b>")] if title else []
    inner += content if isinstance(content, list) else [P(content)]
    t = Table([[inner]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, line),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return KeepTogether([t, Spacer(1, 7)])


W = A4[0] - 2 * 72  # szerokość tekstu (marginesy 2,54 cm)


def on_page(cv, doc):
    cv.saveState()
    cv.setFont("Body", 8)
    cv.setFillColor(GREY)
    cv.drawString(72, A4[1] - 43, "Instrukcja działania projektu UDT->CSV")
    cv.setStrokeColor(LINE)
    cv.setLineWidth(0.5)
    cv.line(72, A4[1] - 47, A4[0] - 72, A4[1] - 47)
    cv.line(72, 50, A4[0] - 72, 50)
    cv.drawString(72, 38, f"UDT->CSV · {DOC_YEAR}")
    cv.setFont("Body", 9)
    cv.drawRightString(A4[0] - 72, 38, f"Strona {doc.page}")
    cv.restoreState()


# ------------------------------------------------------------------ treść
def build():
    s = []
    # ---- tytuł + spis treści (strona 1)
    s.append(Spacer(1, 4))
    s.append(P("Instrukcja działania projektu UDT->CSV", "title"))
    s.append(P("Jak zamienić typy i bloki danych ze sterownika na szablony i instancje AVEVA – "
               "w projektach Claude Desktop", "subtitle"))
    s.append(P(f"Autor: {AUTHOR}<br/>{AUTHOR_NOTE} · wtyczka GalaxyMCP {PLUGIN_VERSION}", "small"))
    t = Table([[""]], colWidths=[W], rowHeights=[2])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1.2, HEAD)]))
    s.append(t)
    s.append(P("Spis treści", "tochead"))
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc0", fontName="Body", fontSize=11, leading=14, spaceBefore=6, spaceAfter=6)]
    toc.dotsMinLevel = 0
    s.append(toc)
    s.append(PageBreak())

    # ---- 1
    s.append(H1("1. Do czego służy projekt"))
    s.append(P("Projekt <b>UDT->CSV</b> zamienia dane ze sterownika na obiekty AVEVA System Platform. Z typów danych "
               "PLC (UDT) powstają <b>szablony</b>, a z bloków danych (DB) – <b>instancje</b> z gotowymi adresami do "
               "drivera OI SIDirect. Całą pracę wykonuje Claude w projekcie; użytkownik dostarcza pliki i odpowiada "
               "na kilka pytań. Projekt i wtyczka GalaxyMCP <b>działają na AVEVA System Platform 2026</b> "
               "(sprawdzone na galaktykach testowych)."))
    s.append(table([
        ["Tryb", "Co dostajesz", "Kiedy wybrać"],
        ["Manual", f"Pliki CSV: szablon {c('$t_&lt;UDT&gt;.csv')} i instancje {c('Instances_&lt;UDT&gt;.csv')} – "
                   "w odpowiedzi wątku i w Library projektu. Importujesz je sam w ArchestrA IDE.",
         "Brak serwera GalaxyMCP, galaktyka na innym komputerze, chcesz przejrzeć pliki przed importem."],
        ["Auto", "Obiekty zapisane bezpośrednio w galaktyce przez serwer GalaxyMcp. Najpierw plan, zapis dopiero "
                 "po Twojej zgodzie.",
         "Masz zainstalowane rozszerzenie „GalaxyMCP” i galaktykę z prawem zapisu."],
    ], [W * 0.13, W * 0.47, W * 0.40]))
    s.append(Spacer(1, 6))
    s.append(note("<b>Jak działa projekt w Claude.</b> Projekt to jedna <b>rozmowa projektu</b>, w której Claude "
                  "(koordynator) przyjmuje zlecenia i dla każdego zadania zakłada osobny <b>wątek</b>. Wątek pracuje "
                  "w chmurze, zadaje pytania i oddaje wyniki. Pliki projektu są w <b>Library</b>, a instrukcja "
                  "projektu – w ustawieniach projektu (rozdział 3.3)."))

    # ---- 2
    s.append(H1("2. Wymagania"))
    s += bullets([
        "Aktualny <b>Claude Desktop</b> (albo przeglądarka: claude.ai/code). Projekty są w lewym menu: "
        f"{ui('Projects')}, pod {ui('Search')}.",
        "Plan <b>Pro, Max lub Ultra</b>. Projekty są w becie: nie ma ich jeszcze w planach Team i Enterprise, "
        "a dostęp włączany jest stopniowo.",
        f"Folder {c('Konfiguracja_projektu')} z repozytorium: {c('Context.zip')}, "
        f"{c('Project_instructions_ustawienia.txt')} i {c('prompt.txt')} (rozdział 3); opcjonalnie OISIDIR.pdf "
        "oraz Permissions.csv.",
        f"Tryb Auto: komputer z <b>AVEVA System Platform 2026</b> (lub dostęp do węzła GR), rozszerzenie "
        f"<b>GalaxyMCP</b> w wersji {PLUGIN_VERSION} oraz <b>uruchomiony Claude Desktop</b> na tym komputerze "
        "w czasie pracy – instalacja i ustawienia w instrukcji użytkownika wtyczki "
        f"({c('GalaxyMcp_Instrukcja_uzytkownika.pdf')}) i w {c('Tools/GalaxyMcp_README.md')}.",
        "W ustawieniach rozszerzenia: galaktyka na liście „Dozwolone galaktyki” i „Galaktyki z prawem zapisu”, "
        "odznaczone „Tylko odczyt”.",
    ])

    # ---- 3 NOWY
    s.append(H1("3. Założenie projektu w Claude Desktop"))
    s.append(P("Projekt zakładasz raz. Potem każde nowe zlecenie wpisujesz w jego rozmowie (rozdział 5)."))
    s.append(P(f"Wszystko, czego potrzebujesz do założenia projektu, jest w folderze {c('Konfiguracja_projektu')} "
               f"repozytorium (po pobraniu: {c('Galaxy_MCP-main\\Konfiguracja_projektu')}):"))
    s.append(table([
        ["Plik", "Do czego", "Gdzie go użyć"],
        [c("Context.zip"), "Pliki projektu: foldery Tools, ITERACJE i Wzorce_SCL, t_SampleUDT.csv, OISIDIR_tekst.txt.",
         f"{ui('Library')} projektu – rozdział 3.2"],
        [c("Project_instructions_ustawienia.txt"), "Instrukcja projektu – reguły, według których Claude pracuje "
         "w każdym wątku.", f"{ui('Project settings')} → {ui('Memory')} → {ui('Project instructions')} – rozdział 3.3"],
        [c("prompt.txt"), "Pierwszy prompt: rozpakowanie Context.zip i sprawdzenie projektu.",
         "Rozmowa projektu, raz po założeniu – rozdział 3.6"],
    ], [W * 0.30, W * 0.38, W * 0.32]))
    s.append(Spacer(1, 4))
    s.append(P(f"Do trybu Auto potrzebny jest jeszcze plik wtyczki {c('GalaxyMcp.mcpb')}. Nie ma go w folderze "
               f"Konfiguracja_projektu ani w Download ZIP – pobierasz go z {ui('Releases')} repozytorium (rozdział 3.5)."))
    s.append(H2("3.1. Utworzenie projektu"))
    s += steps([
        f"Otwórz Claude Desktop i w lewym menu wybierz {ui('Projects')} – pozycja pod {ui('Search')}.",
        f"Kliknij {ui('New project')} (prawy górny róg listy projektów). Jeśli zamiast niego jest "
        f"{ui('Get started')}, kliknij go i wykonaj kroki, które pokaże aplikacja (przeniesienie albo archiwizacja "
        "projektów z czatu), potem wróć do tego kroku.",
        f"W oknie {ui('New project')} wypełnij: {ui('Name')} – np. <b>UDT->CSV</b>; "
        f"{ui('What do you want to work on?')} (opcjonalnie) – jedno zdanie celu, np. „Konwersja typów i bloków "
        "danych z TIA Portal na szablony i instancje AVEVA (pliki CSV albo zapis przez GalaxyMCP)”.",
        f"W polu {ui('Context')} kliknij {ui('+')} i dodaj plik {c('Context.zip')} (rozdział 3.2). Repozytorium "
        "GitHub nie jest potrzebne.",
        f"Kliknij {ui('Create project')}. Otworzy się rozmowa projektu z polem wiadomości na dole.",
        f"Jeśli Claude pokaże {ui('Setup recommendations')} (proponowane repozytoria, zadania cykliczne), "
        f"wyłącz wszystkie propozycje albo po prostu je pomiń – temu projektowi nie są potrzebne.",
    ])
    s.append(H2("3.2. Pliki projektu (Library)"))
    s.append(P(f"Do Library dodajesz <b>jeden plik: {c('Context.zip')}</b> z folderu {c('Konfiguracja_projektu')}. "
               f"Dodaj go w polu {ui('Context')} przy zakładaniu projektu albo później przyciskiem {ui('Library')} "
               f"w nagłówku projektu → {ui('Add')}. Nie rozpakowuj go na dysku – Claude rozpakuje go do plików "
               "projektu po pierwszym prompcie (rozdział 3.6)."))
    s.append(P(f"Opcjonalnie dodaj obok, jako osobne pliki: {c('OISIDIR.pdf')} (oryginał dokumentacji drivera "
               f"OI SIDirect) i {c('Permissions.csv')} (reguły zapisu – możesz go też dołączać do pojedynczego "
               "zlecenia)."))
    s.append(note(
        (f"<b>Aktualizacja pliku:</b> pliki w projekcie są kopiami. Po zmianie pliku na dysku dodaj go ponownie "
          f"({ui('Library')} → {ui('Add')}) i przy pytaniu o istniejącą nazwę wybierz {ui('Replace')}. "
          "Wątki czytają zawsze tę wersję pliku, która jest w Library. Nowy Context.zip rozpakuj tym samym "
          "pierwszym promptem (rozdział 3.6).")))
    s.append(H2("3.3. Instrukcja projektu"))
    s += steps([
        f"W nagłówku projektu kliknij menu <font name=\"Mono\"><b>⋯</b></font> (trzy kropki) → {ui('Settings')}. Otworzy się {ui('Project settings')}.",
        f"W lewym menu wybierz {ui('Memory')} i przewiń do pola {ui('Project instructions')}. To nie jest pole "
        f"{ui('What do you want to work on?')} z zakładki {ui('General')} – tam wpisuje się tylko jedno zdanie celu.",
        f"Otwórz w Notatniku plik {c('Konfiguracja_projektu/Project_instructions_ustawienia.txt')}. Zaznacz całość "
        f"({ui('Ctrl+A')}), skopiuj ({ui('Ctrl+C')}) i wklej w pole ({ui('Ctrl+V')}). Plik mieści się w limicie "
        "pola (16 000 znaków) – wklej go w całości, bez skracania.",
        f"Kliknij {ui('Save changes')}.",
    ])
    s.append(P("Instrukcja projektu to reguły pracy Claude: tryby Manual i Auto, kolejność pytań w wątku, "
               "zasady generowania i zapisu do galaktyki oraz lista plików projektu. Działa w każdym nowym wątku. "
               "Po aktualizacji projektu wklej w to pole nową treść pliku tak samo (zaznacz w polu całość i wklej) "
               "i zlecaj pracę w nowym wątku."))
    s.append(H2("3.4. Modele"))
    s += bullets([
        f"{ui('Project settings')} → sekcja {ui('Models')}: {ui('Coordinator')} – model rozmowy projektu, "
        f"{ui('Threads')} – model i poziom effort wątków (wybierane razem w jednym polu, np. „Opus 5.5 Medium”).",
        f"Zalecany effort wątków: <b>{ui('Medium')}</b> albo <b>{ui('High')}</b>. Medium wystarcza do zwykłych "
        "zleceń i oszczędza limit planu; High wybierz przy dużych plikach i wielu typach naraz.",
        f"W {ui('General')} są też {ui('Pause')}, {ui('Archive')} i {ui('Delete')} (usunięcie projektu jest "
        "nieodwracalne).",
    ])
    s.append(H2("3.5. Wtyczka GalaxyMCP (tylko tryb Auto)"))
    s.append(P("Wtyczkę instalujesz na komputerze z AVEVA System Platform 2026, na którym działa Claude Desktop. "
               "W trybie Manual pomiń ten rozdział."))
    s += steps([
        f"Na stronie repozytorium na GitHubie otwórz {ui('Releases')} (prawa kolumna strony) i wybierz najnowsze "
        f"wydanie – <b>GalaxyMCP {PLUGIN_VERSION}</b>, oznaczone {ui('Latest')}. Bezpośredni link: "
        f"{c('github.com/MateuszAntonowicz/Galaxy_MCP/releases/latest')}.",
        f"W sekcji {ui('Assets')} kliknij {c('GalaxyMcp.mcpb')} i zapisz plik na dysku tego komputera (np. w folderze "
        f"Pobrane). {c('GalaxyMcp.exe')} i {c('GalaxyMcp.exe.config')} z tego wydania nie są potrzebne – wtyczka jest "
        "w całości w pliku .mcpb.",
        f"W Claude Desktop otwórz {ui('Settings')} → {ui('Desktop app')} → {ui('Extensions')} → {ui('Manage')}, "
        f"kliknij {ui('Advanced settings')} i w sekcji {ui('Extension Developer')} kliknij {ui('Install Extension…')}. "
        f"Wskaż pobrany plik {c('GalaxyMcp.mcpb')}. Pliku nie dodajesz w {ui('Settings')} → {ui('Plugins')} – "
        f"{ui('Upload a plugin')} przyjmuje tylko paczki pluginów i skille, nie pliki .mcpb.",
        "W oknie instalacji sprawdź nazwę <b>GalaxyMCP</b> i listę narzędzi, potwierdź instalację. Claude Desktop "
        "rozpakowuje wtyczkę do własnego folderu, więc pobrany plik może zostać w dowolnym miejscu.",
        "Wypełnij formularz ustawień (później: ta sama ścieżka → GalaxyMCP): <b>Węzeł GR</b> – nazwa komputera "
        "z serwerem galaktyk (puste = ten komputer); <b>Galaktyka na start</b>; <b>Dozwolone galaktyki</b>; "
        "<b>Galaktyki z prawem zapisu</b> – tylko galaktyki testowe; <b>Tylko odczyt</b> odznacz dopiero po "
        "wypełnieniu listy zapisu; <b>Zezwól na deploy</b> – zostaw wyłączone, dopóki nie potrzebujesz wdrażania.",
        f"Zapisz i upewnij się, że przełącznik {ui('Enabled')} jest włączony.",
    ])
    s.append(note([
        P("<b>Zmiana ustawień wtyczki:</b> wtyczka czyta ustawienia przy starcie. Po zapisaniu zmian wyłącz "
          f"{ui('Enabled')}, odczekaj kilka sekund i włącz {ui('Enabled')}. Po wyłączeniu proces "
          f"{c('GalaxyMcp.exe')} wylogowuje się z galaktyki i kończy sam – restart komputera nie jest potrzebny."),
        P(f"<b>Aktualizacja:</b> nowy {c('GalaxyMcp.mcpb')} z {ui('Releases')} instalujesz tak samo – zastępuje "
          "zainstalowaną wtyczkę, ustawienia zostają. Wersję pokazuje status galaktyki (pozycja „Wersja”)."),
        P(f"<b>Dziennik GalaxyMcp.log</b> jest w folderze rozszerzeń Claude Desktop ({c('Claude Extensions')}, "
          "podfolder z „galaxy” w nazwie). Znajdziesz go w PowerShell poleceniem: "
          f"{c('Get-ChildItem $env:LOCALAPPDATA, $env:APPDATA -Recurse -Filter GalaxyMcp.log -ErrorAction SilentlyContinue')}. "
          "Dołączaj go do zgłoszeń problemów."),
    ]))
    s.append(P(f"Szczegóły ustawień i diagnostyki: {c('GalaxyMcp_Instrukcja_uzytkownika.pdf')}, rozdziały 2–4 i 8."))
    s.append(H2("3.6. Pierwszy prompt"))
    s.append(P("Pierwszy prompt wysyłasz raz, gdy Context.zip jest już w Library (3.2), a instrukcja projektu "
               "jest zapisana (3.3), a w trybie Auto – po instalacji wtyczki (3.5). Wysyłasz go też po każdej podmianie Context.zip na nowszy."))
    s += steps([
        f"Otwórz w Notatniku plik {c('Konfiguracja_projektu/prompt.txt')}, zaznacz całość ({ui('Ctrl+A')}) "
        f"i skopiuj ({ui('Ctrl+C')}).",
        "Wklej treść w pole wiadomości rozmowy projektu i wyślij. Claude założy wątek.",
        "W wątku Claude: rozpakuje Context.zip do plików projektu (z folderami Tools, ITERACJE, Wzorce_SCL), "
        "sprawdzi kompletność plików, porówna instrukcję projektu z ustawień z Tools/Instrukcja_projektu.md, "
        "uruchomi próbnie generator i sprawdzi, czy są dostępne narzędzia wtyczki GalaxyMCP (tylko odczyt, "
        "galaxy_status).",
        "Jeśli plik w projekcie różni się od wersji z archiwum, Claude zapyta kartą, którą wersję zostawić. "
        "Jeśli nie widzi narzędzi GalaxyMCP, poprosi o połączenie wątku z komputerem z AVEVA – zatwierdź to "
        "(potrzebne tylko w trybie Auto).",
        "Na koniec dostaniesz krótkie podsumowanie: co zapisano, czego brakuje i czy projekt jest gotowy "
        "do pracy w trybie Manual i Auto. Wtedy możesz wysłać pierwsze zlecenie (rozdział 5).",
    ])

    # ---- 4
    s.append(H1("4. Przygotowanie plików ze sterownika"))
    s.append(table([
        ["Plik", "Zawartość", "Jak uzyskać"],
        [c(".udt / .scl"), f"Definicje typów: {c('TYPE &quot;UDT_…&quot; STRUCT … END_TYPE')}. Może być kilka typów "
                           "w jednym pliku.",
         "W środowisku programowania sterownika: PLC data types → zaznacz typy → prawy przycisk → <b>Generate "
         "source from blocks</b>. Dołącz też typy zagnieżdżone."],
        [c(".db"), f"Bloki danych: {c('DATA_BLOCK &quot;…&quot; VAR … END_VAR')}. Każdy element typu UDT = jedna "
                   "instancja.", "Program blocks → zaznacz DB → <b>Generate source from blocks</b>."],
    ], [W * 0.15, W * 0.42, W * 0.43]))
    s.append(Spacer(1, 4))
    s.append(P("<b>Plik z typami jest zawsze potrzebny.</b> Sam plik .db nie wystarczy – generator przerwie pracę "
               "z komunikatem. Jeśli nie masz pliku .db, możesz podać pary „obiekt = DB” w wątku."))
    s.append(P("Instancje powstają z każdego elementu typu UDT w bloku danych:"))
    s.append(table([
        ["Układ w DB", "Nazwa instancji"],
        [c('Pompa_01 : "UDT_Naped_2stany"'), c("DB_Napedy_Pompa_01")],
        [c('Zawory : Array[1..2] of "UDT_zawor"'), f"{c('DB_Linia_Zawory_1')}, {c('DB_Linia_Zawory_2')}"],
        [f"UDT w strukturze: {c('Sekcja_A : Struct … Pompa : &quot;UDT_…&quot;')}", c("DB_Linia_Sekcja_A_Pompa")],
        ["DB utworzony wprost z typu UDT (bez sekcji VAR)", f"nazwa DB, np. {c('DB_Zawor_05')}"],
    ], [W * 0.58, W * 0.42]))
    s.append(Spacer(1, 4))
    s.append(P("Wartości startowe (sekcja BEGIN) i zmienne proste w DB są pomijane. DB instancyjny bloku FB jest "
               "pomijany z ostrzeżeniem."))

    # ---- 5
    s.append(H1("5. Przebieg pracy krok po kroku"))
    s += steps([
        f"Otwórz projekt: lewe menu → {ui('Projects')} → <b>UDT->CSV</b>. Zlecenia piszesz w polu "
        "wiadomości na dole <b>rozmowy projektu</b>.",
        f"Dołącz pliki .udt i .db (opcjonalnie także Permissions.csv) przyciskiem {ui('+')} obok pola wiadomości "
        f"albo dodaj je wcześniej do {ui('Library')}. Napisz np. „Wygeneruj szablony i instancje z tych plików”.",
        "Claude założy <b>wątek</b> – pojawi się jako karta pod Twoją wiadomością. Kliknij ją, żeby otworzyć wątek. "
        f"Wszystkie wątki widać w panelu {ui('Overview')} (przycisk {ui('Threads')} w nagłówku; kropka na nim = "
        f"wątek czeka na Ciebie, grupa {ui('Waiting on you')}).",
        "Odpowiedz w wątku na pytania – pojawiają się jako karty z opcjami do kliknięcia: tryb (Manual/Auto), czy "
        "tworzyć instancje, czy wpisać adresy PLC, skąd reguły zapisu (dołączony Permissions.csv albo reguły "
        "podane w wątku), a na końcu nazwa szablonu – $t_UDT_zawor czy $UDT_zawor.",
        "Gdy wybrałeś adresy – podaj nazwę obiektu DI (SIDirect) w galaktyce i grupę skanowania (np. S7C_01 i SG1).",
        "Claude pokaże przykładowe adresy z Twoich danych. Zatwierdź je albo wklej jeden poprawny adres z działającej "
        "galaktyki – Claude dopasuje do niego wzorzec.",
        "Claude uruchomi generator i pokaże podsumowanie: liczbę zmiennych i instancji, tabelę typów i tryby "
        "(R / RW / W) oraz punkty „Do sprawdzenia”. Postęp widać na liście kroków w wątku.",
        f"<b>Manual:</b> pobierz pliki CSV z odpowiedzi w wątku albo z {ui('Library')} i zaimportuj (rozdział 6). "
        "<b>Auto:</b> przejrzyj plan i odpowiedz w wątku „tak” dla wskazanej galaktyki – dopiero wtedy nastąpi "
        "zapis (rozdział 7).",
    ])
    s.append(note("Poprawki i pytania do tej samej konwersji pisz <b>w wątku</b> (jego własne pole wiadomości). "
                  "Nowe, niezależne zlecenie – w rozmowie projektu; Claude założy dla niego nowy wątek. Wątek, który "
                  "skończył pracę, zamyka się sam po tygodniu bez aktywności."))
    s.append(P("Przykładowy wzorzec adresów:"))
    s.append(codeblock([
        "stan_Stan_Aktywny        → S7C_01.SG1.Mieszalnik_1.Zawor_Wody.stan.Stan_Aktywny",
        "stan_Komenda_HMI_Aktywuj → S7C_01.SG1.attribute(Mieszalnik_1.Zawor_Wody.stan.\"Komenda_HMI_ Aktywuj\")",
        "Pomiary_Temp_1           → S7C_01.SG1.Mieszalnik_1.Naped.Pomiary.Temp[1]",
    ]))

    # ---- 6
    s.append(H1("6. Tryb Manual – import w ArchestrA IDE"))
    s += steps([
        f"Pobierz pliki z wątku albo z {ui('Library')} projektu i zapisz na dysku <b>bez zmiany nazw</b>.",
        f"<b>Szablony:</b> menu {c('Galaxy → Import → Object(s)…')} → plik {c('$t_&lt;UDT&gt;.csv')}. Przy wielu "
        "typach najpierw typ zawierany, potem zawierające. Szablon nie może być otwarty ani wyewidencjonowany.",
        f"Przy konflikcie nazw: {c('Replace entire template')}, gdy szablon nie ma ręcznych dodatków; gdy ma – "
        f"najpierw wyeksportuj kopię, potem {c('Overwrite Wizards, and update attributes and linked content')}.",
        f"<b>Instancje:</b> {c('Galaxy → Galaxy Load…')} → plik {c('Instances_&lt;UDT&gt;.csv')}.",
        f"Sprawdź jeden obiekt (atrybuty, {c('#IO.Mode')}, {c('InputSource')}), potem check in i deploy.",
    ])

    # ---- 7
    s.append(H1("7. Tryb Auto – zapis przez GalaxyMCP"))
    s.append(P("Wątek pracuje w chmurze, a GalaxyMCP – na Twoim komputerze. Wątek widzi narzędzia galaktyki tylko "
               "wtedy, gdy jest <b>połączony z komputerem</b>, na którym działa Claude Desktop z włączonym "
               "rozszerzeniem."))
    s += steps([
        "Na komputerze z AVEVA uruchom Claude Desktop (zalogowany na to samo konto) i nie zamykaj go do końca "
        "zapisu. Komputer nie może przejść w uśpienie.",
        "Gdy wątek poprosi o dostęp do Twojego komputera (karta w wątku), zatwierdź ją – przy kilku komputerach "
        "wybierz ten z AVEVA.",
        f"Claude sprawdza serwer ({c('galaxy_status')}) i podaje aktywną galaktykę oraz czy zapis jest dozwolony. "
        "Zmiana galaktyki tylko na Twoją prośbę.",
        f"Claude pokazuje plan ({c('dry_run')}): co zostanie utworzone lub zmienione. Nic nie jest jeszcze zapisywane.",
        "Zamknij w IDE edytory obiektów, których dotyczy zapis, i potwierdź w wątku zapis dla konkretnej galaktyki.",
        "Claude zapisuje najpierw szablon, potem instancje, a następnie sprawdza jedną instancję i powtarza plan – "
        "powinien pokazać same „bez zmian”.",
        "Deploy wykonywany jest tylko na wyraźne polecenie (wymaga włączenia w ustawieniach rozszerzenia).",
    ])
    s.append(P("Zabezpieczenia serwera: nie usuwa obiektów ani atrybutów; odrzuca zapis do galaktyki spoza listy "
               "zapisu lub innej niż aktywna; pomija instancje utworzone z innego szablonu. Jeden proces wtyczki "
               "obsługuje wszystkie wątki połączone z komputerem – galaktyka przełączona w jednym wątku jest "
               "aktywna także w innych."))

    # ---- 8
    s.append(H1("8. Zasady konwersji"))
    s.append(H2("8.1. Typy danych"))
    s.append(table([
        ["Sterownik", "AVEVA"],
        ["Bool", "MxBoolean"], ["Real", "MxFloat"], ["LReal", "MxDouble"],
        ["SInt, Int, DInt, USInt, UInt, UDInt, Byte, Word, DWord", "MxInteger"],
        ["LInt, LWord, ULInt", "MxInteger (ostrzeżenie: 64 bity)"],
        ["String, String[n], WString, Char, WChar", "MxString"],
        ["Time", "MxElapsedTime (sufiks T, tylko odczyt)"],
        ["LTime, S5Time, Time_Of_Day, Date, LDT, Date_And_Time", "MxTime (z sufiksem)"],
        ["DTL, LTime_Of_Day", "MxTime bez sufiksu – sprawdź w Object Viewer"],
    ], [W * 0.55, W * 0.45]))
    s.append(Spacer(1, 4))
    s.append(P("Typ czasowy, który ma być zapisywalny ze SCADA, dostaje typ MxInteger w jednostce drivera (ms, dla "
               "LTime ns, dla Date dni)."))
    s.append(H2("8.2. Nazwy"))
    s += bullets([
        f"Struktury i zagnieżdżone UDT są spłaszczane przez „_”: {c('stan.Stan_Aktywny')} → "
        f"{c('stan_Stan_Aktywny')}; adres zachowuje ścieżkę w PLC.",
        f"Tablice: {c('Temp[1..3]')} → {c('Temp_1…Temp_3')}; 2D {c('Siatka_1_0')}; indeks ujemny {c('Neg_m1')}.",
        "Spacje są usuwane, polskie litery bez ogonków (Prędkość → Predkosc), inne niedozwolone znaki zamieniane na „_”; "
        "nazwy różniące się tylko wielkością liter dostają licznik (stan_x_1); adres zachowuje oryginalną nazwę.",
        f"Nazwy i opisy nie są skracane. Instancja z DB ma nazwę {c('&lt;DB&gt;_&lt;element&gt;')}, np. "
        f"{c('Mieszalnik_1_Zawor_Wody')}.",
    ])
    s.append(H2("8.3. Kierunek zapisu"))
    s.append(P("<b>Plik Permissions.csv jest opcjonalny.</b> Jeśli chcesz z niego skorzystać, dodaj go do Library "
               "projektu albo dołącz do zlecenia razem z plikami .udt/.db. Bez pliku podajesz reguły w wątku (np. "
               "„Komenda_ = zapis, reszta odczyt”), a gdy ich nie podasz, obowiązują reguły domyślne: "
               f"{c('Cmd_')}, {c('Set_')}, {c('Cfg_')}, {c('Par_')} → odczyt i zapis, reszta → tylko odczyt."))
    s.append(P("Kierunek wynika z początku nazwy zmiennej (bez nazw struktur nadrzędnych); decyduje pierwsza "
               "pasująca reguła, brak dopasowania = tylko odczyt."))
    s.append(table([
        ["Access_Mode", "W IDE", "Przykładowe prefiksy (wzorcowy Permissions.csv)"],
        ["Input", "Read (R)", "Stan_, Status_, Alarm, Warn_, PV_, Act_, Wydajnosc_, Komenda_Historia"],
        ["InputOutput", "Read/Write (RW)", "Komenda_, Konfiguracja_, Zadana_, Nastawa_, Cmd_, Set_, Cfg_, Par_"],
        ["Output", "Write (W)", "brak we wzorcowym pliku; w trybie Auto pomijane z ostrzeżeniem"],
    ], [W * 0.18, W * 0.2, W * 0.62]))
    s.append(Spacer(1, 4))
    s.append(P(f"Plik Permissions.csv ma kolumny {c('Prefix_or_Keyword')}, {c('Access_Mode')} i opcjonalnie "
               f"{c('Description')}; edytujesz go w Excelu (przecinek lub średnik). <b>Nie zmieniaj nazw kolumn.</b> "
               "Wielkość liter w prefiksie ma znaczenie."))
    s.append(H2("8.4. Elementy pomijane (z ostrzeżeniem)"))
    s += bullets([
        "Variant, typy bez definicji w dołączonych plikach, rekurencja typów.",
        f"Tablice o granicach ze stałej ({c('[1..&quot;MAX_N&quot;]')}) i poza limitami drivera (ponad 6 wymiarów "
        "lub 1600 elementów).",
        "Zmienne proste na poziomie głównym DB (nie są instancją żadnego UDT).",
        f"Wartości początkowe tablic ({c(':= [1, 2]')}) i literały dat i godzin ({c('D#…')}, {c('TOD#…')}) – "
        f"pozostałe wartości {c(':= …')} (Bool, liczby, tekst, T#…) trafiają do szablonu.",
    ])

    # ---- 9
    s.append(H1("9. Najczęstsze problemy"))
    s.append(table([
        ["Objaw", "Rozwiązanie"],
        [f"Brak {ui('Projects')} w lewym menu pod {ui('Search')}",
         f"Sprawdź pod {ui('More')} i zaktualizuj Claude Desktop. Projekty wymagają planu Pro, Max lub Ultra "
         "(beta, włączana stopniowo; brak w Team i Enterprise)."],
        [f"{ui('Get started')} zamiast {ui('New project')}",
         "Kliknij go i wykonaj kroki, które pokazuje aplikacja (przeniesienie albo archiwizacja projektów z czatu)."],
        ["Claude nie zna reguł projektu / pracuje „po swojemu”",
         "Sprawdź, czy w Project instructions jest wklejona cała treść Project_instructions_ustawienia.txt "
         "(rozdział 3.3) i czy po pierwszym prompcie (3.6) w Library są foldery Tools, ITERACJE i Wzorce_SCL. "
         "Instrukcja działa w nowych wątkach – zleć zadanie ponownie."],
        ["Wątek czyta nieaktualną treść pliku",
         f"Dodaj plik ponownie w {ui('Library')} i wybierz {ui('Replace')}; potem nowy wątek."],
        ["Wątek czeka i nic się nie dzieje",
         f"Otwórz {ui('Threads')} → grupa {ui('Waiting on you')}: wątek czeka na odpowiedź albo zatwierdzenie "
         "karty w samym wątku."],
        ["„W pliku nie ma bloku TYPE … STRUCT”", "Dołącz plik z typami (.udt/.scl), nie tylko .db."],
        ["Mniej instancji niż elementów w DB",
         "Brakuje definicji typu w pliku .udt (ostrzeżenie „brak definicji typu”) albo element jest zmienną prostą "
         "– dołącz brakujące typy."],
        ["„W pliku Permissions.csv nie ma reguł”", "Przywróć nazwy kolumn Prefix_or_Keyword i Access_Mode."],
        ["Zmienne Komenda_… są tylko do odczytu",
         "Nie dołączono Permissions.csv ani reguł – działają reguły domyślne. Dołącz plik albo podaj reguły w wątku."],
        ["Brak trybu Auto / narzędzi galaxy",
         "Na komputerze z AVEVA uruchom Claude Desktop i sprawdź w Settings → Desktop app → Extensions (Manage), czy rozszerzenie jest "
         "włączone. W wątku napisz „Połącz się z moim komputerem” i zatwierdź kartę. Jeśli nadal brak – sprawdź w "
         "Ustawienia → Code (Claude Code), czy włączone jest „Use this computer from your phone and claude.ai”, "
         "i poproś w rozmowie projektu o nowy wątek."],
        ["„Zapis zablokowany”",
         "Dopisz galaktykę do „Galaktyki z prawem zapisu”, odznacz „Tylko odczyt”, potem uruchom wtyczkę ponownie "
         "(wyłącz Enabled, odczekaj kilka sekund, włącz Enabled)."],
        ["Zapis odrzucony – obiekt wyewidencjonowany", "Zamknij edytor obiektu w IDE (check in) i powtórz."],
        ["Serwer znika bez komunikatu", "Securden zablokował GalaxyMcp.exe – zatwierdź aplikację albo poproś IT o regułę."],
        ["Plan pokazuje „POMINIĘTE atrybuty Write”", "Reguły zawierają Output – tryb Auto ich nie tworzy; dodaj je w IDE albo użyj trybu Manual."],
    ], [W * 0.36, W * 0.64]))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Instrukcja_UDT_CSV.pdf")
    a = ap.parse_args()
    doc = Doc(a.out, pagesize=A4, leftMargin=72, rightMargin=72, topMargin=62, bottomMargin=64,
              title="Instrukcja działania projektu UDT->CSV", author=f"{AUTHOR} {AUTHOR_NOTE}",
              subject="TIA Portal → AVEVA System Platform (CSV / GalaxyMCP)")
    doc.multiBuild(build(), onFirstPage=on_page, onLaterPages=on_page)
    print("Zapisano:", a.out)


if __name__ == "__main__":
    main()
