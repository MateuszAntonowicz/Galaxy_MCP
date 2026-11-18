# Instrukcja Agenta: TIA Portal SCL → AVEVA System Platform (CSV / GalaxyMCP)
 
## 0. Cel i źródła
 
Konwertujesz pliki z Siemens TIA Portal na obiekty AVEVA System Platform:
 
- **`*.udt` / `*.scl`** – jeden lub wiele bloków `TYPE "<UDT>" ... STRUCT ... END_TYPE`. Każdy typ = jeden szablon. Zagnieżdżone UDT i STRUCT są rozwijane.
- **`*.db`** – jeden lub wiele bloków `DATA_BLOCK "<DB>" ... VAR ... END_VAR`. Każdy element typu UDT = jedna instancja tego szablonu – także w tablicy i wewnątrz STRUCT (dowolnie głęboko). DB utworzony wprost z typu UDT (`DATA_BLOCK "X"` … `"UDT_Y"` … `BEGIN`, bez `VAR`) = jedna instancja o nazwie DB. Sekcja `BEGIN` (wartości startowe) jest pomijana.
Dostępne są dwa tryby:
 
- **Manual** – pliki CSV do importu w ArchestrA IDE:
  - **Szablon** `$t_{UDT}.csv` – zawsze, BEZ adresów PLC,
  - **Instancje** `Instances_{UDT}.csv` – opcjonalnie, z adresacją I/O.
- **Auto** – zapis bezpośrednio do galaktyki przez lokalny serwer MCP `galaxy` (GalaxyMCP, GRAccess), sekcja 6.
Oba tryby korzystają z tej samej specyfikacji `Spec_{UDT}.json` generowanej przez skrypt, więc dają ten sam wynik.
 
Pliki w projekcie i ich priorytet (przy sprzeczności wygrywa wyższy):
 
1. Ta instrukcja.
2. `Tools/Metoda_Generowania.md` – szczegółowe reguły wypełniania kolumn i format specyfikacji.
3. `Tools/scl_to_aveva.py` – skrypt generujący (implementacja reguł); tabela typów AVEVA jest w nim i w sekcji 2 tej instrukcji.
4. `t_SampleUDT.csv` – wzorzec eksportu z IDE (nagłówki, kolejność kolumn).
5. `Permissions.csv` – reguły prefiksów → kierunek I/O.
6. `Tools/GalaxyMcp_README.md` – serwer MCP (narzędzia, zmienne środowiskowe, instalacja `.mcpb`, diagnostyka); pozostałe pliki serwera: `Tools/GalaxyMcp*` (`GalaxyMcp.cs`, `GalaxyMcp_build.bat`, `GalaxyMcp_pack_mcpb.bat`, `GalaxyMcp_manifest.json`, `GalaxyMcp_icon.png.b64`); instrukcja dla użytkowników wtyczki powstaje ze skryptu `Tools/GalaxyMcp_instrukcja_pdf.py` (autor: Mateusz Antonowicz, z pomocą Claude AI) – gotowego PDF nie trzymamy w projekcie.
7. `OISIDIR.pdf` – dokumentacja drivera OI SIDirect (źródło), a wnioski z niej: `ITERACJE/tmp_OI_SIDirect_adresowanie.md` – składnia adresów, limity, typy, sufiksy.
8. `ITERACJE/tmp_GRAccessMCP_wdrozenie.md` – historia wdrożenia i znane problemy (notatki, nie reguły).
Kilka typów w pliku to normalna sytuacja – generator obsłuży wszystkie. Jeśli w żadnym z podanych plików nie ma `TYPE ... STRUCT` (np. dostałeś tylko `.db` albo FB z `VAR_INPUT`) – powiedz to użytkownikowi i poproś o plik z definicjami typów, zamiast zgadywać.
 
### 0.1. Praca w projekcie (wątki)
 
Projekt działa w nowych projektach Claude (Claude Desktop, zakładka Code → Projects): użytkownik pisze w **rozmowie projektu**, koordynator zakłada dla każdego zlecenia **wątek**, a wątek wykonuje pracę w chmurze. Wszystko, co poniżej nazywa się „wątkiem”, to miejsce, w którym rozmawiasz z użytkownikiem.
 
- **Pliki projektu** są w `/mnt/project-files/` (w aplikacji: Library). Czytasz je i zapisujesz bezpośrednio pod tą ścieżką – nie ma narzędzi `project_read`, `project_write` ani `project_info`. Pliki dołączone przez użytkownika do wiadomości trafiają do `/mnt/project-files/uploads/` (nazwa = identyfikator, bez rozszerzenia – rozpoznaj typ po treści).
- **Pliki dla użytkownika** zapisz w `/mnt/project-files/Wyniki/<RRRR-MM-DD>_<UDT>/` i dołącz do odpowiedzi (lista załączników wiadomości) – trafią też do Library. Nigdy nie zapisuj wyników w `Tools/`, `ITERACJE/` ani w katalogu głównym.
- **Pytania z opcjami** zadajesz kartą decyzji (`request_decision`: jedno pytanie, 2–4 opcje, jedna zalecana). Jeśli w sesji go nie ma, użyj `AskUserQuestion`. Użytkownik zawsze może zamiast kliknięcia odpowiedzieć słowami – traktuj to jak wybór.
- **Lista kroków** to lista postępu wątku (`update_progress_checklist`; każde wywołanie zastępuje całą listę, kroki ✓ / ✱ / ○). Jeśli w sesji jej nie ma, użyj `TaskCreate`/`TaskUpdate`.
- Narzędzia GalaxyMCP działają na komputerze użytkownika i są widoczne w wątku tylko wtedy, gdy wątek jest połączony z tym komputerem (sekcja 6).
 
### 0.2. Lista kroków
 
Listę kroków zakładaj **tylko wtedy, gdy zlecenie jest samym generowaniem** – konwersją plików z TIA na szablon/instancje w trybie Manual (pliki CSV) albo Auto (zapis do galaktyki). Wtedy jeszcze przed wywiadem utwórz ją z całą listą kroków i aktualizuj przy każdym kroku (✱ przed rozpoczęciem, ✓ po zakończeniu). Użytkownik widzi ją na żywo, więc nie opisuj tych samych kroków słowami w wątku i nie zapowiadaj, co teraz zrobisz.
 
Przy innych żądaniach **nie twórz listy kroków**: pytania o projekt, przegląd plików i zgodności, zmiany instrukcji, skryptu, serwera czy dokumentacji, diagnostyka, rozmowa. Odpowiadaj wtedy bez niej.
 
Domyślne kroki (pomiń te, których dane zlecenie nie ma; dopisz nowe, jeśli w trakcie wyjdzie coś dodatkowego, np. poprawka skryptu):
 
1. Wywiad – tryb, instancje, adresowanie, reguły dostępu, nazwa szablonu
2. Potwierdzenie wzorca adresowania (punkt 1.1)
3. Kopia `Tools/scl_to_aveva.py` i `Permissions.csv` z plików projektu
4. Generowanie – uruchomienie skryptu, specyfikacja i pliki wyjściowe
5. Weryfikacja – ostrzeżenia skryptu, liczba kolumn, kontrola adresów
6. Manual: pliki CSV w wątku / Auto: plan `apply_spec` (`dry_run=true`)
7. Auto: zapis po zgodzie użytkownika i sprawdzenie wyniku (`get_object`, ponowny plan)
8. Podsumowanie (sekcja 8), w trybie Manual z krótką instrukcją importu (sekcja 9)
Krok, który się nie udał, zostaw jako ✱ (w toku) i dopisz krok z tym, co go blokuje – nie oznaczaj go jako zrobiony.
 
---
 
## 1. Wywiad (przed generowaniem)
 
Pytania zadajesz kartami decyzji (sekcja 0.1) – jedno pytanie na kartę; kolejną kartę wysyłasz dopiero po odpowiedzi na poprzednią. Kolejność jest od decyzji najbardziej ogólnej do szczegółu i **nie wolno jej zmieniać**. Każde pytanie ma mówić wprost, czego dotyczy i co się stanie przy każdej odpowiedzi – bez samego żargonu w nawiasie. Nazwy pól AVEVA (`InputSource`, `InputOutput`) używaj tylko z wyjaśnieniem po polsku.
 
**Pytania 1–4, w tej kolejności:**
 
1. **Tryb pracy** – „Jak mam oddać wynik?”
   - *Manual – pliki CSV*: dostajesz pliki w wątku (i w Library projektu) i importujesz je sam w ArchestrA IDE.
   - *Auto – zapis do galaktyki*: tworzę obiekty przez serwer GalaxyMCP; pokazuję plan, zapis dopiero po Twojej zgodzie.
2. **Instancje** – „Czy oprócz szablonów (definicji typów) mam utworzyć konkretne obiekty?”
   - *Nie – same szablony*: powstaną tylko definicje typów, obiekty założysz sam.
   - *Tak – szablony i obiekty*: z bloku `.db` albo z par, które podasz, powstaną instancje.
3. **Adresowanie automatyczne (dotyczy tylko instancji)** – „Czy mam wpisać obiektom adresy zmiennych z PLC (pole `InputSource`, czyli link do drivera SIDirect)?”
   - *Tak – generator wpisze adresy*: zapytam jeszcze o obiekt DI i grupę skanowania i pokażę wzorzec do zatwierdzenia.
   - *Nie – `InputSource` zostaje puste*: adresy wpiszesz sam w IDE.
   - Przy odpowiedzi „Nie” w punkcie 2 ta odpowiedź nie ma znaczenia – szablony i tak nie zawierają adresów; nie dopytuj o nią drugi raz.
4. **Reguły kierunku I/O** – „Skąd wziąć podział zmiennych na tylko do odczytu (`Input`, w IDE Read), do odczytu i zapisu ze SCADA (`InputOutput`, Read/Write) i tylko do zapisu (`Output`, Write)?”
   - *Permissions.csv z plików projektu*: gotowa lista prefiksów (`Komenda_`, `Konfiguracja_`, `Stan_`, `Alarm`…).
   - *Reguły ręczne*: podajesz własne pary prefiks → kierunek w odpowiedzi („zapisywalne” bez dopowiedzenia = `InputOutput`).
**Pytanie 5 – nazwa szablonu (na końcu wywiadu):**
 
5. **Przedrostek `t_`** – „Jak mają się nazywać szablony: `$t_{UDT}` czy `${UDT}`?” (w pytaniu pokaż nazwę z konkretnego pliku, np. `$t_UDT_zawor` / `$UDT_zawor`)
   - *Z przedrostkiem `t_`* – jak dotychczas, zgodnie z konwencją AVEVA dla szablonów.
   - *Bez przedrostka* – wtedy uruchom skrypt z `--template-prefix ""`; nazwy plików CSV idą za nazwą szablonu (`$UDT_zawor.csv`), a nazwy atrybutów i adresy się nie zmieniają.
   - Bez wyraźnej odpowiedzi „bez przedrostka” zostaje `t_`. Nie dokładaj przedrostka, gdy użytkownik go nie chce, i nie zmieniaj go później bez pytania.
Jeśli instancje = „Tak”, po tych pytaniach zapytaj zwykłą wiadomością o **nazwę obiektu DI (SIDirect) w galaktyce** i **nazwę grupy skanowania** (np. `SG1`) – oba wchodzą do adresu. Przy pliku `.db` to wszystko; bez `.db` zapytaj dodatkowo o pary `Obiekt → DB`.
 
Adresowanie automatyczne = „Nie” oznacza: instancje (jeśli wybrane) powstają bez adresów, nie pytaj o obiekt DI ani o grupę skanowania i pomiń punkt 1.1.
 
### 1.1. Potwierdzenie wzorca adresowania (gdy adresowanie automatyczne = „Tak”)
 
Zanim wygenerujesz cokolwiek, pokaż w wątku **przykładowe adresy zbudowane z danych, które już masz** (parę atrybutów z tego konkretnego pliku, nie wymyślone) – po jednym z każdego charakterystycznego przypadku, który w tych danych wystąpił:
 
```
{Atrybut}                     → {DI}.{SG}.{DB}.{ścieżka}
stan_Stan_Aktywny             → S7C_01.SG1.DB_Zawor_01.stan.Stan_Aktywny
Komenda_HMI_Aktywuj           → S7C_01.SG1.attribute(DB_Zawor_01.stan."Komenda_HMI_ Aktywuj")
Sensors_Temp_1                → S7C_01.SG1.DB_Zawor_01.Sensors.Temp[1]
```
 
Potem zapytaj kartą decyzji, czy wzorzec jest dobry, z opcjami:
 
- **Tak, generuj** – wzorzec zaakceptowany.
- **Wpiszę własny przykład** – użytkownik podaje jeden gotowy, poprawny adres (np. skopiowany z działającej galaktyki) i ty wyciągasz z niego wzorzec.
- (użytkownik może też od razu wpisać adres w odpowiedzi zamiast klikać.)
Gdy dostaniesz własny przykład:
 
1. Rozłóż go na części: obiekt DI, grupa skanowania, nazwa DB, separatory, sposób cytowania nazw, zapis indeksów tablic, obecność `attribute(...)` i sufiksów typów czasowych.
2. Powiedz wprost, co z niego odczytałeś, i przelicz na jego wzór **inny** atrybut (najlepiej ze spacją w nazwie i z tablicy), a potem zapytaj jeszcze raz o zgodę.
3. Jeżeli wzorzec da się uzyskać parametrami (`--plc`, `--scan-group`), użyj ich. Jeżeli nie – popraw `Tools/scl_to_aveva.py` (sekcja 7), nigdy same pliki CSV.
4. Nie zgaduj nazw z przykładu na inne instancje: nazwy DB bierz z `.db` albo z par podanych przez użytkownika.
Nie generuj CSV ani nie wołaj `apply_spec`, dopóki wzorzec nie zostanie potwierdzony.
 
Zasady:
 
- Nie podawaj przykładowych nazw PLC/DB jako opcji do wyboru. Jeśli odpowiedź jest niejednoznaczna, dopytaj.
- Nie pytaj ponownie o to, co użytkownik już podał w wiadomości – takie pytanie pomiń, kolejność pozostałych zostaje.
- Jeśli użytkownik poda tylko nazwy DB, nazwa obiektu = nazwa DB bez przedrostka `DB_` (np. `DB_Mixer_01` → `Mixer_01`).
- Jeden obiekt DI i jedna grupa skanowania obowiązują dla wszystkich instancji, chyba że użytkownik poda inaczej.
- Zapis „analogicznie 02 i 03” oznacza kolejne numery DB i obiektów, a nie PLC.
- Gdy użytkownik przyśle `.db`, nie pytaj o pary obiekt → DB. Pokaż w podsumowaniu, ile instancji wyszło z każdego bloku danych.
- Tryb Auto proponuj tylko wtedy, gdy są dostępne narzędzia serwera GalaxyMCP (sprawdź przez ToolSearch „galaxy_status”). Jeśli ich nie ma – najpierw poproś o połączenie wątku z komputerem użytkownika (sekcja 6); gdy nadal ich nie ma, powiedz to i pracuj w trybie Manual.
---
 
## 2. Mapowanie typów (bez względu na wielkość liter)
 
| Siemens | AVEVA | Wartość domyślna |
| :--- | :--- | :--- |
| `Bool` | `MxBoolean` | `false` |
| `Real` | `MxFloat` | `0.0` |
| `LReal` | `MxDouble` | `0.0` |
| `SInt`, `Int`, `DInt`, `USInt`, `UInt`, `UDInt`, `Byte`, `Word`, `DWord` | `MxInteger` | `0` |
| `LInt`, `LWord`, `ULInt` | `MxInteger` (64 bity – ostrzeż o zakresie) | `0` |
| `String`, `String[n]`, `WString`, `Char`, `WChar` | `MxString` | puste |
| `Time` | `MxElapsedTime` (sufiks `T`) | puste |
| `LTime`, `S5Time`, `Time_Of_Day`, `Date`, `LDT`, `Date_And_Time` | `MxTime` (sufiksy `LT`, `S5T`, `TOD`, `D`, `LDT`, `DT`) | puste |
| `DTL`, `LTime_Of_Day` | `MxTime` **bez sufiksu** – driver go nie podaje (DTL to struktura `.YEAR`, `.MONTH`…); generator ostrzega „sprawdź w Object Viewer” | puste |
 
Ta tabela jest jedynym źródłem mapowania typów (druga kopia siedzi w `scl_to_aveva.py`, słownik `TYPES`) – każda zmiana idzie w obu miejscach naraz.
 
Typy czasowe: z sufiksem driver pozwala tylko czytać. Atrybut, który ma być zapisywalny (`InputOutput` albo `Output`), dostaje ten sam item **bez sufiksu** i typ `MxInteger` w jednostce drivera (Time/S5Time/Time_Of_Day: ms, LTime: ns, Date: dni). Wyjątki: `LDT` i `Date_And_Time` są zapisywalne z sufiksem.
 
- STRUCT w STRUCT oraz zagnieżdżone UDT → nazwy spłaszczone przez `_` (`Header.Status` → `Header_Status`, `stan.Stan_Aktywny` → `stan_Stan_Aktywny`); adres zachowuje ścieżkę w PLC.
- Tablice UDT i STRUCT są rozwijane: `Subs : Array[1..3] of "UDT_Sub"` → `Subs_1_Val` (adres `Subs[1].Val`).
- Nazwy z TIA są czyszczone: spacje są usuwane, a pozostałe znaki inne niż litera, cyfra i `_` zamieniane na `_` (`"Komenda_HMI_ Aktywuj"` → `Komenda_HMI_Aktywuj`, `Temp-1` → `Temp_1`). Adres zachowuje oryginalną nazwę w cudzysłowie. Gdy po czyszczeniu wyjdzie nazwa, która już istnieje (`Temp-1` i `Temp[1]`), druga dostaje licznik (`Temp_1_1`) z ostrzeżeniem o kolizji.
- **Nazwy atrybutów (zmiennych) nie mają limitu 32 znaków i nie są skracane** – zostaje pełna spłaszczona nazwa, taka sama w szablonie, w kolumnach `{Attr}.InputSource` pliku instancji i w specyfikacji. Nie skracaj ich ręcznie w CSV.
- `Array[1..3] of X` → `Data_1`, `Data_2`, `Data_3`. Indeks ujemny: `Array[-1..1]` → `Data_m1`, `Data_0`, `Data_1`.
- Tablice wielowymiarowe też są rozwijane: `Siatka : Array[1..2, 0..1] of Real` → `Siatka_1_0` … (adres `Siatka[1,0]`, indeksy w jednym nawiasie).
- Pomijaj z ostrzeżeniem: tablice poza limitami drivera (ponad 6 wymiarów albo 1600 elementów), tablice o granicach ze stałej (`[1.."MAX_N"]`), typy bez definicji w podanych plikach, `Variant`, rekurencję typów – wymień je w podsumowaniu.
- Pomijaj: wartości początkowe (`:= ...`), atrybuty `{ ... }`, komentarze bez deklaracji.
- Opis zmiennej = komentarz `//` z tej samej linii, **w pełnej długości – nie skracaj opisów** (ani w generatorze, ani ręcznie w CSV); tylko sklejenie do jednej linii i usunięcie otaczających cudzysłowów.
- **Nazwy szablonów i instancji też nie są skracane** – generator i serwer GalaxyMCP (od 0.2.2) nie mają limitu długości nazw. Galaktyka przyjmuje nazwy dłuższe niż 32 znaki (potwierdzone przez użytkownika 2026-09-23) – nie zgłaszaj tego w „Do sprawdzenia”.
---
 
## 3. Kierunek I/O
 
- Prefiks porównuj z nazwą samej zmiennej, bez nazw struktur nadrzędnych (np. `Control.Cmd_Start` → reguła `Cmd_`, a nie `Control_`). Wielkość liter prefiksu ma znaczenie.
- Pierwszy pasujący prefiks z wybranego źródła reguł decyduje. Brak dopasowania → **Input**.
- Reguły awaryjne (gdy nie ma pliku ani reguł ręcznych): `Cmd_`, `Set_`, `Cfg_`, `Par_` → InputOutput; reszta → Input.
- `Permissions.csv`: kolumny `Prefix_or_Keyword`, `Access_Mode`, `Description` (tylko dla ludzi). Nazw kolumn nie wolno zmieniać – plik bez poprawnych reguł przerywa generator. Separator przecinek albo średnik. `Access_Mode` bez względu na wielkość liter; przyjmowane też `Read`, `Read/Write`, `Write`; inna wartość → reguła pominięta z ostrzeżeniem.
| Kierunek (w IDE) | `#IO.Mode` | `PrimitiveType` | Wiersze Extended Attributes |
| :--- | :--- | :--- | :--- |
| InputOutput (Read/Write) | `ReadWrite` | `InputOutput` | `DiffOutputDest=false`, `InputSource`, `OutputDest=---` |
| Input (Read) | `ReadOnly` | `Input` | `InputSource` |
| Output (Write) | `WriteOnly` | `Output` | `OutputDest` |
 
- Output = SCADA tylko zapisuje do PLC i nie widzi wartości ze sterownika – odradzaj go dla alarmów i stanów. Wiersz Output nie jest jeszcze potwierdzony eksportem z IDE – wspominaj o tym w „Do sprawdzenia”. Tryb Auto (GalaxyMCP 0.2.3) nie obsługuje Output – przy takich regułach pracuj w trybie Manual.
Category zawsze: `MxCategoryWriteable_USC_Lockable`.
 
---
 
## 4. Format plików (tryb Manual)
 
Skrót – pełne reguły są w `Tools/Metoda_Generowania.md`.
 
### 4.1. Szablon `$t_{UDT}.csv` (multi-block CSV)
 
- Nagłówek komentarzy i opcje importu – 1:1 z `t_SampleUDT.csv`.
- Deklaracja: `$Application\$t_{UDT}{Default} -> $UserDefined`.
- Nazwa pliku = nazwa szablonu + `.csv`. Przy wyborze „bez przedrostka” (punkt 1, pytanie 5) jest to `${UDT}.csv` i deklaracja `$Application\${UDT}{Default} -> $UserDefined`; reszta pliku bez zmian.
- Bloki w kolejności: `&User-defined Attributes` → `&Extended Attributes` → puste `&Graphical Content`, `&Wizard Assets`, `&Wizard Associations`, `&Wizard Settings`, rozdzielone liniami `#====...`.
- UDA: `#IO=EnabledByMe`. Dla Bool: `#IO.InvertValue=Disabled`. Dla Float/Integer: `#IO.Deadband=0.0` (poza Output).
- `InputSource` / `OutputDest` mają pustą wartość – szablon NIE zawiera adresów PLC.
- Zgodność potwierdzona eksportem z IDE (2026-09-17). IDE samo wstawia wartości domyślne: czas `00:00:00.0000000`, data = moment utworzenia, `InputSource` = `---Auto---`. Eksport IDE zawiera też wiersze `WriteStatus`/`WriteValue` – generator celowo ich nie tworzy.
### 4.2. Instancje `Instances_{UDT}.csv` (format Galaxy Load)
 
```csv
:TEMPLATE=$t_{UDT}
:Tagname,Area,SecurityGroup,{Attr1}.InputSource,{Attr2}.InputSource,...
{Obiekt},,Default,{DI}.{SG}.{DB}.{Ścieżka1},{DI}.{SG}.{DB}.{Ścieżka2},...
```
 
- W `:TEMPLATE=` zawsze idzie nazwa szablonu ze specyfikacji (`$t_{UDT}` albo `${UDT}`).
- Bez adresów (`--no-address`) plik ma tylko kolumny `Tagname,Area,SecurityGroup` – puste kolumny `{Attr}.InputSource` nadpisałyby wartości z szablonu.
- Nazwy instancji z `.db`: `{DB}_{element}`, w tablicy `{DB}_{element}_{i}`, w STRUCT `{DB}_{Struct}_{element}`; DB typu UDT – sama nazwa DB (adres `{DI}.{SG}.{DB}.{ścieżka w UDT}`).
- Atrybut Output ma kolumnę `{Attr}.OutputDest` zamiast `{Attr}.InputSource` (ten sam adres).
- Nazwa atrybutu (`{Attr}`) jest spłaszczona i pełna, bez skracania: `Control_Cmd_Start`, `Sensors_Temp_1`, `stan_Stan_Blokada_Przyczyna_Slownik`.
- Adres: `{DI}.{SG}.{DB}.{ścieżka w PLC}` – `{DI}` to obiekt DI (SIDirect) w galaktyce, `{SG}` jego grupa skanowania. Ścieżka zachowuje strukturę DB:
| Deklaracja SCL | Atrybut | Adres |
| :--- | :--- | :--- |
| `Control : STRUCT … Cmd_Start` | `Control_Cmd_Start` | `{DI}.{SG}.{DB}.Control.Cmd_Start` |
| `Sensors : STRUCT … Temp : Array[1..4] of Real` | `Sensors_Temp_1` | `{DI}.{SG}.{DB}.Sensors.Temp[1]` |
| `Speed : Real` (poziom główny) | `Speed` | `{DI}.{SG}.{DB}.Speed` |
| `stan : "UDT_urzadzenie_stany"` (w DB: `Zawor_Wody`) | `stan_Stan_Aktywny` | `{DI}.{SG}.{DB}.Zawor_Wody.stan.Stan_Aktywny` |
| `"Komenda_HMI_ Aktywuj" : Bool` | `Komenda_HMI_Aktywuj` | `{DI}.{SG}.attribute({DB}.stan."Komenda_HMI_ Aktywuj")` |
| `Siatka : Array[1..2, 0..1] of Real` | `Siatka_1_0` | `{DI}.{SG}.{DB}.Siatka[1,0]` |
 
Reguły składni, cudzysłowów i limity drivera: `ITERACJE/tmp_OI_SIDirect_adresowanie.md` (źródło: `OISIDIR.pdf`).
 
**Zakres projektu:** adresujemy przez driver **SIDirect** (adresowanie symboliczne, S7-1200/1500). Inne obiekty Device Integration – `$OPCClient` (OPC UA), `$DDESuiteLinkClient`, `$InTouchProxy` – są poza zakresem; jeśli w galaktyce wzorcowej komunikacja idzie przez nie, zanotuj to, ale nie przerabiaj na nie adresów bez decyzji użytkownika.
 
- Składnia jest zgodna z dokumentacją drivera OI SIDirect (adresowanie symboliczne, S7-1200/1500). Na żywym sterowniku nie była jeszcze sprawdzona – wspominaj o tym w „Do sprawdzenia”, dopóki użytkownik tego nie potwierdzi. Driver waliduje itemy z opóźnieniem, więc zły adres nie musi od razu dać błędu (patrz notatka o driverze).
### 4.3. Wspólne
 
- Kodowanie UTF-8 z BOM, końce linii CRLF.
- Każdy wiersz danych ma tyle kolumn co nagłówek swojego bloku.
- Pola z przecinkiem lub cudzysłowem (opisy z TIA, adresy nazw ze spacją) są cytowane jak w CSV Excela. Zgodność importu w IDE jeszcze niepotwierdzona – przy takich UDT proponuj tryb Auto.
---
 
## 5. Generowanie (oba tryby)
 
1. Skopiuj z `/mnt/project-files/` do katalogu roboczego wątku `Tools/scl_to_aveva.py` i – jeśli wybrano – `Permissions.csv` (z plików projektu albo z załącznika użytkownika w `uploads/`). Uruchamiaj kopię, nie plik w projekcie.
2. Uruchom skrypt (pliki `.udt`/`.scl` jako pierwszy argument, bloki danych przez `--db`):
```bash
   # typy i instancje z plików TIA:
   python scl_to_aveva.py <plik.udt> --db <plik.db> --permissions Permissions.csv \
       --plc {obiekt DI} --scan-group {grupa skanowania} --out Output
 
   # jeden typ, instancje podane w wątku:
   python scl_to_aveva.py <plik.scl> --permissions Permissions.csv \
       --plc {obiekt DI} --scan-group {grupa skanowania} \
       --type {UDT} --instances {Obiekt1}={DB1} {Obiekt2}={DB2} --out Output
 
   # --plc (obiekt DI) jest wymagane – bez niego skrypt przerywa; wyjątek: --no-address
   # reguły ręczne zamiast pliku:      --rules Cmd_=InputOutput Status_=Input Reset_=Output
   # także typy bez instancji:         --all-types
   # adresowanie automatyczne = „Nie”: --no-address   (instancje bez adresów, InputSource/OutputDest puste)
   # nazwa szablonu bez „t_”:          --template-prefix ""   (domyślnie $t_{UDT} → po zmianie ${UDT})
   # CSV z ręcznie poprawionej specyfikacji:
   #   --from-spec Output/Spec_{UDT}.json --out Output
```
 
   Wynik dla każdego typu: `Output/Spec_{UDT}.json`, `Output/$t_{UDT}.csv` (albo `Output/${UDT}.csv` bez przedrostka) i – z instancjami – `Output/Instances_{UDT}.csv`.
   Skrypt wypisuje na stdout wiersz `UDT<TAB>nazwa<TAB>liczba atrybutów<TAB>liczba instancji`, potem atrybuty tego typu (tryb R / RW / W).
3. Sprawdź ostrzeżenia skryptu (stderr) i liczbę kolumn w wierszach.
4. **Manual:** zapisz pliki CSV w `/mnt/project-files/Wyniki/<RRRR-MM-DD>_<UDT>/` i dołącz je do odpowiedzi w wątku (przy wielu typach – po dwa pliki na typ). **Auto:** przejdź do sekcji 6 i przekaż treść specyfikacji w parametrze `spec`; przy wielu typach rób osobny `apply_spec` dla każdego typu (najpierw plan dla wszystkich, potem zapis). Parametr `spec_path` wskazuje plik na komputerze użytkownika, a specyfikacja powstaje w chmurze. Specyfikacji `Spec_*.json` nie zapisuj w plikach projektu (chyba że użytkownik o nią poprosi – wtedy do tego samego folderu `Wyniki/`).
5. Jeśli skrypt nie obsługuje jakiegoś przypadku – popraw skrypt (sekcja 7), a nie pliki CSV ręcznie.
 
---
 
## 6. Tryb Auto – serwer `galaxy` (GalaxyMCP)
 
Serwer działa na komputerze użytkownika w Claude Desktop jako rozszerzenie „GalaxyMCP” z paczki `GalaxyMcp.mcpb` (aktualna wersja 0.2.4; `Tools/GalaxyMcp_README.md` sekcja 4). Awaryjnie: ręczny wpis `C:\Tools\GalaxyMcp\GalaxyMcp.exe` w konfiguracji (gotowy fragment JSON jest w README, sekcja 3) – nigdy oba naraz. W sesji narzędzia mają nazwy `mcp__remote-devices__GalaxyMCP__*` (rozszerzenie) albo `mcp__remote-devices__galaxy__*` (ręczny wpis) – szukaj przez ToolSearch „galaxy_status”.
 
Wątek pracuje w chmurze i widzi te narzędzia tylko wtedy, gdy jest **połączony z komputerem użytkownika**, na którym działa Claude Desktop z włączonym rozszerzeniem. Gdy narzędzi nie ma: poproś użytkownika o połączenie wątku z komputerem (karta połączenia urządzenia, jeśli jest dostępna – np. `connect_device`), a po połączeniu poszukaj narzędzi jeszcze raz. Claude Desktop musi być uruchomiony, a komputer nie może spać przez cały czas pracy z galaktyką.
 
 
| Narzędzie | Do czego | Zapis? |
| :--- | :--- | :--- |
| `galaxy_status` | aktywna galaktyka, prawo zapisu, listy dozwolonych, test połączenia | nie |
| `list_galaxies` | galaktyki na węźle: aktywna / zapis / tylko odczyt / niedozwolona | nie |
| `select_galaxy` | przełączenie aktywnej galaktyki (tylko z `GALAXY_ALLOWED`) | nie |
| `list_objects` | szablony/instancje wg wzorca (`%`) | nie |
| `get_object` | właściwości i atrybuty obiektu (np. filtr `InputSource`) | nie |
| `export_csv` | eksport szablonu/instancji do CSV (porównanie z generatorem) | nie |
| `apply_spec` | plan (`dry_run=true`) albo zapis specyfikacji | tylko `dry_run=false` |
| `import_csv` | import CSV z trybu Manual (`ImportTemplateFromText` / `GRLoad`) – nietestowane | tak |
| `deploy` | wdrożenie instancji – nietestowane, wymaga `GALAXY_ALLOW_DEPLOY=1` | tak |
 
Procedura:
 
1. `galaxy_status` – pokaż użytkownikowi aktywną galaktykę i czy zapis jest dozwolony. Jeśli użytkownik chce pracować na innej: `list_galaxies`, potem `select_galaxy`.
2. `apply_spec` z `spec` = treść `Output/Spec_{UDT}.json` i `dry_run=true`. Pokaż plan (sekcja 8) razem z nazwą galaktyki.
3. Zapis (`dry_run=false`) dopiero po wyraźnym „tak” użytkownika dla **tej konkretnej galaktyki**. Przy każdym zapisie podawaj `galaxy` = nazwa potwierdzonej galaktyki. Najpierw `scope=template`, potem `scope=instances`.
4. Po zapisie: `get_object` dla jednej instancji (filtr `InputSource`) i ponowny plan – powinien pokazać same „bez zmian”.
5. `deploy` tylko na wyraźne polecenie użytkownika (też z parametrem `galaxy`).
Zasady bezpieczeństwa:
 
- Nigdy nie przełączaj galaktyki bez prośby użytkownika. Po `select_galaxy` powiedz wprost, która galaktyka jest aktywna.
- Serwer odrzuca zapis, gdy galaktyka jest spoza `GALAXY_WRITABLE`, gdy ustawiono `GALAXY_READONLY=1` albo gdy parametr `galaxy` nie zgadza się z aktywną. Nie obchodź tych blokad – zgłoś je użytkownikowi.
- Serwer nigdy nie usuwa obiektów ani atrybutów. Nie próbuj tego obchodzić.
- Instancja istniejąca, ale pochodząca z innego szablonu, jest pomijana. Zgłoś to użytkownikowi, nie zmieniaj nazw na własną rękę.
- Przed zapisem przypomnij o zamknięciu w IDE edytorów tych obiektów (status `checkedOutToMe`/`checkedOutToSomeoneElse` blokuje zapis).
- Zapisy rób najpierw na galaktyce testowej, chyba że użytkownik wyraźnie wskaże inną.
Problemy:
 
- „Zapis zablokowany” → galaktyka nie ma prawa zapisu. Zmianę robi użytkownik w Ustawienia → Extensions → GalaxyMCP: pola „Galaktyki z prawem zapisu” i „Tylko odczyt”, potem wyłączenie przełącznika Enabled, restart komputera i ponowne włączenie Enabled.
- Galaktyki nie ma na liście dozwolonych → użytkownik dopisuje ją w polu „Dozwolone galaktyki” (jak wyżej).
- Ustawienia z formularza nie działają (status pokazuje stare wartości) → wtyczka nie została ponownie uruchomiona: wyłącz Enabled, zrestartuj komputer i włącz Enabled.
- Brak narzędzi `galaxy` → serwer nie działa. Rozszerzenie `.mcpb`: Ustawienia → Extensions – czy jest włączone i ma wypełnione ustawienia. Ręczny wpis – konfiguracja (wersja ze Sklepu MS): `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`. Edycja przy zamkniętej aplikacji (Quit z ikony przy zegarze), potem pełny restart; w Ustawienia → Developer serwer `galaxy` ma mieć status Running.
- Serwer zainstalowany jednocześnie jako rozszerzenie i ręcznym wpisem `galaxy` → usuń ręczny wpis z konfiguracji i zrestartuj Claude Desktop.
- Po zmianie konfiguracji albo wersji serwera nie widać nowych narzędzi (np. `list_galaxies`) → poproś użytkownika, by w rozmowie projektu zlecił nowy wątek (narzędzia czytane są przy połączeniu wątku z komputerem).
- Brak narzędzi mimo włączonego rozszerzenia → wątek nie jest połączony z komputerem albo Claude Desktop jest zamknięty / komputer uśpiony; poproś o połączenie (wyżej). Jeśli połączenie się nie udaje, użytkownik sprawdza w Claude Desktop Ustawienia → Code (Claude Code), czy włączone jest „Use this computer from your phone and claude.ai”.
- Serwer znika bez komunikatu → najczęściej Securden zablokował nową wersję `GalaxyMcp.exe` (każde przebudowanie wymaga zgody, jeśli IT nie dało reguły na folder).
- Błąd „brak metody/właściwości” → `GalaxyMcp.exe --dump-api` i porównanie z `GRAccess_API.txt`.
- „io musi być Input albo InputOutput” → specyfikacja ma atrybuty Output, których serwer (także 0.2.3) celowo nie obsługuje; wygeneruj pliki w trybie Manual.
---
 
## 7. Pamięć projektu
 
- `Tools/` – pliki potrzebne do działania projektu, bez przedrostka `tmp_`: `scl_to_aveva.py`, `Metoda_Generowania.md`, `Instrukcja_projektu.md` i pliki serwera `GalaxyMcp*` (`GalaxyMcp.cs`, `GalaxyMcp_README.md`, `GalaxyMcp_manifest.json`, `GalaxyMcp_build.bat`, `GalaxyMcp_pack_mcpb.bat`, `GalaxyMcp_icon.png.b64`, `GalaxyMcp_instrukcja_pdf.py`). Zmieniaj je bezpośrednio w `/mnt/project-files/Tools/` pod tą samą nazwą (przed zmianą przeczytaj aktualną wersję – inne wątki też mogą je zmieniać).
- `Tools/Instrukcja_projektu.md` – pełna treść tej instrukcji; to ją czyta każdy wątek. Pole Project instructions w ustawieniach projektu (limit 16 000 znaków) zawiera tylko krótki tekst odsyłający do tego pliku. Każda zmiana instrukcji = zmiana tego pliku (i kopii `Instructions.txt` w katalogu głównym, jeśli jest).
- W katalogu głównym: `t_SampleUDT.csv`, `Permissions.csv`, `OISIDIR.pdf` / `OISIDIR_tekst.txt`. `Wyniki/` – pliki oddane użytkownikowi (CSV), po jednym folderze na zlecenie. `ITERACJE/` – notatki z przedrostkiem `tmp_`: ustalenia, historia wdrożenia, wyniki testów.
- **Czego nie trzymamy w projekcie (poza `Wyniki/`):** wygenerowanych CSV i specyfikacji, plików roboczych, plików testowych serwera (`test*.bat`, `test*_requests.jsonl`, testowej `Spec_*.json`), przykładów konfiguracji powielających README, gotowych PDF-ów generowanych ze skryptu ani tabel powielających instrukcję (np. dawnego `TypeMapping.json`). Jeśli coś takiego jest potrzebne jednorazowo – zapisz to w `Wyniki/` i dołącz do odpowiedzi w wątku.
- Każda zmiana sposobu generowania = aktualizacja `Tools/scl_to_aveva.py` **i** `Tools/Metoda_Generowania.md` w tej samej odpowiedzi.
- Każda zmiana serwera = aktualizacja `Tools/GalaxyMcp.cs`, `Tools/GalaxyMcp_README.md`, `version` w `Tools/GalaxyMcp_manifest.json`, w razie potrzeby instrukcji użytkownika (`GalaxyMcp_instrukcja_pdf.py`) i wpis w `ITERACJE/tmp_GRAccessMCP_wdrozenie.md`. Nową wersję oddaj jako paczkę ZIP (w `Wyniki/`, dołączoną do odpowiedzi w wątku), z nazwami bez przedrostka `GalaxyMcp_` (np. `build.bat`, `README.md`; `GalaxyMcp.cs` bez zmian). Użytkownik przebudowuje ją (`build.bat`), sprawdza `GalaxyMcp.exe --version`, pakuje (`pack_mcpb.bat`) i instaluje nowy `GalaxyMcp.mcpb`.
- Przed dopisaniem czegokolwiek do projektu sprawdź, czy ta treść nie jest już w instrukcji, `Metoda_Generowania.md` albo README serwera. Duplikat, którego nic nie czyta, jest gorszy niż jego brak – rozjeżdża się z resztą.
---
 
## 8. Podsumowanie w wątku
 
Maksymalnie ok. 8 linii, bez nagłówków i bez opisywania kolejnych kroków:
 
1. Jedno zdanie: jakie pliki powstały (Manual) albo co zostanie / zostało zapisane w której galaktyce (Auto), ile zmiennych, ile instancji.
2. Tabela: Zmienna | Typ AVEVA | Tryb (R / RW / W). Zmienne o tym samym typie i trybie połącz w jednym wierszu.
3. Najwyżej 2 punkty „Do sprawdzenia”: przyjęte założenia i pominięte elementy.
W trybie Auto przed zapisem zakończ pytaniem o zgodę na zapis. W trybie Manual po podsumowaniu dopisz krótką instrukcję importu (sekcja 9).
 
Nie powtarzaj informacji o formacie i kodowaniu plików.
 
---
 
## 9. Import CSV w IDE (tryb Manual)
 
Po podsumowaniu dopisz te kroki skrótowo (kilka linii, bez rozwijania):
 
1. Pobierz pliki z wątku albo z Library projektu i zapisz na dysku, nazw nie zmieniaj.
2. **Szablony:** ArchestrA IDE → menu `Galaxy` → `Import` → `Object(s)…` → wskaż plik szablonu (nazwy pozycji różnią się między wersjami IDE). Przy wielu typach importuj w kolejności zależności: najpierw typ zawierany, potem typy, które go zawierają. Szablon nie może być w tym czasie otwarty ani wyewidencjonowany (check out).
3. **Konflikt nazw** – okno `Template Import conflict resolution` pojawia się tylko wtedy, gdy szablon o tej nazwie już jest w galaktyce:
   - `Replace entire template` – szablon pochodzi w całości z generatora; nadpisuje wszystko, także grafikę, skrypty i wizardy dodane w IDE.
   - `Overwrite Wizards, and update attributes and linked content` – aktualizuje atrybuty i treść powiązaną, gdy w IDE dołożono własną zawartość, która ma zostać (wizardy i tak zostaną nadpisane pustymi blokami z pliku).
   - `Skip template (and descendants)` – pomija ten szablon i jego pochodne.
   - `Stop template import` – przerywa cały import.
   Przy pierwszym imporcie okno nie wystąpi. Przy ponownym: gdy szablon nie ma ręcznych dodatków – `Replace entire template`; gdy ma – wyeksportuj go najpierw z IDE (kopia) i wybierz opcję z `Overwrite Wizards…`.
4. **Instancje:** po szablonie, `Galaxy` → `Galaxy Load…` (import CSV w formacie Galaxy Load) → wskaż `Instances_{UDT}.csv`.
5. Sprawdź jeden obiekt: atrybuty, `#IO.Mode` i `InputSource` (dla zmiennych Write – `OutputDest`). Przy generowaniu bez adresów te pola są puste – uzupełnij je w IDE. Na koniec check in i deploy.
 