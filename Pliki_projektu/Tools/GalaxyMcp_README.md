# GalaxyMCP – serwer MCP dla galaktyki AVEVA System Platform (GRAccess)

Tryb **Auto** projektu *SCL → AVEVA*. Serwer wykonuje w galaktyce specyfikację `Spec_<UDT>.json`,
którą generuje `scl_to_aveva.py`. Tworzy szablon z atrybutami i rozszerzeniami I/O, tworzy instancje,
dodaje instancjom ich własne atrybuty i ustawia `InputSource`. Ta sama specyfikacja służy do generowania plików CSV w trybie **Manual**.

```
SCL ──scl_to_aveva.py──► Spec_<UDT>.json ──► CSV (Manual)
                                            └──► GalaxyMCP ──GRAccess──► galaktyka (Auto)
```

> **Wersja 0.2.8** – wtyczka **GalaxyMCP** dla **AVEVA System Platform 2026**. Obsługuje wiele galaktyk (`list_galaxies` /
> `select_galaxy`, listy `GALAXY_ALLOWED` / `GALAXY_WRITABLE`), wszystkie typy UDA z okna IDE, atrybuty dodawane do pojedynczej
> instancji i plan zmian przed zapisem. Każdy zapis (`apply_spec` z `dry_run=false`, `import_csv`, `deploy`) wymaga parametru
> `galaxy` równego aktywnej galaktyce. Nie był testowany w galaktyce: `deploy`.
> Po zmianie konfiguracji lub instalacji nowej paczki nowe narzędzia widać w nowym wątku projektu.

> W projekcie Claude pliki serwera leżą w `Tools/` z przedrostkiem `GalaxyMcp_`: `GalaxyMcp.cs`, `GalaxyMcp_build.bat`,
> `GalaxyMcp_pack_mcpb.bat`, `GalaxyMcp_manifest.json`, `GalaxyMcp_icon.png.b64`, `GalaxyMcp_README.md`, `GalaxyMcp_instrukcja_pdf.py`.
> Po pobraniu na komputer usuń przedrostek z plików pomocniczych (`build.bat`, `pack_mcpb.bat`, `README.md`);
> `GalaxyMcp.cs` zostaje bez zmian, a `GalaxyMcp_manifest.json` → `manifest.json`. Ikona jest zapisana tekstowo:
> `certutil -decode GalaxyMcp_icon.png.b64 icon.png` (bez ikony `pack_mcpb.bat` robi paczkę bez ikony).
> Instrukcja dla użytkowników wtyczki (PDF) powstaje ze skryptu `Tools/GalaxyMcp_instrukcja_pdf.py` – gotowy PDF nie jest trzymany w projekcie.
> Pliki testowe (`test.bat`, `test_write.bat`, `test_requests.jsonl`, `test_write_requests.jsonl`, przykładowa specyfikacja)
> nie są trzymane w projekcie – gdy są potrzebne, poproś o nie w wątku projektu; Claude przygotuje je z tego opisu (sekcja 2).

## Wymagania

- Windows z zainstalowanym AVEVA System Platform (IDE / GRAccess) i dostępem do galaktyki.
- .NET Framework 4.x (jest w każdym Windows 10/11 i Server 2016+).
- Nie są potrzebne: Visual Studio, NuGet, Python ani dostęp do internetu.

## 1. Budowanie

```
build.bat          (32-bit – domyślnie)
build.bat x64      (tylko jeśli GRAccess w Twojej wersji jest 64-bitowy)
```

Wynik: `GalaxyMcp.exe` obok pliku `.cs`. Błędy kompilacji wklej w wątku projektu. Najpewniej będą dotyczyć
wyłącznie sekcji `warstwa GRAccess`.

## 2. Test bez Claude

Podstawowy test nie wymaga żadnych dodatkowych plików:

```
set GALAXY_NAME=NazwaGalaktyki
set GALAXY_READONLY=1
GalaxyMcp.exe --selftest
```

`--selftest` ładuje GRAccess, wypisuje galaktyki z węzła i loguje się do wskazanej (kroki 1–4 w `GalaxyMcp.log`).

Test pełnego protokołu MCP (lista narzędzi, `galaxy_status`, `list_objects`, plan `apply_spec`) polega na podaniu
serwerowi zapytań JSON-RPC na standardowe wejście:

```
GalaxyMcp.exe < test_requests.jsonl > test_responses.jsonl
```

Zestaw zapytań i przykładową specyfikację przygotuje Claude w wątku projektu – pliki nie są
trzymane w projekcie. Test zapisu (tworzenie szablonu i instancji, eksport do CSV, powtórny plan „bez zmian”)
rób wyłącznie na pustej galaktyce testowej, z `GALAXY_READONLY=0` i tą galaktyką w `GALAXY_WRITABLE`.

## 3. Rejestracja w Claude Desktop (wpis ręczny – tylko awaryjnie)

Obowiązująca instalacja to paczka `.mcpb` z sekcji 4. Wpis ręczny stosuj tylko wtedy, gdy rozszerzenia są niedostępne.

1. Skopiuj folder, np. do `C:\Tools\GalaxyMcp\`.
2. W Claude Desktop otwórz: Settings → Developer → Edit Config (plik `claude_desktop_config.json`).
3. Dopisz sekcję i uzupełnij `GALAXY_NAME`:

```json
{
  "mcpServers": {
    "galaxy": {
      "command": "C:\\Tools\\GalaxyMcp\\GalaxyMcp.exe",
      "env": {
        "GALAXY_NAME": "test_mcp",
        "GALAXY_ALLOWED": "test_mcp,test_1",
        "GALAXY_WRITABLE": "test_mcp",
        "GALAXY_READONLY": "0",
        "GALAXY_ALLOW_DEPLOY": "0",
        "GALAXY_NODE": "",
        "GALAXY_USER": "",
        "GALAXY_PASSWORD": "",
        "GRACCESS_DLL": ""
      }
    }
  }
}
```

4. Uruchom ponownie Claude Desktop. W wątku projektu połączonym z tym komputerem pojawią się narzędzia
   serwera `galaxy`. Nigdy nie trzymaj jednocześnie wpisu ręcznego i rozszerzenia `.mcpb`.

### Zmienne środowiskowe

| Zmienna | Znaczenie | Domyślnie |
|---|---|---|
| `GALAXY_NAME` | galaktyka aktywna po starcie (zmiana w trakcie pracy: `select_galaxy`) | brak – trzeba wybrać |
| `GALAXY_ALLOWED` | galaktyki, na które wolno się przełączyć (lista po przecinku) | wszystkie z węzła |
| `GALAXY_WRITABLE` | galaktyki z prawem zapisu (lista po przecinku); pozostałe tylko odczyt | wszystkie dozwolone |
| `GALAXY_NODE` | węzeł GR (Galaxy Repository) | ten komputer |
| `GALAXY_USER`, `GALAXY_PASSWORD` | logowanie, gdy galaktyka ma zabezpieczenia | puste |
| `GALAXY_READONLY` | `1` / `true` = zapis zablokowany we wszystkich galaktykach | `0` |
| `GALAXY_ALLOW_DEPLOY` | `1` / `true` = narzędzie `deploy` aktywne | `0` |
| `GRACCESS_DLL` | pełna ścieżka do `ArchestrA.GRAccess.dll` | `...\ArchestrA\Framework\Bin\` |

Haseł nie trzymaj w pliku konfiguracji na współdzielonym komputerze. Użyj konta z minimalnymi
uprawnieniami albo galaktyki testowej bez zabezpieczeń.

## 4. Instalacja jako rozszerzenie Claude Desktop (.mcpb) – zalecana na kolejnych komputerach

Paczka `.mcpb` to archiwum ZIP z `manifest.json`, `GalaxyMcp.exe`, `GalaxyMcp.exe.config` i `icon.png`.
Claude Desktop instaluje ją przez Install Extension… (sekcja niżej) i sam pokazuje formularz ustawień – bez ręcznej edycji `claude_desktop_config.json`.

**Tworzenie paczki (raz, u osoby, która buduje serwer):**

1. `build.bat` → `GalaxyMcp.exe` + `GalaxyMcp.exe.config`.
2. `pack_mcpb.bat` → `GalaxyMcp.mcpb` (używa `tar.exe` z Windows 10/11). Ten plik rozsyłasz – kolejne komputery nie muszą niczego budować.
   Skrypt najpierw sprawdza `GalaxyMcp.exe --version` i przerywa, jeśli exe ma inną wersję niż `version` w `manifest.json`
   (czyli `build.bat` nie został uruchomiony po zmianie `GalaxyMcp.cs`).

**Instalacja (każdy komputer):**

1. Jeśli serwer był dodany ręcznie: zamknij Claude Desktop (Quit), usuń wpis `"galaxy"` z `claude_desktop_config.json`
   i uruchom aplikację ponownie. Inaczej serwer działałby podwójnie.
2. W Claude Desktop: Settings → Desktop app → przy Extensions **Manage** → **Advanced settings** → sekcja Extension Developer → **Install Extension…** i wskaż `GalaxyMcp.mcpb`. (Pliku `.mcpb` nie dodaje się w Settings → Plugins – tam trafiają paczki pluginów z `.claude-plugin/plugin.json`.)
3. Wypełnij ustawienia:

| Pole | Zmienna | Uwagi |
|---|---|---|
| Węzeł GR | `GALAXY_NODE` | puste = ten komputer; na stacji bez GR wpisz nazwę komputera z GR |
| Galaktyka na start | `GALAXY_NAME` | np. `test_mcp` |
| Dozwolone galaktyki | `GALAXY_ALLOWED` | lista po przecinku |
| Galaktyki z prawem zapisu | `GALAXY_WRITABLE` | tylko galaktyki testowe |
| Tylko odczyt | `GALAXY_READONLY` | **domyślnie zaznaczone** – odznacz po ustawieniu listy zapisu |
| Zezwól na deploy | `GALAXY_ALLOW_DEPLOY` | domyślnie wyłączone |
| Użytkownik / hasło | `GALAXY_USER` / `GALAXY_PASSWORD` | tylko galaktyki z zabezpieczeniami; hasło jest polem poufnym |
| Ścieżka GRAccess | `GRACCESS_DLL` | tylko gdy biblioteka nie zostanie znaleziona |

4. Otwórz nowy wątek w projekcie (połączony z tym komputerem) i sprawdź `galaxy_status`.

**Uwagi:**

- Claude Desktop rozpakowuje rozszerzenie do własnego folderu `Claude Extensions\local.mcpb.<autor>.galaxy\`.
  Tam powstaje `GalaxyMcp.log`; tam też można uruchomić `GalaxyMcp.exe --selftest`. Położenie folderu zależy od wersji
  Claude Desktop (np. `%APPDATA%\Claude\` albo folder pakietu w `%LOCALAPPDATA%\Packages\`). Plik znajdzie polecenie PowerShell:
  `Get-ChildItem $env:LOCALAPPDATA, $env:APPDATA -Recurse -Filter GalaxyMcp.log -ErrorAction SilentlyContinue | Select-Object FullName`.
- Securden widzi exe w folderze rozszerzeń, a nie w `C:\Tools\GalaxyMcp\` – reguła IT powinna dotyczyć skrótu (hash) pliku albo podpisu.
- Zmiana ustawień: Settings → Desktop app → Extensions (Manage) → GalaxyMCP. Nowe wartości działają po ponownym uruchomieniu serwera:
  wyłącz przełącznik Enabled, odczekaj kilka sekund (serwer sam się wylogowuje i kończy) i włącz Enabled. Restart komputera
  ani zamykanie procesów w Menedżerze zadań nie są potrzebne. Sprawdzenie: `galaxy_status`.
- Nowa wersja serwera = nowy `build.bat` + `pack_mcpb.bat` + podniesienie `version` w `manifest.json`; instalacja nadpisuje poprzednią.
- W firmowym koncie administrator może ograniczyć instalowanie własnych rozszerzeń – wtedy potrzebna jest jego zgoda.
- Puste pola docierają do serwera jako pusty tekst (manifest ma wartości domyślne), a pola typu przełącznik jako `true`/`false`.
  Serwer akceptuje oba zapisy i ignoruje niepodstawione `${user_config.*}`.

## Narzędzia

| Narzędzie | Co robi | Zapisuje? |
|---|---|---|
| `galaxy_status` | aktywna galaktyka, prawo zapisu, listy dozwolonych, test połączenia | nie |
| `list_galaxies` | galaktyki na węźle z oznaczeniem: aktywna / zapis / tylko odczyt / niedozwolona | nie |
| `select_galaxy` | przełącza aktywną galaktykę (tylko z `GALAXY_ALLOWED`) | nie (zmienia tylko sesję serwera) |
| `list_objects` | szablony/instancje wg wzorca (`%` = dowolny ciąg) | nie |
| `get_object` | właściwości i atrybuty obiektu (np. filtr `InputSource`) | nie |
| `apply_spec` | plan (`dry_run=true`, domyślnie) albo zapis specyfikacji | tylko przy `dry_run=false` |
| `import_csv` | import CSV z trybu Manual: szablon (`ImportTemplateFromText`) lub instancje (`GRLoad`); `mode` ignore/update/replace/terminate | tak |
| `export_csv` | eksport szablonów (`ExportTemplateToText`) lub instancji (`GRDump`) do CSV, zwraca treść | nie |
| `deploy` | wdrożenie instancji | tak, gdy `GALAXY_ALLOW_DEPLOY=1` |

### Bezpieczeństwo przy wielu galaktykach

- Każdy zapis (`apply_spec` z `dry_run=false`, `import_csv`, `deploy`) sprawdza, czy aktywna galaktyka jest na liście
  `GALAXY_WRITABLE` (i czy nie ustawiono `GALAXY_READONLY=1`).
- Parametr `galaxy` jest przy zapisie obowiązkowy i musi być równy aktywnej galaktyce – inaczej serwer odmawia i nic nie zapisuje.
  Agent podaje w nim nazwę potwierdzoną przez użytkownika.
- Plan i raport zapisu zawsze zaczynają się od nazwy galaktyki.

### Zasady `apply_spec`

- Nazwy szablonu, instancji i atrybutów nie mają limitu długości po stronie serwera; sprawdzane są tylko
  znaki (`[A-Za-z_][A-Za-z0-9_]*`, szablon z `$`). Jeśli galaktyka nie przyjmie długiej nazwy, błąd zgłosi GRAccess
  (`CreateTemplate` / `CreateInstance` / `AddUDA`) i trafi do raportu zapisu.
- Typy atrybutów (wszystkie z listy „Data type” w oknie UDA): `MxBoolean`, `MxInteger`, `MxFloat`, `MxDouble`,
  `MxString`, `MxTime`, `MxElapsedTime`, `MxInternationalizedString`, `MxBigString`. Kierunek `io`: `Input` (Read) albo
  `InputOutput` (Read/Write). Atrybuty `Output` (Write) serwer pomija: plan i raport wypisują je w linii
  „POMINIĘTE atrybuty Write”, a pozostałe atrybuty specyfikacji są zapisywane. Atrybuty Write dodaje się w IDE albo
  importem plików CSV (tryb Manual).
- Wartość początkowa (`default`, w IDE „Initial value”): Boolean `true`/`false`/`1`/`0`, Integer liczba całkowita, Float/Double
  liczba z kropką albo przecinkiem – sprawdzane już przy odczycie specyfikacji (zła wartość = specyfikacja odrzucona, nic nie zapisano).
  Teksty i czas (`MxTime`, `MxElapsedTime`, np. `00:00:05.0000000`) idą jako tekst – konwersję robi GRAccess, a błąd jest tylko
  ostrzeżeniem w raporcie.
- Szablon nie istnieje → zostaje utworzony z `$UserDefined`, z atrybutami UDA (kategoria
  `MxCategoryWriteable_USC_Lockable`, `MxSecurityOperate`) oraz rozszerzeniem `inputextension`
  albo `inputoutputextension`.
- Szablon istnieje → dopisywane są **tylko brakujące** atrybuty. Nic nie jest usuwane ani zmieniane.
  Lista `template.attributes` może być pusta, gdy specyfikacja dotyczy tylko instancji istniejącego szablonu.
- Instancja nie istnieje → zostaje utworzona z szablonu i dostaje `InputSource` ze specyfikacji.
- Instancja istnieje → zmieniane są tylko `InputSource` o innej wartości. Instancja pochodząca z innego
  szablonu jest pomijana z błędem.
- **Atrybuty instancji**: `instances[].attributes` ma ten sam format co `template.attributes`. Brakujące atrybuty
  są dodawane tylko do tej instancji (UDA + rozszerzenie I/O + wartość początkowa + opis), przed ustawieniem `InputSource`,
  więc w `input_source` można podać adres także dla nich. Nazwa nie może powtarzać atrybutu szablonu. Przykład:

```json
{ "spec_version": 1, "source": "watek",
  "template": { "name": "$UDT_zawor", "base": "$UserDefined", "attributes": [] },
  "instances": [ { "name": "Instancja_test", "security_group": "Default",
                   "attributes": [ { "name": "A_test", "type": "MxDouble", "default": "50", "io": "InputOutput",
                                     "description": "" } ],
                   "input_source": {} } ] }
```

- Każdy obiekt jest pobierany do edycji (CheckOut), zapisywany (Save) i zwracany (CheckIn) z komentarzem.
  Przy błędzie pobranie jest cofane (UndoCheckOut).
- Po zapisie serwer zwalnia zapisane obiekty ze swojej sesji GRAccess (`Unload`), a po każdym narzędziu zapisującym
  (`apply_spec` z `dry_run=false`, `import_csv`, `deploy`) wylogowuje się z galaktyki (w logu: „sesja zamknięta po …”).
  Dzięki temu obiekt utworzony lub zmieniony przez wtyczkę można od razu pobrać, zmienić i zwrócić (Check-in) w ArchestrA
  IDE przy włączonej wtyczce. Następne wywołanie loguje się ponownie (ok. 10–15 s).
- Błędy przy ustawianiu opisu, wartości domyślnej, obszaru (Area), grupy bezpieczeństwa (SecurityGroup)
  i toolsetu są tylko ostrzeżeniami. Wszystkie zapisy trafiają do `GalaxyMcp.log` (poziom `ZAPIS`).
- `import_csv`: GRAccess zgłasza sukces całej operacji, nawet gdy pojedynczy obiekt się nie zaimportował. Serwer liczy
  więc wynik także z komunikatów dla obiektów: gdy którykolwiek ma błąd, odpowiedź zaczyna się od `BŁĄD:`, linia `Wynik:`
  pokazuje `BŁĄD (błędy dla obiektów: N)`, a każdy komunikat z błędem trafia do `GalaxyMcp.log` (poziom `ERROR`).
- Atrybut `MxTime` bez wartości początkowej dostaje od GRAccess czas utworzenia szablonu (np. `11/23/2026 3:07:15 PM`).
  Przy atrybutach I/O wartość i tak przychodzi ze sterownika.
- Zmiana kierunku I/O atrybutu w IDE (np. Read/Write → Write) usuwa adresy tego atrybutu w instancjach
  (`OutputDest = ---`). Po takiej zmianie wczytaj ponownie `Instances_<UDT>.csv` (Galaxy Load albo `import_csv`).
- Przed zapisem zamknij w IDE edytory obiektów, których dotyczy zmiana, bo IDE i GRAccess
  korzystają z tych samych blokad obiektów.

## Diagnostyka

- `GalaxyMcp.exe --version` – wypisuje wersję i kończy działanie.
- Zakończenie pracy: serwer wychodzi, gdy Claude Desktop zamknie stdin albo gdy zniknie proces, który go
  uruchomił (sprawdzenie co 2 s) – czyli po wyłączeniu wtyczki (Enabled) lub zamknięciu aplikacji. Wylogowanie z galaktyki
  ma 5 s; potem proces kończy się bez niego. W `GalaxyMcp.log`: „nadzór rodzica: …” przy starcie i „GalaxyMCP stop: …”.
- `build.bat` odmawia budowania tylko wtedy, gdy działa `GalaxyMcp.exe` z tego samego folderu. Kopia z folderu rozszerzeń
  Claude (wtyczka `.mcpb`) nie blokuje budowania w innym folderze.
- Pierwsze wywołanie po starcie trwa ok. 30 s (`QueryGalaxies` i logowanie do galaktyki); kolejne odczyty są szybkie.
  Pierwsze wywołanie po zapisie trwa dłużej (ponowne logowanie).
- `get_object` pokazuje `CheckoutStatus`, `checkedOutBy` i `EditStatus`. Gdy Check-in w IDE się nie udaje, sprawdź tam
  stan obiektu: `checkedOutToMe` lub `editedByYouInOtherSession` po zapisie przez wtyczkę oznacza, że pobranie nie zostało
  cofnięte (w `GalaxyMcp.log` jest wtedy `ERROR … nie cofnięto pobrania`) – cofnij je w IDE (Undo Check-Out).
- Claude Desktop może uruchomić dwa procesy serwera naraz (dwa wpisy „start” i „stop” w logu o tym samym czasie).
  Każdy działa samodzielnie; nie jest to błąd wtyczki.
- `GRDump` (`export_csv` z `kind=instances`) zapisuje liczby z separatorem dziesiętnym z ustawień regionalnych Windows
  (np. `"0,0"`), a eksport szablonu i pliki generatora używają kropki. Przy porównywaniu plików trzeba to uwzględnić.
- `GalaxyMcp.exe --selftest` – ładowanie GRAccess, lista galaktyk, logowanie (kroki 1–4 w `GalaxyMcp.log`).
- `GalaxyMcp.exe --dump-api` – zapisuje pełny opis API biblioteki GRAccess do `GRAccess_API.txt`
  (interfejsy, metody, właściwości, wartości enumeracji). Przydatne przy błędzie „brak metody/właściwości”
  albo „W GRAccess brak wartości MxDataType.…” (nazwa typu w tej wersji GRAccess).
- Securden: serwer i każde jego przebudowanie wymagają zgody (najlepiej reguła dla folderu `C:\Tools\GalaxyMcp\`).
- GRAccess jest wywoływany przez interfejsy interop (wiązanie wczesne). Późne wiązanie (IDispatch) nie działa
  (`TYPE_E_LIBNOTREGISTERED`), bo biblioteka typów GRAccess nie jest zarejestrowana.

## Wywołania GRAccess do sprawdzenia przy pierwszym uruchomieniu

Serwer ładuje GRAccess dopiero w czasie działania i wywołuje go przez interfejsy biblioteki (refleksja). Kompilacja
nie zależy więc od wersji System Platform. Jeśli któraś nazwa w Twojej wersji jest inna, zobaczysz
czytelny błąd z tą nazwą. Poprawka dotyczy wtedy tylko sekcji `warstwa GRAccess`.

| Element | Użyta nazwa | Pewność |
|---|---|---|
| aplikacja | `GRAccessAppClass.QueryGalaxies(node)` | wysoka |
| logowanie | `IGalaxy.Login(user, pwd)`, `CommandResult.Successful/Text/CustomMessage` | wysoka |
| wyszukiwanie | `QueryObjectsByName(EgObjectIsTemplateOrInstance, ref string[])` | wysoka |
| lista | `QueryObjects(..., EConditionType.namedLike, wzorzec, EMatch.MatchCondition)` | potwierdzone |
| tworzenie | `ITemplate.CreateTemplate(name, true)`, `CreateInstance(name, true)` | wysoka |
| edycja | `CheckOut()`, `Save()`, `CheckIn(komentarz)`, `UndoCheckOut()` | wysoka |
| atrybut UDA | `AddUDA(name, MxDataType, MxAttributeCategory, MxSecurityClassification, false, 0)` – na szablonie potwierdzone; na instancji do sprawdzenia | wysoka |
| typy UDA Double / tekst | `MxDataType.MxDouble`, `MxInternationalizedString`, `MxBigString` | średnia (nazwy do potwierdzenia w `GRAccess_API.txt`) |
| rozszerzenie I/O | `AddExtensionPrimitive("inputextension" / "inputoutputextension", name, false)` | potwierdzone |
| wartości | `ConfigurableAttributes[name].SetValue(MxValueClass)` + `PutBoolean/PutInteger/PutFloat/PutDouble/PutString` | średnia (`PutDouble` do potwierdzenia) |
| deploy | `IInstance.Deploy(deployChanges, dontSkipIfCurrentlyUndeployed, doDeployOnScan, doForceOffScan, dontCascade, false)` | wysoka (zgodne z API) |
| import/eksport CSV | `IGalaxy.ImportTemplateFromText(plik, GRLoadMode)`, `GRLoad(plik, GRLoadMode)`, `ExportTemplateToText(string[], plik)`, `GRDump(string[], plik)` | wysoka (zgodne z API) |
| referencje | `InputSource` typu `MxReferenceType`: `value.GetMxReference()` → `FullReferenceString` → `PutMxReference` (awaryjnie `PutString`) | potwierdzone |
| opis / grupa | `IAttribute.Description` (właściwość), `ConfigurableAttributes.SecurityGroup` | wysoka (zgodne z API) |

Nazwy zweryfikowano z `GRAccess_API.txt` (ArchestrA.GRAccess 2.0.0.0). `IgObject` nie ma właściwości `SecurityGroup` –
ustawia się ją przez `ConfigurableAttributes`.

## Scenariusz pierwszego testu

1. Galaktyka testowa + kopia zapasowa (backup `.cab`).
2. `GALAXY_READONLY=1` → w Claude: „sprawdź status galaktyki”, potem plan dla specyfikacji.
3. `GALAXY_READONLY=0` → zapis samego szablonu (`scope=template`) i sprawdzenie w IDE:
   typy, kierunek I/O, opisy.
4. Zapis instancji (`scope=instances`) i sprawdzenie `InputSource` w IDE.
5. Porównanie z wynikiem importu CSV tego samego UDT (tryb Manual). Oba tryby powinny dać to samo.
6. Instancja z własnym atrybutem: `Instancja_test` z `$UDT_zawor` + `A_test` MxDouble = 50, InputOutput –
   sprawdzenie w IDE typu, Initial value i Read/Write; dodatkowo po jednym atrybucie każdego nowego typu.
