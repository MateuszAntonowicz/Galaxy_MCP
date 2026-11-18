#!/usr/bin/env python3
"""
Siemens TIA Portal (SCL / UDT / DB) -> AVEVA System Platform (ArchestrA IDE).

Przepływ:  pliki z TIA -> Spec_<UDT>.json (format pośredni) -> CSV (tryb Manual)
                                                          \\-> serwer GalaxyMCP (tryb Auto)
Wejście:
  *.udt / *.scl  - jeden lub wiele bloków TYPE "<UDT>" ... STRUCT ... END_TYPE (źródło szablonów)
  *.db           - jeden lub wiele bloków DATA_BLOCK "<DB>" ... VAR ... END_VAR (źródło instancji)

Generuje dla każdego szablonu:
  Output/Spec_<UDT>.json       - specyfikacja: szablon, atrybuty, kierunki I/O, instancje, adresy
  Output/$t_<UDT>.csv          - czysty szablon (multi-block CSV, bez adresów PLC)
  Output/Instances_<UDT>.csv   - instancje (format Galaxy Load) z InputSource / OutputDest

Użycie:
  python scl_to_aveva.py udt_praktykanta.udt --db przykladowe_db.db --plc S7C_01 --scan-group SG1 \\
      --permissions Permissions.csv --out Output

  python scl_to_aveva.py MA_Mixer.scl --permissions Permissions.csv \\
      --plc S7C_01 --scan-group SG1 --instances Mixer_01=DB_Mixer_01 Mixer_02=DB_Mixer_02 --out Output

  Reguły ręczne zamiast pliku:  --rules Cmd_=InputOutput Status_=Input Reset_=Output
  Wybrane typy:                 --type UDT_zawor UDT_naped_stany
  Wszystkie typy z pliku:       --all-types (domyślnie: tylko te, które mają instancje)
  Bez adresów:                  --no-address (InputSource/OutputDest instancji zostają puste)
  Nazwa szablonu bez "t_":      --template-prefix "" (domyślnie $t_<UDT>, po zmianie $<UDT>)
  CSV z ręcznie poprawionej specyfikacji:  --from-spec Output/Spec_<UDT>.json --out Output

Zasady:
  * Zagnieżdżone UDT i STRUCT są rozwijane: nazwa atrybutu spłaszczona przez "_",
    adres zachowuje ścieżkę w PLC (stan.Stan_Aktywny -> atrybut stan_Stan_Aktywny).
  * Tablice: Temp[1..2] -> Temp_1, Temp_2 (adres Temp[1]); indeks ujemny -> Neg_m1 (adres Neg[-1]).
    Tablice wielowymiarowe też: Siatka[1..2, 0..1] -> Siatka_1_0 (adres Siatka[1,0]).
    Tablice UDT i STRUCT są rozwijane (Zawory[1].stan -> Zawory_1_stan).
  * Nazwy z TIA są czyszczone do wymagań AVEVA: spacje są usuwane, a pozostałe znaki inne niż
    litera, cyfra i "_" zamieniane na "_" ("Komenda_HMI_ Aktywuj" -> Komenda_HMI_Aktywuj,
    Temp-1 -> Temp_1); adres w PLC zachowuje oryginalną nazwę.
  * Nazwy NIE są skracane - atrybuty, szablony i instancje mają pełne nazwy, bez limitu 32 znaków
    (decyzja użytkownika 2026-09-18). Licznik dostaje tylko nazwa, która koliduje z inną.
  * Opisy (komentarze // z TIA) też NIE są skracane - trafiają do Description w pełnej długości.
  * Kierunek I/O: prefiks dopasowywany do nazwy zmiennej w SCL (liścia), nie do nazwy spłaszczonej.
    Input = Read (ReadOnly), InputOutput = Read/Write (ReadWrite), Output = Write (WriteOnly: SCADA tylko
    zapisuje, adres w OutputDest zamiast InputSource; format niepotwierdzony eksportem z IDE, tryb Auto
    - GalaxyMCP 0.2.2 - go nie obsługuje).
  * Adres (InputSource / OutputDest) wg dokumentacji drivera OI SIDirect (adresowanie symboliczne):
    <obiekt DI>.<grupa skanowania>.<item>, item = [DB].[Tag]<[i]>.[Member]; nazwy ze spacją lub kropką
    w cudzysłowie (indeks poza nim), a cały item w attribute(...). Obiekt DI (--plc) jest wymagany,
    chyba że podano --no-address.
  * Instancje z DB: nazwa = <DB>_<element> (pełna, bez skracania), item = <DB>.<element>.<ścieżka w UDT>.
    UDT w STRUCT w DB: <DB>_<Struct>_<element>; DB typu UDT (DATA_BLOCK "X" "UDT_Y"): jedna instancja <DB>.
    Sekcja BEGIN (wartości startowe) jest pomijana. Bez adresów plik instancji ma tylko Tagname/Area/SecurityGroup.
  * Typy czasowe: atrybut tylko do odczytu dostaje sufiks (Cfg_Czas T), atrybut do zapisu (InputOutput
    albo Output) jest MxInteger bez sufiksu (Time/S5Time/TOD: ms, LTime: ns, Date: dni). DTL
    i LTime_Of_Day nie mają sufiksu w dokumentacji drivera - zostaje ostrzeżenie do sprawdzenia w Object Viewer.
  * Limity drivera: 6 wymiarów, 1600 elementów, 8 poziomów zagnieżdżenia, 252 składowe,
    nazwa symboliczna 128 znaków.
  * Pomijane z ostrzeżeniem: tablice poza limitami drivera, tablice o granicach ze stałej,
    typy bez definicji w pliku, typy nieobsługiwane (np. Variant), rekurencja typów.
"""
import argparse, csv, io, itertools, json, os, re, sys

# ---------------------------------------------------------------- stałe formatu
HEADER = "# ***************************************************************************\n# ******* This file contains multi-block CSV data: Edit with caution! *******\n# ***************************************************************************\n# \n# ******************************** Sections *********************************\n# [options]\n# <template-declaration>\n# [User-defined attributes]\n# [Extended attributes]\n# [Graphical Content]\n# [Wizard Assets]\n# [Wizard Associations]\n# [Wizard Settings]\n# \n# ***************************** Import Options ******************************\n# Options have the following format:\n#   .<condition> = <disposition>\n# Import options define what action the import operation should take when a conflict or boundary condition is encountered.\n# You must define import options before all other blocks in the import file.\n# \n# # Boundary conditions are events that may cause a conflict with default import behavior. These include:\n#   - Conditions that are not allowed. For example: Changing the properties of an attribute that is locked in the parent object.\n#   - Conditions that may be allowed - but user action is required - such as creating an intermediate template to satisfy an import request.\n# # Dispositions may be specified individually or as a comma-separated set. They include:\n#   - abort:          Stop importing the current object and its descendants.\n#   - warn:           Log a warning message and skip (if the condition is not allowed) or process (if the condition is allowed) the action that triggered the boundary condition. Then continue importing the current object. The progress dialog will advise the IDE user to review the logs for boundary conditions handled in this way.\n#   - ignore:         Log an info message and skip (if the condition is not allowed) or process (if the condition is allowed) the action that triggered the boundary condition. Then continue with the import of the current object. No other indication is sent to the user when a condition is ignored.\n# [*] You only need to include the action (abort/ignore/warn) to be taken. The template generally will include all three possible actions when it is exported. To simplify editing you can simply add an asterisk to the specified action instead of deleting the other two actions. For example: {abort<comma> *warn<comma> ignore} is the same as specifying only warn.\n# [*] If you do not specify an option to handle a boundary condition the default option for that condition is used - typically *warn for disallowed conditions and *abort for allowed ones.\n# \n# *************************** Template Declaration **************************\n# The template declaration block must contain exactly one line that declares the name of the template being imported and the name of the template from which it is derived in the following format:\n# $$template_name -> $base_template_name\n# The [$template_name] supports the following adornments:\n# - Its folder in the template toolbox:\n#   $System\\Pumps\\$TwoHP -> $Pump\n# - Protection indicator [^]:\n#   $System\\Pumps\\$TwoHP^ -> $Pump\n# - Its assigned Security Group:\n#   $System\\Pumps\\$TwoHP^{Default} -> $Pump\n# \n# The [$base_template_name] identifies the template from which [$template_name] is derived.\n# - [$base_template_name] must identify an existing template for [$template_name] to be imported.\n# - [$base_template_name] can represent the entire lineage of [$template_name]:\n#   $$TwoHP -> $Pump -> $Electrical -> $Master_UserDefined -> $UserDefined\n# - [$base_template_name] are pure template names--they may not be adorned in any way.\n# \n# ****************************** Data Sections *****************************\n# The remaining sections describe the data with which the template is to be configured.\n# - The Banner record--identified by the leading [&]--identifies the section as one of the following:\n#   &User-defined Attributes\n#   &Extended Attributes\n#   &Graphical Content\n#   &Wizard Assets\n#   &Wizard Associations\n#   &Wizard Settings\n# \n# - The Header record--identified by the leading [:]--enumerates the names of the configurable elements in the section as a comma-separated list:\n#   :Attribute<comma>Type<comma>Value<comma>LockStatus<comma>SecurityClassification<comma>Category<comma>...:\n# \n# - Configuration data corresponding to the cells identified by the Header record are listed as a comma-separated table.\n#   PV<comma>Integer<comma>12<comma>Unlocked<comma>Operate<comma>ObjectWriteable<comma>...:\n# \n# ************ Wizard Setting values with special significance **************\n#   - <empty>:        Register an empty override ('')\n#   - <default>:      No value override (accept default value)\n#   - <inherited>:    No value override (accept inherited value)\n# \n# ************************* File Import Options *****************************\n.asset_owned_by_parent = {abort,*warn,ignore}\n.nominal_template_declaration = {abort,*warn,ignore}\n.bad_visual_element_reference = {abort,*warn,ignore}\n.uncontained_dotted_object_name = {abort,*warn,ignore}\n.object_has_field_attributes = {abort,*warn,ignore}\n.invalid_wizsetting_attribution = {abort,warn,*ignore}\n.invalid_security_group = {abort,*warn,ignore}\n.experimental_features = {*abort,warn,ignore}\n# "   # blok komentarzy + opcje importu (skopiowane z t_SampleUDT.csv)

UDA_COLS = ("Attribute,Type,Value,LockStatus,SecurityClassification,Category,Description,"
    "Description.LockStatus,Description.SecurityClassification,EngUnits,EngUnits.LockStatus,"
    "Boolean.OnMsg,Boolean.OnMsg.LockStatus,Boolean.OffMsg,Boolean.OffMsg.LockStatus,#IO,#IO.Mode,"
    "#IO.ScalingEnabled,#IO.Buffered,#IO.DiffOutputDest,#IO.DiffOutputDest.LockStatus,#IO.Deadband,"
    "#IO.Deadband.LockStatus,#IO.Deadband.SecurityClassification,#IO.InvertValue,"
    "#IO.InvertValue.LockStatus,#History,#History.EnableSwingingDoor,"
    "#History.EnableSwingingDoor.LockStatus,#History.EnableSwingingDoor.SecurityClassification,"
    "#Limit Alarms,#Limit.HiHi,#Limit.HiHi.LockStatus,#Limit.Hi,#Limit.Hi.LockStatus,#Limit.Lo,"
    "#Limit.Lo.LockStatus,#Limit.LoLo,#Limit.LoLo.LockStatus,#ROC Alarms,#ROC.IncreasingHi,"
    "#ROC.IncreasingHi.LockStatus,#ROC.DecreasingHi,#ROC.DecreasingHi.LockStatus,#Deviation Alarms,"
    "#Dev.Minor,#Dev.Minor.LockStatus,#Dev.Major,#Dev.Major.LockStatus,#State Alarm,"
    "#Bad Value Alarm,#Statistics,#Log Change").split(",")
EXT_COLS = ["Primitive", "Attribute", "PrimitiveType"] + [c for c in UDA_COLS[2:] if c != "Category"]
SEP = "#" + "=" * 139
TAIL = [
    "&Graphical Content", ":Visual Element,Visual Element Type,Description,IsLinked", SEP,
    "&Wizard Assets", ":ChoiceOrOption,ChoiceGroup,Description,VisibilityRules,Enabled,"
    "InstanceVisibility,PositionAfterGroupOrOption", SEP,
    "&Wizard Associations", ":ChoiceOrOption,ChoiceGroup,LinkType,LinkedAsset,TrimIfUnchecked", SEP,
    "&Wizard Settings", ":ChoiceOrOption,ChoiceGroup,LinkType,LinkedAsset,Setting,Value,"
    "InstanceVisibility,SymbolIsReference,SymbolWizardAssetIsChecked,IsOverride", SEP,
]

# typ Siemens -> (typ AVEVA, wartość domyślna, sufiks w adresie, tylko odczyt, uwaga)
# Źródło: AVEVA Communication Drivers Pack - Siemens SIDirect, User Guide 2020-11-18:
# "Auto-Build Data Type Mapping" (s. 35-36) oraz "General Data Types" (s. 87-89).
TYPES = {}


BIG_INT = set("LINT INT64 LWORD BITSET64 UINT64 ULINT".split())   # 64-bit: MxInteger to 32 bity


def _t(keys, mx, default="", suffix="", read_only=False, note="", unit=""):
    for k in keys.split():
        TYPES[k] = {"mx": mx, "default": default, "suffix": suffix, "read_only": read_only,
                    "note": note, "unit": unit}


_t("BOOL", "MxBoolean", "false")
_t("BYTE USINT UINT8 BITSET8 SINT INT8 INT INTEGER INT16 UINT UINT16 WORD BITSET16 "
   "DINT INT32 UDINT UINT32 DWORD BITSET32 LINT INT64 LWORD BITSET64 UINT64 ULINT", "MxInteger", "0")
_t("REAL REAL32", "MxFloat", "0.0")
_t("LREAL DOUBLE REAL64", "MxDouble", "0.0")            # LReal to VT_R8 -> MxDouble, nie MxFloat
_t("STRING WSTRING CHAR WCHAR STRING2 WSTRING2", "MxString")
# Typy czasowe: z sufiksem driver zwraca tekst i pozwala tylko czytać, bez sufiksu - liczbę
# (Time/S5Time/Time_Of_Day: milisekundy, LTime: nanosekundy, Date: dni) do odczytu i zapisu.
_t("TIME TIMESPAN", "MxElapsedTime", suffix="T", read_only=True, unit="milisekundy")
_t("LTIME", "MxTime", suffix="LT", read_only=True, unit="nanosekundy")
_t("S5TIME", "MxTime", suffix="S5T", read_only=True, unit="milisekundy")
_t("TIME_OF_DAY TOD", "MxTime", suffix="TOD", read_only=True, unit="milisekundy")
_t("DATE", "MxTime", suffix="D", read_only=True, unit="dni od 1990-01-01")
_t("LDT", "MxTime", suffix="LDT")                        # LDT: sufiks read/write
_t("DATE_AND_TIME DT", "MxTime", suffix="DT")            # DT wymagany dla SuiteLink
_t("LTIME_OF_DAY LTOD", "MxTime", note="driver nie podaje sufiksu dla LTime_Of_Day - sprawdź wartość w Object Viewer")
_t("DTL", "MxTime", note="DTL jest strukturą (.YEAR, .MONTH, ...) tylko do odczytu - sprawdź w Object Viewer")


def mx(key):
    return TYPES[key]["mx"]
DEFAULT_RULES = [("Cmd_", "InputOutput"), ("Set_", "InputOutput"),
                 ("Cfg_", "InputOutput"), ("Par_", "InputOutput")]

# Kierunek I/O. Access_Mode z pliku reguł -> PrimitiveType; nazwy z IDE (Read, Read/Write, Write) też działają.
MODES = {"input": "Input", "read": "Input", "inputoutput": "InputOutput", "read/write": "InputOutput",
         "readwrite": "InputOutput", "output": "Output", "write": "Output"}
IO_MODE = {"Input": "ReadOnly", "InputOutput": "ReadWrite", "Output": "WriteOnly"}   # -> #IO.Mode
IO_SHORT = {"Input": "R", "InputOutput": "RW", "Output": "W"}
WRITABLE = ("InputOutput", "Output")

# ---------------------------------------------------------------- parser TIA (SCL / UDT / DB)
MAX_SYMBOL = 128       # limit nazwy symbolicznej w tabeli DB (driver SIDirect, s. 87)
MAX_ARRAY_ELEMENTS = 1600   # limit elementów tablicy (driver SIDirect, s. 87)
MAX_ARRAY_DIMS = 6          # limit wymiarów tablicy (driver SIDirect, s. 87)
MAX_NESTING = 8             # limit zagnieżdżenia struktury (driver SIDirect, s. 87)
MAX_MEMBERS = 252           # limit składowych struktury (driver SIDirect, s. 87)

RE_TYPE = re.compile(r'^\s*TYPE\s+"?([^"\s]+)"?', re.I)
RE_DB = re.compile(r'^\s*DATA_BLOCK\s+"?([^"\s]+)"?', re.I)
RE_OPEN = re.compile(r'^(STRUCT|VAR(\s+\w+)?)$', re.I)
RE_END = re.compile(r'^(END_TYPE|END_DATA_BLOCK)\b', re.I)
RE_NOISE = re.compile(r'^(VERSION|NON_RETAIN|RETAIN|END_VAR|FAMILY|AUTHOR|TITLE|NAME|\{|\})', re.I)
RE_BEGIN = re.compile(r'^BEGIN\b', re.I)
RE_DB_TYPE = re.compile(r'^"([^"]+)"\s*;?\s*(?://.*)?$')   # DB typu UDT: sama nazwa typu zamiast VAR ... END_VAR
UNSUPPORTED = set("VARIANT ANY POINTER DB_ANY BLOCK_DB BLOCK_FB BLOCK_FC".split())
DECL = re.compile(r'^\s*(?:"(?P<qname>[^"]+)"|(?P<name>\w+))\s*(?:\{[^}]*\})?\s*:\s*'
                  r'(?P<type>(?:[^;/]|/(?!/))+?)\s*(?:;|(?=//)|$)\s*(?://\s*(?P<desc>.*))?$')   # komentarz także bez ';' (Struct // opis)
ARR = re.compile(r'^Array\s*\[(.+?)\]\s*of\s+(.+)$', re.I)
DIM = re.compile(r'^\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*$')


def parse_source(text, warn, types=None, dbs=None):
    """Czyta plik z TIA: bloki TYPE (szablony) i DATA_BLOCK (instancje).
    Zwraca (types, dbs): {nazwa typu: [członkowie]}, {nazwa DB: [członkowie]}.
    Członek: {raw, desc, dims, kind: scalar|struct|udt|typed_db, type, members}.
    DB typu UDT (DATA_BLOCK "X" ... "UDT_Y" BEGIN, bez VAR) -> jeden członek kind=typed_db.
    Sekcja BEGIN ... END_DATA_BLOCK (wartości startowe) jest pomijana."""
    types = {} if types is None else types
    dbs = {} if dbs is None else dbs
    stack, kind, opened = [], None, False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if kind is None:
            m = RE_TYPE.match(line)
            if m:
                name = m.group(1)
                if name in types:
                    warn.append("typ '%s' występuje więcej niż raz - użyto pierwszej definicji" % name)
                    types.setdefault(name, [])
                else:
                    types[name] = []
                kind, opened, stack = "type", False, [types[name]]
                continue
            m = RE_DB.match(line)
            if m:
                name = m.group(1)
                if name in dbs:
                    warn.append("blok danych '%s' występuje więcej niż raz - użyto pierwszej definicji" % name)
                dbs.setdefault(name, [])
                kind, opened, stack = "db", False, [dbs[name]]
            continue
        if RE_END.match(line):
            kind, opened, stack = None, False, []
            continue
        if kind == "begin":                                          # wartości startowe DB - pomijamy
            continue
        if kind == "db" and RE_BEGIN.match(line):
            kind = "begin"
            continue
        if kind == "db" and not opened:
            m = RE_DB_TYPE.match(line)
            if m:                                                    # DB utworzony wprost z typu UDT
                stack[0].append({"raw": None, "desc": "", "dims": None, "kind": "typed_db",
                                 "type": m.group(1).strip(), "members": None})
                continue
        if not opened and RE_OPEN.match(line):
            opened = True
            continue
        if re.match(r'^END_STRUCT', line, re.I):
            if len(stack) > 1:
                stack.pop()
            continue
        if RE_NOISE.match(line):
            continue
        # wartość początkowa tekstowa może zawierać '//' (np. := 'http://...') - nie jest komentarzem
        m = DECL.match(re.sub(r":=\s*'[^']*'", ":= ''", line))
        if not m:
            warn.append("nie rozpoznano deklaracji: " + line[:70])
            continue
        t = re.sub(r':=.*$', '', m.group("type")).strip()          # usuń wartość początkową
        node = {"raw": m.group("qname") or m.group("name"), "desc": (m.group("desc") or "").strip(),
                "dims": None, "kind": "scalar", "type": t, "members": None}
        a = ARR.match(t)
        if a:
            node["dims"] = a.group(1)
        et = (a.group(2) if a else t).strip().strip('"').strip()
        node["type"] = et
        if re.fullmatch(r'Struct', et, re.I):
            node["kind"], node["members"] = "struct", []
        elif et.split("[")[0].strip().upper() in TYPES:
            node["kind"] = "scalar"
        else:
            node["kind"] = "udt"
        stack[-1].append(node)
        if node["kind"] == "struct":
            stack.append(node["members"])
    return types, dbs


# ---------------------------------------------------------------- nazwy
def clean_name(raw, warn=None):
    """Nazwa zgodna z AVEVA: spacje usuwane, pozostałe znaki inne niż litera, cyfra i '_'
    zamieniane na '_' ("Komenda_HMI_ Aktywuj" -> Komenda_HMI_Aktywuj, Temp-1 -> Temp_1).
    Adres w PLC zostaje bez zmian (oryginalna nazwa w cudzysłowie)."""
    n = re.sub(r'[^A-Za-z0-9_]', '_', re.sub(r'\s+', '', raw.strip()))
    if not n or not re.match(r'^[A-Za-z_]', n):
        n = "A_" + n
    if warn is not None and n != raw.strip():
        w = "nazwa '%s' zamieniona na '%s' (AVEVA nie dopuszcza takich znaków)" % (raw.strip(), n)
        if w not in warn:
            warn.append(w)
    return n


def item_ref(parts, suffix=""):
    """Item drivera SIDirect (adresowanie symboliczne, User Guide s. 85-87, 96):
    [DB].[Tag]<[i]>.[Member] - nazwy ze spacją lub kropką w cudzysłowie, a cały item
    w `attribute(...)`, bo inaczej Application Server nie przyjmie odwołania."""
    out, quoted = [], False
    for p in parts:
        base = re.sub(r'(\[[^\]]*\])$', '', p)
        idx = p[len(base):]
        if re.fullmatch(r'[A-Za-z_]\w*', base):
            out.append(base + idx)
        else:
            out.append('"%s"%s' % (base, idx))
            quoted = True
    item = ".".join(out)
    if suffix:
        item += " " + suffix          # sufiks konwersji, np. "MyTime T"
    return "attribute(%s)" % item if (quoted or suffix) else item


def address(plc, scan_group, parts, suffix=""):
    """Pełny adres (InputSource / OutputDest): <obiekt DI>.<grupa skanowania>.<item> (User Guide s. 84)."""
    head = ".".join([x for x in (plc, scan_group) if x])
    return (head + "." if head else "") + item_ref(parts, suffix)


def fit(name, used, warn, what="atrybut"):
    """Nazwa unikalna w obrębie `used`, bez skracania (brak limitu długości - decyzja 2026-09-18).
    Przy kolizji (np. "Temp-1" i Temp[1] dają to samo Temp_1) dostaje licznik _1, _2..."""
    new, k = name, 1
    while new in used:
        new = "%s_%d" % (name, k)
        k += 1
    if new != name:
        warn.append("%s '%s' koliduje z inną nazwą - zmieniony na '%s'" % (what, name, new))
    used.add(new)
    return new


def clean_desc(text):
    """Opis atrybutu = komentarz z TIA w PEŁNEJ długości (bez skracania - decyzja użytkownika 2026-09-18):
    tylko sklejony do jednej linii i bez otaczających cudzysłowów."""
    return re.sub(r'\s+', ' ', (text or "").strip()).strip('"').strip()


# ---------------------------------------------------------------- spłaszczanie
def indices(dims, label, warn):
    """Krotki indeksów tablicy: [None] dla zmiennej pojedynczej, [] gdy tablicę trzeba pominąć.
    Driver SIDirect przyjmuje indeksy wielowymiarowe w postaci Tag[2,5] (User Guide s. 86)."""
    if dims is None:
        return [None]
    parts = [DIM.match(d) for d in dims.split(",")]
    if not all(parts):
        warn.append("%s: tablica o niestałych granicach '%s' pominięta" % (label, dims))
        return []
    if len(parts) > MAX_ARRAY_DIMS:
        warn.append("%s: tablica ma %d wymiarów (driver obsługuje %d) - pominięta"
                    % (label, len(parts), MAX_ARRAY_DIMS))
        return []
    ranges = [range(int(d.group(1)), int(d.group(2)) + 1) for d in parts]
    total = 1
    for r in ranges:
        total *= len(r)
    if total > MAX_ARRAY_ELEMENTS:
        warn.append("%s: tablica ma %d elementów (limit drivera %d) - pominięta"
                    % (label, total, MAX_ARRAY_ELEMENTS))
        return []
    return [tuple(c) for c in itertools.product(*ranges)]


def flatten(members, types, warn, names=(), path=(), seen=()):
    """Liście struktury: nazwa spłaszczona, nazwa zmiennej w SCL, ścieżka w PLC (lista elementów),
    typ Siemensa i opis. Ścieżka jest listą, bo cudzysłowy dokłada dopiero item_ref()."""
    out = []
    if len(names) > MAX_NESTING:
        warn.append("%s: zagnieżdżenie głębsze niż %d poziomów (limit drivera) - pominięto"
                    % ("_".join(names), MAX_NESTING))
        return out
    if len(members) > MAX_MEMBERS:
        warn.append("%s: struktura ma %d składowych (limit drivera %d) - sprawdź w Object Viewer"
                    % ("_".join(names) or "(poziom główny)", len(members), MAX_MEMBERS))
    for m in members:
        base = clean_name(m["raw"], warn)
        if len(m["raw"]) > MAX_SYMBOL:
            warn.append("%s: nazwa symboliczna dłuższa niż %d znaków - driver jej nie przyjmie"
                        % (base, MAX_SYMBOL))
        for i in indices(m["dims"], "_".join(names + (base,)), warn):
            if i is None:
                nm, pt = names + (base,), path + (m["raw"],)
            else:   # indeks ujemny: '-' niedozwolony w nazwie atrybutu -> 'm' (Neg_m1)
                nm = names + (base + "".join("_" + str(x).replace("-", "m") for x in i),)
                pt = path + (m["raw"] + "[" + ",".join(str(x) for x in i) + "]",)
            full = "_".join(nm)
            if m["kind"] == "scalar":
                key = m["type"].split("[")[0].strip().upper()   # String[20] -> STRING
                if key not in TYPES:
                    warn.append("%s: nieobsługiwany typ '%s' pominięty" % (full, m["type"]))
                    continue
                out.append({"name": full, "leaf": base, "plc_parts": list(pt),
                            "plc_type": key, "desc": clean_desc(m["desc"])})
            elif m["kind"] == "struct":
                out += flatten(m["members"], types, warn, nm, pt, seen)
            elif m["type"].upper() in UNSUPPORTED:
                warn.append("%s: nieobsługiwany typ '%s' pominięty" % (full, m["type"]))
            elif m["type"] not in types:
                warn.append("%s: brak definicji typu '%s' w podanych plikach - pominięto" % (full, m["type"]))
            elif m["type"] in seen:
                warn.append("%s: typ '%s' zagnieżdżony w sobie - pominięto" % (full, m["type"]))
            else:
                out += flatten(types[m["type"]], types, warn, nm, pt, seen + (m["type"],))
    return out


def attributes(udt, types, rules, warn):
    """Atrybuty szablonu: spłaszczone nazwy (pełne, bez skracania), typ AVEVA, sufiks adresu, kierunek I/O."""
    used, attrs = set(), []
    for leaf in flatten(types[udt], types, warn, seen=(udt,)):
        name = fit(leaf["name"], used, warn)
        desc = leaf["desc"]
        t = TYPES[leaf["plc_type"]]
        mx_type, default, suffix, note = t["mx"], t["default"], t["suffix"], t["note"]
        io = io_mode(leaf["leaf"], rules)
        if t["read_only"] and io in WRITABLE:
            # zapis wymaga postaci liczbowej (driver: ten sam item bez sufiksu jest Read/Write)
            mx_type, default, suffix = "MxInteger", "0", ""
            warn.append("%s: typ %s zapisywalny tylko jako liczba (%s) - atrybut MxInteger bez sufiksu"
                        % (name, leaf["plc_type"], t["unit"] or "wartość surowa"))
        elif t["read_only"]:
            note = note or ("driver udostępnia %s jako tekst tylko do odczytu (sufiks %s)"
                            % (leaf["plc_type"], suffix))
        if leaf["plc_type"] in BIG_INT:
            warn.append("%s: typ %s jest 64-bitowy, a MxInteger ma 32 bity - sprawdź zakres wartości"
                        % (name, leaf["plc_type"]))
        if note:
            warn.append("%s (%s): %s" % (name, leaf["plc_type"], note))
        attrs.append({"name": name, "plc_type": leaf["plc_type"], "type": mx_type, "default": default,
                      "io": io, "description": desc, "plc_parts": leaf["plc_parts"],
                      "plc_suffix": suffix, "plc_path": item_ref(leaf["plc_parts"], suffix)})
    return attrs


# ---------------------------------------------------------------- reguły dostępu
def norm_mode(mode):
    """Access_Mode -> Input / InputOutput / Output (wielkość liter i spacje bez znaczenia); None = nieznany."""
    return MODES.get((mode or "").strip().lower().replace(" ", ""))


def load_rules(path, manual, warn):
    """Reguły kierunku I/O: --rules, plik CSV (kolumny Prefix_or_Keyword, Access_Mode; przecinek albo
    średnik) albo reguły awaryjne DEFAULT_RULES, gdy pliku nie ma."""
    if manual:
        rules = []
        for r in manual:
            p, _, m = r.partition("=")
            mode = norm_mode(m)
            if not p or not mode:
                sys.exit("Niepoprawna reguła '%s' (format Prefiks=Input|InputOutput|Output)" % r)
            rules.append((p, mode))
        return rules
    if path and os.path.exists(path):
        lines = []   # dekodowanie per linia: UTF-8, awaryjnie CP1250 (plik edytowany w Notatniku/Excelu)
        for no, b in enumerate(open(path, "rb").read().splitlines(), 1):
            try:
                lines.append(b.decode("utf-8-sig"))
            except UnicodeDecodeError:
                lines.append(b.decode("cp1250"))
                warn.append(f"{os.path.basename(path)}: linia {no} nie jest w UTF-8 (odczytano jako CP1250)")
        sample = "\n".join(lines[:2])
        delim = ";" if sample.count(";") > sample.count(",") else ","   # Excel z polskimi ustawieniami daje ';'
        rules = []
        for r in csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delim):
            p = (r.get("Prefix_or_Keyword") or "").strip()
            if not p:
                continue
            mode = norm_mode(r.get("Access_Mode"))
            if not mode:
                warn.append("%s: reguła '%s' ma nieznany Access_Mode '%s' (dozwolone: Input, InputOutput, "
                            "Output) - pominięta" % (os.path.basename(path), p, r.get("Access_Mode")))
                continue
            rules.append((p, mode))
        if not rules:
            # zła nazwa kolumny dałaby po cichu same Input - lepiej przerwać
            sys.exit("W pliku %s nie ma reguł (potrzebne kolumny Prefix_or_Keyword i Access_Mode - "
                     "nie zmieniaj nazw kolumn)." % path)
        return rules
    return DEFAULT_RULES


def io_mode(leaf, rules):
    """Pierwsza reguła, której prefiks pasuje do nazwy liścia. Brak -> Input."""
    for p, mode in rules:
        if leaf.startswith(p):
            return mode
    return "Input"


# ---------------------------------------------------------------- specyfikacja (format pośredni)
SPEC_VERSION = 1


def build_spec(udt, attrs, instances, plc, scan_group, source, warn, no_address=False,
               template_prefix="t_"):
    """Specyfikacja JSON dla jednego szablonu - wspólne wejście generatora CSV i serwera MCP.
    instances: lista {name, db, parts} - parts to ścieżka elementu w PLC (bez nazwy zmiennej).
    Adres: <obiekt DI>.<grupa skanowania>.<item>, item wg zasad drivera SIDirect.
    Atrybuty Input/InputOutput -> input_source, atrybuty Output -> output_dest.
    no_address=True: instancje bez adresów (puste, adresy wpisze uzytkownik w IDE).
    template_prefix: przedrostek nazwy szablonu po '$' ("t_" -> $t_<UDT>, "" -> $<UDT>)."""
    names = set()
    out = []
    for inst in instances:
        nm = fit(inst["name"], names, warn, "obiekt")
        adr = {a["name"]: ("" if no_address else
                           address(plc, scan_group, inst["parts"] + a["plc_parts"], a["plc_suffix"]))
               for a in attrs}
        entry = {"name": nm, "area": "", "security_group": "Default", "plc": plc,
                 "scan_group": scan_group, "db": inst["db"],
                 "plc_prefix": ".".join(inst["parts"]),
                 "input_source": {a["name"]: adr[a["name"]] for a in attrs if a["io"] != "Output"}}
        if any(a["io"] == "Output" for a in attrs):
            entry["output_dest"] = {a["name"]: adr[a["name"]] for a in attrs if a["io"] == "Output"}
        out.append(entry)
    if any(a["io"] == "Output" for a in attrs):
        warn.append("atrybuty Output (Write, #IO.Mode=WriteOnly, adres w OutputDest): format niepotwierdzony "
                    "eksportem z IDE; tryb Auto (GalaxyMCP 0.2.2) ich nie obsługuje - użyj trybu Manual")
    tpl = fit("$" + template_prefix + udt, set(), warn, "szablon")
    return {
        "spec_version": SPEC_VERSION,
        "generator": "scl_to_aveva.py",
        "source": source,
        "template": {"name": tpl, "base": "$UserDefined", "toolset": "Application",
                     "security_group": "Default", "udt": udt, "attributes": attrs},
        "instances": out,
        "warnings": list(warn),
    }


def load_spec(path):
    with open(path, encoding="utf-8-sig") as f:
        spec = json.load(f)
    if spec.get("spec_version") != SPEC_VERSION:
        sys.exit("Nieobsługiwana wersja specyfikacji: %s" % spec.get("spec_version"))
    return spec


# ---------------------------------------------------------------- generatory CSV (ze specyfikacji)
def csv_line(values):
    """Wiersz CSV: pola z przecinkiem lub cudzysłowem są cytowane (RFC 4180, jak w Excelu)."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(list(values))
    return buf.getvalue()


def row(cols, d):
    return csv_line(d.get(c, "") for c in cols)


def build_template(spec):
    t = spec["template"]
    L = HEADER.splitlines() + [
        f"${t['toolset']}\\{t['name']}{{{t['security_group']}}} -> {t['base']}",
        "&User-defined Attributes", ":" + csv_line(UDA_COLS)]
    for a in t["attributes"]:
        d = {"Attribute": a["name"], "Type": a["type"], "Value": a["default"],
             "LockStatus": "MxUnLocked", "SecurityClassification": "MxSecurityOperate",
             "Category": "MxCategoryWriteable_USC_Lockable",
             "#IO": "EnabledByMe", "#IO.Mode": IO_MODE[a["io"]]}
        if a["description"]:
            d.update({"Description": a["description"], "Description.LockStatus": "MxUnLocked",
                      "Description.SecurityClassification": "MxSecurityOperate"})
        if a["type"] == "MxBoolean":
            d.update({"#IO.InvertValue": "Disabled", "#IO.InvertValue.LockStatus": "MxUnLocked"})
        elif a["type"] in ("MxFloat", "MxInteger") and a["io"] != "Output":   # deadband dotyczy odczytu
            d.update({"#IO.Deadband": "0.0", "#IO.Deadband.LockStatus": "MxUnLocked",
                      "#IO.Deadband.SecurityClassification": "MxSecurityConfigure"})
        L.append(row(UDA_COLS, d))
    L += [SEP, "&Extended Attributes", ":" + csv_line(EXT_COLS)]
    for a in t["attributes"]:
        p = a["io"]
        b = {"Primitive": a["name"], "PrimitiveType": p, "LockStatus": "MxUnLocked"}
        if p == "InputOutput":
            L.append(row(EXT_COLS, {**b, "Attribute": "DiffOutputDest", "Value": "false"}))
        if p != "Output":
            L.append(row(EXT_COLS, {**b, "Attribute": "InputSource", "Value": "",   # BEZ adresu PLC
                                    "SecurityClassification": "MxSecurityConfigure"}))
        if p in WRITABLE:   # InputOutput: '---' = ten sam adres co InputSource; Output: pusty (adres w instancji)
            L.append(row(EXT_COLS, {**b, "Attribute": "OutputDest", "Value": "---" if p == "InputOutput" else "",
                                    "SecurityClassification": "MxSecurityConfigure"}))
    return L + [SEP] + TAIL


def build_instances(spec):
    """Format Galaxy Load. Bez adresów (--no-address) plik ma tylko Tagname, Area, SecurityGroup -
    puste kolumny <Attr>.InputSource nadpisałyby wartości z szablonu (wzorzec użytkownika 2026-09-23)."""
    attrs = spec["template"]["attributes"]
    if not any(v for i in spec["instances"] for d in (i.get("input_source", {}), i.get("output_dest", {}))
               for v in d.values()):
        attrs = []
    col = lambda a: "OutputDest" if a["io"] == "Output" else "InputSource"
    L = [f":TEMPLATE={spec['template']['name']}",
         ":" + csv_line(["Tagname", "Area", "SecurityGroup"] + [f"{a['name']}.{col(a)}" for a in attrs])]
    for i in spec["instances"]:
        src = {**i.get("input_source", {}), **i.get("output_dest", {})}
        L.append(csv_line([i["name"], i["area"], i["security_group"]]
                          + [src.get(a["name"], "") for a in attrs]))
    return L


def write(path, lines):   # UTF-8 z BOM + CRLF (jak eksport z IDE)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")


# ---------------------------------------------------------------- instancje z bloków danych
def db_instances(dbs, types, warn):
    """Z bloków DATA_BLOCK robi instancje. Zwraca {typ UDT: [{name, db, parts}]}, parts = ścieżka w PLC.
    - element typu UDT (także tablica UDT)  -> instancja <DB>_<element>[_i], adres <DB>.<element>[i]...
    - UDT wewnątrz STRUCT (dowolnie głęboko) -> instancja <DB>_<Struct>_<element>, adres <DB>.<Struct>.<element>...
    - DB typu UDT (DATA_BLOCK "X" "UDT_Y")  -> jedna instancja o nazwie DB, adres <DB>.<ścieżka w UDT>
    Zmienne proste w DB nie są instancją żadnego szablonu - pomijane z ostrzeżeniem."""
    per_type = {}

    def add(udt, name, db, parts):
        per_type.setdefault(udt, []).append({"name": name, "db": db, "parts": parts})

    def walk(db, members, names, path):
        for m in members:
            if m["kind"] == "typed_db":
                label = "%s (DB typu '%s')" % (db, m["type"])
                if m["type"] in types:
                    add(m["type"], clean_name(db, warn), db, [db])
                else:
                    warn.append("%s: brak definicji typu w podanych plikach (albo DB instancyjny bloku FB)"
                                " - pominięto" % label)
                continue
            label = ".".join([db] + path[1:] + [m["raw"]])
            if m["kind"] == "scalar":
                warn.append("%s: zmienna prosta (%s), nie instancja UDT - pominięta" % (label, m["type"]))
                continue
            if m["kind"] == "udt" and m["type"] not in types:
                warn.append("%s: brak definicji typu '%s' w podanych plikach - pominięto" % (label, m["type"]))
                continue
            base = clean_name(m["raw"], warn)
            for i in indices(m["dims"], label, warn):
                suffix = "" if i is None else "".join("_" + str(x).replace("-", "m") for x in i)
                part = m["raw"] + ("" if i is None else "[" + ",".join(str(x) for x in i) + "]")
                if m["kind"] == "struct":
                    walk(db, m["members"], names + [base + suffix], path + [part])
                else:
                    add(m["type"], "_".join(names + [base + suffix]), db, path + [part])

    for db, members in dbs.items():
        walk(db, members, [clean_name(db, warn)], [db])
    return per_type


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="plik .udt / .scl (typy), może też zawierać DATA_BLOCK")
    ap.add_argument("--db", nargs="*", default=[], help="pliki .db z blokami danych (instancje)")
    ap.add_argument("--from-spec", help="generuj CSV z gotowej specyfikacji JSON (zamiast plików z TIA)")
    ap.add_argument("--permissions", default="Permissions.csv")
    ap.add_argument("--rules", nargs="*", help="ręczne reguły Prefix=Input|InputOutput|Output")
    ap.add_argument("--plc", default="", help="nazwa obiektu DI (SIDirect) w galaktyce - wymagane, "
                                              "gdy adresowanie jest włączone")
    ap.add_argument("--scan-group", default="", help="grupa skanowania obiektu DI, np. SG1 (driver SIDirect)")
    ap.add_argument("--no-address", action="store_true",
                    help="adresowanie automatyczne wylaczone: InputSource/OutputDest w instancjach zostaja puste")
    ap.add_argument("--instances", nargs="*", default=[], help="Obiekt=DB ... (gdy nie ma pliku .db)")
    ap.add_argument("--type", nargs="*", default=[], help="tylko wskazane typy UDT")
    ap.add_argument("--all-types", action="store_true", help="także typy bez instancji")
    ap.add_argument("--template-prefix", default="t_",
                    help='przedrostek nazwy szablonu po "$": domyślnie "t_" ($t_<UDT>), '
                         'pusty ciąg = bez przedrostka ($<UDT>)')
    ap.add_argument("--out", default="Output")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if a.from_spec:
        spec = load_spec(a.from_spec)
        udt = spec["template"]["udt"]
        write(os.path.join(a.out, "%s.csv" % spec["template"]["name"]), build_template(spec))
        if spec["instances"]:
            write(os.path.join(a.out, "Instances_%s.csv" % udt), build_instances(spec))
        print("UDT\t%s\t%d\t%d" % (udt, len(spec["template"]["attributes"]), len(spec["instances"])))
        return
    if not a.src:
        ap.error("podaj plik z TIA (.udt/.scl) albo --from-spec")
    # obiekt DI wchodzi do każdego adresu - bez niego adresy byłyby niepoprawne, a błąd
    # wyszedłby dopiero w IDE albo na driverze, dlatego przerywamy od razu.
    if not a.no_address and not a.plc:
        ap.error("podaj --plc <obiekt DI w galaktyce> (i --scan-group), albo --no-address "
                 "dla instancji bez adresów")

    warn = []
    types, dbs = parse_source(open(a.src, encoding="utf-8-sig").read(), warn)
    for f in a.db:
        parse_source(open(f, encoding="utf-8-sig").read(), warn, types, dbs)
    if not types:
        sys.exit("W pliku %s nie ma bloku TYPE ... STRUCT (to nie jest plik z definicją UDT)." % a.src)
    rules = load_rules(a.permissions, a.rules, warn)
    source = ", ".join(os.path.basename(f) for f in [a.src] + list(a.db))

    if a.no_address:
        warn.append("adresowanie automatyczne wylaczone (--no-address): InputSource/OutputDest instancji są puste")
    elif not a.scan_group:
        warn.append("nie podano --scan-group: adresy nie mają grupy skanowania obiektu DI "
                    "(driver SIDirect oczekuje <obiekt DI>.<grupa>.<item>) - uzupełnij przed importem")
    inst_per_type = db_instances(dbs, types, warn) if dbs else {}
    manual = [tuple(s.split("=", 1)) for s in a.instances]
    if manual:
        if dbs:
            warn.append("podano --instances i plik .db - użyto tylko bloków danych z pliku")
        else:
            targets = a.type or list(types)
            if len(targets) != 1:
                sys.exit("--instances wymaga jednego typu: użyj --type <UDT> (plik ma: %s)" % ", ".join(types))
            inst_per_type[targets[0]] = [{"name": obj, "db": db, "parts": [db]} for obj, db in manual]

    chosen = [t for t in types if not a.type or t in a.type]
    unknown = [t for t in a.type if t not in types]
    if unknown:
        sys.exit("W plikach nie ma typów: %s (dostępne: %s)" % (", ".join(unknown), ", ".join(types)))
    if not a.all_types and inst_per_type:
        skipped = [t for t in chosen if t not in inst_per_type]
        if skipped:
            warn.append("typy bez instancji pominięte (--all-types żeby je wygenerować): " + ", ".join(skipped))
        chosen = [t for t in chosen if t in inst_per_type]

    for udt in chosen:
        tw = list(warn)
        attrs = attributes(udt, types, rules, tw)
        if not attrs:
            warn.append("typ '%s' nie ma obsługiwanych zmiennych - pominięty" % udt)
            continue
        spec = build_spec(udt, attrs, inst_per_type.get(udt, []), a.plc, a.scan_group, source, tw,
                          a.no_address, a.template_prefix)
        with open(os.path.join(a.out, "Spec_%s.json" % udt), "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        write(os.path.join(a.out, "%s.csv" % spec["template"]["name"]), build_template(spec))
        if spec["instances"]:
            write(os.path.join(a.out, "Instances_%s.csv" % udt), build_instances(spec))
        print("UDT\t%s\t%d\t%d" % (udt, len(attrs), len(spec["instances"])))
        for at in attrs:
            print("%s\t%s\t%s" % (at["name"], at["type"], IO_SHORT[at["io"]]))
        for w in spec["warnings"]:
            if w not in warn:                     # ogólne ostrzeżenia są wypisywane raz, na końcu
                print("WARN\t%s\t%s" % (udt, w), file=sys.stderr)
    for w in warn:
        print("WARN\t-\t%s" % w, file=sys.stderr)


if __name__ == "__main__":
    main()
