# Wzorce źródeł SCL: typy UDT (.udt) i bloki danych (.db)

Wzorcowe pliki tekstowe, które można napisać ręcznie (albo wygenerować) bez otwierania TIA Portal,
a potem zaimportować do projektu jako *External source files*. Są też poprawnym wejściem dla
generatora `Tools/scl_to_aveva.py` (UDT → CSV dla AVEVA), co sprawdza test `tests/test_generator.py`
(klasa `Wzorce`).

| Plik | Co pokazuje |
|---|---|
| `UDT_Wzorzec.udt` | dwa typy PLC: prosty `UDT_Wz_Alarm` i `UDT_Wz_Naped` z wartościami startowymi, komentarzami, atrybutami członków, tablicą, zagnieżdżonym UDT, tablicą UDT i strukturą anonimową |
| `DB_Wzorzec_Globalny.db` | globalny DB z sekcją `VAR`, instancjami UDT (pojedynczo, w tablicy, w strukturze) i wartościami startowymi w `BEGIN` |
| `DB_Wzorzec_Typu_UDT.db` | DB utworzony wprost z typu UDT (bez `VAR`, sama nazwa typu) |
| `SEW_ECDriveS/` | prawdziwe pliki .udt/.db z przykładowego projektu SEW (opis w `SEW_ECDriveS/README.md`) |

Pliki `*_Wzorzec*` napisano samodzielnie na podstawie źródeł z sekcji [Źródła](#źródła-ocena-z-2026-11-23); nie są kopią cudzych przykładów.

## Budowa typu UDT

```
TYPE "Nazwa_Typu"             // nazwa w cudzysłowie
TITLE = tekst tytułu          // opcjonalnie
AUTHOR : MA                   // opcjonalnie, maks. 8 znaków, bez spacji
FAMILY : Wzorce               // opcjonalnie, maks. 8 znaków
VERSION : 0.1                 // format x.y
//komentarz bloku             // opcjonalnie, linie zaczynające się od //
   STRUCT
      Nazwa : Typ;                        // komentarz członka
      Nazwa : Typ := wartość_startowa;    // wartość domyślna
      Nazwa { Atrybut := 'True'} : Typ;   // atrybut członka
   END_STRUCT;
END_TYPE
```

## Budowa bloku danych

```
DATA_BLOCK "Nazwa_DB"
TITLE = tekst tytułu
{ S7_Optimized_Access := 'TRUE' }   // dostęp zoptymalizowany ('FALSE' = klasyczny, adresy bajtowe)
AUTHOR : MA
FAMILY : Wzorce
VERSION : 0.1
NON_RETAIN                          // bez tej linii DB jest remanentny (RETAIN)
   VAR
      Pompa_01 : "UDT_Wz_Naped";
      Wentylatory : Array[1..3] of "UDT_Wz_Naped";
   END_VAR
BEGIN                               // wartości startowe, nadpisują domyślne z UDT
   Pompa_01.Nazwa := 'Pompa 01';
   Wentylatory[1].Cfg_Czas_Rozbiegu := T#10S;
END_DATA_BLOCK
```

DB z dostępem klasycznym (`S7_Optimized_Access := 'FALSE'`) deklaruje członków w
`STRUCT ... END_STRUCT;` zamiast `VAR ... END_VAR` (przykład: `SEW_ECDriveS/IO_data.db`).

DB typu UDT: zamiast `VAR ... END_VAR` wpisuje się samą nazwę typu w cudzysłowie (`"UDT_Wz_Naped"`),
a w `BEGIN` ścieżki zaczynają się od członka typu (`Nazwa := 'Pompa 03';`). Numeru DB nie podajemy,
TIA nada go sam.

## Najczęstsze elementy

- **Typy proste**: `Bool, Byte, Word, DWord, LWord, SInt, Int, DInt, LInt, USInt, UInt, UDInt, ULInt,
  Real, LReal, Char, WChar, String[n], WString, Time, LTime, Date, Time_Of_Day, DTL`.
- **Literały**: `TRUE`, `1450.0`, `'tekst'`, `T#5S`, `T#1M_30S`, `D#2026-01-01`, `TOD#08:00:00`,
  `16#FF` (hex), `2#1010` (bin).
- **Tablice**: `Array[1..3] of Real`, wielowymiarowe `Array[1..2, 0..1] of Bool`, granice mogą być ujemne
  (`Array[-1..1] of Int`). W `BEGIN` element tablicy: `Temp[2] := 20.0;`.
- **Struktura anonimowa**: `Nazwa : Struct ... END_STRUCT;` wewnątrz `STRUCT` lub `VAR`.
- **Atrybuty członka** (w klamrach przed dwukropkiem, kilka rozdziela się średnikiem):
  `ExternalAccessible`, `ExternalVisible`, `ExternalWritable` (dostęp z HMI/OPC UA),
  `S7_SetPoint` (wartość zadana), `S7_HMI_Visible`. Wartości w apostrofach: `'True'` / `'False'`.
- **Nazwy**: litery, cyfry i `_`, nie zaczynają się od cyfry. Nazwy ze spacją, myślnikiem lub cyfrą na
  początku muszą być w cudzysłowie przy deklaracji i przy każdym użyciu (`"1SM01_RPM" : Real;`).
  Bezpieczniej używać prefiksu literowego (`rSM01_RPM`). Polskie litery w nazwach są dozwolone w TIA,
  ale generator UDT → CSV zamienia je na `_`, więc lepiej ich unikać.

## Import do TIA Portal

1. Najpierw plik z typami: *External source files* > *Add new external source file* > wybrać `.udt`,
   potem prawy klik > *Generate blocks from source*. Kolejność typów w pliku: najpierw podrzędne
   (`UDT_Wz_Alarm`), potem te, które ich używają.
2. Skompilować PLC (typy muszą istnieć, inaczej import DB zgłosi nieznany typ).
3. To samo dla plików `.db`. DB pojawi się w *Program blocks*.
4. W drugą stronę: prawy klik na bloku lub typie > *Generate source from blocks* daje plik w tym
   samym formacie. To najpewniejszy sposób, żeby sprawdzić składnię dla danej wersji TIA.

## Na co uważać

- Plik zapisywać jako UTF-8 i kończyć pustą linią. Według artykułu z industrialmonitordirect.com
  BOM albo rozbity na kilka linii blok `{ ... }` potrafią dać błąd „DATA_BLOCK is not defined”, a numer
  linii w błędzie wskazuje linię powyżej faktycznej usterki (nie sprawdzono w TIA).
- `S7_Optimized_Access` ustawia się dla całego DB. Typ UDT nie ma tego atrybutu, przejmuje dostęp od DB.
- Wartości startowe z `BEGIN` trafiają do DB dopiero przy pełnym ładowaniu (lub reinicjalizacji),
  zwykłe ładowanie zmian ich nie nadpisuje w sterowniku.
- Generator UDT → CSV pomija sekcję `BEGIN` i zmienne proste DB (np. `Liczba_Napedow : Int`); instancją
  obiektu w AVEVA jest tylko członek typu UDT.

## Źródła (ocena z 2026-11-23)

1. **Artykuł** [S7-1500 DB creation from SCL external source files in TIA V15.1](https://industrialmonitordirect.com/blogs/knowledgebase/s7-1500-db-creation-from-scl-external-source-files-in-tia-v151)
   (industrialmonitordirect.com). Najbardziej przydatny: szkielet `DATA_BLOCK` z `S7_Optimized_Access`,
   `VERSION`, `NON_RETAIN`, `VAR`, `BEGIN`, członkowie typu UDT i tablice UDT, kroki importu, typowe
   błędy (cudzysłowy przy nazwach z cyfrą na początku, „DATA_BLOCK is not defined”). Nie pokazuje
   `TYPE ... END_TYPE`. To blog sprzedawcy sprzętu bez odnośników do dokumentacji Siemens, więc część
   uwag (limity firmware, zachowanie starszych wersji, nazwy metod TIA Openness) jest niepotwierdzona.
   Wskazuje też dokumentację narzędzia Siemens AX `tia2st` (nie sprawdzone):
   https://docs.industrial-operations-x.siemens.cloud/r/en-us/ax/tia2st/1.0.7/command-import-scl/getting-started
2. **Siemens** *STEP 7 (TIA Portal) Global library "Sample Library for Instructions"*, Installation Manual
   10/2018, A5E46487685-AA, ID 109476781 (V15.1, DOKU v1.04):
   https://support.industry.siemens.com/cs/attachments/109476781/109476781_Sample_Library_for_Instructions-V15_1_DOKU_v1_04_en.pdf
   Nieprzydatny dla składni: opisuje tylko instalację i użycie biblioteki globalnej (otwieranie,
   przeciąganie przykładów do projektu, wymagania firmware, wersje). Sama biblioteka jest binarna,
   źródła tekstowe trzeba by z niej wygenerować w TIA (*Generate source from blocks*).
3. **SEW-EURODRIVE ECDriveS** (podręcznik, wyd. 01/2019):
   - [Generating UDTs](https://download.sew-eurodrive.com/download/html/25938266/en-EN/25465710731.html):
     prawy klik na zaimportowanym źródle > *Generate blocks from source*, typy pojawiają się w
     *PLC data types*. Potwierdza kroki importu, bez składni.
   - [Importing source files](https://download.sew-eurodrive.com/download/html/25938266/en-EN/25461686283.html):
     *External source files* > *Add new external file*; SEW dostarcza typy jako pliki `.scl`
     (wiele `TYPE` w jednym pliku), co pokazuje, że rozszerzenie `.scl` też działa dla typów.
   - Przykładowy projekt *ECDriveS_Positioning* (sew-eurodrive.com > Data & documents > Software,
     `SEW_ECDriveS_Positioning_V1.0.zip`): binarny projekt TIA V14/V15 bez plików `.udt`/`.db` na
     wierzchu, ale z dołączonymi źródłami zewnętrznymi zapisanymi wewnątrz `System/PEData.plf`.
     Wyciągnięte pliki .udt i .db (4 pliki) są w `SEW_ECDriveS/`. Najcenniejsze źródło: prawdziwe pliki
     z TIA, m.in. DB z dostępem klasycznym i atrybuty członków.
4. **[Speedstuff/TiaExportBlocks](https://github.com/Speedstuff/TiaExportBlocks)** (GitHub, fork
   cezar1/TiaExportBlocks): narzędzie C# na TIA Openness (testowane z V15.1), które hurtowo eksportuje
   z projektu funkcje SCL do `.scl`, DB do `.db`, UDT do `.udt` i tabele zmiennych do `.xml`.
   Przydatne do zebrania prawdziwych źródeł z istniejących projektów jako wejścia dla generatora
   UDT → CSV; wymaga zainstalowanego TIA i grupy Windows „Siemens TIA Openness”.
5. Pomoc TIA Portal (F1), hasło „External source files”, to źródło rozstrzygające w razie wątpliwości.
