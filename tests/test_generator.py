"""Testy generatora Pliki_projektu/Tools/scl_to_aveva.py (bez galaktyki, bez Claude).

Uruchomienie z katalogu repozytorium:  python -m unittest discover -s tests -v
Pliki wejściowe: tests/dane/ (typy.udt - typy z zagnieżdżeniami, tablicami, nazwami do czyszczenia i elementami
do pominięcia; napedy.db - DB z instancjami w różnych układach; Permissions.csv - reguły ze średnikiem;
poprawki_025.udt/.db - nazwy ze spacjami, polskimi literami i różniące się tylko wielkością liter).
"""
import json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "Pliki_projektu", "Tools", "scl_to_aveva.py")
DANE = os.path.join(ROOT, "tests", "dane")

# Reguły specyfikacji takie jak w Spec.Parse serwera GalaxyMCP (GalaxyMcp.cs) - kontrola zgodności obu trybów.
MX = {"MxBoolean", "MxInteger", "MxFloat", "MxDouble", "MxString", "MxTime", "MxElapsedTime",
      "MxInternationalizedString", "MxBigString"}
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def server_errors(spec, allow_output=False):
    err, seen = [], set()
    for a in spec["template"]["attributes"]:
        n = a["name"]
        if not NAME.match(n): err.append("nazwa atrybutu " + n)
        if n.lower() in seen: err.append("zdublowany atrybut " + n)
        seen.add(n.lower())
        if a["type"] not in MX: err.append("typ " + a["type"])
        if a["io"] not in ("Input", "InputOutput") and not (allow_output and a["io"] == "Output"):
            err.append("io " + a["io"])
    inst = set()
    for i in spec["instances"]:
        if not NAME.match(i["name"]): err.append("nazwa instancji " + i["name"])
        if i["name"].lower() in inst: err.append("zdublowana instancja " + i["name"])
        inst.add(i["name"].lower())
        for k in i.get("input_source", {}):
            if k.lower() not in seen: err.append("InputSource " + k)
    return err


def run(*args, cwd=None):
    p = subprocess.run([sys.executable, "-I", GEN] + list(args), cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, p.stdout + p.stderr


def read_tree(d):
    out = {}
    for n in sorted(os.listdir(d)):
        with open(os.path.join(d, n), "rb") as f:
            out[n] = f.read()
    return out


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, "Out")
        cls.code, cls.log = run(os.path.join(DANE, "typy.udt"), "--db", os.path.join(DANE, "napedy.db"),
                                "--plc", "S7C_01", "--scan-group", "SG1",
                                "--permissions", os.path.join(DANE, "Permissions.csv"), "--out", cls.out)
        with open(os.path.join(cls.out, "Spec_UDT_Silnik.json"), encoding="utf-8") as f:
            cls.spec = json.load(f)
        cls.attrs = {a["name"]: a for a in cls.spec["template"]["attributes"]}
        cls.inst = {i["name"]: i for i in cls.spec["instances"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pliki_wyjsciowe(self):
        self.assertEqual(self.code, 0, self.log)
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["$t_UDT_Silnik.csv", "Instances_UDT_Silnik.csv", "Spec_UDT_Silnik.json"])

    def test_atrybuty_i_kierunki(self):
        self.assertEqual(len(self.attrs), 38)
        self.assertEqual(self.attrs["Cmd_Start"]["io"], "InputOutput")
        self.assertEqual(self.attrs["Cfg_Czas"]["io"], "InputOutput")      # Access_Mode „Read/Write”
        self.assertEqual(self.attrs["Status_Praca"]["io"], "Input")
        self.assertEqual(self.attrs["Reset_Alarm"]["io"], "Output")        # Access_Mode „Write”
        self.assertEqual(self.attrs["Cfg_Czas"]["type"], "MxInteger")      # TIME do zapisu = liczba ms
        self.assertEqual(self.attrs["Czas_Odczyt"]["plc_path"], "attribute(Czas_Odczyt T)")

    def test_atrybut_output_jak_eksport_ide(self):
        # Wzorzec: eksport IDE (SP 2026, 2026-11-23) atrybutu ustawionego na Write - #IO.Mode=WriteOnly,
        # w &Extended Attributes tylko OutputDest z PrimitiveType Output (bez InputSource i DiffOutputDest).
        with open(os.path.join(self.out, "$t_UDT_Silnik.csv"), encoding="utf-8-sig") as f:
            rows = [l.split(",") for l in f.read().splitlines()]
        uda = [r for r in rows if r[0] == "Reset_Alarm"]
        self.assertEqual(uda[0][16], "WriteOnly")
        ext = [r[1:4] for r in rows if len(r) > 3 and r[0] == "Reset_Alarm" and r[2] == "Output"]
        self.assertEqual(ext, [["OutputDest", "Output", ""]])
        self.assertNotIn("niepotwierdzony", self.log)

    def test_rozwijanie_i_nazwy(self):
        for n in ("Temp_1", "Temp_3", "Neg_m1", "Siatka_2_1", "stan_Stan_Aktywny", "Zawory_2_Kod_Bledu",
                  "Grupa_Temp_1", "KomendaHMIAktywuj"):
            self.assertIn(n, self.attrs)
        self.assertEqual(self.attrs["Neg_m1"]["plc_path"], "Neg[-1]")
        self.assertEqual(self.attrs["Siatka_2_1"]["plc_path"], "Siatka[2,1]")
        self.assertEqual(self.attrs["Grupa_Temp_1"]["plc_path"], 'attribute(Grupa."Temp-1")')
        for n in ("Dziwny", "Brak_Typu", "Stala_Tab"):                     # pominięte z ostrzeżeniem
            self.assertNotIn(n, self.attrs)

    def test_instancje_i_adresy(self):
        self.assertEqual(sorted(self.inst), sorted([
            "DB_Napedy_Pompa_01", "DB_Napedy_Pompa02", "DB_Napedy_Silniki_1", "DB_Napedy_Silniki_2",
            "DB_Napedy_Sekcja_A_Mieszadlo", "DB_Silnik_05", "DB_Kropka_M1"]))
        self.assertEqual(self.inst["DB_Napedy_Silniki_2"]["input_source"]["Zawory_2_Kod_Bledu"],
                         "S7C_01.SG1.DB_Napedy.Silniki[2].Zawory[2].Kod_Bledu")
        self.assertEqual(self.inst["DB_Napedy_Pompa02"]["input_source"]["Cmd_Start"],
                         'S7C_01.SG1.attribute(DB_Napedy."Pompa 02".Cmd_Start)')
        self.assertEqual(self.inst["DB_Kropka_M1"]["input_source"]["Cmd_Start"],
                         'S7C_01.SG1.attribute("DB.Kropka".M1.Cmd_Start)')
        self.assertEqual(self.inst["DB_Silnik_05"]["output_dest"]["Reset_Alarm"], "S7C_01.SG1.DB_Silnik_05.Reset_Alarm")

    def test_zgodnosc_ze_serwerem(self):
        # jedyna różnica dopuszczona: atrybuty Output (tryb Auto ich nie obsługuje - tylko Manual)
        self.assertEqual(server_errors(self.spec, allow_output=True), [])
        self.assertEqual(server_errors(self.spec), ["io Output"])

    def test_csv_z_specyfikacji_identyczne(self):
        with tempfile.TemporaryDirectory() as t:
            code, log = run("--from-spec", os.path.join(self.out, "Spec_UDT_Silnik.json"), "--out", t)
            self.assertEqual(code, 0, log)
            a, b = read_tree(self.out), read_tree(t)
            for n in ("$t_UDT_Silnik.csv", "Instances_UDT_Silnik.csv"):
                self.assertEqual(a[n], b[n], n)

    def test_powtarzalnosc(self):
        with tempfile.TemporaryDirectory() as t:
            run(os.path.join(DANE, "typy.udt"), "--db", os.path.join(DANE, "napedy.db"), "--plc", "S7C_01",
                "--scan-group", "SG1", "--permissions", os.path.join(DANE, "Permissions.csv"), "--out", t)
            self.assertEqual(read_tree(self.out), read_tree(t))

    def test_bledy_wejscia(self):
        with tempfile.TemporaryDirectory() as t:
            bad = os.path.join(t, "bad.csv")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("Prefix_,Access\nCmd_,InputOutput\n")
            code, log = run(os.path.join(DANE, "typy.udt"), "--db", os.path.join(DANE, "napedy.db"),
                            "--plc", "X", "--permissions", bad, "--out", os.path.join(t, "o"))
            self.assertNotEqual(code, 0)
            self.assertIn("Prefix_or_Keyword", log)
            code, log = run(os.path.join(DANE, "napedy.db"), "--plc", "X", "--out", os.path.join(t, "o2"))
            self.assertNotEqual(code, 0)                                   # sam plik .db nie wystarczy
            code, log = run(os.path.join(DANE, "typy.udt"), "--db", os.path.join(DANE, "napedy.db"),
                            "--out", os.path.join(t, "o3"))
            self.assertNotEqual(code, 0)                                   # brak --plc i --no-address



class Poprawki025(unittest.TestCase):
    """Błędy znalezione w teście z 2026-11-18, poprawione w GalaxyMCP 0.2.5 (generator)."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, "Out")
        cls.code, cls.log = run(os.path.join(DANE, "poprawki_025.udt"), "--db", os.path.join(DANE, "poprawki_025.db"),
                                "--plc", "S7C_01", "--scan-group", "SG1",
                                "--permissions", os.path.join(DANE, "Permissions.csv"), "--out", cls.out)
        with open(os.path.join(cls.out, "Spec_UDTMojtyp.json"), encoding="utf-8") as f:
            cls.spec = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_typ_ze_spacja_w_nazwie(self):                       # błąd 3: TYPE "UDT Mój typ" czytany jako UDT
        self.assertEqual(self.code, 0, self.log)
        self.assertEqual(self.spec["template"]["udt"], "UDT Mój typ")
        self.assertEqual(self.spec["template"]["name"], "$t_UDTMojtyp")
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["$t_UDTMojtyp.csv", "Instances_UDTMojtyp.csv", "Spec_UDTMojtyp.json"])
        self.assertEqual(self.spec["instances"][0]["db"], "DB Napęd 1")   # DB ze spacją też w całości

    def test_kolizje_bez_wielkosci_liter(self):                  # błąd 1: Stan_X i stan_x to ta sama nazwa
        names = [a["name"] for a in self.spec["template"]["attributes"]]
        self.assertEqual(names[:2], ["Stan_X", "stan_x_1"])
        self.assertEqual(len({n.lower() for n in names}), len(names))
        inst = [i["name"] for i in self.spec["instances"]]
        self.assertEqual(inst, ["DBNaped1_Silnik", "DBNaped1_SILNIK_1"])
        self.assertEqual(server_errors(self.spec), [])
        # adres zostaje przy oryginalnej nazwie z PLC
        self.assertEqual(self.spec["instances"][0]["input_source"]["stan_x_1"],
                         'S7C_01.SG1.attribute("DB Napęd 1".Silnik.stan_x)')

    def test_polskie_litery(self):                                # błąd 4: transliteracja zamiast '_'
        names = [a["name"] for a in self.spec["template"]["attributes"]]
        self.assertIn("Predkosczadana", names)
        self.assertIn('"Prędkość zadana"', self.spec["instances"][0]["input_source"]["Predkosczadana"])

    def test_nazwy_z_instances(self):                             # błąd 2: --instances bez czyszczenia nazw
        with tempfile.TemporaryDirectory() as t:
            code, log = run(os.path.join(DANE, "poprawki_025.udt"), "--plc", "S7", "--scan-group", "SG",
                            "--permissions", os.path.join(DANE, "Permissions.csv"),
                            "--instances", "Z 2=DB1", "Żuraw-1=DB2", "z2=DB3", "--out", t)
            self.assertEqual(code, 0, log)
            with open(os.path.join(t, "Spec_UDTMojtyp.json"), encoding="utf-8") as f:
                spec = json.load(f)
            self.assertEqual([i["name"] for i in spec["instances"]], ["Z2", "Zuraw_1", "z2_1"])
            self.assertEqual(server_errors(spec), [])
            code, log = run(os.path.join(DANE, "poprawki_025.udt"), "--plc", "S7", "--instances", "BezDB",
                            "--out", t)
            self.assertNotEqual(code, 0)
            self.assertIn("Obiekt=DB", log)

    def test_brak_pliku_uprawnien(self):                          # błąd 5: brak ostrzeżenia o --permissions
        with tempfile.TemporaryDirectory() as t:
            code, log = run(os.path.join(DANE, "poprawki_025.udt"), "--plc", "S7", "--instances", "A=DB1",
                            "--permissions", os.path.join(t, "brak.csv"), "--out", t)
            self.assertEqual(code, 0, log)
            self.assertIn("nie znaleziono pliku uprawnień", log)
            self.assertIn("brak.csv", log)

    def test_bez_starych_wersji_w_tekstach(self):                  # błąd 8: „GalaxyMCP 0.2.2” w ostrzeżeniu
        with open(GEN, encoding="utf-8") as f:
            self.assertNotIn("GalaxyMCP 0.2.2", f.read())


class Wzorce(unittest.TestCase):
    """Wzorcowe pliki Pliki_projektu/Wzorce_SCL/ muszą być czytane przez generator bez błędów składni."""

    def test_wzorce_scl(self):
        wz = os.path.join(ROOT, "Pliki_projektu", "Wzorce_SCL")
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "o")
            code, log = run(os.path.join(wz, "UDT_Wzorzec.udt"), "--db", os.path.join(wz, "DB_Wzorzec_Globalny.db"),
                            os.path.join(wz, "DB_Wzorzec_Typu_UDT.db"), "--plc", "PLC1", "--scan-group", "SG1",
                            "--out", out)
            self.assertEqual(code, 0, log)
            self.assertNotIn("nie rozpoznano", log)
            with open(os.path.join(out, "Spec_UDT_Wz_Naped.json"), encoding="utf-8") as f:
                spec = json.load(f)
            self.assertEqual(len(spec["template"]["attributes"]), 28)
            self.assertEqual(sorted(i["name"] for i in spec["instances"]),
                             ["DB_Wz_Napedy_Pompa_01", "DB_Wz_Napedy_Pompa_02", "DB_Wz_Napedy_Sekcja_B_Mieszadlo",
                              "DB_Wz_Napedy_Wentylatory_1", "DB_Wz_Napedy_Wentylatory_2",
                              "DB_Wz_Napedy_Wentylatory_3", "DB_Wz_Pompa_03"])
            self.assertEqual(server_errors(spec), [])

    def test_zrodla_sew(self):
        sew = os.path.join(ROOT, "Pliki_projektu", "Wzorce_SCL", "SEW_ECDriveS")
        with tempfile.TemporaryDirectory() as t:
            code, log = run(os.path.join(sew, "ECCDFC_ALL_UDTs_rev1.7.udt"), "--db", os.path.join(sew, "IO_data.db"),
                            "--all-types", "--no-address", "--out", os.path.join(t, "o"))
            self.assertEqual(code, 0, log)
            self.assertNotIn("nie rozpoznano", log)
            self.assertEqual(len([n for n in os.listdir(os.path.join(t, "o")) if n.startswith("Spec_")]), 10)


class Repozytorium(unittest.TestCase):
    """Pliki serwera w Pliki_projektu/Tools muszą być takie same jak w najnowszym GalaxyMcp/GalaxyMcp_<wersja>."""

    def test_tools_zgodne_z_najnowsza_wersja(self):
        base = os.path.join(ROOT, "GalaxyMcp")
        vers = [d for d in os.listdir(base) if re.fullmatch(r"GalaxyMcp_\d+\.\d+\.\d+", d)]
        newest = max(vers, key=lambda d: tuple(int(x) for x in d.split("_")[1].split(".")))
        tools = os.path.join(ROOT, "Pliki_projektu", "Tools")
        pairs = {"GalaxyMcp.cs": "GalaxyMcp.cs", "manifest.json": "GalaxyMcp_manifest.json",
                 "README.md": "GalaxyMcp_README.md", "build.bat": "GalaxyMcp_build.bat",
                 "pack_mcpb.bat": "GalaxyMcp_pack_mcpb.bat"}
        for src, dst in pairs.items():
            with open(os.path.join(base, newest, src), "rb") as a, open(os.path.join(tools, dst), "rb") as b:
                self.assertEqual(a.read(), b.read(), "%s/%s różni się od Tools/%s" % (newest, src, dst))
        with open(os.path.join(tools, "GalaxyMcp_manifest.json"), encoding="utf-8") as f:
            version = json.load(f)["version"]
        self.assertEqual(newest, "GalaxyMcp_" + version)
        with open(os.path.join(tools, "GalaxyMcp.cs"), encoding="utf-8") as f:
            self.assertIn('Version = "%s"' % version, f.read())

    def test_instrukcja_projektu_miesci_sie_w_ustawieniach(self):
        """Instrukcja projektu jest wklejana w całości w Project instructions (limit pola: 16 000 znaków)."""
        with open(os.path.join(ROOT, "Pliki_projektu", "Tools", "Instrukcja_projektu.md"), encoding="utf-8") as f:
            instr = f.read()
        with open(os.path.join(ROOT, "Konfiguracja_projektu", "Project_instructions_ustawienia.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), instr, "Project_instructions_ustawienia.txt różni się od Tools/Instrukcja_projektu.md")
        self.assertLess(len(instr), 16000, "Instrukcja_projektu.md ma %d znaków – skróć ją poniżej 16 000" % len(instr))


if __name__ == "__main__":
    unittest.main()
