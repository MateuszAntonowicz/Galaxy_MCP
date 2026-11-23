#!/usr/bin/env python3
"""
Generuje GalaxyMcp_Instrukcja_uzytkownika.pdf - instrukcję korzystania z wtyczki
"GalaxyMCP" w Claude Desktop (projekt UDT->CSV).
Dotyczy projektów Claude (zakładka Code → Projects: rozmowa projektu + wątki, Library,
połączenie wątku z komputerem) i wtyczki 0.2.5.

Użycie:  python GalaxyMcp_instrukcja_pdf.py [--icon icon.png] [--out GalaxyMcp_Instrukcja_uzytkownika.pdf]
Wymaga:  reportlab; czcionka TTF z polskimi znakami (DejaVu Sans, Segoe UI, Arial - szukane automatycznie).
Ikona:   icon.png albo GalaxyMcp_icon.png.b64 obok skryptu (opcjonalnie).
Treść instrukcji jest w tym pliku - zmiany w wtyczce = aktualizacja tekstu poniżej i ponowne wygenerowanie PDF.
"""
import argparse, base64, io, os, sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

VERSION = "0.2.5"   # wersja wtyczki, której dotyczy instrukcja (nie jest drukowana)
DOC_YEAR = "2026"
AUTHOR = "Mateusz Antonowicz"
AUTHOR_NOTE = "z pomocą Claude AI"
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ czcionki
FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\consola.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\cour.ttf"),
]
for reg, bold, mono in FONT_CANDIDATES:
    if all(os.path.exists(p) for p in (reg, bold, mono)):
        pdfmetrics.registerFont(TTFont("Body", reg))
        pdfmetrics.registerFont(TTFont("Body-Bold", bold))
        pdfmetrics.registerFont(TTFont("Mono", mono))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")
        break
else:
    sys.exit("Brak czcionki TTF z polskimi znakami (DejaVu Sans / Segoe UI / Arial).")

# ------------------------------------------------------------------ kolory i style
NAVY = colors.HexColor("#12346A")
BLUE = colors.HexColor("#2F6FB5")
SKY = colors.HexColor("#E8F1FB")
AMBER = colors.HexColor("#FFF4DB")
AMBER_LINE = colors.HexColor("#E0A526")
RED_BG = colors.HexColor("#FDECEC")
RED_LINE = colors.HexColor("#C0392B")
GREEN_BG = colors.HexColor("#EAF6EE")
GREEN_LINE = colors.HexColor("#2E8B57")
GREY = colors.HexColor("#5B6573")
LINE = colors.HexColor("#C9D3DF")
TEXT = colors.HexColor("#1D2430")

S = {
    "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=26, leading=32, textColor=NAVY, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=11.5, leading=16, textColor=GREY, spaceAfter=18),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=17, leading=22, textColor=NAVY, spaceBefore=14, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=17, textColor=BLUE, spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.5, textColor=TEXT, spaceAfter=5, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.8, leading=12, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9, leading=12.2, textColor=TEXT),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=9, leading=12.2, textColor=colors.white),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=10, leading=14.5, textColor=TEXT, leftIndent=14,
                             bulletIndent=3, spaceAfter=2.5),
    "step": ParagraphStyle("step", fontName="Body", fontSize=10, leading=14.5, textColor=TEXT, leftIndent=18,
                           bulletIndent=0, spaceAfter=3.5, bulletFontName="Body-Bold", bulletColor=BLUE),
    "prompt": ParagraphStyle("prompt", fontName="Mono", fontSize=9, leading=12.5, textColor=NAVY),
    "tochead": ParagraphStyle("tochead", fontName="Body-Bold", fontSize=20, leading=26, textColor=NAVY, spaceAfter=14),
    "author": ParagraphStyle("author", fontName="Body", fontSize=10.5, leading=15, textColor=GREY),
}


def P(t, st="body"):
    return Paragraph(t, S[st])


def H1(t):
    """Nagłówek rozdziału: trafia do spisu treści (z odnośnikiem) i do zakładek PDF."""
    h = Paragraph(t, S["h1"])
    h.toc_key = "sec_%d" % (abs(hash(t)) % 10**8)
    return h


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        key = getattr(f, "toc_key", None)
        if key:
            text = f.getPlainText()
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


def code(t):
    return f'<font name="Mono" color="#12346A">{t}</font>'


def bullets(items):
    return [Paragraph(i, S["bullet"], bulletText="•") for i in items]


def steps(items):
    return [Paragraph(t, S["step"], bulletText=f"{n}.") for n, t in enumerate(items, 1)]


def table(rows, widths, header=True, zebra=True):
    data = [[c if not isinstance(c, str) else Paragraph(c, S["cellb" if (header and r == 0) else "cell"])
             for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("BOX", (0, 0), (-1, -1), 0.6, LINE)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if (r % 2 == 0):
                st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F5F8FC")))
    t.setStyle(TableStyle(st))
    return t


def box(content, kind="info", title=None):
    bg, line = {"info": (SKY, BLUE), "warn": (AMBER, AMBER_LINE), "stop": (RED_BG, RED_LINE),
                "ok": (GREEN_BG, GREEN_LINE)}[kind]
    inner = []
    if title:
        inner.append(Paragraph(f"<b>{title}</b>", S["body"]))
    inner += content if isinstance(content, list) else [Paragraph(content, S["body"])]
    t = Table([[inner]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, line),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return KeepTogether([t, Spacer(1, 8)])


def prompt_box(text):
    t = Table([[Paragraph(text, S["prompt"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F5F8")),
                           ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return KeepTogether([t, Spacer(1, 6)])


def flow_diagram():
    cells = ["Pliki ze sterownika<br/>.udt / .scl / .db", "Claude<br/>(projekt)",
             "Wtyczka<br/>GalaxyMCP", "Galaktyka<br/>AVEVA SP"]
    st = ParagraphStyle("fd", parent=S["cell"], alignment=1, textColor=colors.white, fontName="Body-Bold", fontSize=8.2)
    arrow = ParagraphStyle("ar", parent=S["cell"], alignment=1, textColor=BLUE, fontName="Body-Bold", fontSize=14)
    row = []
    for i, c in enumerate(cells):
        row.append(Paragraph(c, st))
        if i < len(cells) - 1:
            row.append(Paragraph("→", arrow))
    w = [36 * mm, 7 * mm] * 3 + [36 * mm]
    t = Table([row], colWidths=w, rowHeights=[16 * mm])
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
             ("RIGHTPADDING", (0, 0), (-1, -1), 2)]
    for i in range(0, len(row), 2):
        style.append(("BACKGROUND", (i, 0), (i, 0), NAVY if i in (0, len(row) - 1) else BLUE))
    t.setStyle(TableStyle(style))
    return t


def load_icon(path):
    if path and os.path.exists(path):
        return open(path, "rb").read()
    for cand in (os.path.join(HERE, "icon.png"), os.path.join(HERE, "GalaxyMcp_icon.png.b64")):
        if os.path.exists(cand):
            raw = open(cand, "rb").read()
            if cand.endswith(".b64"):
                lines = [l for l in raw.decode().splitlines() if l and not l.startswith("-----")]
                raw = base64.b64decode("".join(lines))
            return raw
    return None


def on_page(c, doc):
    c.saveState()
    if doc.page > 1:
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)
        c.setFont("Body", 8)
        c.setFillColor(GREY)
        c.drawString(20 * mm, 284 * mm, "Wtyczka GalaxyMCP – instrukcja użytkownika")
    c.setFont("Body", 8)
    c.setFillColor(GREY)
    c.drawRightString(190 * mm, 12 * mm, f"Strona {doc.page}")
    c.drawString(20 * mm, 12 * mm, f"UDT->CSV · {DOC_YEAR}")
    c.restoreState()


# Ponowne uruchomienie wtyczki po zmianie ustawień - jedno miejsce, używane w rozdz. 3, 4 i 8.
# Samo przełączenie Enabled nie zamyka procesu GalaxyMcp.exe, który czyta ustawienia tylko przy starcie.
RESTART_SHORT = ("wyłącz Enabled, zrestartuj komputer (albo zakończ wszystkie procesy GalaxyMcp.exe "
                 "w Menedżerze zadań) i włącz Enabled")


def restart_box():
    return box([
        P("Wtyczka czyta ustawienia <b>tylko przy starcie</b> procesu GalaxyMcp.exe. Samo wyłączenie i włączenie "
          "przełącznika Enabled <b>nie wystarcza</b> – stary proces może dalej działać w tle ze starymi ustawieniami."),
        P("<b>Sposób 1 – restart komputera (zalecany):</b>"),
        *steps(["Wyłącz przełącznik <b>Enabled</b> (wpisane ustawienia zostają).",
                "<b>Zrestartuj komputer.</b>",
                "Włącz <b>Enabled</b>."]),
        P("<b>Sposób 2 – bez restartu, ręczne zamknięcie procesów:</b>"),
        *steps(["Wyłącz przełącznik <b>Enabled</b>.",
                "Otwórz Menedżer zadań (<b>Ctrl+Shift+Esc</b>) → karta <b>Szczegóły</b>.",
                f"Zaznacz każdy proces {code('GalaxyMcp.exe')} → <b>Zakończ zadanie</b>. "
                "Na liście nie może zostać żaden.",
                "Włącz <b>Enabled</b>."]),
        P("Na koniec sprawdź status (rozdział 4): listy galaktyk muszą pokazywać nowe wartości."),
    ], "warn", "Po każdej zmianie ustawień – ponowne uruchomienie wtyczki")


# ------------------------------------------------------------------ treść
def build(icon_bytes):
    s = []
    # ---- strona tytułowa
    s.append(Spacer(1, 12 * mm))
    if icon_bytes:
        s.append(Image(io.BytesIO(icon_bytes), width=34 * mm, height=34 * mm, hAlign="LEFT"))
        s.append(Spacer(1, 8 * mm))
    s.append(P("Wtyczka GalaxyMCP", "title"))
    s.append(P("Instrukcja dla nowych użytkowników: instalacja, konfiguracja i praca<br/>"
               "Rozszerzenie Claude Desktop „GalaxyMCP”", "subtitle"))
    s.append(flow_diagram())
    s.append(Spacer(1, 10 * mm))
    s.append(P("W skrócie", "h2"))
    s += bullets([
        "Wtyczka pozwala Claude tworzyć w galaktyce AVEVA System Platform <b>szablony, atrybuty z I/O i instancje</b> "
        "na podstawie plików ze sterownika – bez ręcznego importu plików CSV.",
        "<b>Działa na AVEVA System Platform 2026</b> – sprawdzone na galaktykach testowych (plan, zapis szablonów "
        "i instancji, status wtyczki).",
        "Obsługiwane pliki: <b>.udt / .scl</b> z definicjami typów (także kilka typów w jednym pliku i typy "
        "zagnieżdżone w innych) oraz <b>.db</b> z blokami danych – z nich powstają instancje i ich adresy.",
        "Obsługuje <b>wszystkie typy danych atrybutów</b> z IDE: Boolean, Integer, Float, Double, String, Time, "
        "ElapsedTime, InternationalizedString i BigString (Dodatek B). Potrafi też dodać atrybut do jednej instancji, "
        "bez zmiany szablonu.",
        "Działa <b>lokalnie</b> na Twoim komputerze, przez bibliotekę GRAccess z ArchestrA IDE. Claude pracuje "
        "w chmurze, w wątku projektu, i sięga do wtyczki przez Claude Desktop uruchomiony na tym komputerze.",
        "Tworzy tylko zmienne, których wartość SCADA widzi: <b>Read</b> i <b>Read/Write</b>. Zmienne tylko do zapisu "
        "(Write) celowo pomija – wysyłają polecenia do sterownika „na ślepo”, bez odczytu stanu (Dodatek B). "
        "Takie zmienne zakładasz świadomie w trybie Manual.",
        "Zawsze najpierw pokazuje <b>plan</b>. Zapis następuje dopiero po Twoim wyraźnym „tak”, tylko w galaktykach, "
        "które dopuścisz w ustawieniach. Wtyczka <b>niczego nie usuwa</b>.",
        "Zmiana ustawień wtyczki wymaga <b>restartu komputera</b> albo <b>ręcznego zamknięcia procesów GalaxyMcp.exe</b> "
        "(rozdział 3).",
    ])
    s.append(PageBreak())

    # ---- spis treści (osobna strona, jedna kolumna, odnośniki do rozdziałów)
    s.append(P("Spis treści", "tochead"))
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("tocl0", fontName="Body", fontSize=11.5, leading=15, textColor=TEXT,
                                      leftIndent=0, firstLineIndent=0, spaceBefore=5, spaceAfter=5)]
    toc.dotsMinLevel = 0
    s.append(toc)
    s.append(PageBreak())

    # ---- 1. Wymagania
    s.append(H1("1. Wymagania"))
    s.append(table([
        ["Element", "Wymaganie", "Jak sprawdzić"],
        ["System", "Windows 10 (1803+) lub 11", "Ustawienia → System → Informacje"],
        ["AVEVA System Platform", "<b>AVEVA System Platform 2026</b> (wtyczka działa na tej wersji – sprawdzone) z zainstalowanym ArchestrA IDE (zawiera bibliotekę "
         "GRAccess) i dostępem do serwera galaktyk (Galaxy Repository)", "IDE otwiera galaktykę, z którą chcesz pracować"],
        [".NET Framework", "4.x (jest w każdym Windows 10/11)", "–"],
        ["Claude Desktop", "Aktualna wersja aplikacji, zalogowana na Twoje konto i <b>uruchomiona na tym komputerze</b> "
         "w czasie pracy w trybie Auto. Plan <b>Pro, Max lub Ultra</b> (projekty są w becie i nie ma ich jeszcze "
         "w planach Team i Enterprise).", "Zakładka <b>Code</b> → w lewym pasku <b>Projects</b> (albo pod <b>More</b>)"],
        ["Projekt UDT->CSV", "Projekt z plikami i instrukcją konwersji (założenie: instrukcja „Instrukcja działania "
         "projektu UDT->CSV”, rozdział 3)", "Projekt widoczny na liście <b>Projects</b>"],
        ["Plik wtyczki", code("GalaxyMcp.mcpb"), "–"],
    ], [38 * mm, 78 * mm, 54 * mm]))
    s.append(Spacer(1, 6))
    s.append(box("Tryb <b>Manual</b> (pliki CSV do importu w IDE) działa bez wtyczki – wystarczy dostęp do projektu. "
                 "Wtyczka jest potrzebna tylko do trybu <b>Auto</b>, czyli zapisu bezpośrednio do galaktyki.", "info"))

    # ---- 2. Instalacja
    s.append(H1("2. Instalacja wtyczki"))
    s += steps([
        f"Zapisz plik {code('GalaxyMcp.mcpb')} na dysku.",
        "W Claude Desktop otwórz <b>Ustawienia → Extensions → Advanced settings</b> i kliknij "
        f"<b>Install Extension…</b>, a następnie wskaż plik {code('GalaxyMcp.mcpb')}.",
        "W oknie instalacji sprawdź nazwę <b>GalaxyMCP</b> i listę 9 narzędzi, potwierdź instalację.",
        "Wypełnij formularz ustawień (rozdział 3) i zapisz.",
        "Upewnij się, że przełącznik <b>Enabled</b> jest włączony. Jeśli na tym komputerze wtyczka była już "
        "zainstalowana, uruchom ją ponownie tak, jak po zmianie ustawień (rozdział 3).",
    ])
    s.append(box("<b>Aktualizacja wtyczki:</b> zainstaluj nowy plik .mcpb tak samo jak pierwszy – zastępuje on "
                 "zainstalowaną wtyczkę, a ustawienia zostają. Potem uruchom wtyczkę ponownie (rozdział 3) i w nowym wątku "
                 "projektu sprawdź status: pozycja „Wersja” ma pokazać 0.2.5.", "info"))
    s.append(box("Claude Desktop rozpakowuje wtyczkę do własnego folderu rozszerzeń. Tam znajdziesz też plik "
                 f"dziennika {code('GalaxyMcp.log')} (przydatny przy zgłaszaniu problemów).", "info"))

    # ---- 3. Ustawienia
    s.append(H1("3. Ustawienia wtyczki"))
    s.append(P("Ustawienia otwierasz w <b>Ustawienia → Extensions → GalaxyMCP</b>."))
    s.append(table([
        ["Pole", "Co wpisać", "Przykład"],
        ["Węzeł GR (Galaxy Repository)", "Nazwa komputera z serwerem galaktyk. <b>Puste = ten komputer.</b> "
         "Na stacji bez GR wpisz nazwę serwera.", code("SRV-GR01")],
        ["Galaktyka na start", "Galaktyka aktywna po uruchomieniu. Puste = wybierzesz ją w wątku.", code("Galaktyka_Test")],
        ["Dozwolone galaktyki", "Lista po przecinku – tylko na nie Claude może się przełączyć. Puste = wszystkie.",
         code("Galaktyka_Test, Galaktyka_Dev, Galaktyka_Prod")],
        ["Galaktyki z prawem zapisu", "Lista po przecinku – <b>tylko galaktyki testowe</b>. Pozostałe są tylko do odczytu.",
         code("Galaktyka_Test")],
        ["Tylko odczyt", "Zaznaczone (domyślnie) = wtyczka niczego nie zapisuje. Odznacz <b>dopiero po</b> "
         "wypełnieniu listy galaktyk z prawem zapisu.", "odznaczone"],
        ["Zezwól na deploy", "Włącza wdrażanie instancji.", "wyłączone"],
        ["Użytkownik / Hasło", "Tylko dla galaktyk z włączonymi zabezpieczeniami. Hasło jest polem poufnym.", "puste"],
        ["Ścieżka do ArchestrA.GRAccess.dll", "Tylko gdy wtyczka nie znajdzie biblioteki sama.", "puste"],
    ], [42 * mm, 80 * mm, 48 * mm]))
    s.append(Spacer(1, 6))
    s.append(restart_box())
    s.append(box("Pusta lista „Galaktyki z prawem zapisu” przy odznaczonym „Tylko odczyt” oznacza zapis we "
                 "<b>wszystkich</b> dozwolonych galaktykach. Nie zostawiaj tego pola pustego.", "stop"))

    # ---- 4. Pierwsze uruchomienie
    s.append(H1("4. Pierwsze uruchomienie i test"))
    s.append(P("Wtyczka działa na Twoim komputerze, a Claude – w chmurze, w <b>wątku</b> projektu. Wątek dostaje "
               "narzędzia wtyczki dopiero wtedy, gdy jest <b>połączony z komputerem</b>, na którym działa "
               "Claude Desktop z włączoną wtyczką."))
    s += steps([
        "Na komputerze z AVEVA uruchom <b>Claude Desktop</b> i zostaw go otwartego (wtyczka działa tylko razem "
        "z aplikacją; komputer nie może przejść w uśpienie).",
        "Otwórz projekt: zakładka <b>Code</b> → <b>Projects</b> → <b>UDT->CSV</b>.",
        "W polu wiadomości na dole rozmowy projektu wpisz polecenie:",
    ])
    s.append(prompt_box("Sprawdź status galaktyki i listę galaktyk."))
    s += [Paragraph(t, S["step"], bulletText=f"{n}.") for n, t in [
        (4, "Claude zakłada do tego <b>wątek</b> – pojawia się jako karta pod Twoją wiadomością. Kliknij ją, żeby "
            "otworzyć wątek (wątki są też w panelu <b>Overview</b>, przycisk <b>Threads</b> w nagłówku projektu)."),
        (5, "Jeśli w wątku pojawi się karta z prośbą o <b>połączenie wątku z Twoim komputerem</b> – zatwierdź ją "
            "(wybierz komputer z AVEVA, jeśli masz kilka). Bez tego wątek nie widzi wtyczki."),
        (6, "Wynik pojawi się w wątku. Dalsze polecenia i zgody w tej samej sprawie pisz w polu wiadomości "
            "<b>tego wątku</b>."),
    ]]
    s.append(P("Prawidłowy wynik (przykład dla ustawień z rozdziału 3):"))
    s.append(table([
        ["Pozycja w statusie", "Oczekiwana wartość"],
        ["Wersja", "0.2.5"],
        ["Galaktyka (aktywna)", "Galaktyka_Test"],
        ["Zapis w aktywnej galaktyce", "DOZWOLONY"],
        ["Dozwolone galaktyki", "Galaktyka_Test, Galaktyka_Dev, Galaktyka_Prod"],
        ["Galaktyki z zapisem", "Galaktyka_Test"],
        ["Połączenie", "OK"],
    ], [70 * mm, 100 * mm]))
    s.append(Spacer(1, 6))
    s.append(box("Jeśli status pokazuje stare wartości (np. „nie wybrano”, „tylko odczyt” albo stare listy galaktyk "
                 "mimo zmiany w formularzu), nadal działa stary proces wtyczki. Samo przełączenie Enabled nie pomoże: "
                 f"{RESTART_SHORT} – szczegóły w rozdziale 3.", "info"))

    # ---- 5. Przykładowe polecenia
    s.append(H1("5. Przykładowe polecenia"))
    s.append(P("Nowe zadanie wpisujesz w <b>rozmowie projektu</b> – Claude założy do niego wątek. Pliki ze sterownika "
               "dołączasz przyciskiem <b>+</b> obok pola wiadomości albo dodajesz je wcześniej w <b>Library</b> "
               "projektu. Odpowiedzi na pytania, zgodę na zapis („tak”) i polecenia dotyczące tej samej konwersji "
               "piszesz już <b>w wątku</b>. Nazwy plików w poleceniu są dowolne."))
    s.append(table([
        ["Cel", "Polecenie do Claude"],
        ["Typy i instancje ze sterownika", "Przetwórz załączone pliki ze sterownika (definicje typów i blok danych), PLC_01."],
        ["Tylko szablony", "Przetwórz sam plik z definicjami typów, bez instancji."],
        ["Wybrany typ", "Zrób szablon tylko dla typu UDT_zawor."],
        ["Atrybut w jednej instancji", "Dodaj instancji Mixer_01 atrybut A_test typu Double, wartość początkowa 50, "
         "odczyt i zapis. Najpierw pokaż plan w Galaktyka_Test."],
        ["Sprawdzenie połączenia", "Sprawdź status galaktyki."],
        ["Lista galaktyk", "Pokaż listę galaktyk i które mają prawo zapisu."],
        ["Przełączenie galaktyki", "Przełącz na galaktykę Galaktyka_Dev."],
        ["Przegląd szablonów", "Pokaż szablony zaczynające się od $t_."],
        ["Przegląd instancji", "Pokaż instancje Mixer%."],
        ["Adresy instancji", "Pokaż InputSource instancji Mixer_01."],
        ["Pełne przetworzenie", "Przetwórz załączony plik SCL w trybie Auto, PLC_01, DB_Mixer_01..03."],
        ["Tylko plan", "Pokaż plan dla tej specyfikacji w Galaktyka_Test, bez zapisu."],
        ["Zapis (w wątku)", "Tak, zapisz szablon i instancje w Galaktyka_Test."],
        ["Porównanie z CSV", "Wyeksportuj szablon $t_UDT_Mixer_Advanced do CSV i porównaj z generatorem."],
        ["Tylko pliki", "Przetwórz plik SCL w trybie Manual (same pliki CSV)."],
    ], [48 * mm, 122 * mm]))

    # ---- 6. Zmiana galaktyki
    s.append(H1("6. Zmiana galaktyki"))
    s += bullets([
        "Poproś Claude: „Przełącz na galaktykę &lt;nazwa galaktyki&gt;”. Przełączenie trwa kilka sekund i nic nie zapisuje.",
        "Można przełączyć się tylko na galaktyki z pola <b>Dozwolone galaktyki</b>.",
        "Zapis jest możliwy tylko w galaktykach z pola <b>Galaktyki z prawem zapisu</b>. W pozostałych działa odczyt, "
        "plan i eksport.",
        "Przy każdym zapisie Claude podaje nazwę galaktyki, którą potwierdziłeś. Jeśli aktywna jest inna – wtyczka "
        "odmawia i nic nie zapisuje.",
        "Jeden proces wtyczki obsługuje <b>wszystkie wątki</b> połączone z tym komputerem. Galaktyka przełączona "
        "w jednym wątku jest aktywna także w innych – dlatego przed zapisem Claude zawsze sprawdza aktywną galaktykę.",
        "Stałą zmianę list galaktyk robisz w ustawieniach wtyczki. Nowe listy zaczną działać dopiero po restarcie "
        "komputera albo ręcznym zamknięciu procesów GalaxyMcp.exe (rozdział 3).",
    ])

    # ---- 7. Bezpieczeństwo
    s.append(KeepTogether([H1("7. Zasady bezpieczeństwa"), box([*bullets([
        "Pierwsze zapisy rób <b>na galaktyce testowej</b> i miej jej kopię zapasową (.cab).",
        "Nie dopisuj galaktyk produkcyjnych do listy zapisu bez uzgodnienia.",
        "Czytaj plan przed zgodą – zwłaszcza nazwę galaktyki i liczbę obiektów.",
        "Zgoda dotyczy jednej, nazwanej galaktyki. Nowa galaktyka = nowa zgoda.",
        "Deploy tylko na osobne, wyraźne polecenie i przy włączonym przełączniku „Zezwól na deploy”.",
        "Nie wpisuj haseł w rozmowie projektu ani w wątku. Hasło galaktyki – tylko w polu poufnym wtyczki.",
        "Wtyczka nigdy nie usuwa obiektów ani atrybutów. Usuwanie rób ręcznie w IDE.",
        "Wtyczka nie tworzy zmiennych tylko do zapisu (Write). Każda zmienna, którą zakłada, ma odczyt ze "
        "sterownika – operator zawsze widzi stan, na który wpływa.",
    ])], "ok", "Dobre praktyki")]))

    # ---- 8. Problemy
    s.append(H1("8. Rozwiązywanie problemów"))
    s.append(box("Zgłaszając problem, dołącz: wynik „Sprawdź status galaktyki”, treść błędu z wątku i końcówkę pliku "
                 f"{code('GalaxyMcp.log')} z folderu rozszerzenia.", "info"))
    s.append(table([
        ["Objaw", "Przyczyna", "Co zrobić"],
        ["Dwuklik na .mcpb nic nie robi", "Skojarzenie pliku", "Ustawienia → Extensions → Advanced settings → Install Extension…"],
        ["Komunikat o blokadzie przez organizację", "Administrator ogranicza własne rozszerzenia",
         "Poproś administratora konta o dopuszczenie wtyczki"],
        ["Claude nie widzi narzędzi galaktyki", "Wątek nie jest połączony z Twoim komputerem, Claude Desktop jest "
         "zamknięty lub komputer uśpiony, wtyczka wyłączona albo wątek założony przed instalacją",
         "Uruchom Claude Desktop i sprawdź Enabled; w wątku poproś „Połącz się z moim komputerem” i zatwierdź kartę; "
         "jeśli nie pomoże – poproś w rozmowie projektu o nowy wątek"],
        ["Brak Projects w zakładce Code", "Plan bez projektów (np. Team/Enterprise) albo beta jeszcze nie "
         "dotarła na konto", "Sprawdź pod More; zaktualizuj Claude Desktop; w razie potrzeby pracuj w trybie Manual "
         "u osoby z dostępem"],
        ["Wtyczka znika bez komunikatu", "Oprogramowanie ochronne zablokowało GalaxyMcp.exe",
         "Poproś dział IT o zgodę na uruchomienie pliku"],
        ["Status pokazuje stare ustawienia mimo przełączenia Enabled",
         "Stary proces GalaxyMcp.exe nadal działa – samo przełączenie Enabled go nie zamyka",
         f"{RESTART_SHORT[0].upper()}{RESTART_SHORT[1:]} (rozdział 3)"],
        ["GalaxyMcp.exe działa w tle po wyłączeniu wtyczki", "Proces nie zakończył się sam",
         "Menedżer zadań → Szczegóły → zakończ każdy GalaxyMcp.exe albo zrestartuj komputer"],
        ["„Nie wybrano galaktyki”", "Puste pole „Galaktyka na start”", "Wpisz galaktykę w ustawieniach albo poproś o przełączenie"],
        ["„Zapis … zablokowany”", "Tylko odczyt lub galaktyka spoza listy zapisu",
         "Popraw ustawienia i uruchom wtyczkę ponownie (rozdział 3) – decyzja użytkownika"],
        ["„Galaktyka … nie jest na liście GALAXY_ALLOWED”", "Galaktyka spoza listy dozwolonych",
         "Dopisz ją w ustawieniach i uruchom wtyczkę ponownie (rozdział 3)"],
        ["„podano galaktykę X, a aktywna jest Y”", "Zgoda dotyczyła innej galaktyki", "Przełącz galaktykę albo potwierdź właściwą"],
        ["Błąd CheckOut / obiekt pobrany", "Obiekt otwarty w IDE", "Zamknij edytor obiektu w IDE i powtórz zapis"],
        ["„istnieje, ale pochodzi z …”", "Instancja o tej nazwie ma inny szablon", "Zmień nazwę obiektu lub usuń go ręcznie w IDE"],
        ["Błąd przy tworzeniu obiektu lub atrybutu o długiej nazwie", "Galaktyka nie przyjęła nazwy dłuższej niż 32 znaki",
         "Zgłoś to osobie utrzymującej projekt; do tego czasu skróć nazwę w programie sterownika"],
        ["„wartość początkowa … nie pasuje do typu …”", "Initial value niezgodna z typem (np. tekst w Integer)",
         "Popraw wartość (Dodatek B) – nic nie zostało zapisane"],
        ["„io musi być Input albo InputOutput”", "Zmienne tylko do zapisu (Write) – celowo wyłączone w trybie Auto "
         "(Dodatek B)", "Przetwórz ten plik w trybie Manual (pliki CSV)"],
        ["„W GRAccess brak wartości MxDataType…”", "Twoja wersja GRAccess nie zna tego typu",
         "Zgłoś to osobie utrzymującej projekt (z wersją AVEVA System Platform)"],
        ["„Nie można załadować GRAccess”", "Brak IDE lub nietypowa ścieżka", "Zainstaluj IDE albo podaj ścieżkę DLL w ustawieniach"],
        ["Serwer uruchamia się podwójnie", "Pozostał ręczny wpis \"galaxy\"", "Zamknij Claude Desktop (Quit) i usuń wpis z claude_desktop_config.json"],
    ], [50 * mm, 52 * mm, 68 * mm]))

    # ---- Dodatki
    s.append(H1("Dodatek A. Narzędzia wtyczki"))
    s.append(table([
        ["Narzędzie", "Co robi", "Zapis?"],
        [code("galaxy_status"), "Wersja, aktywna galaktyka, prawo zapisu, listy dozwolonych, test połączenia", "nie"],
        [code("list_galaxies"), "Galaktyki na węźle: aktywna / zapis / tylko odczyt / niedozwolona", "nie"],
        [code("select_galaxy"), "Przełącza aktywną galaktykę (tylko z listy dozwolonych)", "nie"],
        [code("list_objects"), "Szablony lub instancje pasujące do wzorca (% = dowolny ciąg)", "nie"],
        [code("get_object"), "Właściwości i atrybuty obiektu (np. filtr InputSource)", "nie"],
        [code("export_csv"), "Eksport szablonu lub instancji do CSV", "nie"],
        [code("apply_spec"), "Plan (domyślnie) albo zapis specyfikacji: szablon, atrybuty, instancje "
         "(także ich własne atrybuty), adresy", "tylko po zgodzie"],
        [code("import_csv"), "Import plików CSV z trybu Manual (niesprawdzone)", "tak"],
        [code("deploy"), "Wdrożenie instancji (wymaga włączenia w ustawieniach; niesprawdzone)", "tak"],
    ], [34 * mm, 106 * mm, 30 * mm]))

    s.append(H1("Dodatek B. Typy danych atrybutów"))
    s.append(P("Wtyczka obsługuje wszystkie typy z listy <b>Data type</b> w oknie atrybutu w IDE. Typ wybiera Claude "
               "na podstawie typu zmiennej w sterowniku – nie musisz go podawać, chyba że dodajesz atrybut ręcznie."))
    s.append(table([
        ["Typ w IDE", "Zmienne ze sterownika (TIA)", "Wartość początkowa – przykład"],
        ["Boolean", "Bool", "false, true, 0, 1"],
        ["Integer", "SInt, Int, DInt, USInt, UInt, UDInt, Byte, Word, DWord; LInt, LWord, ULInt (tylko 32 bity – "
         "sprawdź zakres); typy czasu do zapisu jako liczba", "0"],
        ["Float", "Real", "0.0 (kropka albo przecinek)"],
        ["Double", "LReal", "0.0"],
        ["String", "String, WString, Char, WChar", "dowolny tekst"],
        ["Time", "LTime, S5Time, Time_Of_Day, Date, LDT, Date_And_Time, DTL", "2026-09-24 12:00:00"],
        ["ElapsedTime", "Time", "00:00:05.0000000"],
        ["InternationalizedString", "brak odpowiednika – tylko atrybut dodany ręcznie", "dowolny tekst"],
        ["BigString", "brak odpowiednika – tylko atrybut dodany ręcznie", "dowolny tekst"],
    ], [42 * mm, 82 * mm, 46 * mm]))
    s.append(Spacer(1, 6))
    s.append(box(bullets([
        "Kierunek wymiany z PLC: <b>Read</b> albo <b>Read/Write</b>. Write jest wyłączony w trybie Auto ze względów "
        "bezpieczeństwa – zapisuje do sterownika „na ślepo”, bez podglądu stanu. Takie zmienne zakładaj świadomie "
        "w trybie Manual.",
        "Liczby (Boolean, Integer, Float, Double) wtyczka sprawdza przed zapisem – zła wartość zatrzymuje cały zapis. "
        "Teksty i czas przekazuje do galaktyki bez sprawdzania; błąd pokaże się jako ostrzeżenie w raporcie.",
    ]), "info", "Warto wiedzieć"))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--icon")
    ap.add_argument("--out", default="GalaxyMcp_Instrukcja_uzytkownika.pdf")
    a = ap.parse_args()
    doc = Doc(a.out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm,
              bottomMargin=20 * mm, title="Wtyczka GalaxyMCP – instrukcja użytkownika",
              author=f"{AUTHOR} {AUTHOR_NOTE}", subject="Wtyczka GalaxyMCP")
    doc.multiBuild(build(load_icon(a.icon)), onFirstPage=on_page, onLaterPages=on_page)
    print("Zapisano:", a.out)


if __name__ == "__main__":
    main()
