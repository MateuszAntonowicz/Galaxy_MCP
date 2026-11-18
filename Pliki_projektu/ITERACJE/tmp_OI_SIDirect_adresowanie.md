# OI SIDirect – adresowanie symboliczne i typy (wnioski z dokumentacji)

Źródło: **AVEVA™ Communication Drivers Pack – Siemens – SIDIRECT Driver, User Guide**, publikacja 2020-11-18
(plik `OISIDIR.pdf`, 137 stron; numery stron w nawiasach). Dokument dostarczył użytkownik 2026-09-17.
Dotyczy S7-1200 / S7-1500 z adresowaniem **symbolicznym** (obiekt *SIDirect Symbolic*; obiekt *Legacy* obsługuje
tylko adresy absolutne typu `DB1,B20` i **nie** obsługuje adresowania symbolicznego, s. 85).

## 1. Składnia itemu (to, czego szukaliśmy)

| Przypadek | Składnia | Przykład z dokumentacji |
| :--- | :--- | :--- |
| Typ podstawowy | `[DataBlockName].[SymbolicTagName]` | `DB5_INT.TAG_INT` (s. 85) |
| Tablica / struktura | `[DataBlockName].[SymbolicTagName]<[ArrayIndex]>.<MemberName>` | `Kettle2.PigmentTube[4]`, `Data_block_Items.IEC_Timer1.CV` (s. 85) |
| UDT (dowolna głębokość) | `[DataBlockName].{[StructTagName]<[ArrayIndex]>}.[MemberName]<[ArrayIndex]>` | `ProductionRoom.Reactor1.Concentrate_Pump.Motor_OL`, `FoodPlant.CookDeck[1].IngredientTanks[2,5].InletValve` (s. 86) |
| DB o tej samej nazwie co struktura | `[DataBlockName].THIS[i].<MemberName>` | `PUMP.THIS[0].Speed` (s. 86) |
| Tag PLC (I/O, pamięć, licznik, timer) | `[PLCTagName]` | `PLCTag_Byte`, `PLCTag_Timer` (s. 86) |

**Indeks tablicy wielowymiarowej podaje się w jednym nawiasie, po przecinku: `IngredientTanks[2,5]`** (s. 86).
Indeksy mogą być od -n do n, włącznie z zerem (s. 85).

## 2. Nazwy ze spacją lub kropką – rozwiązanie problemu z nazewnictwem

Cytat (s. 96): *„The symbolic tag names supports space and period characters in item syntax. For the names of the
data block, tag, or member with a space or a period, write it within the double quotes”*.

Odwołanie w Application Server (kolumna „In UDO” = to, co wpisujemy w `InputSource` atrybutu):

| DB | Tag | Member | Odwołanie w Application Server |
| :--- | :--- | :--- | :--- |
| DB | Tag | Member | `DB.Tag.Member` |
| DB | Tag | `Mem D` | `attribute(DB.Tag."Mem D")` |
| `DB D2` | `Tag T2` | `Mem M2` | `attribute("DB D2"."Tag T2"."Mem M2")` |
| `DB.D2` | `Tag.T2` | `Mem.M2` | `attribute("DB.D2"."Tag.T2"."Mem.M2")` |
| DB | `T2[0]` | Mem | `attribute(DB.T2[0].Mem)` |
| DB | `T1 T2[2]` | Mem | `attribute(DB."T1 T2"[2].Mem)` |

**Wnioski:**

- Cudzysłowy obejmują **samą nazwę**, a indeks zostaje poza nimi: `"T1 T2"[2]`.
- Gdy w itemie jest cudzysłów (albo spacja), całe odwołanie trzeba owinąć w **`attribute( ... )`**.
- Bez znaków specjalnych piszemy zwyczajnie, bez `attribute()`.

## 3. Pełny adres w `InputSource`

Z przykładu składni dla VT_Array (s. 84):

```
S7C_S7_001.SG1.attribute(DB111,WORD10,4)[-1]
<SIDirect_DiDevice_Instance>.<ScanGroup>.attribute(<item>)
```

Czyli adres w atrybucie to **`<obiekt DI w galaktyce>.<grupa skanowania>.<item>`**. Grupa skanowania („device group”)
to nazwa zakładana w konfiguracji drivera (zakładka *Device Groups*, s. 23) i **musi** być częścią adresu.
Dotąd generator pomijał ten element – to była luka.

Dla tablic typu VT_Array (czytanych jako całość) driver wymaga dodatkowego przesunięcia `[-1]` (s. 84).
Nasz generator rozwija tablice na osobne atrybuty, więc tego nie używamy.

## 4. Limity drivera (s. 87)

| Limit | Wartość |
| :--- | :--- |
| Długość nazwy symbolicznej w tabeli DB | 128 znaków |
| Liczba wymiarów tablicy | 6 |
| Liczba elementów tablicy | 1600 |
| Głębokość zagnieżdżenia struktury | 8 poziomów |
| Liczba składowych struktury | 252 |

Limit 32 znaków pochodzi z ArchestrA, nie z drivera. Od 2026-09-18 (decyzja użytkownika) generator i GalaxyMcp 0.2.2
nie skracają żadnych nazw – ani atrybutów, ani szablonów, ani instancji.

## 5. Mapowanie typów (Auto-Build, s. 35–36)

| Siemens | AVEVA | Uwaga |
| :--- | :--- | :--- |
| BOOL | MxBoolean | |
| BYTE, USINT, SINT, INT, UINT, WORD, DINT, UDINT, DWORD, BITSET8/16/32 | MxInteger | |
| LINT, LWORD, ULINT, UINT64, BITSET64 | MxInteger | 64 bity w 32-bitowym MxInteger – ostrzegamy |
| REAL | MxFloat | |
| **LREAL, DOUBLE** | **MxDouble** | wcześniej mieliśmy MxFloat – poprawione |
| CHAR, STRING, WCHAR, WSTRING | MxString | |
| TIME (TIMESPAN) | MxElapsedTime | |
| **LTIME, S5TIME, TIME_OF_DAY, LTIME_OF_DAY, LDT, DATE** | **MxTime** | wcześniej LTIME mieliśmy jako MxElapsedTime |

## 6. Sufiksy typów czasowych (s. 87–89, 97–98)

Driver udostępnia typy czasu na dwa sposoby:

| Typ | Bez sufiksu | Z sufiksem |
| :--- | :--- | :--- |
| Time | VT_I4, milisekundy, **Read/Write** | `T` → tekst, **Read only** |
| LTime | VT_I8, nanosekundy, Read/Write | `LT` → tekst, Read only |
| S5Time | VT_I4, milisekundy, Read/Write | `S5T` → tekst, Read only |
| Time_Of_Day | VT_UI4, milisekundy, Read/Write | `TOD` → tekst, Read only |
| Date | VT_UI2, dni od 1990-01-01, Read/Write | `D` → tekst, Read only |
| LDT | VT_UI8, nanosekundy, Read/Write | `LDT` → tekst, Read/Write |
| Date_And_Time | VT_Date, Read/Write | `DT` → tekst, Read/Write; **sufiks DT wymagany dla SuiteLink** |

Sufiks pisze się po nazwie, po spacji: `MyTime T`, `MyDate D` (s. 97–98). Spacja oznacza, że item trzeba owinąć
w `attribute(...)`.

**Wniosek dla generatora:** atrybut tylko do odczytu → typ czasowy z sufiksem; atrybut do zapisu → ten sam item
bez sufiksu, ale jako `MxInteger` w jednostce z tabeli. Inaczej powstałby atrybut RW, którego driver nie zapisze.

`DTL` w adresowaniu symbolicznym jest strukturą (`.YEAR`, `.MONTH`, `.DAY`, `.WEEKDAY`, `.HOUR`, `.MINUTE`,
`.SECOND`, `.NANOSECOND`), której składowe są **tylko do odczytu** (s. 88–89). W adresowaniu absolutnym (Legacy)
DTL można czytać i zapisywać jako całość tekstem (s. 83–84). Generator zostawia DTL jako jeden atrybut MxTime
i dodaje ostrzeżenie – do potwierdzenia w Object Viewer.

## 7. Pozostałe przydatne fakty

- **Auto-Build** (rozdz. 4) potrafi sam zbudować szablony i instancje z bazy tagów PLC: typy PDT i UDT → szablony,
  tagi globalne → instancje i atrybuty. Wymaga licencji *Professional Communication Driver*, instalacji na węźle GR
  i IE 11 (s. 31–34). Nie wspiera: adresów tagów, komentarzy, retain, ustawień widoczności HMI (s. 34–35).
  To alternatywa dla naszej ścieżki – warto zobaczyć, co wygeneruje, i porównać z naszymi szablonami.
- **Walidacja itemów** jest opóźniona: driver dodaje item bez sprawdzenia i dopiero po zapytaniu PLC ustawia typ.
  Gdy baza tagów PLC jest niedostępna, item przyjmuje typ VT_EMPTY (s. 100). Zły adres nie musi więc od razu
  dać błędu – trzeba patrzeć na jakość (quality) i Log Viewer.
- **S7-1200/1500 wymaga przygotowania**: „Special Pre-Configuration for S7-1200 and S7-1500 PLCs” (s. 14) –
  m.in. zgoda na dostęp PUT/GET i wyłączenie „Optimized Block Access” tam, gdzie używa się adresów absolutnych
  (symbolicznie działa niezależnie od tej opcji, s. 85).
- `$SYS$Status` służy do monitorowania łączności z PLC (0 = brak, 1 = OK).

## 8. Co z tego zmieniło się w projekcie (2026-09-17)

1. Adres: `<obiekt DI>.<grupa skanowania>.<item>`; nowy parametr skryptu `--scan-group`.
2. Cudzysłowy tylko na nazwie, indeks poza nimi, całość w `attribute(...)`, gdy trzeba.
3. Tablice wielowymiarowe są obsługiwane (`[i,j]`), z limitami 6 wymiarów i 1600 elementów.
4. Mapowanie typów: LReal → MxDouble, LTime/S5Time/TOD/LDT/Date → MxTime, dodane LInt/LWord/ULInt.
5. Typy czasowe: sufiks dla odczytu, MxInteger bez sufiksu dla zapisu.
6. Ostrzeżenia o limitach drivera: 128 znaków nazwy, 8 poziomów zagnieżdżenia, 252 składowe, liczba elementów tablicy.
7. `TypeMapping.json` przepisany zgodnie z tabelą Auto-Build (z sufiksami i uwagami).

## 9. Zakres: tylko SIDirect

Ustalenie z 2026-09-17: projekt celuje w driver **SIDirect** (adresowanie symboliczne). W galaktyce wzorcowej
`VWPNPGGalaxy` w Device Integration są `$DDESuiteLinkClient`, `$OPCClient` i `$RedundantDIObject`, a nie ma
obiektu SIDirect – to znaczy, że tamten projekt komunikuje się inaczej (DDE/SuiteLink albo OPC UA).
Traktujemy to jako informację o środowisku, nie jako wzorzec adresowania. Gdyby kiedyś trzeba było wspierać
OPC UA lub DDE/SuiteLink, format `InputSource` jest inny (`<obiekt>.<topic>.<item>` dla DDE/SL) i wymaga
osobnej decyzji oraz zmiany generatora.

## 10. Do sprawdzenia w praktyce

- Nazwa obiektu DI i grupy skanowania w galaktyce (u nas w plikach: `PLC_01` i `SG1` jako wartości zastępcze).
- Czy `attribute("...")` przechodzi przez import CSV w IDE (w trybie Auto zapis idzie przez GRAccess, nie CSV).
- Czy DTL da się czytać jako jeden atrybut w adresowaniu symbolicznym.
- Czy Auto-Build z drivera daje te same szablony co nasz generator (porównanie wartościowe, gdy będzie licencja).
- ~~Czy IDE i GRAccess przyjmują nazwy dłuższe niż 32 znaki~~ – tak, potwierdził użytkownik 2026-09-23.

## 2026-11-18 – nowy tekst dokumentacji drivera
- `OISIDIR_tekst.txt` podmieniony na pełniejszy tekst z `OISIDIR.pdf` od użytkownika (AVEVA Communication Drivers Pack – Siemens –
  SIDIRECT Driver User Guide, © 2015-2023): ten sam podręcznik, ale z numerami stron („Page 98”) – przy cytowaniu podawaj stronę.
  Sufiksy symboliczne (D, LDT, LT, S5T, T, TOD) są na stronach 98–100; DTL bez sufiksu = tekst (VT_BSTR), z TREAL = data (VT_DATE)
  – tylko adresowanie absolutne (strony 79–84).
