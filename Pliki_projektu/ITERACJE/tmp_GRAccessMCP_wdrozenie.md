# Wdrożenie GRAccess-MCP (gotowe rozwiązanie) – stan prac

> **2026-09-17 ZMIANA DECYZJI:** GRAccess-MCP WSTRZYMANY. Wracamy do własnego serwera `tmp_GalaxyMcp*` (C#, .exe, stdio).
> Powód: u kolegi działa analogiczny własny serwer `MCPGalaxy.exe` (C#, Visual Studio) uruchamiany wprost przez
> Claude Desktop (status Running, obok serwera `aveva-historian`); brak do niego dostępu, więc budujemy własny.
> Stan GalaxyMcp: krok 1 = rozpakować `GalaxyMcp.zip` do `C:\Tools\GalaxyMcp` (build.bat bezpośrednio w folderze,
> przed rozpakowaniem: Właściwości → Odblokuj), krok 2 = `build.bat` i wklejenie wyniku. Dalej wg `tmp_GalaxyMcp_README.md`.
> 2026-09-17: `build.bat` OK – kod skompilował się bez błędów: `C:\Tools\GalaxyMcp\GalaxyMcp.exe (x86)`.
> 2026-09-17 test.bat (galaktyka `test_1`, węzeł `MARCELK-PRA3`): protokół MCP OK (initialize, tools/list),
> ale proces kończy się BEZ komunikatu przy łączeniu z GRAccess (brak odpowiedzi na id 3–5, selftest bez OK/BŁĄD).
> `GRAccess: (szukam w GAC)` – DLL nie ma w `...\ArchestrA\Framework\Bin\`.
> Wersja 0.1.1: logowanie kroków 1–4 (ładowanie DLL, COM, QueryGalaxies, Login), UnhandledException → log,
> więcej ścieżek DLL, build.bat tworzy `GalaxyMcp.exe.config` (useLegacyV2RuntimeActivationPolicy).
> Następny krok: przebudować, `where /r` dla ArchestrA.GRAccess.dll, `GalaxyMcp.exe --selftest`, treść `GalaxyMcp.log`,
> ew. Podgląd zdarzeń → Dziennik aplikacji (.NET Runtime / Application Error).
> 2026-09-17 selftest 0.1.1: DLL znaleziony (`C:\Program Files (x86)\Common Files\ArchestrA\ArchestrA.GRAccess.dll`,
> ładowany z GAC, ArchestrA.GRAccess 2.0.0.0, CLR v2.0.50727), proces 32-bit STA, krok 1 i 2 OK,
> proces znika przy kroku 3 `QueryGalaxies(MARCELK-PRA3)` – jednocześnie okno Securden „Aplikacja GalaxyMcp.exe
> nie została rozpoznana”. Wniosek: przyczyną jest Securden (kod nie był winny). Przepisanie na wiązanie wczesne
> (bez dynamic/IDispatch) WSTRZYMANE – wrócić tylko, jeśli po zgodzie IT proces nadal zniknie na kroku 3.
> Następny krok: „Poproś o dostęp” + prośba do IT o regułę dla FOLDERU `C:\Tools\GalaxyMcp\` (każde przebudowanie
> zmienia skrót pliku .exe). Plan B przy odmowie: serwer MCP w PowerShell (podpisany powershell.exe 32-bit z SysWOW64).
> 2026-09-17 po zgodzie Securden: krok 3 OK (QueryGalaxies ~4 s), potem `COMException 0x8002801D TYPE_E_LIBNOTREGISTERED`
> w `InvokeDispMethod` (późne wiązanie IDispatch na zwróconych obiektach COM). Wniosek: biblioteka typów GRAccess
> niezarejestrowana → trzeba wiązania wczesnego. Wersja 0.1.2: klasa `Com` (MethodInfo/PropertyInfo z interfejsów
> interop, QueryInterface przez IsInstanceOfType), bez `dynamic`; `--dump-api` → `GRAccess_API.txt`.
> Uwaga: Securden wymaga zgody po KAŻDYM przebudowaniu (inny skrót .exe), jeśli IT nie dało reguły na folder.
> Następny krok: build.bat, `GalaxyMcp.exe --dump-api`, `GalaxyMcp.exe --selftest` → wynik + GRAccess_API.txt do czatu.
> **2026-09-17 11:18 SUKCES 0.1.2:** `--dump-api` zapisał `GRAccess_API.txt`; `--selftest`: QueryGalaxies OK (~7 s),
> galaktyki na MARCELK-PRA3: MA_Galaxy, Scheme, test, test_1, test_16IX; obiekt galaktyki implementuje
> IGalaxy…IGalaxy17 (nowa wersja SP); Login do test_1 OK (~9 s). Wiązanie wczesne działa.
> Następne kroki: (1) przesłać `GRAccess_API.txt` do weryfikacji nazw (QueryObjects, AddUDA, AddExtensionPrimitive,
> MxValue, Deploy); (2) `test.bat` (tylko odczyt: list_objects + plan dry_run Mixera) → `test_responses.jsonl`;
> (3) rejestracja w Claude Desktop z GALAXY_READONLY=1.
> 2026-09-17 test.bat (0.1.2, READONLY): galaxy_status OK; list_objects: $t_Mixer, $t_UDT_Mixer, $t_UDT_Mixer_Advanced;
> apply_spec dry_run Mixera: szablon istnieje (29 atrybutów, bez zmian), Mixer_01/02 istnieją z $t_UDT_Mixer (pominięte),
> Mixer_03 do utworzenia. GRAccess_API.txt: nazwy zgodne; IgObject NIE ma SecurityGroup (jest w ConfigurableAttributes),
> IAttribute ma właściwość Description; IGalaxy ma ImportTemplateFromText/GRLoad/ExportTemplateToText/GRDump (GRLoadMode).
> Wersja 0.1.3: narzędzia import_csv (CSV z trybu Manual) i export_csv; InputSource przez IMxReference (fallback PutString);
> opis przez IAttribute.Description; SecurityGroup przez ConfigurableAttributes. test_requests: + get_object Mixer_01, export_csv.
> Następny krok: build.bat (zgoda Securden), test.bat → test_responses.jsonl; potem Claude Desktop (READONLY=1).
> 2026-09-17 11:29 test 0.1.3 OK: wszystkie narzędzia widoczne; get_object czyta InputSource (Mixer_01: płaskie adresy
> PLC_01.DB_Mixer_01.Cmd_Start…, CheckoutStatus=checkedOutToMe – zwolnić w IDE przed zapisem); export_csv:
> ExportTemplateToText OK („Dumped… Export of Template(s) completed”), ale plik nie powstał pod podaną nazwą –
> GRAccess sam nazywa plik. Wersja 0.1.4: eksport do osobnego folderu %TEMP%\GalaxyMcp_export_<stamp>\ + odczyt wszystkich plików.
> Następny krok: build.bat, rejestracja w Claude Desktop (READONLY=1), test narzędzi z czatu.
> 2026-09-17 11:34 test 0.1.4 na NOWEJ PUSTEJ galaktyce `test_mcp`: plan = utworzyć szablon (29 atr.: 10 IO, 19 I)
> + Mixer_01..03; ExportTemplateToText traktuje 2. parametr jako FOLDER (utworzył katalog templates.csv\$t_UDT_Mixer_Advanced.csv,
> 0 znaków, bo szablonu brak). Wersja 0.1.5: eksport szablonu do folderu; nowy test_write.bat (+ test_write_requests.jsonl):
> zapis szablonu → get_object → export_csv → zapis instancji → get_object Mixer_01 → plan (oczekiwane „bez zmian”).
> Następny krok: build.bat, `set GALAXY_NAME=test_mcp`, test_write.bat → test_write_responses.jsonl + GalaxyMcp.log.
> **2026-09-17 11:38 ZAPIS POTWIERDZONY (0.1.5, test_mcp):** apply_spec utworzył $t_UDT_Mixer_Advanced (29 UDA + I/O, opisy PL OK)
> i Mixer_01..03 z 29 InputSource każdy (adresy strukturalne i tablicowe `…Temp_Bearings[1]` zapisane poprawnie, SetValue OK);
> obiekty zwrócone (notCheckedOut); ponowny plan = same „bez zmian” (idempotencja). Czas całości ~24 s.
> Porównanie eksportu IDE (ExportTemplateToText) z CSV generatora: nagłówek, opcje, deklaracja, 29 UDA, typy, #IO.Mode,
> Deadband, InvertValue, opisy – IDENTYCZNE. Różnice tylko w wartościach domyślnych IDE: MxElapsedTime `00:00:00.0000000`,
> MxTime = czas utworzenia, InputSource `---Auto---` (u nas puste) oraz wiersze runtime WriteStatus/WriteValue (celowo pomijane).
> Następny krok: rejestracja w Claude Desktop (galaxy, GALAXY_NAME=test_mcp, READONLY=1) i test z czatu; potem deploy (nietestowany).
> **2026-09-17 TRYB AUTO DZIAŁA Z CZATU:** Claude Desktop (wersja ze Sklepu MS – konfiguracja w
> `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`, edytować przy
> zamkniętej aplikacji, potem pełny restart) → serwer `galaxy` Running. W sesji Cowork narzędzia:
> `mcp__remote-devices__galaxy__{galaxy_status,list_objects,get_object,apply_spec,import_csv,export_csv,deploy}`.
> Sprawdzone z czatu: galaxy_status (test_mcp, READONLY), list_objects (Mixer_01..03), apply_spec z `spec` przekazanym
> w treści wywołania (spec wygenerowany w chmurze) → plan „bez zmian”.
> Do zrobienia: fragment instrukcji projektu (tryb Manual/Auto), test import_csv i deploy, reguła Securden na folder.

Decyzja 2026-09-16: tryb Auto przez gotowy serwer społecznościowy **AL1T0/GRAcces-MCP-Server**
(https://github.com/AL1T0/GRAcces-MCP-Server, MIT, proof of concept). Własny serwer `tmp_GalaxyMcp*` zostaje jako zapasowy.

## Ograniczenia GRAccess-MCP (wg README i server.py)
- Narzędzia: list_galaxies(), connect_galaxy(galaxy_name), disconnect_galaxy(), query_objects(instances_only=True),
  get_attribute(tagname, attribute), set_attribute(tagname, attribute, value), list_attributes(tagname),
  get_object_info(tagname), list_deployment_view(), create_instance(template_name, instance_name, host=""),
  deploy_instance(tagname, host="").
- NIE tworzy szablonów ani UDA z I/O → szablon nadal importem `$t_<UDT>.csv` w IDE.
- Instancje: create_instance + set_attribute(<Attr>.InputSource) wg `Spec_<UDT>.json` (każdy zapis = osobny checkout/checkin).
- Brak dry-run, trybu tylko-do-odczytu i blokady deploy → agent pokazuje listę operacji i czeka na zgodę.
- `server.py` kończy się `mcp.run("sse")` → ZAWSZE SSE (port 8000, zmienna FASTMCP_PORT), bez uwierzytelniania.
  Claude Desktop (stdio) wymaga pośrednika `mcp-remote` (Node.js). Nie wystawiać portu na sieć.
- `start_mcp_server.ps1` ustawia: SYSTEMPLATFORM=nazwa komputera, GRACCESS_GALAXY="Default" (ZMIENIĆ),
  GRACCESS_USER="DefaultUser", GRACCESS_PASSWORD="BLANK", FASTMCP_PORT=8000; uruchamia python z `.venv-grserver`.
- Kod pisany pod `from mcp.server.fastmcp import FastMCP` (SDK mcp 1.x). Zainstalowało się mcp 2.2.0 –
  jeśli start zgłosi ImportError/AttributeError: `pip install --only-binary=:all: "mcp<2"`.
- IDE zamknięte podczas zapisów (wspólne blokady obiektów).

## Pułapki środowiska użytkownika
- Securden blokuje nieznane .exe (uv.exe, rustup-init.exe) → używać `python.exe -m pip`, zawsze `--only-binary=:all:`
  (brak części paczek win32 w najnowszych wersjach → pip próbował kompilować w Rust).
- Skrypty .ps1: w razie blokady `powershell -ExecutionPolicy Bypass -File .\start_mcp_server.ps1`.

## PUNKT WZNOWIENIA (hasło użytkownika: „kontynuuj”)
Ostatni wykonany krok: instalacja bibliotek (`Successfully installed ...`, zrzut ekranu 2026-09-16).
Instrukcja kroków 1–5 poniżej została podana, ale NIE była jeszcze wykonana. Po „kontynuuj” zacząć od kroku 1
i poprosić o wyniki kroków 1, 3 i 5:
1. Sprawdzenie 32-bit venv.
2. `start_mcp_server.ps1`: GRACCESS_GALAXY = nazwa galaktyki testowej (SYSTEMPLATFORM/USER/PASSWORD tylko w razie potrzeby).
3. `powershell -ExecutionPolicy Bypass -File .\start_mcp_server.ps1` → Uvicorn na 127.0.0.1:8000; przy błędzie FastMCP/ImportError/run:
   `.venv-grserver\Scripts\python.exe -m pip install --only-binary=:all: "mcp<2"`.
4. Przeglądarka `http://127.0.0.1:8000/sse` → `event: endpoint`.
5. `node -v` (potrzebny do mcp-remote; możliwa blokada Securden).

## Stan na 2026-09-16 (komputer użytkownika)
- [x] Repozytorium w `C:\Tools\graccess-mcp` (pliki bezpośrednio w tym folderze).
- [x] Python 3.13.0 32-bit: `C:\Users\MATEUSZA\AppData\Local\Programs\Python\Python313-32\python.exe` (`py -3.13-32`).
- [x] `.venv-grserver` (py -m venv) + `pip install --only-binary=:all: -r requirements-server.txt` – OK
      (mcp 2.2.0, pythonnet 3.1.0, pywin32 312, pydantic 2.13.5, uvicorn 0.53.0).
- [ ] Sprawdzenie 32-bit venv.
- [ ] Edycja `start_mcp_server.ps1` (GRACCESS_GALAXY) i start → Uvicorn na 127.0.0.1:8000; test w przeglądarce `http://127.0.0.1:8000/sse` (event: endpoint).
- [ ] Node.js (`node -v`) + Claude Desktop config: `"GRAccess": {"command": "npx", "args": ["-y", "mcp-remote", "http://127.0.0.1:8000/sse"]}`
      (serwer musi być uruchomiony ręcznie przed Claude Desktop). Możliwa blokada Securden dla node/npx.
- [ ] Rozmowa powiązana z tym komputerem; test „pokaż galaktyki”.
- [ ] Galaktyka testowa + backup; szablon z CSV; instancje Mixer_01..03 przez MCP; weryfikacja InputSource w IDE.

## 2026-09-17 – wersja 0.2.0: wiele galaktyk (POTWIERDZONA)
- Nowe narzędzia `list_galaxies`, `select_galaxy` (Logout z bieżącej → Login do wskazanej, bez restartu).
- `GALAXY_NAME` = galaktyka startowa (opcjonalna), `GALAXY_ALLOWED` = dozwolone do przełączania (puste = wszystkie),
  `GALAXY_WRITABLE` = z prawem zapisu (puste = wszystkie dozwolone), `GALAXY_READONLY=1` blokuje zapis wszędzie.
- Zapis (`apply_spec` dry_run=false, `import_csv`, `deploy`) → `RequireWrite`: prawo zapisu aktywnej galaktyki
  + opcjonalny parametr `galaxy` musi być równy aktywnej (agent podaje nazwę potwierdzoną przez użytkownika).
- Proponowana konfiguracja: `GALAXY_NAME=test_mcp`, `GALAXY_ALLOWED=test_mcp,test_1,MA_Galaxy`, `GALAXY_WRITABLE=test_mcp`, `GALAXY_READONLY=0`.
- Uwaga wdrożeniowa: po zmianie `env` i pełnym restarcie Claude Desktop nowe narzędzia widać dopiero w NOWEJ rozmowie
  (w starej `RefreshMcpTools` nie pomaga); pojawiły się też po ponownym połączeniu serwera remote-devices.
- **Test z czatu 2026-09-17 – WSZYSTKO OK** (konfiguracja: NAME=test_mcp, ALLOWED=test_mcp,test_1,MA_Galaxy, WRITABLE=test_mcp,
  READONLY=0, ALLOW_DEPLOY=0):
  1. `galaxy_status`: aktywna test_mcp, zapis DOZWOLONY, listy zgodne z konfiguracją, połączenie OK.
  2. `list_galaxies` (6 na MARCELK-PRA3): MA_Galaxy i test_1 [tylko odczyt], Scheme, test, test_16IX [niedozwolona],
     test_mcp [AKTYWNA, zapis].
  3. `select_galaxy test_1` → „Przełączono: test_mcp → test_1”, zapis zablokowany (spoza GALAXY_WRITABLE).
     `list_objects template $t_%` w test_1: $t_Mixer, $t_UDT_Mixer, $t_UDT_Mixer_Advanced.
  4. `select_galaxy Scheme` → odrzucone („nie jest na liście GALAXY_ALLOWED”).
  5. `apply_spec dry_run=false galaxy=test_1` (celowo niepoprawny spec jako zabezpieczenie) → odrzucone:
     „zapis do galaktyki 'test_1' jest zablokowany (galaktyka spoza GALAXY_WRITABLE)”. Nic nie zapisano.
  6. `apply_spec dry_run=false galaxy=test_mcp` przy aktywnej test_1 → odrzucone: „podano galaktykę 'test_mcp',
     a aktywna jest 'test_1'. Nic nie zapisano”.
  7. `select_galaxy MA_Galaxy` → OK, zapis zablokowany. `select_galaxy TEST_MCP` (inna wielkość liter) → „MA_Galaxy → test_mcp”,
     zapis DOZWOLONY; `list_objects instance Mixer%` → Mixer_01..03 z $t_UDT_Mixer_Advanced.
  Przełączenie trwa kilka sekund; RequireWrite działa przed walidacją specyfikacji.
- Do zrobienia: podmiana sekcji 6 w ustawieniach projektu na wersję z `tmp_Instrukcja_projektu.md`; test `import_csv` i `deploy`;
  reguła Securden na folder `C:\Tools\GalaxyMcp\`.

## 2026-09-17 – porządki w projekcie: folder `Tools/`
- Pliki potrzebne do działania przeniesione z `ITERACJE/tmp_*` do `Tools/` bez przedrostka `tmp_`: `scl_to_aveva.py`, `Metoda_Generowania.md`,
  `GalaxyMcp.cs`, `GalaxyMcp_README.md`, `GalaxyMcp_build.bat`, `GalaxyMcp_claude_desktop_config.example.json`, `GalaxyMcp_test.bat`,
  `GalaxyMcp_test_requests.jsonl`, `GalaxyMcp_test_write.bat`, `GalaxyMcp_test_write_requests.jsonl`. Stare kopie usunięte.
- W `ITERACJE/` zostały notatki: ten plik i `tmp_Instrukcja_projektu.md`. Starsze wpisy powyżej używają dawnych nazw `tmp_*`.
- Zmiany treści: `generator` w specyfikacji = `scl_to_aveva.py`; w `GalaxyMcp.cs` tylko teksty opisów (nazwa skryptu) – bez zmiany działania,
  przebudowa niepotrzebna (wejdzie przy następnej wersji). `Metoda_Generowania.md`: sekcja trybu Auto zaktualizowana do 0.2.0.
- Instrukcja projektu: ścieżki `Tools/` w sekcjach 0, 4, 5 i 7 – do wklejenia w ustawieniach projektu.

## 2026-09-17 – wersja 0.2.1: rozszerzenie Claude Desktop (.mcpb) – do przetestowania
- Nowe pliki: `Tools/GalaxyMcp_manifest.json` (MCPB manifest_version 0.3, serwer typu binary, 9 narzędzi, `user_config`),
  `Tools/GalaxyMcp_pack_mcpb.bat` (pakowanie `tar --format=zip` → `GalaxyMcp.mcpb`), `icon.png` (tylko w paczce ZIP).
- Manifest sprawdzony schematami MCPB 0.3 i latest (repo modelcontextprotocol/mcpb) – bez błędów. Podstawianie zmiennych
  sprawdzone kodem z repo (`getMcpConfigForManifest`): pola z domyślnymi → pusty tekst, przełączniki → `true`/`false`;
  pole bez domyślnej wartości zostałoby jako tekst `${user_config.x}`.
- Serwer 0.2.1: `Env` ignoruje niepodstawione `${...}`; `GALAXY_READONLY` / `GALAXY_ALLOW_DEPLOY` przyjmują 1/true/yes/tak.
  Brak kompilatora w chmurze – zmiana sprawdzona tylko przeglądem kodu; wymaga `build.bat` (zgoda Securden).
- Domyślnie w formularzu: tylko odczyt = zaznaczone, deploy = wyłączony, listy galaktyk puste.
- Do zrobienia: Quit Claude Desktop → rozpakować paczkę do `C:\Tools\GalaxyMcp` → `build.bat` → `pack_mcpb.bat` →
  usunąć ręczny wpis `galaxy` z konfiguracji → start aplikacji → dwuklik `GalaxyMcp.mcpb` → ustawienia (test_mcp, ALLOWED,
  WRITABLE=test_mcp, odznaczyć tylko odczyt) → nowa rozmowa: `galaxy_status`, `list_galaxies`. Sprawdzić przedrostek nazw
  narzędzi w sesji Cowork (dotąd `mcp__remote-devices__galaxy__*`), folder rozszerzenia (log) i reakcję Securden.
- 2026-09-17 11:24 kontrola przesłanego `GalaxyMcp.mcpb`: budowa ZIP poprawna (manifest.json identyczny z projektem, bez BOM;
  GalaxyMcp.exe x86 60 928 B; GalaxyMcp.exe.config; icon.png), ALE exe = 0.2.0 (brak tekstów 0.2.1 / `${` / `tak`) –
  `build.bat` nie został uruchomiony po podmianie `GalaxyMcp.cs` (albo przerwał, bo Claude Desktop trzymał exe).
  Skutek przy 0.2.0: pole „Tylko odczyt” (`true`) byłoby ignorowane (0.2.0 sprawdza tylko `1`), deploy nie dałby się włączyć.
  Paczki NIE instalować. Poprawka w 0.2.1 (przed pierwszym zbudowaniem): `GalaxyMcp.exe --version`; `pack_mcpb.bat`
  przerywa, gdy exe nie zna `--version` albo wersja różni się od `version` w manifest.json.
- 2026-09-17 12:01 kontrola nowego `GalaxyMcp.mcpb`: OK – exe 0.2.1 (x86, 61 440 B, SHA-256 114e72ef…c480ee; zawiera `--version`,
  obsługę `${` i `true/tak`, brak śladów 0.2.0), manifest.json = projekt (version 0.2.1, bez BOM), config i ikona poprawne.
  Paczka dopuszczona do instalacji. Następny krok: instalacja, formularz, nowa rozmowa, `galaxy_status` + `list_galaxies`.
- **2026-09-17 ROZSZERZENIE DZIAŁA (0.2.1 z .mcpb):** ręczny wpis usunięty, rozszerzenie „AVEVA Galaxy (GalaxyMcp)” uruchomione.
  Nazwy narzędzi w sesji Cowork: `mcp__remote-devices__AVEVA_Galaxy__GalaxyMcp___<narzędzie>` (przedrostek z `display_name`).
  `galaxy_status`: 0.2.1, węzeł MARCELK-PRA3, GRAccess znaleziony, galaktyka nie wybrana, dozwolone = wszystkie, zapis zablokowany
  (przełącznik „Tylko odczyt” = `true` rozpoznany poprawnie), deploy wyłączony. `list_galaxies`: 6 galaktyk, wszystkie tylko odczyt.
  Wniosek: formularz został z wartościami domyślnymi – do uzupełnienia (test_mcp, ALLOWED, WRITABLE, odznaczyć tylko odczyt).
  Kosmetyka na przyszłość: komunikat pokazuje „GALAXY_READONLY=1” także przy wartości `true`.

## 2026-09-17 – ZAMKNIĘCIE ETAPU MCP (GalaxyMcp 0.2.1 jako rozszerzenie)
- Po zapisaniu formularza i ponownym uruchomieniu serwera `galaxy_status`: aktywna test_mcp, zapis DOZWOLONY,
  dozwolone test_mcp, test_1, MA_Galaxy, zapis tylko test_mcp, deploy wyłączony, połączenie OK. Wniosek: nowe ustawienia
  działają dopiero po restarcie serwera (wyłącz/włącz Enabled albo Quit) – opisane w README i instrukcji użytkownika.
- Porządki: wszystkie pliki potrzebne do działania w `Tools/` (dodane: `Instrukcja_projektu.md` – przeniesiona z ITERACJE,
  `GalaxyMcp_icon.png.b64`, `GalaxyMcp_test_Spec_UDT_Mixer_Advanced.json`, `GalaxyMcp_instrukcja_pdf.py`).
  Instrukcja użytkownika: `GalaxyMcp_Instrukcja_uzytkownika.pdf` (8 stron, generowana skryptem; PDF oddany na czacie).
- Otwarte punkty (kolejne kroki):
  1. Instrukcja projektu w ustawieniach = treść `Tools/Instrukcja_projektu.md` (prefiks narzędzi rozszerzenia, sekcje 0/1/6/7).
  2. Pełny test trybu Auto na nowym UDT (inny niż Mixer) z instalacji .mcpb – od SCL do weryfikacji w IDE.
  3. Weryfikacja adresów z prawdziwym driverem/sterownikiem (OI Server / DI Object, składnia tablic `[i]`) – potem ew. zmiana formatu.
  4. Test `import_csv` (szablon + instancje) i `deploy` na galaktyce testowej; decyzja o `import_csv` vs `apply_spec`.
  5. Securden: reguła IT po skrócie/podpisie `GalaxyMcp.exe`; rozważyć podpis kodu i `mcpb sign`.
  6. Poprawka kosmetyczna 0.2.2: komunikat „GALAXY_READONLY=1” przy wartości `true`; status bez błędu przy braku galaktyki.
  7. Generator: obsługa Array of Struct / zagnieżdżonych UDT (rozwinięcie z drugiego pliku SCL), tablic 2D, stałych w granicach.
  8. Pilotaż u drugiego użytkownika (inny komputer, GALAXY_NODE = serwer GR) wg instrukcji PDF; zebrać uwagi.
  9. Dystrybucja w zespole: udostępnienie projektu, miejsce na `GalaxyMcp.mcpb` + PDF, ew. wtyczka Cowork ze skillem.
- 2026-09-17: instrukcja PDF poprawiona wg uwag (UWAGI.docx): spis treści na osobnej stronie, w jednej kolumnie, z odnośnikami
  i zakładkami; stopka „Projekt MA_SCL -> CSV · 2026”; bez numeru wersji w nagłówku i podtytule; wymagania: AVEVA SP 26,
  Claude w wersji Premium (tworzenie projektu), bez Securden; usunięte: ramka o ręcznej konfiguracji, rozdziały „Praca krok po
  kroku”, „Aktualizacja wtyczki”, „Ograniczenia”; restart = wyłącz Enabled, restart komputera, włącz Enabled;
  autor: Mateusz Antonowicz z pomocą Claude AI, Astor Wrocław 2026. PDF ma 8 stron.
- 2026-09-17: PDF – autor na stronie tytułowej w dwóch liniach („Autor: Mateusz Antonowicz” / „z pomocą Claude AI”), bez „Astor Wrocław 2026”.

## 2026-09-17 – generator v2: pliki .udt (wiele typów, zagnieżdżone UDT) i .db (instancje)
- Materiał z TIA: `udt_praktykanta.udt` (4 typy: UDT_urzadzenie_stany, UDT_Naped_Regulacja, UDT_naped_stany, UDT_zawor;
  trzy z nich zawierają `stan : "UDT_urzadzenie_stany"`) oraz `przykladowe_db.db` (DATA_BLOCK Mieszalnik_1 i Mieszalnik_2,
  po 12 elementów typu UDT).
- Stan przed zmianą: czytany tylko pierwszy TYPE; 9 z 21 zmiennych ginęło BEZ ostrzeżenia (nazwy w cudzysłowie ze spacją);
  nazwy > 32 znaków przechodziły; zagnieżdżone UDT pomijane; plik .db kończył się wyjątkiem.
- Decyzje użytkownika: pełne wsparcie .udt + .db; spacje w nazwach usuwane; nazwy > 32 znaków skracane automatycznie;
  instancje z DB nazywane `<DB>_<element>` (skracane do 32).
- Zrobione w `Tools/scl_to_aveva.py`: nowy parser (TYPE + DATA_BLOCK, wiele bloków w pliku), rekurencyjne rozwijanie
  UDT i STRUCT, tablice UDT/STRUCT, czyszczenie nazw (adres zachowuje oryginał w cudzysłowie), skracanie nazw
  atrybutów/obiektów z licznikiem (pełna nazwa w opisie), opisy do jednej linii i 200 znaków, `--db/--type/--all-types`,
  osobny Spec/CSV na każdy typ (spec_version 1 bez zmian → serwer GalaxyMcp nie wymaga przebudowy).
- Poprawiony błąd zastany: pola CSV nie były cytowane, a opisy z TIA zawierają przecinki i cudzysłowy – 13 wierszy
  szablonu miało złą liczbę kolumn. Teraz zapis przez `csv.writer` (RFC 4180).
- Testy: udt+db → 3 szablony (21/23/23 atrybuty) i 24 instancje, adresy `PLC_01.Mieszalnik_1.Zawor_Wody.stan.Stan_Aktywny`
  i `...stan."Komenda_HMI_ Aktywuj"`; plik brzegowy (tablice 2D, granice ze stałej, Variant, brak definicji typu,
  rekurencja, tablica UDT w DB, skalar w DB) → same ostrzeżenia, bez wyjątków; regresja Mixers_2.0.scl bajt w bajt
  zgodna z wynikiem zatwierdzonym 2026-09-17.
- Do sprawdzenia: czy import CSV w IDE przyjmuje cytowane pola (w trybie Auto nie ma tego problemu) oraz czy driver
  przyjmuje adresy z nazwami w cudzysłowie (`stan."Komenda_HMI_ Aktywuj"`) – dochodzi do listy pytań o driver.
- Dokumentacja: `Tools/Metoda_Generowania.md`, `Tools/Instrukcja_projektu.md` (sekcje 0, 1, 2, 4, 5) i instrukcja PDF
  (obsługiwane pliki, przykładowe polecenia, słownik).

## 2026-09-17 – dokumentacja drivera OI SIDirect: poprawione adresy i typy
- Użytkownik dostarczył `OISIDIR.pdf` (AVEVA Communication Drivers Pack – Siemens SIDirect, User Guide 2020-11-18).
  Wnioski i cytaty: `ITERACJE/tmp_OI_SIDirect_adresowanie.md` (składnia itemów, limity, typy, sufiksy, Auto-Build).
- Najważniejsze: adres to `<obiekt DI>.<grupa skanowania>.<item>` (s. 84) – grupy skanowania dotąd brakowało;
  nazwy ze spacją/kropką w cudzysłowie, indeks poza cudzysłowem, całość w `attribute(...)` (s. 96);
  tablice wielowymiarowe w jednym nawiasie `[2,5]` (s. 86); limity: 128 znaków nazwy, 6 wymiarów, 1600 elementów,
  8 poziomów zagnieżdżenia, 252 składowe (s. 87).
- Typy (s. 35-36, 87-89): LReal → MxDouble (było MxFloat), LTime/S5Time/Time_Of_Day/LDT/Date → MxTime,
  dodane LInt/LWord/ULInt → MxInteger z ostrzeżeniem o 32 bitach. Sufiksy T/LT/S5T/TOD/D dają tekst tylko do odczytu,
  dlatego atrybut RW dostaje ten sam item bez sufiksu jako MxInteger (ms/ns/dni). LDT i DT są zapisywalne z sufiksem.
- Zmiany w `Tools/scl_to_aveva.py`: `--scan-group`, `item_ref`/`address` (cudzysłowy + attribute), tablice 2D+,
  limity drivera jako ostrzeżenia, nowa tabela typów z sufiksami, wymuszenie Input/MxInteger dla typów czasowych.
  `TypeMapping.json` przepisany wg tabeli Auto-Build. Regresja Mixer: instancje bajt w bajt, w szablonie zmieniły się
  tylko dwa atrybuty Time (Set_AccelTime/Set_DecelTime) – teraz MxInteger RW zamiast MxElapsedTime RW.
- Pliki praktykanta przeliczone ponownie (PLC_01/SG1 jako wartości zastępcze) i oddane na czacie.
- Do sprawdzenia: prawdziwe nazwy obiektu DI i grupy skanowania, DTL jako jeden atrybut, import CSV z `attribute("...")`,
  porównanie z wynikiem Auto-Build z drivera (wymaga licencji Professional).

## 2026-09-17 – galaktyka wzorcowa `VWPNPGGalaxy` i zakres (tylko SIDirect)

- Użytkownik dostał gotowy projekt AVEVA SP; dostępu przez GalaxyMcp jeszcze nie ma (brak uprawnień Securden/helpdesk),
  więc materiał idzie zrzutami z IDE. `list_galaxies` w tej rozmowie zwróciło „Connection closed”.
- Template Toolbox (dolna część listy): tylko szablony bazowe (`$SQLData`, `$UserDefined`), folder **Device Integration**
  = `$DDESuiteLinkClient`, `$InTouchProxy`, `$OPCClient`, `$RedundantDIObject` oraz folder **System**
  (`$AppEngine`, `$Area`, `$InTouchViewApp`, `$ViewApp`, `$ViewEngine`, `$WebViewEngine`, `$WinPlatform`).
  Brak obiektu SIDirect i (w widzianym fragmencie) brak własnych szablonów `$t_...`.
- **Ustalenie (decyzja użytkownika):** projekt celuje wyłącznie w driver **SIDirect** (adres `<obiekt DI>.<grupa skanowania>.<item>`).
  OPC UA (`$OPCClient`) i DDE/SuiteLink są poza zakresem – nie przerabiamy pod nie adresacji. Zapisane w
  `Tools/Instrukcja_projektu.md` (sekcja 4.2) i `ITERACJE/tmp_OI_SIDirect_adresowanie.md` (sekcja 9).
- Do raportu różnic potrzebna jest jeszcze górna część listy szablonów (czy są własne `$t_...`) oraz Galaxy Dump
  jednej instancji – dopiero dump pokaże prawdziwe `InputSource`.
- `test.aaPKG` (63 MB) sprawdzony: to paczka **szablonów bazowych** galaktyki (zip → `File1.cab` → zip; 924 pliki:
  24 `*.aaPDF` + `$WinPlatform`, `$AppEngine`, `$Area`, `$AnalogDevice`, `$DiscreteDevice`, `$UserDefined`,
  `$Sequencer`, `$SQLData`, `$DDESuiteLinkClient`, `$OPCClient`, `$InTouchProxy`, `$RedundantDIObject`, `$ViewApp`…
  i ~700 symboli/widgetów). Zero szablonów `$t_...`, zero instancji, zero łańcuchów `InputSource` z adresem,
  brak słów `SIDirect`/`attribute(`/`UDT_`. Do raportu różnic nie nadaje się – potrzebny eksport własnych
  szablonów/instancji albo Galaxy Dump.

## 2026-09-18 – pełne nazwy bez limitu 32 znaków (generator + GalaxyMcp 0.2.2)
- Decyzja użytkownika: nazwy zmiennych (atrybutów), szablonów i instancji NIE są skracane do 32 znaków – ani w CSV,
  ani w specyfikacji.
- `Tools/scl_to_aveva.py`: `fit()` bez limitu długości, licznik `_1`, `_2` tylko przy kolizji nazw; opis atrybutu to sam
  komentarz z TIA. Test: atrybut 48 znaków i instancja `DB_Bardzo_Dluga_Nazwa_Bloku_Danych_Element_Instancji_Z_Dluga_Nazwa`
  (66 znaków) przechodzą bez zmian; nagłówek szablonu zgodny z `t_SampleUDT.csv`, 53 kolumny.
- `Tools/GalaxyMcp.cs` 0.2.2: `Spec.Parse` nie odrzuca już szablonu ani instancji dłuższych niż 32 znaki (zostaje kontrola
  znaków); `manifest.json` → 0.2.2. Kompilacja niesprawdzona w chmurze – wymaga `build.bat`, `GalaxyMcp.exe --version`
  (ma pokazać 0.2.2), `pack_mcpb.bat` i ponownej instalacji `GalaxyMcp.mcpb`.
- Do sprawdzenia na galaktyce testowej: czy IDE (import CSV) i GRAccess (`CreateTemplate`, `CreateInstance`, `AddUDA`)
  przyjmują nazwy dłuższe niż 32 znaki. ArchestrA historycznie ogranicza tagname do 32 znaków – jeśli zapis się nie uda,
  błąd pojawi się w raporcie `apply_spec` / logu importu i trzeba będzie wrócić do decyzji o skracaniu.
- 2026-09-18 (dalej 0.2.2, jeszcze niezainstalowana): `build.bat` w `Desktop\GalaxyMcp_0.2.2` odmówił – „GalaxyMcp.exe jest
  uruchomiony”. Sprawdzał każdy proces o tej nazwie, także wtyczkę z folderu rozszerzeń Claude. Poprawki:
  (1) `build.bat` sprawdza tylko exe z własnego folderu (PowerShell `Get-Process … Path`);
  (2) serwer kończy się sam: po końcu stdin wylogowanie z limitem 5 s i `Environment.Exit`, a wątek `ParentWatch` co 2 s
  sprawdza proces nadrzędny (PID z `NtQueryInformationProcess`) i kończy serwer, gdy rodzic zniknie – żeby wyłączona
  wtyczka nie zostawała w tle. Kompilacja niesprawdzona w chmurze.
- 2026-09-18: instrukcja użytkownika PDF zaktualizowana do 0.2.2 (`Tools/GalaxyMcp_instrukcja_pdf.py`, 8 stron, układ bez zmian):
  „W skrócie” – nazwy w pełnej długości; ponowne uruchomienie = wyłącz Enabled, odczekaj kilka sekund, włącz (restart
  komputera tylko gdy status dalej stary); nowe wiersze w rozwiązywaniu problemów (GalaxyMcp.exe w tle po wyłączeniu –
  wersja sprzed 0.2.2; błąd długiej nazwy); słownik: szablon bez `t_`, nazwa UDA w pełnej długości.
- 2026-09-18: decyzja użytkownika – opisy (komentarze `//` z TIA) też bez skracania. `clean_desc()` w `scl_to_aveva.py`
  nie przycina już do 200 znaków; reguła zapisana w instrukcji projektu (sekcja 2) i `Metoda_Generowania.md`.
  Serwer GalaxyMcp opisów nie przycinał – bez zmian.

## 2026-09-23 – raport weryfikacji i pełna obsługa plików .db
- Raport weryfikacji (Word, na czacie): 14/16 testów OK; GalaxyMcp 0.2.2 zainstalowany i działa (`galaxy_status`: galaktyka
  test_xml, zapis test_xml + test_mcp, deploy wyłączony); plan `apply_spec` dry_run na test_xml poprawny.
- Luki znalezione w raporcie i poprawione w `Tools/scl_to_aveva.py`: DB typu UDT (`DATA_BLOCK "X"` … `"UDT_Y"` … `BEGIN`),
  UDT wewnątrz STRUCT w DB (także tablica STRUCT), sekcja BEGIN czytana jak deklaracje, komentarz po `Struct` bez średnika,
  `//` w wartości tekstowej, powtarzane ostrzeżenia, komunikat dla `Variant`.
- Wzorzec użytkownika `Instances_UDT_Naped_2stany.csv` (pliki `przykładowa_struktura.udt`, `Napedy.db`): bez adresów plik instancji
  ma tylko `Tagname,Area,SecurityGroup` – generator dostosowany, wynik bajt w bajt zgodny.
- Użytkownik potwierdził: galaktyka przyjmuje nazwy dłuższe niż 32 znaki.
- Do zrobienia: wkleić `Tools/Instrukcja_projektu.md` do ustawień projektu (ustawienia są starsze – brak kierunku Output).

## 2026-11-18 – repozytorium GitHub i synchronizacja Tools z 0.2.3
- Projekt w prywatnym repozytorium GitHub `MateuszAntonowicz/Galaxy_MCP`. Źródła wersji 0.2.3 (paczka z 2026-09-24) w `GalaxyMcp/GalaxyMcp_0.2.3/`.
- `Tools/GalaxyMcp.cs`, `Tools/GalaxyMcp_manifest.json` i `Tools/GalaxyMcp_README.md` były jeszcze w wersji 0.2.2 – podmienione na 0.2.3
  (identyczne z paczką). `build.bat`, `pack_mcpb.bat` i ikona bez zmian.
- `GalaxyMcp.exe` i `GalaxyMcp.mcpb` nie są trzymane w repozytorium. Buduje je workflow GitHub Actions (`.github/workflows/wydanie.yml`,
  Windows, ten sam kompilator co `build.bat`) i dołącza do wydania `v<wersja>` w zakładce Releases, gdy na `main` trafi nowa wersja.

## 2026-11-18 – wersja 0.2.4: nazwa GalaxyMCP
- Decyzja użytkownika: wtyczka nazywa się **GalaxyMCP** (`display_name` w manifeście; wcześniej „AVEVA Galaxy (GalaxyMcp)”).
  Nazwa zmieniona w README, instrukcjach, komunikatach serwera (log, status, komentarz check-in) i w trzech PDF.
  Nazwy plików (`GalaxyMcp.exe`, `.mcpb`, `.log`, `.cs`, `GalaxyMcp_*` w Tools), `name: galaxy` w manifeście i nazwy narzędzi bez zmian.
- Wersja 0.2.4 = 0.2.3 + nowa nazwa (kod bez zmian funkcjonalnych). Przedrostek narzędzi w wątku po reinstalacji
  prawdopodobnie `mcp__remote-devices__GalaxyMCP__…` (z `display_name`) – szukać przez ToolSearch „galaxy_status”.
- PDF: potwierdzenie działania na AVEVA System Platform 2026; w instrukcji użytkownika pogrubione
  „ręcznego zamknięcia procesów GalaxyMcp.exe”. `GalaxyMcp_Jak_to_dziala.pdf` poprawiony skryptem
  `Dokumentacja/zrodla/GalaxyMcp_Jak_to_dziala_galaxy_mcp.py` (PyMuPDF).

## 2026-11-23 – wersja 0.2.5: poprawki z testu projektu (2026-11-18)
- Generator `scl_to_aveva.py`:
  - kolizje nazw wykrywane bez rozróżniania wielkości liter (`Stan_X` i `stan_x` → `Stan_X`, `stan_x_1`) – jak w AVEVA i w serwerze;
  - nazwy obiektów z `--instances` czyszczone jak pozostałe (`"Z 2"` → `Z2`); zły format `Obiekt=DB` przerywa pracę;
  - `TYPE "UDT Mój typ"` i `DATA_BLOCK "DB Napęd 1"` czytane w całości (wcześniej ucinane na spacji); nazwa szablonu
    i plików wynikowych czyszczona (`$t_UDTMojtyp`, `Spec_UDTMojtyp.json`), pole `udt` w specyfikacji zachowuje nazwę z TIA;
  - polskie litery zamieniane na litery bez ogonków (`Prędkość zadana` → `Predkosczadana`) zamiast `_`;
  - ostrzeżenie, gdy nie ma pliku `--permissions` (wcześniej cicho reguły awaryjne);
  - usunięte nieaktualne „GalaxyMCP 0.2.2” z ostrzeżeń i opisów.
- Serwer `GalaxyMcp.cs`: parametr `galaxy` obowiązkowy przy każdym zapisie (`apply_spec` z `dry_run=false`, `import_csv`,
  `deploy`; w `import_csv` i `deploy` także w `required` schematu). Wcześniej zapis bez `galaxy` przechodził na aktywnej galaktyce.
- Testy: `tests/test_generator.py` klasa `Poprawki025` (dane `tests/dane/poprawki_025.*`) i `Repozytorium` (Tools = najnowszy
  `GalaxyMcp/GalaxyMcp_<wersja>`); `tests/test_serwer.ps1` sprawdza odmowę zapisu bez `galaxy`.
- Nie sprawdzone w galaktyce (brak dostępu do AVEVA w sesji) – do potwierdzenia po instalacji 0.2.5: zapis z `galaxy` działa
  jak w 0.2.4, a bez `galaxy` serwer odmawia.
