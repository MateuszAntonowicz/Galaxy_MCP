# UDT->CSV: TIA Portal → AVEVA System Platform 2026

Zestaw narzędzi, który zamienia typy danych (UDT) i bloki danych (DB) z Siemens TIA Portal na szablony i instancje **AVEVA System Platform 2026** z adresacją I/O dla drivera OI SIDirect. Skrypt `scl_to_aveva.py` czyta pliki `.udt/.scl/.db` i tworzy specyfikację `Spec_<UDT>.json`. Z niej powstają pliki CSV do importu w ArchestrA IDE (tryb Manual) albo obiekty zapisywane wprost w galaktyce przez lokalny serwer MCP **GalaxyMcp** (C#/.NET, GRAccess), czyli rozszerzenie Claude Desktop (tryb Auto). Zapis zawsze poprzedza plan (dry run). Serwer działa tylko w dozwolonych galaktykach i nigdy nic nie usuwa. Projekt powstał jako projekt Claude: Claude prowadzi wywiad, uruchamia generator i wywołuje narzędzia GalaxyMcp.

## Struktura

```
README.md
Pliki_projektu/            ← to, co dodajesz do Library projektu Claude (bez zmiany układu)
  Tools/                   generator, reguły, pełna instrukcja dla Claude, źródła serwera GalaxyMcp
    scl_to_aveva.py        TIA (.udt/.scl/.db) → Spec_<UDT>.json i pliki CSV
    Metoda_Generowania.md  reguły wypełniania kolumn i format specyfikacji
    Instrukcja_projektu.md pełna instrukcja projektu dla Claude
    GalaxyMcp*             serwer MCP (C#, build, pakowanie .mcpb, README, manifest, ikona, skrypt PDF)
  ITERACJE/                notatki: adresowanie OI SIDirect, historia wdrożenia GalaxyMcp
  t_SampleUDT.csv          wzorzec eksportu szablonu z ArchestrA IDE
  OISIDIR_tekst.txt        tekst dokumentacji drivera OI SIDirect (zamiennik OISIDIR.pdf)
Konfiguracja_projektu/     założenie / odtworzenie projektu w Claude
  Project_instructions_ustawienia.txt   tekst do pola Project instructions (limit 16 000 znaków)
  prompt.txt               polecenie odtworzenia projektu z kopii
  Context.zip              Pliki_projektu spakowane jako kopia zapasowa (używa go prompt.txt)
Dokumentacja/              instrukcje PDF: projekt UDT->CSV, instrukcja użytkownika wtyczki, „Jak to działa”
  zrodla/                  skrypty generujące / poprawiające PDF
GalaxyMcp/                 gotowa wtyczka GalaxyMcp.mcpb
  GalaxyMcp_0.2.3/         źródła i pliki wersji 0.2.3 (bez GalaxyMcp.exe, który jest w Releases)
```

Instrukcja zakładania projektu krok po kroku: `Dokumentacja/Instrukcja_UDT_CSV.pdf`, rozdział 3.
Opcjonalne pliki użytkownika (`Permissions.csv`, `OISIDIR.pdf`) dodaje się do Library obok `t_SampleUDT.csv`.

## Pliki binarne

Skompilowany `GalaxyMcp.exe` nie jest trzymany w repozytorium. Pobierz go z zakładki **Releases** (wydanie `v0.2.3`) razem z `GalaxyMcp.mcpb`, albo zbuduj sam skryptem `GalaxyMcp/GalaxyMcp_0.2.3/build.bat`.

## Wymagania

- Python 3 (generator; reportlab tylko do PDF),
- tryb Auto: Windows, AVEVA System Platform 2026 z ArchestrA IDE (GRAccess), Claude Desktop z rozszerzeniem GalaxyMcp 0.2.3.

Autor: Mateusz Antonowicz, z pomocą Claude AI.
