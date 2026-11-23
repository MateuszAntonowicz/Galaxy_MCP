# UDT->CSV: TIA Portal → AVEVA System Platform 2026

Projekt zamienia typy danych (UDT) i bloki danych (DB) z Siemens TIA Portal na szablony i instancje **AVEVA System Platform 2026** z adresacją I/O dla drivera OI SIDirect. Całą pracę wykonuje Claude w projekcie Claude: prowadzi wywiad, uruchamia generator `scl_to_aveva.py` i oddaje wynik w jednym z dwóch trybów:

- **Manual** – pliki CSV do samodzielnego importu w ArchestrA IDE,
- **Auto** – obiekty zapisane wprost w galaktyce przez wtyczkę **GalaxyMCP** (rozszerzenie Claude Desktop, GRAccess). Zapis zawsze poprzedza plan, wtyczka działa tylko w dozwolonych galaktykach i niczego nie usuwa.

Projekt i wtyczka GalaxyMCP działają na **AVEVA System Platform 2026** (sprawdzone na galaktykach testowych).

---

## Jak zacząć

### Krok 1. Którą instrukcję czytać

| Co chcesz zrobić | Instrukcja | Rozdziały |
|---|---|---|
| Założyć projekt w Claude i z niego korzystać (oba tryby) | [`Dokumentacja/Instrukcja_UDT_CSV.pdf`](Dokumentacja/Instrukcja_UDT_CSV.pdf) – **zacznij od niej** | 2 wymagania, 3 założenie projektu, 5 praca krok po kroku, 6 tryb Manual, 7 tryb Auto, 9 problemy |
| Zainstalować i ustawić wtyczkę GalaxyMCP (tylko tryb Auto) | [`Dokumentacja/GalaxyMcp_Instrukcja_uzytkownika.pdf`](Dokumentacja/GalaxyMcp_Instrukcja_uzytkownika.pdf) | 1 wymagania, 2 instalacja, 3 ustawienia, 4 pierwszy test, 8 problemy |
| Zrozumieć, jak działa wtyczka i gdzie są zabezpieczenia | [`Dokumentacja/GalaxyMcp_Jak_to_dziala.pdf`](Dokumentacja/GalaxyMcp_Jak_to_dziala.pdf) | całość (nie jest potrzebna do pracy) |
| Zbudować wtyczkę samodzielnie ze źródeł | [`GalaxyMcp/GalaxyMcp_0.2.7/README.md`](GalaxyMcp/GalaxyMcp_0.2.7/README.md) | 1 budowanie, 4 instalacja `.mcpb` |

### Krok 2. Pobierz pliki

Repozytorium jest prywatne – musisz być zalogowany na GitHubie na konto z dostępem.

**A. Pliki projektu i instrukcje (potrzebne zawsze)**

1. Na stronie repozytorium kliknij zielony przycisk **Code** → **Download ZIP** i rozpakuj archiwum na dysku.
   (Albo: `git clone https://github.com/MateuszAntonowicz/Galaxy_MCP.git`.)
2. Z rozpakowanego folderu będą Ci potrzebne:

| Plik | Do czego |
|---|---|
| `Dokumentacja/*.pdf` | instrukcje z kroku 1 |
| `Konfiguracja_projektu/Context.zip` | pliki projektu do dodania w Library (zawiera to samo co folder `Pliki_projektu/`) |
| `Konfiguracja_projektu/Project_instructions_ustawienia.txt` | instrukcja projektu do wklejenia w całości w Project settings → Memory → Project instructions (ta sama treść co `Pliki_projektu/Tools/Instrukcja_projektu.md`) |
| `Konfiguracja_projektu/prompt.txt` | pierwszy prompt do wklejenia w rozmowie projektu po jego założeniu – Claude rozpakuje `Context.zip` i sprawdzi projekt |

**B. Wtyczka GalaxyMCP (tylko tryb Auto, na komputerze z AVEVA System Platform 2026)**

1. Wejdź w zakładkę **Releases** (prawa kolumna strony repozytorium) i otwórz najnowsze wydanie (**GalaxyMCP 0.2.7**, oznaczone *Latest*).
   Bezpośredni link: <https://github.com/MateuszAntonowicz/Galaxy_MCP/releases/latest>
2. W sekcji **Assets** kliknij **`GalaxyMcp.mcpb`** i zapisz plik. To cała wtyczka – instalujesz ją w Claude Desktop według `GalaxyMcp_Instrukcja_uzytkownika.pdf`, rozdział 2.
3. `GalaxyMcp.exe` i `GalaxyMcp.exe.config` z tego samego wydania są potrzebne tylko do awaryjnego wpisu ręcznego (`GalaxyMcp/GalaxyMcp_0.2.7/README.md`, rozdział 3). Przy instalacji z `.mcpb` ich nie pobierasz.

> `GalaxyMcp.exe` i `GalaxyMcp.mcpb` nie są przechowywane w samym repozytorium – są tylko w Releases. Nie szukaj ich w Download ZIP.

### Krok 3. Załóż projekt i pracuj

1. Załóż projekt w Claude – `Instrukcja_UDT_CSV.pdf`, rozdział 3: 3.1 projekt, 3.2 `Context.zip` do Library, 3.3 instrukcja projektu, 3.4 modele (effort wątków Medium/High), 3.5 wtyczka GalaxyMCP (tylko tryb Auto), 3.6 pierwszy prompt z `prompt.txt`.
2. Tylko tryb Auto: szczegóły ustawień wtyczki i pierwszy test – `GalaxyMcp_Instrukcja_uzytkownika.pdf`, rozdziały 2–4.
3. Przygotuj pliki `.udt`/`.scl` i `.db` z TIA Portal i wyślij zlecenie w rozmowie projektu – `Instrukcja_UDT_CSV.pdf`, rozdziały 4 i 5.

### Aktualizacja do nowej wersji

1. Pobierz ponownie repozytorium (Download ZIP albo `git pull`), w Library projektu podmień `Context.zip` na nowy (przy istniejącej nazwie wybierz **Replace**) i wyślij w rozmowie projektu ponownie treść `prompt.txt`.
2. W Project settings → Memory → Project instructions zastąp tekst całą treścią nowego `Project_instructions_ustawienia.txt` i kliknij **Save changes**.
3. Jeśli w Releases jest nowsza wersja wtyczki, pobierz nowy `GalaxyMcp.mcpb` i zainstaluj go w miejsce zainstalowanego (Settings → Desktop app → Extensions (Manage) → Advanced settings → Install Extension…). Wersję sprawdzisz poleceniem „pokaż status galaktyki” – pozycja „Wersja”.

---

## Struktura repozytorium

```
README.md
Pliki_projektu/            ← pliki projektu Claude (to samo co Context.zip)
  Wzorce_SCL/              wzorcowe pliki .udt/.db z opisem składni i źródłami
  Tools/                   generator, reguły, pełna instrukcja dla Claude, źródła wtyczki GalaxyMCP
    scl_to_aveva.py        TIA (.udt/.scl/.db) → Spec_<UDT>.json i pliki CSV
    Metoda_Generowania.md  reguły wypełniania kolumn i format specyfikacji
    Instrukcja_projektu.md pełna instrukcja projektu dla Claude
    GalaxyMcp*             wtyczka: C#, build, pakowanie .mcpb, README, manifest, ikona, skrypt PDF
  ITERACJE/                notatki: adresowanie OI SIDirect, historia wdrożenia GalaxyMCP
  t_SampleUDT.csv          wzorzec eksportu szablonu z ArchestrA IDE
  OISIDIR_tekst.txt        tekst dokumentacji drivera OI SIDirect (zamiennik OISIDIR.pdf)
Konfiguracja_projektu/     założenie / odtworzenie projektu w Claude
  Context.zip              Pliki_projektu spakowane do dodania w Library
  Project_instructions_ustawienia.txt   instrukcja projektu do wklejenia w pole Project instructions
  prompt.txt               polecenie odtworzenia projektu z kopii
Dokumentacja/              trzy instrukcje PDF (patrz „Jak zacząć”)
  zrodla/                  skrypty generujące / poprawiające PDF
GalaxyMcp/                 źródła kolejnych wersji wtyczki
  GalaxyMcp_0.2.7/         aktualna wersja – z niej powstaje wydanie
  GalaxyMcp_0.2.3/ … 0.2.6/ archiwum źródeł wydań v0.2.3 – v0.2.6
.github/workflows/         automatyczne budowanie wtyczki i tworzenie wydania
```

Opcjonalne pliki użytkownika (`Permissions.csv`, `OISIDIR.pdf`) nie są w repozytorium – dodaje się je do Library projektu obok `t_SampleUDT.csv`.

## Wymagania

- Projekt Claude: Claude Desktop albo claude.ai/code, plan Pro, Max lub Ultra (szczegóły: `Instrukcja_UDT_CSV.pdf`, rozdział 2).
- Tryb Auto: Windows 10/11, **AVEVA System Platform 2026** z ArchestrA IDE (GRAccess), .NET Framework 4.x, Claude Desktop z wtyczką GalaxyMCP 0.2.7 uruchomiony w czasie pracy.
- Budowanie PDF lub uruchamianie generatora poza Claude: Python 3 (reportlab tylko do PDF).

## Dla utrzymujących: wydania

Wydania tworzy workflow **Wydanie GalaxyMCP** (`.github/workflows/wydanie.yml`). Gdy na `main` trafi nowy folder `GalaxyMcp/GalaxyMcp_<wersja>/` (z `version` w `manifest.json` zgodnym z `Version` w `GalaxyMcp.cs`), workflow buduje `GalaxyMcp.exe` na Windows tym samym kompilatorem co `build.bat`, pakuje `GalaxyMcp.mcpb` i tworzy wydanie `v<wersja>`. Istniejących wydań nie nadpisuje; można go też uruchomić ręcznie w zakładce Actions. Nazwy plików (`GalaxyMcp.exe`, `GalaxyMcp.mcpb`, `GalaxyMcp.log`) pozostają bez zmian, żeby nie psuć istniejących instalacji.

Autor: Mateusz Antonowicz, z pomocą Claude AI.
