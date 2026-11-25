# Metoda generowania – TIA Portal SCL → AVEVA System Platform 2026

Narzędzie: `Tools/scl_to_aveva.py` (samodzielne, bez zależności).

```
.udt / .scl (TYPE)  ─┐
                     ├─scl_to_aveva.py─► Spec_<UDT>.json ─► $t_<UDT>.csv + Instances_<UDT>.csv   (Manual)
.db (DATA_BLOCK)    ─┘                                   └─► serwer GalaxyMCP → galaktyka       (Auto)
```

Pliki wejściowe:

- `*.udt` / `*.scl` – bloki `TYPE "<UDT>" ... STRUCT ... END_TYPE`; **może być ich wiele w jednym pliku**. Każdy typ = jeden szablon.
- `*.db` – bloki `DATA_BLOCK "<DB>" ... VAR ... END_VAR`; każdy element typu UDT = jedna instancja tego szablonu.
  Jeden plik może mieć wiele bloków danych (np. `Mieszalnik_1`, `Mieszalnik_2`). Obsługiwane układy DB:

| Układ w DB | Nazwa instancji | Adres (item) |
| :--- | :--- | :--- |
| `Pompa_01 : "UDT_X"` (poziom główny) | `<DB>_Pompa_01` | `<DB>.Pompa_01.<ścieżka>` |
| `Zawory : Array[1..2] of "UDT_X"` | `<DB>_Zawory_1` | `<DB>.Zawory[1].<ścieżka>` |
| `Sekcja_A : Struct … Pompa : "UDT_X"` (dowolnie głęboko) | `<DB>_Sekcja_A_Pompa` | `<DB>.Sekcja_A.Pompa.<ścieżka>` |
| `Stacje : Array[1..2] of Struct … Mieszadlo : "UDT_X"` | `<DB>_Stacje_1_Mieszadlo` | `<DB>.Stacje[1].Mieszadlo.<ścieżka>` |
| DB typu UDT: `DATA_BLOCK "DB_Zawor_05"` … `"UDT_X"` … `BEGIN` (bez `VAR`) | `DB_Zawor_05` | `DB_Zawor_05.<ścieżka>` |

  - Sekcja `BEGIN … END_DATA_BLOCK` (wartości startowe) jest pomijana.
  - DB typu, którego nie ma w plikach z typami (np. DB instancyjny bloku FB), jest pomijany z ostrzeżeniem.
  - Zmienne proste w DB (także w STRUCT) nie są instancją żadnego szablonu – pomijane z ostrzeżeniem.
- Zamiast `.db` można podać instancje ręcznie (`--instances Obiekt=DB`), wtedy trzeba wskazać jeden typ (`--type`).

```
# typy + instancje z plików TIA (pełny przebieg):
python scl_to_aveva.py udt_praktykanta.udt --db przykladowe_db.db --permissions Permissions.csv \
    --plc S7C_01 --scan-group SG1 --out Output

# jeden typ, instancje podane ręcznie:
python scl_to_aveva.py MA_Mixer.scl --permissions Permissions.csv --plc S7C_01 --scan-group SG1 \
    --type UDT_Mixer_Advanced --instances Mixer_01=DB_Mixer_01 --out Output

# --plc (obiekt DI w galaktyce) jest WYMAGANE, chyba że podano --no-address; bez --scan-group
#   generator tylko ostrzega (adres bez grupy skanowania nie zadziała na driverze).
# reguły ręczne:        --rules Cmd_=InputOutput Status_=Input Reset_=Output
# także typy bez instancji:  --all-types   (domyślnie: tylko typy, które mają instancje)
# bez adresów:          --no-address   (instancje powstają, InputSource/OutputDest puste)
# nazwa szablonu:       --template-prefix ""   (bez przedrostka: $<UDT>; domyślnie "t_" → $t_<UDT>)
# CSV z (poprawionej ręcznie) specyfikacji:  --from-spec Output/Spec_<UDT>.json --out Output
```

Dla każdego wybranego typu powstaje osobny zestaw: `Spec_<UDT>.json`, `<nazwa szablonu>.csv` (`$t_<UDT>.csv`, a przy `--template-prefix ""` `$<UDT>.csv`), `Instances_<UDT>.csv`.
Specyfikacja ma `spec_version` 1 i jeden szablon w pliku, więc tryb Auto wykonuje po jednym `apply_spec` na typ
(serwer bierze nazwę szablonu z `template.name`, więc przedrostek działa w obu trybach).

## Mapowanie typów (bez względu na wielkość liter)

| Siemens | AVEVA | Wartość domyślna |
| :--- | :--- | :--- |
| `Bool` | `MxBoolean` | `false` |
| `Real` | `MxFloat` | `0.0` |
| `LReal` | `MxDouble` | `0.0` |
| `SInt`, `Int`, `DInt`, `USInt`, `UInt`, `UDInt`, `Byte`, `Word`, `DWord` | `MxInteger` | `0` |
| `LInt`, `LWord`, `ULInt` | `MxInteger` (64 bity w 32-bitowym MxInteger – ostrzeżenie o zakresie) | `0` |
| `String`, `String[n]`, `WString`, `Char`, `WChar` | `MxString` | puste |
| `Time` | `MxElapsedTime` (sufiks `T`) | puste |
| `LTime`, `S5Time`, `Time_Of_Day`, `Date` | `MxTime` tylko do odczytu (sufiksy `LT`, `S5T`, `TOD`, `D`) | puste |
| `LDT`, `Date_And_Time` | `MxTime` zapisywalne z sufiksem (`LDT`, `DT`) | puste |
| `DTL`, `LTime_Of_Day` | `MxTime` **bez sufiksu** – driver go nie podaje (DTL to struktura `.YEAR`, `.MONTH`…); ostrzeżenie „sprawdź w Object Viewer” | puste |

- Ta tabela i słownik `TYPES` w `scl_to_aveva.py` to jedyne miejsca mapowania typów – każda zmiana idzie w obu naraz.
- Typy czasowe z sufiksem driver pozwala tylko czytać. Atrybut zapisywalny (`InputOutput` albo `Output`) dostaje ten sam item
  **bez sufiksu** i typ `MxInteger` w jednostce drivera (Time/S5Time/Time_Of_Day: ms, LTime: ns, Date: dni od 1990-01-01).
  `LDT` i `Date_And_Time` są zapisywalne z sufiksem.
- Wartości początkowe (`:= ...`) z deklaracji w UDT, STRUCT i VAR trafiają do `Value` atrybutu szablonu (`default` w specyfikacji):
  Bool `TRUE`/`FALSE`/`1`/`0` → `true`/`false`; liczby całkowite (także `16#FF`, `2#1010`, `DINT#5`, `_` w liczbie) → liczba
  dziesiętna (poza 32 bitami – pominięta z ostrzeżeniem); Real/LReal → liczba z kropką (`1.5E+3` → `1500.0`); tekst w apostrofach →
  tekst bez apostrofów (`''` → `'`, `$$` → `$`); `T#…` → milisekundy (atrybut `MxInteger`) albo `hh:mm:ss.fffffff` (`MxElapsedTime`).
  Bez przenoszenia, z ostrzeżeniem: tablice (`:= [1, 2]`) i literały innych typów (`D#…`, `TOD#…`, `DTL#…`).
- Pomijane bez ostrzeżenia: atrybuty `{ ... }`, komentarze bez deklaracji, sekcja `BEGIN` w DB (wartości startowe instancji).

## Kierunek I/O i `Permissions.csv`
- Trzy kierunki (nazwy jak w IDE w nawiasie):

| `Access_Mode` | W IDE | `#IO.Mode` | `PrimitiveType` | Wiersze `&Extended Attributes` | Kolumna w instancjach |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Input` | Read | `ReadOnly` | `Input` | `InputSource` (puste) | `<Attr>.InputSource` |
| `InputOutput` | Read/Write | `ReadWrite` | `InputOutput` | `DiffOutputDest=false`, `InputSource` (puste), `OutputDest=---` | `<Attr>.InputSource` |
| `Output` | Write | `WriteOnly` | `Output` | `OutputDest` (puste) | `<Attr>.OutputDest` |

- `Output` = SCADA tylko zapisuje do PLC i nie odczytuje wartości z powrotem – nie dla alarmów i stanów.
  Wiersz Output (`WriteOnly`, sam `OutputDest`, bez `#IO.Deadband`) jest zgodny z eksportem z IDE (SP 2026). IDE dopisuje
  jeszcze `OutputEveryScan=false` i `WriteStatus` – generator ich nie potrzebuje.
- Zmiana kierunku atrybutu w szablonie (w IDE) usuwa jego adresy w instancjach – potem wczytaj ponownie `Instances_<UDT>.csv`.
- `MxTime` bez wartości początkowej dostaje od GRAccess czas utworzenia szablonu; przy atrybutach I/O nie ma to znaczenia.
- Tryb Auto: GalaxyMCP pomija atrybuty z `io=Output` (linia „POMINIĘTE atrybuty Write” w planie) i zapisuje resztę; atrybuty Write – w IDE albo tryb Manual.
- `Permissions.csv`: kolumny `Prefix_or_Keyword`, `Access_Mode`, `Description` (opcjonalna, generator jej nie czyta).
  **Nazw kolumn nie wolno zmieniać** – plik bez żadnej poprawnej reguły (np. nagłówek `Prefix_`) przerywa generator komunikatem,
  zamiast po cichu dać same Input.
- Separator: przecinek albo średnik (Excel z polskimi ustawieniami) – wykrywany z pierwszych dwóch linii.
- `Access_Mode` bez względu na wielkość liter i spacje; przyjmowane też nazwy z IDE: `Read`, `Read/Write`, `Write`.
  Nieznana wartość → reguła pominięta z ostrzeżeniem. `--rules` z nieznanym trybem → przerwanie.
- Brak pliku i brak `--rules` → reguły awaryjne `DEFAULT_RULES` (`Cmd_`, `Set_`, `Cfg_`, `Par_` → InputOutput) i ostrzeżenie
  o braku pliku – przekaż je użytkownikowi.
- Category zawsze `MxCategoryWriteable_USC_Lockable`.

## Specyfikacja `Spec_<UDT>.json` (spec_version 1) – format pośredni
- WSZYSTKIE decyzje (typy, wartości domyślne, kierunek I/O, format adresu, nazwa szablonu) zapadają w `build_spec()`.
  Generator CSV i serwer MCP tylko je wykonują – oba tryby dają ten sam wynik.
- `template`: `name` (`$t_<UDT>`; z `--template-prefix ""` → `$<UDT>`), `base` (`$UserDefined`), `toolset` (`Application`), `security_group` (`Default`), `udt`,
  `attributes[]`: `name`, `plc_type`, `type` (Mx…), `default`, `io` (Input/InputOutput/Output), `description`, `plc_path`.
- `instances[]`: `name`, `area`, `security_group`, `plc`, `db`, `input_source{atrybut: adres}` (atrybuty Input i InputOutput,
  adres już złożony) oraz – tylko gdy szablon ma atrybuty Output – `output_dest{atrybut: adres}`.
- `warnings[]`: pominięte elementy SCL, problemy z Permissions.csv, zmiany i kolizje nazw, uwaga o atrybutach Output.
- `output_dest` jest polem opcjonalnym (występuje tylko przy atrybutach Output).
- Zmiana formatu specyfikacji = podbicie `spec_version` w skrypcie i w serwerze (`Spec.Parse`).

## Szablon `<nazwa szablonu>.csv` (domyślnie `$t_<UDT>.csv`)
- Nagłówek i opcje importu skopiowane 1:1 z `t_SampleUDT.csv`. Deklaracja: `$<toolset>\<name>{<security_group>} -> <base>`.
- Nazwa pliku = nazwa szablonu ze specyfikacji + `.csv`, więc `--template-prefix ""` daje `$<UDT>.csv` i deklarację `$Application\$<UDT>{Default} -> $UserDefined`.
- Przedrostek dotyczy tylko nazwy szablonu; nazwy atrybutów, instancji i adresy nie zmieniają się.
- UDA: Value wg tabeli typów (`false` / `0.0` / `0`), Category `MxCategoryWriteable_USC_Lockable`, `#IO=EnabledByMe`, `#IO.Mode` ReadOnly/ReadWrite/WriteOnly.
- Opis z komentarza `//` → Description (+ `MxUnLocked`, `MxSecurityOperate`).
- Bool → `#IO.InvertValue=Disabled,MxUnLocked`. Float/Integer (Input, InputOutput) → `#IO.Deadband=0.0,MxUnLocked,MxSecurityConfigure`;
  dla Output bez deadbandu (dotyczy odczytu).
- Extended wg tabeli w sekcji „Kierunek I/O”. Pominięte: `WriteStatus`, `WriteValue` (wartości runtime).
- Bloki w kolejności: `&User-defined Attributes` → `&Extended Attributes` → puste `&Graphical Content`, `&Wizard Assets`,
  `&Wizard Associations`, `&Wizard Settings`, rozdzielone liniami `#====...`.
- Szablon nie zawiera adresów PLC (`InputSource` / `OutputDest` puste).
- Po imporcie IDE samo wstawia wartości domyślne: MxElapsedTime `00:00:00.0000000`, MxTime = moment utworzenia,
  `InputSource` = `---Auto---`. Eksport szablonu z IDE ma też wiersze `WriteStatus`/`WriteValue` – przy porównaniu z plikiem
  generatora to nie są różnice.

## Adresy (InputSource / OutputDest) – wg dokumentacji drivera OI SIDirect
Szczegóły i cytaty: `ITERACJE/tmp_OI_SIDirect_adresowanie.md` (źródło: `OISIDIR.pdf`).

**Zakres:** driver **SIDirect** (adresowanie symboliczne, S7-1200/1500). Inne obiekty Device Integration – `$OPCClient`
(OPC UA), `$DDESuiteLinkClient`, `$InTouchProxy` – są poza zakresem; jeśli w galaktyce komunikacja idzie przez nie, zanotuj to,
ale nie przerabiaj adresów bez decyzji użytkownika. Driver waliduje itemy z opóźnieniem, więc zły adres nie musi od razu dać
błędu – sprawdzenie adresów na żywym sterowniku wpisuj w „Do sprawdzenia”, dopóki użytkownik go nie potwierdzi.

- Pełny adres: **`<obiekt DI>.<grupa skanowania>.<item>`**, np. `S7C_01.SG1.Mieszalnik_1.Zawor_Wody.stan.Stan_Aktywny`.
  Obiekt DI podaje `--plc` (bez niego generator przerywa), grupę skanowania `--scan-group` (brak = ostrzeżenie).
  Ten sam adres trafia do `InputSource` (Input, InputOutput) albo do `OutputDest` (Output).
- Item: `[DB].[Tag]<[i]>.[Member]`; zagnieżdżenie dowolnej głębokości (limit drivera: 8 poziomów).
- Nazwy ze spacją lub kropką w cudzysłowie, indeks poza cudzysłowem (`"T1 T2"[2]`), a **cały item w `attribute(...)`**:
  `S7C_01.SG1.attribute(Mieszalnik_1.Zawor_Wody.stan."Komenda_HMI_ Aktywuj")`.
- Tablice wielowymiarowe: jeden nawias, przecinek między indeksami (`Siatka[1,0]`). Limity drivera: 6 wymiarów,
  1600 elementów, nazwa symboliczna 128 znaków, 252 składowe struktury.
- Typy czasowe: atrybut tylko do odczytu → item z sufiksem (`attribute(Cfg_Czas T)`), atrybut do zapisu (InputOutput albo Output) →
  ten sam item bez sufiksu i typ `MxInteger` w jednostce drivera (Time/S5Time/TOD: ms, LTime: ns, Date: dni).

### Potwierdzenie wzorca adresowania (obowiązkowe)
- Przed generowaniem trzeba zapytać, czy adresowanie automatyczne ma być wykonane (instrukcja projektu, sekcja 1).
- „Nie” → `--no-address`: instancje powstają, ale wszystkie `InputSource`/`OutputDest` są puste (generator dodaje o tym
  ostrzeżenie); adresy wpisuje użytkownik w IDE.
- „Tak” → najpierw pokazać 2–3 adresy zbudowane z realnych danych z tego pliku (przypadek zwykły, nazwa ze spacją
  w `attribute(...)`, element tablicy) i poprosić o zgodę albo o własny przykładowy adres.
- Własny przykład użytkownika rozkładamy na: obiekt DI, grupę skanowania, nazwę DB, separatory, cytowanie,
  zapis indeksów, `attribute(...)`, sufiksy. Co da się ustawić parametrami (`--plc`, `--scan-group`) – ustawiamy;
  czego nie – zmieniamy w `scl_to_aveva.py` (razem z opisem tutaj), nigdy w gotowych CSV.

## Instancje `Instances_<UDT>.csv`
- Format Galaxy Load: `:TEMPLATE=<nazwa szablonu ze specyfikacji>` (`$t_<UDT>` albo `$<UDT>`), kolumny `Tagname,Area,SecurityGroup,<Attr>.InputSource…`
  (dla atrybutów Output: `<Attr>.OutputDest`), w kolejności atrybutów szablonu.
- Bez adresów (`--no-address`, wszystkie adresy puste) plik ma **tylko** `Tagname,Area,SecurityGroup` – puste kolumny
  `<Attr>.InputSource` nadpisałyby wartości z szablonu.
- Area puste, SecurityGroup `Default`.
- Nazwy kolumn `<Attr>.InputSource` / `<Attr>.OutputDest` mają pełne nazwy atrybutów (bez skracania).
- Ścieżka PLC zachowuje strukturę DB (NIE nazwę spłaszczoną):
  `Control.Cmd_Start` → atrybut `Control_Cmd_Start`, adres `S7C_01.SG1.DB_X.Control.Cmd_Start`;
  `Sensors.Temp[1]` → atrybut `Sensors_Temp_1`, adres `S7C_01.SG1.DB_X.Sensors.Temp[1]`.

## Tryb Auto – serwer GalaxyMCP 0.2.8 (rozszerzenie .mcpb, AVEVA System Platform 2026)
- Pliki w projekcie (folder `Tools/`): `GalaxyMcp.cs`, `GalaxyMcp_README.md`, `GalaxyMcp_build.bat`, `GalaxyMcp_pack_mcpb.bat`,
  `GalaxyMcp_manifest.json` (→ `manifest.json`), `GalaxyMcp_icon.png.b64` (ikona: `certutil -decode`),
  `GalaxyMcp_instrukcja_pdf.py` (źródło instrukcji użytkownika PDF). Kopia instrukcji projektu: `Tools/Instrukcja_projektu.md`.
  Pliki testowe serwera (`test.bat`, `test_write.bat`, `*_requests.jsonl`, testowa specyfikacja), przykład
  `claude_desktop_config.json` i gotowy PDF instrukcji **nie są trzymane w projekcie** – sposób testowania i wzór
  konfiguracji są w README (sekcje 2 i 3); potrzebne pliki agent tworzy w `Wyniki/`.
  Instalacja na kolejnych komputerach: paczka `GalaxyMcp.mcpb` (README, sekcja 4). Po pobraniu na komputer usuń z plików pomocniczych przedrostek `GalaxyMcp_`
  (np. `build.bat`, `README.md`); `GalaxyMcp.cs` zostaje bez zmian, bo `build.bat` oczekuje tej nazwy.
- C# 5 / .NET Framework 4.x, budowany `build.bat` (wbudowany csc, `/codepage:65001`, domyślnie x86). GRAccess ładowany w czasie działania,
  wywołania przez interfejsy interop (wiązanie wczesne, klasa `Com`).
- Narzędzia: `galaxy_status`, `list_galaxies`, `select_galaxy`, `list_objects`, `get_object`, `export_csv`, `apply_spec`
  (`dry_run` domyślnie true, `scope` all/template/instances, `galaxy` obowiązkowe przy każdym zapisie), `import_csv`, `deploy` (wymaga `GALAXY_ALLOW_DEPLOY=1`).
- `apply_spec`: tworzy brakujący szablon i dopisuje brakujące UDA (+ `inputextension`/`inputoutputextension`); tworzy brakujące instancje; zmienia tylko różniące się `InputSource`. Niczego nie usuwa. CheckOut → Save → CheckIn, przy błędzie UndoCheckOut; potem zwalnia obiekty (Unload) i wylogowuje się z galaktyki, więc Check-in w IDE działa przy włączonej wtyczce. Log zapisów: `GalaxyMcp.log`.
  Kierunku Output (`outputextension`, `OutputDest`) serwer nie obsługuje – specyfikację z `io=Output` odrzuca w `Spec.Parse`.
- Serwer nie sprawdza długości nazw (szablon, instancja, atrybut) – tylko dozwolone znaki
  (`[A-Za-z_][A-Za-z0-9_]*`, szablon z `$`). Ewentualne ograniczenie galaktyki zgłosi GRAccess przy zapisie.
- W wątku połączonym z komputerem użytkownika narzędzia serwera mają przedrostek
  `mcp__remote-devices__GalaxyMCP__` (rozszerzenie `.mcpb`) albo `mcp__remote-devices__galaxy__` (ręczny wpis w konfiguracji).
- Procedura agenta: spec → `apply_spec` dry_run → pokazać plan → zapis dopiero po potwierdzeniu → deploy tylko na wyraźne polecenie.

## Wspólne
- Kodowanie CSV: UTF-8 z BOM, końce linii CRLF. Specyfikacja JSON: UTF-8 bez BOM.
- Typy AVEVA: sekcja „Mapowanie typów”. Szczegóły drivera: `ITERACJE/tmp_OI_SIDirect_adresowanie.md`.
- STRUCT w STRUCT → `A_B`. `String[n]` → String. Nieobsługiwane typy są pomijane z ostrzeżeniem.
- **Zagnieżdżone UDT** (`stan : "UDT_urzadzenie_stany"`) są rozwijane rekurencyjnie z definicji podanych w plikach:
  atrybut `stan_Stan_Aktywny`, adres `stan.Stan_Aktywny`. Brak definicji typu → pominięcie z ostrzeżeniem.
  Rekurencja (typ w sobie samym) jest przerywana i zgłaszana.
- **Tablice UDT i STRUCT** też są rozwijane: `Subs : Array[1..3] of "UDT_Sub"` → `Subs_1_Val`, adres `Subs[1].Val`.
- **Nazwy z TIA** są czyszczone do wymagań AVEVA: spacje są usuwane, polskie litery zamieniane na litery bez ogonków
  (`Prędkość` → `Predkosc`), a pozostałe znaki inne niż litera, cyfra i `_` na `_`
  (`"Komenda_HMI_ Aktywuj"` → `Komenda_HMI_Aktywuj`, `Temp-1` → `Temp_1`). Tak samo czyszczone są nazwa szablonu
  (`TYPE "UDT Mój typ"` → `$t_UDTMojtyp`; nazwy typów i DB w cudzysłowie mogą mieć spacje) i nazwy z `--instances`. Adres w PLC zachowuje
  oryginalną nazwę w cudzysłowie (`stan."Komenda_HMI_ Aktywuj"`, `"Temp-1"`). Każda zmiana nazwy jest w ostrzeżeniach.
  Czyszczenie może dać nazwę, która już istnieje (`Temp-1` i `Temp[1]` → `Temp_1`) – druga dostaje licznik
  (`Temp_1_1`) z ostrzeżeniem „koliduje z inną nazwą”. Kolizje są wykrywane bez rozróżniania wielkości liter
  (`Stan_X` i `stan_x` → `Stan_X`, `stan_x_1`), bo AVEVA i serwer GalaxyMCP traktują je jako tę samą nazwę.
- **Nazwy atrybutów nie są skracane**: atrybut ma pełną spłaszczoną nazwę, np.
  `stan_Stan_Blokada_Przyczyna_Slownik_Bardzo_Dlugi`, taką samą w szablonie, w kolumnie `<Attr>.InputSource`
  instancji i w specyfikacji. Licznik dostaje tylko nazwa kolidująca z inną (patrz wyżej). Opis atrybutu to sam komentarz z TIA.
- **Opis atrybutu**: komentarz `//` sklejony do jednej linii, bez otaczających cudzysłowów, **w pełnej długości –
  bez skracania**.
- Tablice (stałe granice, także wielowymiarowe): `Array[1..3] of X` → atrybuty `X_1..X_3`, adresy `X[1]..X[3]`.
  Indeks ujemny: `Array[-1..1]` → `X_m1, X_0, X_1` (`-` niedozwolony w nazwie atrybutu), adres `X[-1]`.
  Tablica wielowymiarowa: `Array[1..2, 0..1] of Real` → `Siatka_1_0`… , adres `Siatka[1,0]` (indeksy w jednym nawiasie).
- Pomijane z ostrzeżeniem: tablice poza limitami drivera (ponad 6 wymiarów albo 1600 elementów), tablice o granicach
  ze stałej (`[1.."MAX_N"]`), typy bez definicji w podanych plikach, typy nieobsługiwane (`Variant`, `Any`, `Pointer`, `DB_ANY`),
  zmienne proste w DB.
- Parser: komentarz `//` jest rozpoznawany także bez średnika (`Sekcja : Struct   // opis`); wartość początkowa tekstowa
  z `//` (`:= 'http://…'`) nie jest brana za komentarz. Ostrzeżenia ogólne są wypisywane raz, per typ – tylko własne.
- `Permissions.csv` czytany linia po linii: UTF-8, a gdy się nie da – CP1250 z ostrzeżeniem (plik należy zapisać ponownie jako UTF-8).
  Pozostałe zasady pliku reguł: sekcja „Kierunek I/O i `Permissions.csv`”.
- Reguły prefiksów: dopasowanie do nazwy LIŚCIA (zmiennej w SCL, bez prefiksów struktur nadrzędnych), wielkość liter ma znaczenie,
  pierwsze dopasowanie wygrywa. Brak dopasowania → Input.
- **Nazwy szablonów i instancji też nie są skracane** – ani generator, ani serwer GalaxyMCP nie mają limitu długości nazw.
  Galaktyka przyjmuje nazwy dłuższe niż 32 znaki – nie zgłaszaj tego w „Do sprawdzenia”.
- Instancje z `.db`: nazwa `<DB>_<element>` (pełna, bez skracania), adres `<DI>.<SG>.<DB>.<element>.<ścieżka w UDT>`.
  Tablica elementów w DB daje kilka instancji (`DB_Tablica_1`, `DB_Tablica_2`); UDT w STRUCT i DB typu UDT – tabela w „Pliki wejściowe”.
- Pola CSV są cytowane zgodnie z RFC 4180 (`csv.writer`), bo opisy z TIA zawierają przecinki i cudzysłowy,
  a adresy nazw ze spacją mają cudzysłowy. Do sprawdzenia w IDE: czy import przyjmuje cytowane pola
  (w trybie Auto problem nie występuje – wartości idą przez GRAccess, nie przez CSV).
- Kontrola: każdy wiersz danych ma tyle kolumn co nagłówek (UDA/Extended: 53).
- Wygenerowane pliki CSV i specyfikacje zapisuj tylko w `Wyniki/<RRRR-MM-DD>_<UDT>/` i dołączaj do odpowiedzi w wątku.
  Nie zapisuj ich w `Tools/`, `ITERACJE/` ani w katalogu głównym i nie dodawaj przedrostka `tmp_`.
- Narzędzia potrzebne do działania projektu (skrypt, opis metody, pliki serwera) są w `Tools/` bez przedrostka `tmp_`.
- Przedrostek `tmp_` (folder `ITERACJE/`) tylko dla notatek: ustalenia, historia wdrożenia, kopia instrukcji.
- Zanim dopiszesz nowy plik do projektu, sprawdź, czy jego treści nie ma już w instrukcji, tym opisie albo README serwera.
  Duplikat, którego nic nie czyta, rozjeżdża się z resztą – taki plik oddaj w `Wyniki/`.
