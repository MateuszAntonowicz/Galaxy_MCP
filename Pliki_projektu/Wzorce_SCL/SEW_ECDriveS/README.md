# Prawdziwe źródła SCL z projektu SEW ECDriveS_Positioning

Pliki w tym katalogu to oryginalne *External source files* (typy UDT i bloki DB) wyciągnięte z przykładowego
projektu TIA **SEW-EURODRIVE ECDriveS_Positioning V1.0** (luty 2019, TIA V14 → V15).
Pobrane z sew-eurodrive.com > Data & documents > Software, plik `SEW_ECDriveS_Positioning_V1.0.zip`.
Autor i właściciel treści: SEW-EURODRIVE GmbH & Co KG. Według README projektu to tylko program
przykładowy, bez odpowiedzialności producenta za jego działanie. Trzymane tu jako materiał
referencyjny składni i dane testowe dla generatora UDT → CSV.

## Skąd się wzięły

Zip nie zawiera plików tekstowych `.udt`/`.db`, tylko binarny projekt (`.ap14`). TIA przechowuje
jednak dołączone źródła zewnętrzne wewnątrz `System/PEData.plf`, jako strony po 4096 bajtów
skompresowane zlib. Odczytano je bez TIA (dekompresja kolejnych stron po nazwie pliku, usunięcie
dopełnienia zerami i znacznika BOM). `EC_Positioning_DB.db` był zapisany bez kompresji. Wersje
angielska i niemiecka projektu mają te same źródła. Zachowano oryginalną treść i końce linii CRLF.

| Plik | Zawartość |
|---|---|
| `ECCDFC_ALL_UDTs_rev1.7.udt` | 10 typów `ECCDFC*_IN/_OUT` (dane procesowe sterownika ECC-DFC-24-00 w trybach PLC i ZPA) |
| `MDRUDTs.udt` | typ `MDR_PM_Data` (dane identyfikacyjne silnika MDR); w projekcie SEW plik nazywał się `MDRUDTs.scl`, treść bez zmian |
| `IO_data.db` | globalny DB z **dostępem klasycznym** (`S7_Optimized_Access := 'FALSE'`), wartości startowe w `BEGIN` |
| `EC_Positioning_DB.db` | DB instancyjny FB: zamiast `VAR` sama nazwa bloku `"EC_Positioning"` |

Pominięto pliki `.scl` z projektu: `EC_Positioning.scl` (blok funkcyjny SEW i starsza wersja typów
`ECCDFCPLC_IN/_OUT`) oraz `ECCDFC ALL UDTs rev1.6.scl` (starsza wersja tych samych typów).

## Co z nich wynika dla składni

- DB z dostępem klasycznym deklaruje członków w `STRUCT ... END_STRUCT;`, a nie w `VAR ... END_VAR`.
- Atrybuty członków w praktyce: `{ ExternalAccessible := 'False'; ExternalVisible := 'False';
  ExternalWritable := 'False'}` oraz `{ S7_HMI_Visible := 'False'}` (kilka rozdzielonych `;`).
- Nazwy z nawiasami w cudzysłowie: `"Reserved[3]" : Bool;` (generator zamienia je na `Reserved_3_`).
- Typy bez TITLE/AUTHOR, tylko `VERSION : 0.1`; wiele typów `TYPE` w jednym pliku.
- DB instancyjny ma tę samą postać co DB typu UDT: nazwa bloku zamiast sekcji `VAR`.
