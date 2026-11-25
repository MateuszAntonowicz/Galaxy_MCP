// GalaxyMCP - serwer MCP (stdio) dla galaktyki AVEVA System Platform przez GRAccess.
//
// Zasady projektu:
//  * Serwer NIE zna SCL. Przyjmuje specyfikację JSON (Spec_<UDT>.json) z scl_to_aveva.py
//    i tylko ją wykonuje: szablon + atrybuty UDA + rozszerzenia I/O + instancje + InputSource.
//  * Od 0.2.3: wszystkie typy danych UDA z IDE (Boolean, Integer, Float, Double, String, Time, ElapsedTime,
//    InternationalizedString, BigString) oraz atrybuty UDA dodawane do pojedynczej instancji
//    (instances[].attributes w specyfikacji) z wartością początkową i kierunkiem I/O.
//  * Domyślnie dry_run=true (tylko plan). Zapis wymaga dry_run=false. Deploy domyślnie wyłączony.
//  * Istniejące obiekty/atrybuty nie są usuwane ani przebudowywane (tylko dopisywane / aktualizowane InputSource).
//  * C# 5, .NET Framework 4.x, bez NuGet. GRAccess ładowany w czasie działania (Assembly.LoadFrom),
//    wywołania przez interfejsy interop (wiązanie wczesne, klasa Com) - różnice między wersjami GRAccess
//    wychodzą jako czytelne błędy. GalaxyMcp.exe --dump-api zapisuje opis API biblioteki do GRAccess_API.txt.
//  * Sesja GRAccess nie trzyma obiektów: po zapisie obiekt jest zwalniany (Unload), a po narzędziu zapisującym
//    (apply_spec z dry_run=false, import_csv, deploy) serwer wylogowuje się z galaktyki - inaczej Check-in
//    tego obiektu w ArchestrA IDE kończy się błędem (obiekt edytowany w innej sesji tego samego użytkownika).
//  * stdout = wyłącznie JSON-RPC. Logi -> stderr + GalaxyMcp.log obok .exe.
//
// Konfiguracja (zmienne środowiskowe):
//  GALAXY_NAME (galaktyka na start, opcjonalna), GALAXY_NODE (domyślnie ten komputer), GALAXY_USER, GALAXY_PASSWORD,
//  GALAXY_ALLOWED (lista galaktyk do przełączania, np. test_mcp,test_1; puste = wszystkie z węzła),
//  GALAXY_WRITABLE (lista galaktyk z prawem zapisu; puste = wszystkie dozwolone),
//  GALAXY_READONLY=1|true (blokuje zapis wszędzie), GALAXY_ALLOW_DEPLOY=1|true (włącza narzędzie deploy),
//  GRACCESS_DLL (ścieżka do ArchestrA.GRAccess.dll, gdy nie jest w domyślnym miejscu).
//  Instalacja jako rozszerzenie Claude Desktop: manifest.json + pack_mcpb.bat (GalaxyMcp.mcpb).
//  Puste pola z .mcpb docierają jako "${user_config.x}" i są traktowane jak brak wartości.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

namespace GalaxyMcp
{
    // ======================================================================= protokół MCP
    static class Program
    {
        public const string Version = "0.2.8";
        public static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        static readonly string[] Protocols = { "2025-06-18", "2025-03-26", "2024-11-05" };
        static TextWriter Out;
        public static readonly Galaxy G = new Galaxy();

        [STAThread]   // GRAccess to COM - wszystkie wywołania w jednym wątku STA
        static int Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--version")   // dla pack_mcpb.bat: kontrola zgodności z manifest.json
            {
                Console.Out.WriteLine(Version);
                return 0;
            }
            var stdin = new StreamReader(Console.OpenStandardInput(), new UTF8Encoding(false));
            var stdout = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false));
            stdout.AutoFlush = true;
            Out = stdout;
            Console.SetOut(Console.Error);   // przypadkowe Console.Write nie zepsuje protokołu
            AppDomain.CurrentDomain.UnhandledException += (s, e) =>
                Log.Error("NIEOBSŁUŻONY WYJĄTEK: " + e.ExceptionObject);
            Log.Info("proces " + (Environment.Is64BitProcess ? "64" : "32") + "-bit, CLR " + Environment.Version +
                     ", wątek " + System.Threading.Thread.CurrentThread.GetApartmentState());
            Log.Info("GalaxyMCP " + Version + " start, galaktyka='" + G.Name + "', węzeł='" + G.Node + "'");

            if (args.Length > 0 && args[0] == "--selftest")
                return SelfTest();
            if (args.Length > 0 && args[0] == "--dump-api")
            {
                try
                {
                    G.Asm();
                    var path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "GRAccess_API.txt");
                    File.WriteAllText(path, Com.DumpApi(), new UTF8Encoding(true));
                    Console.Error.WriteLine("Zapisano opis API: " + path);
                    return 0;
                }
                catch (Exception ex) { Console.Error.WriteLine("BŁĄD: " + ex.Message); return 1; }
            }

            // 0.2.2: serwer kończy pracę, gdy Claude Desktop wyłączy wtyczkę albo zostanie zamknięty
            // (koniec stdin albo zniknięcie procesu nadrzędnego) - nie zostaje w tle i nie blokuje build.bat.
            ParentWatch.Start();

            string line;
            while ((line = stdin.ReadLine()) != null)
            {
                line = line.Trim();
                if (line.Length == 0) continue;
                Dictionary<string, object> msg = null;
                try { msg = Json.DeserializeObject(line) as Dictionary<string, object>; }
                catch (Exception ex) { Send(Error(null, -32700, "Parse error: " + ex.Message)); continue; }
                if (msg == null) { Send(Error(null, -32600, "Invalid request")); continue; }
                var resp = Handle(msg);
                if (resp != null) Send(resp);
            }
            Shutdown("koniec stdin (wtyczka wyłączona albo Claude Desktop zamknięty)");
            return 0;
        }

        // Wylogowanie z galaktyki i twarde zakończenie procesu. Gdy Logout (COM) się zawiesi,
        // proces i tak kończy się po 5 s - nic nie może trzymać GalaxyMcp.exe w pamięci.
        public static void Shutdown(string reason)
        {
            Log.Info("GalaxyMCP stop: " + reason);
            var killer = new System.Threading.Thread(() => { System.Threading.Thread.Sleep(5000); Environment.Exit(0); });
            killer.IsBackground = true;
            killer.Start();
            try { G.Dispose(); } catch { }
            Environment.Exit(0);
        }

        static int SelfTest()
        {
            try
            {
                Console.Error.WriteLine(Tools.Status());
                Console.Error.WriteLine("Galaktyki na węźle: " + string.Join(", ", G.GalaxyNames()));
                G.Connect();
                Console.Error.WriteLine("OK: zalogowano do galaktyki " + G.Name);
                G.Dispose();
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("BŁĄD: " + ex.Message);
                Log.Error(ex.ToString());
                return 1;
            }
        }

        static Dictionary<string, object> Handle(Dictionary<string, object> msg)
        {
            string method = J.Str(msg, "method");
            if (method == null || !msg.ContainsKey("id")) return null;   // notyfikacje i odpowiedzi klienta
            object id = msg["id"];
            var prm = J.Obj(msg, "params");
            try
            {
                switch (method)
                {
                    case "initialize": return Result(id, Initialize(prm));
                    case "ping": return Result(id, new Dictionary<string, object>());
                    case "tools/list": return Result(id, new Dictionary<string, object> { { "tools", Tools.List() } });
                    case "tools/call": return Result(id, Tools.Call(J.Str(prm, "name"), J.Obj(prm, "arguments")));
                    default: return Error(id, -32601, "Method not found: " + method);
                }
            }
            catch (Exception ex)
            {
                Log.Error(ex.ToString());
                return Error(id, -32603, ex.Message);
            }
        }

        static Dictionary<string, object> Initialize(Dictionary<string, object> prm)
        {
            string asked = J.Str(prm, "protocolVersion", Protocols[0]);
            return new Dictionary<string, object> {
                { "protocolVersion", Protocols.Contains(asked) ? asked : Protocols[0] },
                { "capabilities", new Dictionary<string, object> { { "tools", new Dictionary<string, object>() } } },
                { "serverInfo", new Dictionary<string, object> { { "name", "galaxy-mcp" }, { "version", Version } } },
                { "instructions",
                  "Serwer galaktyki AVEVA System Platform. Przyjmuje specyfikację JSON z scl_to_aveva.py. " +
                  "Zawsze najpierw apply_spec z dry_run=true i pokaż plan użytkownikowi; zapis (dry_run=false) " +
                  "i deploy tylko po jego wyraźnym potwierdzeniu. Galaktykę zmienia select_galaxy; przy zapisie " +
                  "podawaj parametr galaxy = nazwa galaktyki potwierdzona przez użytkownika." }
            };
        }

        static void Send(Dictionary<string, object> m) { Out.WriteLine(Json.Serialize(m)); }

        static Dictionary<string, object> Result(object id, object result)
        {
            return new Dictionary<string, object> { { "jsonrpc", "2.0" }, { "id", id }, { "result", result } };
        }

        static Dictionary<string, object> Error(object id, int code, string message)
        {
            return new Dictionary<string, object> {
                { "jsonrpc", "2.0" }, { "id", id },
                { "error", new Dictionary<string, object> { { "code", code }, { "message", message } } } };
        }
    }

    // ======================================================================= nadzór procesu nadrzędnego
    // Claude Desktop uruchamia serwer jako proces potomny. Jeśli rodzic zniknie (wyłączenie wtyczki, zamknięcie
    // aplikacji, awaria), a stdin nie zostanie zamknięty, serwer kończy się sam - sprawdzenie co 2 s.
    static class ParentWatch
    {
        [StructLayout(LayoutKind.Sequential)]
        struct PROCESS_BASIC_INFORMATION
        {
            public IntPtr Reserved1, PebBaseAddress, Reserved2_0, Reserved2_1, UniqueProcessId, InheritedFromUniqueProcessId;
        }

        [DllImport("ntdll.dll")]
        static extern int NtQueryInformationProcess(IntPtr process, int infoClass, ref PROCESS_BASIC_INFORMATION info,
                                                    int size, out int returnLength);

        static int ParentId()
        {
            var pbi = new PROCESS_BASIC_INFORMATION();
            int len;
            using (var me = System.Diagnostics.Process.GetCurrentProcess())
                if (NtQueryInformationProcess(me.Handle, 0, ref pbi, Marshal.SizeOf(pbi), out len) != 0) return 0;
            return pbi.InheritedFromUniqueProcessId.ToInt32();
        }

        public static void Start()
        {
            System.Diagnostics.Process parent = null;
            try
            {
                int ppid = ParentId();
                if (ppid > 0)
                {
                    parent = System.Diagnostics.Process.GetProcessById(ppid);
                    // PID mógł zostać użyty ponownie: rodzic musi być starszy od nas
                    try
                    {
                        using (var me = System.Diagnostics.Process.GetCurrentProcess())
                            if (parent.StartTime > me.StartTime) parent = null;
                    }
                    catch { }   // brak dostępu do StartTime - nadzór i tak działa
                }
            }
            catch (Exception ex) { Log.Info("nadzór rodzica niedostępny: " + ex.Message); parent = null; }
            if (parent == null) { Log.Info("nadzór rodzica: brak procesu nadrzędnego - tylko koniec stdin"); return; }
            Log.Info("nadzór rodzica: " + parent.ProcessName + " (PID " + parent.Id + ")");
            var t = new System.Threading.Thread(() =>
            {
                while (true)
                {
                    System.Threading.Thread.Sleep(2000);
                    bool gone;
                    try { gone = parent.HasExited; } catch { gone = false; }
                    if (gone) { Log.Info("GalaxyMCP stop: proces nadrzędny zakończony"); Environment.Exit(0); }
                }
            });
            t.IsBackground = true;
            t.Start();
        }
    }

    // ======================================================================= narzędzia
    static class Tools
    {
        static Dictionary<string, object> Prop(string type, string desc, params object[] extra)
        {
            var p = new Dictionary<string, object> { { "type", type }, { "description", desc } };
            for (int i = 0; i + 1 < extra.Length; i += 2) p[(string)extra[i]] = extra[i + 1];
            return p;
        }

        static Dictionary<string, object> Tool(string name, string desc, Dictionary<string, object> props, params string[] required)
        {
            var schema = new Dictionary<string, object> { { "type", "object" }, { "properties", props } };
            if (required.Length > 0) schema["required"] = required;
            return new Dictionary<string, object> { { "name", name }, { "description", desc }, { "inputSchema", schema } };
        }

        public static List<object> List()
        {
            var t = new List<object>();
            t.Add(Tool("galaxy_status",
                "Konfiguracja serwera i test połączenia z galaktyką (węzeł, nazwa, użytkownik, tryb tylko-do-odczytu, deploy).",
                new Dictionary<string, object>()));
            t.Add(Tool("list_galaxies",
                "Lista galaktyk na węźle GR z oznaczeniem: aktywna, dozwolona do przełączenia, zapis/tylko odczyt.",
                new Dictionary<string, object>()));
            t.Add(Tool("select_galaxy",
                "Przełącza serwer na inną galaktykę (wyloguje z bieżącej i zaloguje do wskazanej). " +
                "Dozwolone tylko galaktyki z GALAXY_ALLOWED. Nie zapisuje niczego w galaktyce.",
                new Dictionary<string, object> {
                    { "name", Prop("string", "Nazwa galaktyki, np. test_mcp") } },
                "name"));
            t.Add(Tool("list_objects",
                "Lista szablonów albo instancji w galaktyce, których nazwa pasuje do wzorca (znak % = dowolny ciąg).",
                new Dictionary<string, object> {
                    { "kind", Prop("string", "template albo instance", "enum", new[] { "template", "instance" }) },
                    { "pattern", Prop("string", "Wzorzec nazwy, np. %Mixer% (domyślnie %)") } },
                "kind"));
            t.Add(Tool("get_object",
                "Szczegóły obiektu (szablonu lub instancji) i wartości jego atrybutów konfiguracyjnych.",
                new Dictionary<string, object> {
                    { "name", Prop("string", "Tagname obiektu, np. Mixer_01 albo $t_UDT_Mixer") },
                    { "attribute_filter", Prop("string", "Fragment nazwy atrybutu, np. InputSource (opcjonalnie)") } },
                "name"));
            t.Add(Tool("apply_spec",
                "Wykonuje specyfikację z scl_to_aveva.py: tworzy szablon z atrybutami UDA i rozszerzeniami I/O, " +
                "tworzy instancje, dodaje instancjom własne atrybuty UDA (instances[].attributes) i ustawia InputSource. " +
                "Typy UDA: MxBoolean, MxInteger, MxFloat, MxDouble, MxString, MxTime, MxElapsedTime, " +
                "MxInternationalizedString, MxBigString. Domyślnie dry_run=true - zwraca tylko plan. " +
                "Nie usuwa ani nie przebudowuje istniejących obiektów/atrybutów.",
                new Dictionary<string, object> {
                    { "spec", Prop("object", "Zawartość pliku Spec_<UDT>.json") },
                    { "spec_path", Prop("string", "Alternatywnie: ścieżka do pliku Spec_<UDT>.json na tym komputerze") },
                    { "dry_run", Prop("boolean", "true = tylko plan (domyślnie), false = zapis do galaktyki") },
                    { "scope", Prop("string", "all (domyślnie), template albo instances", "enum", new[] { "all", "template", "instances" }) },
                    { "galaxy", Prop("string", "Wymagane przy zapisie (dry_run=false): nazwa galaktyki potwierdzona przez użytkownika; musi być równa aktywnej") } }));
            t.Add(Tool("import_csv",
                "Importuje do galaktyki plik CSV wygenerowany w trybie Manual: kind=template -> ImportTemplateFromText " +
                "($t_<UDT>.csv), kind=instances -> GRLoad (Instances_<UDT>.csv). Zapisuje do galaktyki - tylko po potwierdzeniu użytkownika.",
                new Dictionary<string, object> {
                    { "kind", Prop("string", "template albo instances", "enum", new[] { "template", "instances" }) },
                    { "content", Prop("string", "Pełna treść pliku CSV (zostanie zapisana jako UTF-8 z BOM, CRLF)") },
                    { "path", Prop("string", "Alternatywnie: ścieżka do pliku CSV na tym komputerze") },
                    { "mode", Prop("string", "Co z obiektami, które już istnieją: ignore (domyślnie - pomiń), update, replace, terminate",
                                   "enum", new[] { "ignore", "update", "replace", "terminate" }) },
                    { "galaxy", Prop("string", "Wymagane: nazwa galaktyki potwierdzona przez użytkownika; musi być równa aktywnej") } },
                "kind", "galaxy"));
            t.Add(Tool("export_csv",
                "Eksportuje obiekty do CSV (kind=template -> ExportTemplateToText, kind=instances -> GRDump) i zwraca treść pliku. " +
                "Tylko odczyt. Służy do porównania z plikami generowanymi przez skrypt i do poznania formatu IDE.",
                new Dictionary<string, object> {
                    { "kind", Prop("string", "template albo instances", "enum", new[] { "template", "instances" }) },
                    { "names", Prop("array", "Tagname obiektów, np. [\"$t_UDT_Mixer\"]", "items", new Dictionary<string, object> { { "type", "string" } }) } },
                "kind", "names"));
            t.Add(Tool("deploy",
                "Wdraża wskazane instancje (wymaga GALAXY_ALLOW_DEPLOY=1). Używać tylko na wyraźne polecenie użytkownika.",
                new Dictionary<string, object> {
                    { "names", Prop("array", "Tagname instancji do wdrożenia", "items", new Dictionary<string, object> { { "type", "string" } }) },
                    { "galaxy", Prop("string", "Wymagane: nazwa galaktyki potwierdzona przez użytkownika; musi być równa aktywnej") } },
                "names", "galaxy"));
            return t;
        }

        public static Dictionary<string, object> Call(string name, Dictionary<string, object> args)
        {
            if (args == null) args = new Dictionary<string, object>();
            string text; bool isError = false;
            try
            {
                switch (name)
                {
                    case "galaxy_status": text = StatusWithConnect(); break;
                    case "list_galaxies": text = ListGalaxies(); break;
                    case "select_galaxy": text = SelectGalaxy(J.Str(args, "name", "")); break;
                    case "list_objects": text = ListObjects(J.Str(args, "kind", "template"), J.Str(args, "pattern", "%")); break;
                    case "get_object": text = GetObject(J.Str(args, "name"), J.Str(args, "attribute_filter", "")); break;
                    case "apply_spec": text = ApplySpec(args); break;
                    case "deploy": Program.G.RequireWrite(J.Str(args, "galaxy", ""), "deploy"); text = Deploy(J.Arr(args, "names")); break;
                    case "import_csv": text = ImportCsv(args); break;
                    case "export_csv": text = ExportCsv(J.Str(args, "kind", ""), J.Arr(args, "names")); break;
                    default: text = "Nieznane narzędzie: " + name; isError = true; break;
                }
            }
            catch (Exception ex)
            {
                var inner = ex is TargetInvocationException && ex.InnerException != null ? ex.InnerException : ex;
                Log.Error(name + ": " + inner);
                text = "BŁĄD: " + inner.Message;
                isError = true;
            }
            finally
            {
                // Po zapisie sesja GRAccess jest zamykana, żeby nie blokowała Check-in w ArchestrA IDE.
                // Następne wywołanie zaloguje się ponownie.
                if (WritesGalaxy(name, args)) Program.G.EndSession(name);
            }
            return new Dictionary<string, object> {
                { "content", new object[] { new Dictionary<string, object> { { "type", "text" }, { "text", text } } } },
                { "isError", isError } };
        }

        static bool WritesGalaxy(string name, Dictionary<string, object> args)
        {
            if (name == "import_csv" || name == "deploy") return true;
            return name == "apply_spec" && !J.Bool(args, "dry_run", true);
        }

        public static string Status()
        {
            var g = Program.G;
            var sb = new StringBuilder();
            sb.AppendLine("GalaxyMCP " + Program.Version);
            sb.AppendLine("Węzeł GR: " + g.Node);
            sb.AppendLine("Galaktyka (aktywna): " + (g.Name == "" ? "(nie wybrano - użyj select_galaxy)" : g.Name));
            sb.AppendLine("Użytkownik: " + (g.User == "" ? "(brak - galaktyka bez zabezpieczeń)" : g.User));
            sb.AppendLine("Zapis w aktywnej galaktyce: " + (g.Name == "" ? "-" : g.CanWrite(g.Name) ? "DOZWOLONY" : "zablokowany (" + g.WriteBlockReason(g.Name) + ")"));
            sb.AppendLine("Dozwolone galaktyki: " + (g.Allowed.Count == 0 ? "wszystkie z węzła" : string.Join(", ", g.Allowed)));
            sb.AppendLine("Galaktyki z zapisem: " + (g.ReadOnly ? "żadna (GALAXY_READONLY=1)" : g.Writable.Count == 0 ? "wszystkie dozwolone" : string.Join(", ", g.Writable)));
            sb.AppendLine("Deploy: " + (g.AllowDeploy ? "włączony" : "wyłączony"));
            sb.AppendLine("GRAccess: " + (g.DllPath() ?? "(szukam w GAC)"));
            return sb.ToString();
        }

        static string StatusWithConnect()
        {
            var sb = new StringBuilder(Status());
            try
            {
                Program.G.Connect();
                sb.AppendLine("Połączenie: OK");
            }
            catch (Exception ex)
            {
                sb.AppendLine("Połączenie: BŁĄD - " + ex.Message);
                try { sb.AppendLine("Galaktyki na węźle: " + string.Join(", ", Program.G.GalaxyNames())); }
                catch { }
            }
            return sb.ToString();
        }

        static string ListGalaxies()
        {
            var g = Program.G;
            var names = g.GalaxyNames();
            var sb = new StringBuilder();
            sb.AppendLine("Galaktyki na węźle " + g.Node + " (" + names.Count + "):");
            foreach (var n in names.OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                var tags = new List<string>();
                if (string.Equals(n, g.Name, StringComparison.OrdinalIgnoreCase)) tags.Add("AKTYWNA");
                if (!g.IsAllowed(n)) tags.Add("niedozwolona");
                else tags.Add(g.CanWrite(n) ? "zapis" : "tylko odczyt");
                sb.AppendLine("- " + n + "  [" + string.Join(", ", tags) + "]");
            }
            return sb.ToString();
        }

        static string SelectGalaxy(string name)
        {
            var g = Program.G;
            string before = g.Name;
            g.Select(name);
            return "Przełączono: " + (before == "" ? "(brak)" : before) + " → " + g.Name + Environment.NewLine + Status();
        }

        static string ListObjects(string kind, string pattern)
        {
            var objs = Program.G.Query(pattern, kind == "template");
            if (objs.Count == 0) return "Brak obiektów (" + kind + ") pasujących do '" + pattern + "'.";
            var sb = new StringBuilder();
            sb.AppendLine((kind == "template" ? "Szablony" : "Instancje") + " (" + objs.Count + "):");
            foreach (object o in objs)
                sb.AppendLine("- " + Galaxy.Prop(o, "Tagname") + "  [pochodzi z: " + Galaxy.Prop(o, "DerivedFrom") + "]");
            return sb.ToString();
        }

        static string GetObject(string name, string filter)
        {
            if (string.IsNullOrEmpty(name)) throw new GrException("Podaj nazwę obiektu.");
            bool template = name.StartsWith("$");
            object o = Program.G.Find(name, template);
            if (o == null) throw new GrException("Nie znaleziono obiektu " + name + ".");
            var sb = new StringBuilder();
            sb.AppendLine(name + (template ? " (szablon)" : " (instancja)"));
            foreach (var p in new[] { "DerivedFrom", "Area", "Host", "SecurityGroup", "CheckoutStatus", "checkedOutBy", "EditStatus", "DeploymentStatus" })
                sb.AppendLine("  " + p + ": " + Galaxy.Prop(o, p));
            sb.AppendLine("Atrybuty" + (filter == "" ? "" : " zawierające '" + filter + "'") + ":");
            int n = 0;
            foreach (object a in Galaxy.Items(Galaxy.GetProp(o, "ConfigurableAttributes")))
            {
                string an = Galaxy.Prop(a, "Name");
                if (filter != "" && an.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
                sb.AppendLine("  " + an + " = " + Galaxy.Value(a));
                if (++n >= 500) { sb.AppendLine("  ... (ucięto po 500)"); break; }
            }
            return sb.ToString();
        }

        static string ApplySpec(Dictionary<string, object> args)
        {
            Dictionary<string, object> spec = J.Obj(args, "spec");
            if (spec == null && args.ContainsKey("spec") && args["spec"] is string)
                spec = Program.Json.DeserializeObject((string)args["spec"]) as Dictionary<string, object>;
            string path = J.Str(args, "spec_path");
            if (spec == null && !string.IsNullOrEmpty(path))
                spec = Program.Json.DeserializeObject(File.ReadAllText(path, Encoding.UTF8)) as Dictionary<string, object>;
            if (spec == null) throw new GrException("Podaj spec (obiekt JSON) albo spec_path.");

            bool dryRun = J.Bool(args, "dry_run", true);
            if (!dryRun) Program.G.RequireWrite(J.Str(args, "galaxy", ""), "apply_spec");
            return new SpecApplier(Program.G, Spec.Parse(spec)).Run(dryRun, J.Str(args, "scope", "all"));
        }

        static string ImportCsv(Dictionary<string, object> args)
        {
            string kind = J.Str(args, "kind", "");
            if (kind != "template" && kind != "instances") throw new GrException("kind musi mieć wartość template albo instances.");
            Program.G.RequireWrite(J.Str(args, "galaxy", ""), "import_csv");
            string mode = J.Str(args, "mode", "ignore");
            string path = J.Str(args, "path", "");
            string content = J.Str(args, "content", "");
            if (content != "")
            {
                path = Path.Combine(Path.GetTempPath(), "GalaxyMcp_" + kind + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".csv");
                string norm = content.Replace("\r\n", "\n").Replace("\n", "\r\n");
                if (norm.Length > 0 && norm[0] == '\uFEFF') norm = norm.Substring(1);
                File.WriteAllText(path, norm, new UTF8Encoding(true));
            }
            if (path == "" || !File.Exists(path)) throw new GrException("Podaj content (treść CSV) albo path do istniejącego pliku.");
            return Program.G.ImportCsv(kind, path, mode);
        }

        static string ExportCsv(string kind, object[] names)
        {
            if (kind != "template" && kind != "instances") throw new GrException("kind musi mieć wartość template albo instances.");
            if (names == null || names.Length == 0) throw new GrException("Podaj listę obiektów (names).");
            return Program.G.ExportCsv(kind, names.Select(n => Convert.ToString(n)).ToArray());
        }

        static string Deploy(object[] names)
        {
            if (!Program.G.AllowDeploy)
                throw new GrException("Deploy jest wyłączony. Włącz go zmienną GALAXY_ALLOW_DEPLOY=1 w konfiguracji serwera.");
            if (names == null || names.Length == 0) throw new GrException("Podaj listę instancji.");
            var sb = new StringBuilder();
            foreach (var n in names)
            {
                string name = Convert.ToString(n);
                try
                {
                    Program.G.DeployInstance(name);
                    sb.AppendLine("OK    " + name);
                    Log.Audit("deploy " + name);
                }
                catch (Exception ex) { sb.AppendLine("BŁĄD  " + name + ": " + ex.Message); }
            }
            return sb.ToString();
        }
    }

    // ======================================================================= specyfikacja
    class SpecAttr
    {
        public string Name, Type, Default, Io, Description, PlcPath;
    }

    class SpecInstance
    {
        public string Name, Area, SecurityGroup;
        public Dictionary<string, string> InputSource = new Dictionary<string, string>();
        public List<SpecAttr> Attrs = new List<SpecAttr>();   // 0.2.3: własne atrybuty UDA tej instancji
    }

    class Spec
    {
        public string Template, Base, Toolset, SecurityGroup, Source;
        public List<SpecAttr> Attrs = new List<SpecAttr>();
        public List<SpecInstance> Instances = new List<SpecInstance>();
        public List<string> Warnings = new List<string>();
        public List<string> Skipped = new List<string>();   // atrybuty Output (Write) pominięte w trybie Auto

        // 0.2.3: wszystkie typy danych z okna UDA w IDE (Data type).
        public static readonly string[] Types = { "MxBoolean", "MxInteger", "MxFloat", "MxDouble", "MxString",
                                                  "MxTime", "MxElapsedTime", "MxInternationalizedString", "MxBigString" };
        static readonly Regex AttrName = new Regex(@"^[A-Za-z_][A-Za-z0-9_]*$");

        static SpecAttr ParseAttr(Dictionary<string, object> a, string owner, HashSet<string> seen, List<string> err)
        {
            var sa = new SpecAttr {
                Name = J.Str(a, "name", ""), Type = J.Str(a, "type", ""), Default = J.Str(a, "default", ""),
                Io = J.Str(a, "io", "Input"), Description = J.Str(a, "description", ""), PlcPath = J.Str(a, "plc_path", "") };
            string p = owner == "" ? "" : owner + ": ";
            if (!AttrName.IsMatch(sa.Name)) err.Add(p + "niepoprawna nazwa atrybutu '" + sa.Name + "'");
            if (!seen.Add(sa.Name)) err.Add(p + "zdublowany atrybut '" + sa.Name + "'" + (owner == "" ? "" : " (jest już w szablonie albo w tej instancji)"));
            if (!Types.Contains(sa.Type)) err.Add(p + sa.Name + ": nieobsługiwany typ '" + sa.Type + "' (dozwolone: " + string.Join(", ", Types) + ")");
            if (sa.Io != "Input" && sa.Io != "InputOutput" && sa.Io != "Output")
                err.Add(p + sa.Name + ": io musi być Input, InputOutput albo Output");
            if (sa.Default != "" && !Galaxy.ValueParses(sa.Type, sa.Default))
                err.Add(p + sa.Name + ": wartość początkowa '" + sa.Default + "' nie pasuje do typu " + sa.Type);
            return sa;
        }

        public static Spec Parse(Dictionary<string, object> d)
        {
            var err = new List<string>();
            var s = new Spec();
            int ver = J.Int(d, "spec_version", 0);
            if (ver != 1) err.Add("spec_version=" + ver + " (obsługiwana: 1)");
            s.Source = J.Str(d, "source", "");
            var t = J.Obj(d, "template");
            if (t == null) throw new GrException("Specyfikacja nie zawiera sekcji template.");
            s.Template = J.Str(t, "name", "");
            s.Base = J.Str(t, "base", "$UserDefined");
            s.Toolset = J.Str(t, "toolset", "");
            s.SecurityGroup = J.Str(t, "security_group", "");
            // 0.2.2: bez limitu długości nazw (decyzja 2026-09-18) - ewentualne ograniczenie zgłosi GRAccess przy zapisie.
            if (!s.Template.StartsWith("$") || s.Template.Length < 2)
                err.Add("template.name '" + s.Template + "' musi zaczynać się od $");

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var o in J.Arr(t, "attributes") ?? new object[0])
            {
                var a = o as Dictionary<string, object>;
                if (a == null) continue;
                var sa = ParseAttr(a, "", seen, err);
                if (sa.Io == "Output") s.Skipped.Add(sa.Name);
                else s.Attrs.Add(sa);
            }

            var seenInst = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var o in J.Arr(d, "instances") ?? new object[0])
            {
                var i = o as Dictionary<string, object>;
                if (i == null) continue;
                var si = new SpecInstance {
                    Name = J.Str(i, "name", ""), Area = J.Str(i, "area", ""), SecurityGroup = J.Str(i, "security_group", "") };
                if (si.Name == "" || si.Name.StartsWith("$") || !AttrName.IsMatch(si.Name))
                    err.Add("niepoprawna nazwa instancji '" + si.Name + "' (litery, cyfry, _)");
                if (!seenInst.Add(si.Name)) err.Add("zdublowana instancja '" + si.Name + "'");
                // atrybuty instancji: nazwy nie mogą powtarzać atrybutów szablonu
                var seenHere = new HashSet<string>(seen, StringComparer.OrdinalIgnoreCase);
                foreach (var ao in J.Arr(i, "attributes") ?? new object[0])
                {
                    var a = ao as Dictionary<string, object>;
                    if (a == null) continue;
                    var sa = ParseAttr(a, si.Name, seenHere, err);
                    if (sa.Io == "Output") s.Skipped.Add(si.Name + "." + sa.Name);
                    else si.Attrs.Add(sa);
                }
                var src = J.Obj(i, "input_source");
                if (src != null)
                    foreach (var kv in src)
                    {
                        if (!seenHere.Contains(kv.Key)) err.Add(si.Name + ": InputSource dla nieistniejącego atrybutu '" + kv.Key + "'");
                        si.InputSource[kv.Key] = Convert.ToString(kv.Value, CultureInfo.InvariantCulture);
                    }
                s.Instances.Add(si);
            }
            // 0.2.3: szablon bez atrybutów jest dozwolony, gdy specyfikacja dotyczy instancji (np. instancja z własnym UDA
            // na istniejącym szablonie).
            if (s.Attrs.Count == 0 && s.Instances.Count == 0)
                err.Add("specyfikacja nie ma ani atrybutów szablonu (poza pominiętymi Output), ani instancji");
            foreach (var w in J.Arr(d, "warnings") ?? new object[0]) s.Warnings.Add(Convert.ToString(w));

            if (err.Count > 0)
                throw new GrException("Specyfikacja jest niepoprawna:\n- " + string.Join("\n- ", err));
            return s;
        }
    }

    // ======================================================================= wykonanie specyfikacji
    class SpecApplier
    {
        readonly Galaxy g;
        readonly Spec s;
        readonly StringBuilder r = new StringBuilder();
        readonly List<object> written = new List<object>();   // obiekty pobrane (CheckOut) - zwalniane na końcu Run

        public SpecApplier(Galaxy galaxy, Spec spec) { g = galaxy; s = spec; }

        static string AttrInfo(List<SpecAttr> list)
        {
            int rw = list.Count(x => x.Io == "InputOutput");
            return list.Count + " atrybutów (" + rw + " InputOutput, " + (list.Count - rw) + " Input)";
        }

        static string AttrList(List<SpecAttr> list)
        {
            return string.Join(", ", list.Select(x => x.Name + " " + x.Type + " " + x.Io +
                                                       (x.Default != "" ? " = " + x.Default : "")));
        }

        public string Run(bool dryRun, string scope)
        {
            try { return RunCore(dryRun, scope); }
            finally
            {
                foreach (var o in written) Galaxy.Release(o);
                written.Clear();
            }
        }

        string RunCore(bool dryRun, string scope)
        {
            bool doTpl = scope == "all" || scope == "template";
            bool doInst = scope == "all" || scope == "instances";
            g.Connect();

            r.AppendLine(dryRun ? "TRYB: PLAN (dry_run) - nic nie zostało zapisane." : "TRYB: ZAPIS do galaktyki.");
            r.AppendLine("Galaktyka: " + g.Name + " @ " + g.Node + "   Źródło: " + s.Source);
            int errors = 0;

            // ---------------- szablon
            object tpl = g.Find(s.Template, true);
            var missing = new List<SpecAttr>();
            if (tpl == null)
                missing.AddRange(s.Attrs);
            else
                foreach (var a in s.Attrs)
                    if (Galaxy.Attr(tpl, a.Name) == null) missing.Add(a);

            if (tpl == null)
                r.AppendLine("Szablon " + s.Template + ": UTWÓRZ z " + s.Base + " + " + AttrInfo(missing));
            else if (missing.Count > 0)
                r.AppendLine("Szablon " + s.Template + ": ISTNIEJE - DOPISZ " + AttrInfo(missing) + ": " +
                             string.Join(", ", missing.Select(x => x.Name)));
            else
                r.AppendLine("Szablon " + s.Template + ": ISTNIEJE - bez zmian");

            if (!doTpl) r.AppendLine("  (pominięty - scope=" + scope + ")");
            else if (!dryRun && (tpl == null || missing.Count > 0))
            {
                try
                {
                    tpl = WriteTemplate(tpl, missing);
                    r.AppendLine("  OK");
                }
                catch (Exception ex) { errors++; r.AppendLine("  BŁĄD: " + ex.Message); }
            }

            // ---------------- instancje
            if (s.Instances.Count > 0)
            {
                r.AppendLine("Instancje (" + s.Instances.Count + "):");
                if (!doInst) r.AppendLine("  (pominięte - scope=" + scope + ")");
                else if (tpl == null && !dryRun)
                {
                    errors++;
                    r.AppendLine("  BŁĄD: szablon " + s.Template + " nie istnieje - najpierw utwórz szablon.");
                }
                else
                    foreach (var si in s.Instances)
                        if (!DoInstance(si, tpl, dryRun)) errors++;
            }

            if (s.Skipped.Count > 0)
            {
                r.AppendLine("POMINIĘTE atrybuty Write (io=Output) - tryb Auto ich nie tworzy; dodaj je w IDE " +
                             "albo zaimportuj pliki CSV (tryb Manual): " + string.Join(", ", s.Skipped));
            }
            if (s.Warnings.Count > 0)
            {
                r.AppendLine("Ostrzeżenia generatora (elementy pominięte w specyfikacji):");
                foreach (var w in s.Warnings) r.AppendLine("  - " + w);
            }
            if (!dryRun) r.AppendLine(errors == 0 ? "WYNIK: zakończono bez błędów." : "WYNIK: błędy: " + errors + " (szczegóły powyżej i w GalaxyMcp.log).");
            else r.AppendLine("Aby zapisać: apply_spec z dry_run=false (po potwierdzeniu przez użytkownika).");
            return r.ToString();
        }

        // Dodaje atrybuty UDA (z rozszerzeniem I/O, wartością początkową i opisem) do pobranego (CheckOut) obiektu.
        void AddAttributes(object obj, string objName, List<SpecAttr> attrs)
        {
            foreach (var a in attrs)
            {
                g.AddUda(obj, a.Name, a.Type);
                g.AddIoExtension(obj, a.Name, a.Io);
                if (a.Default != "") SoftSet(obj, a.Name, a.Type, a.Default);
                if (a.Description != "")
                {
                    try { g.SetDescription(obj, a.Name, a.Description); }
                    catch (Exception ex) { r.AppendLine("  uwaga: nie ustawiono opisu " + a.Name + " (" + ex.Message + ")"); }
                }
                Log.Audit(objName + ": + " + a.Name + " " + a.Type + " " + a.Io + (a.Default != "" ? " = " + a.Default : ""));
            }
        }

        object WriteTemplate(object tpl, List<SpecAttr> attrs)
        {
            if (tpl == null)
            {
                object baseTpl = g.Find(s.Base, true);
                if (baseTpl == null) throw new GrException("Brak szablonu bazowego " + s.Base + ".");
                tpl = Com.Call(baseTpl, "CreateTemplate", s.Template, true);
                Galaxy.Check(baseTpl, "CreateTemplate(" + s.Template + ")");
                if (tpl == null) tpl = g.Find(s.Template, true);
                Log.Audit("utworzono szablon " + s.Template + " z " + s.Base);
                if (s.Toolset != "") Soft(tpl, "Toolset", s.Toolset);
            }

            Galaxy.CheckOut(tpl, s.Template);
            written.Add(tpl);
            try
            {
                if (s.SecurityGroup != "") SoftGroup(tpl, s.SecurityGroup);
                AddAttributes(tpl, s.Template, attrs);
                Com.Call(tpl, "Save");
                Galaxy.Check(tpl, "Save(" + s.Template + ")");
                Com.Call(tpl, "CheckIn", "GalaxyMCP: " + attrs.Count + " atrybutów ze " + s.Source);
                Galaxy.Check(tpl, "CheckIn(" + s.Template + ")");
            }
            catch
            {
                Galaxy.UndoCheckOut(tpl, s.Template);
                throw;
            }
            return tpl;
        }

        bool DoInstance(SpecInstance si, object tpl, bool dryRun)
        {
            object inst = g.Find(si.Name, false);
            var changes = new List<KeyValuePair<string, string>>();
            var newAttrs = new List<SpecAttr>();
            if (inst == null)
            {
                newAttrs.AddRange(si.Attrs);
                changes.AddRange(si.InputSource.Where(x => x.Value != ""));
            }
            else
            {
                string derived = Galaxy.Prop(inst, "DerivedFrom");
                if (derived != "" && !string.Equals(derived, s.Template, StringComparison.OrdinalIgnoreCase))
                {
                    r.AppendLine("  " + si.Name + ": BŁĄD - istnieje, ale pochodzi z " + derived + ", nie z " + s.Template + ". Pomijam.");
                    return false;
                }
                foreach (var a in si.Attrs)
                    if (Galaxy.Attr(inst, a.Name) == null) newAttrs.Add(a);
                foreach (var kv in si.InputSource)
                {
                    object a = Galaxy.Attr(inst, kv.Key + ".InputSource");
                    string cur = a == null ? null : Galaxy.Value(a);
                    if (cur == null && kv.Value == "") continue;   // atrybut jeszcze nie istnieje, a adresu brak
                    if (cur != kv.Value) changes.Add(kv);
                }
            }

            string attrPart = newAttrs.Count > 0 ? ", DOPISZ " + AttrInfo(newAttrs) + ": " + AttrList(newAttrs) : "";
            if (inst == null)
                r.AppendLine("  " + si.Name + ": UTWÓRZ, ustaw " + changes.Count + " InputSource" +
                             (si.Area != "" ? ", obszar " + si.Area : "") + attrPart);
            else if (changes.Count > 0 || newAttrs.Count > 0)
                r.AppendLine("  " + si.Name + ": ISTNIEJE" + attrPart +
                             (changes.Count > 0 ? ", ZMIEŃ " + changes.Count + " InputSource: " +
                              string.Join(", ", changes.Take(5).Select(x => x.Key)) + (changes.Count > 5 ? ", ..." : "") : ""));
            else
            {
                r.AppendLine("  " + si.Name + ": ISTNIEJE - bez zmian");
                return true;
            }
            if (dryRun) return true;

            try
            {
                if (inst == null)
                {
                    inst = Com.Call(tpl, "CreateInstance", si.Name, true);
                    Galaxy.Check(tpl, "CreateInstance(" + si.Name + ")");
                    if (inst == null) inst = g.Find(si.Name, false);
                    Log.Audit("utworzono instancję " + si.Name + " z " + s.Template);
                }
                Galaxy.CheckOut(inst, si.Name);
                written.Add(inst);
                try
                {
                    if (si.Area != "") Soft(inst, "Area", si.Area);
                    if (si.SecurityGroup != "") SoftGroup(inst, si.SecurityGroup);
                    AddAttributes(inst, si.Name, newAttrs);   // najpierw UDA, żeby istniało ich InputSource
                    foreach (var c in changes)
                    {
                        g.SetValue(inst, c.Key + ".InputSource", "MxString", c.Value);
                        Log.Audit(si.Name + "." + c.Key + ".InputSource = " + c.Value);
                    }
                    Com.Call(inst, "Save");
                    Galaxy.Check(inst, "Save(" + si.Name + ")");
                    Com.Call(inst, "CheckIn", "GalaxyMCP: " + (newAttrs.Count > 0 ? newAttrs.Count + " atrybutów, " : "") +
                                              "InputSource ze " + s.Source);
                    Galaxy.Check(inst, "CheckIn(" + si.Name + ")");
                }
                catch
                {
                    Galaxy.UndoCheckOut(inst, si.Name);
                    throw;
                }
                r.AppendLine("    OK");
                return true;
            }
            catch (Exception ex)
            {
                r.AppendLine("    BŁĄD: " + ex.Message);
                return false;
            }
        }

        // Ustawienia "miękkie": błąd = ostrzeżenie w raporcie, nie przerywa zapisu.
        void Soft(object obj, string property, string value)
        {
            try { Galaxy.SetProp(obj, property, value); }
            catch (Exception ex) { r.AppendLine("  uwaga: nie ustawiono " + property + "=" + value + " (" + ex.Message + ")"); }
        }

        void SoftGroup(object obj, string group)
        {
            try { Galaxy.SetSecurityGroup(obj, group); }
            catch (Exception ex) { r.AppendLine("  uwaga: nie ustawiono SecurityGroup=" + group + " (" + ex.Message + ")"); }
        }

        void SoftSet(object obj, string attr, string type, string value)
        {
            try { g.SetValue(obj, attr, type, value); }
            catch (Exception ex) { r.AppendLine("  uwaga: nie ustawiono wartości " + attr + " = " + value + " (" + ex.Message + ")"); }
        }
    }

    // ======================================================================= warstwa GRAccess
    // Wszystkie wywołania GRAccess są tutaj. WIĄZANIE WCZESNE: metody i właściwości wywoływane przez
    // interfejsy z biblioteki interop (vtable). Późne wiązanie (dynamic / IDispatch) NIE działa, bo biblioteka
    // typów GRAccess nie jest zarejestrowana (TYPE_E_LIBNOTREGISTERED, test 2026-09-17).
    class GrException : Exception
    {
        public GrException(string m) : base(m) { }
    }

    static class Com
    {
        public static Assembly Asm;
        static List<Type> ifaces;
        static readonly Dictionary<string, List<MethodInfo>> methodCache =
            new Dictionary<string, List<MethodInfo>>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<string, List<PropertyInfo>> propCache =
            new Dictionary<string, List<PropertyInfo>>(StringComparer.OrdinalIgnoreCase);

        static bool Eq(string a, string b) { return string.Equals(a, b, StringComparison.OrdinalIgnoreCase); }

        public static List<Type> Interfaces()
        {
            if (ifaces != null) return ifaces;
            Type[] all;
            try { all = Asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex) { all = ex.Types.Where(t => t != null).ToArray(); }
            ifaces = all.Where(t => t.IsInterface && t.IsPublic).ToList();
            return ifaces;
        }

        static bool Implements(Type iface, object obj)
        {
            try { return iface.IsInstanceOfType(obj); }   // dla COM: QueryInterface
            catch { return false; }
        }

        static MethodInfo FindMethod(object obj, string name, int argc)
        {
            foreach (var m in obj.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance))
                if (Eq(m.Name, name) && m.GetParameters().Length == argc) return m;
            string key = name + "/" + argc;
            List<MethodInfo> list;
            if (!methodCache.TryGetValue(key, out list))
            {
                list = new List<MethodInfo>();
                foreach (var i in Interfaces())
                    foreach (var m in i.GetMethods())
                        if (Eq(m.Name, name) && m.GetParameters().Length == argc) list.Add(m);
                methodCache[key] = list;
            }
            foreach (var m in list)
                if (Implements(m.DeclaringType, obj)) return m;
            return null;
        }

        static PropertyInfo FindProp(object obj, string name, bool set)
        {
            foreach (var q in obj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
                if (Eq(q.Name, name) && q.GetIndexParameters().Length == 0 && (set ? q.CanWrite : q.CanRead)) return q;
            string key = name + (set ? "/set" : "/get");
            List<PropertyInfo> list;
            if (!propCache.TryGetValue(key, out list))
            {
                list = new List<PropertyInfo>();
                foreach (var i in Interfaces())
                    foreach (var q in i.GetProperties())
                        if (Eq(q.Name, name) && q.GetIndexParameters().Length == 0 && (set ? q.CanWrite : q.CanRead)) list.Add(q);
                propCache[key] = list;
            }
            foreach (var q in list)
                if (Implements(q.DeclaringType, obj)) return q;
            return null;
        }

        static object Conv(object v, Type t)
        {
            if (t.IsByRef) t = t.GetElementType();
            if (v == null || t == typeof(object) || t.IsInstanceOfType(v)) return v;
            if (t.IsEnum) return Enum.ToObject(t, Convert.ToInt64(v, CultureInfo.InvariantCulture));
            if (t.IsArray && v is Array)
            {
                var src = (Array)v;
                var dst = Array.CreateInstance(t.GetElementType(), src.Length);
                for (int i = 0; i < src.Length; i++) dst.SetValue(Conv(src.GetValue(i), t.GetElementType()), i);
                return dst;
            }
            if (v is IConvertible && typeof(IConvertible).IsAssignableFrom(t))
                return Convert.ChangeType(v, t, CultureInfo.InvariantCulture);
            return v;
        }

        public static string Describe(object obj)
        {
            if (obj == null) return "null";
            var names = Interfaces().Where(i => Implements(i, obj)).Select(i => i.Name).Take(10).ToList();
            return obj.GetType().Name + (names.Count > 0 ? " [" + string.Join(", ", names) + "]" : "");
        }

        public static object Call(object obj, string name, params object[] args)
        {
            if (obj == null) throw new GrException(name + ": obiekt jest pusty (null)");
            if (args == null) args = new object[0];
            var m = FindMethod(obj, name, args.Length);
            if (m == null)
                throw new GrException("GRAccess: brak metody " + name + " (" + args.Length + " arg.) dla " + Describe(obj));
            var ps = m.GetParameters();
            var a = new object[args.Length];
            for (int i = 0; i < a.Length; i++) a[i] = Conv(args[i], ps[i].ParameterType);
            object r;
            try { r = m.Invoke(obj, a); }
            catch (TargetInvocationException ex) { throw ex.InnerException ?? ex; }
            for (int i = 0; i < a.Length; i++)
                if (ps[i].ParameterType.IsByRef) args[i] = a[i];
            return r;
        }

        public static object Get(object obj, string name)
        {
            if (obj == null) throw new GrException(name + ": obiekt jest pusty (null)");
            var p = FindProp(obj, name, false);
            if (p != null)
            {
                try { return p.GetValue(obj, null); }
                catch (TargetInvocationException ex) { throw ex.InnerException ?? ex; }
            }
            if (!Marshal.IsComObject(obj))
            {
                var f = obj.GetType().GetField(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                if (f != null) return f.GetValue(obj);
            }
            throw new GrException("GRAccess: brak właściwości " + name + " dla " + Describe(obj));
        }

        public static void Set(object obj, string name, object value)
        {
            if (obj == null) throw new GrException(name + ": obiekt jest pusty (null)");
            var p = FindProp(obj, name, true);
            if (p == null) throw new GrException("GRAccess: brak zapisywalnej właściwości " + name + " dla " + Describe(obj));
            try { p.SetValue(obj, Conv(value, p.PropertyType), null); }
            catch (TargetInvocationException ex) { throw ex.InnerException ?? ex; }
        }

        // Opis API biblioteki (GalaxyMcp.exe --dump-api) - do dopasowania nazw wywołań.
        public static string DumpApi()
        {
            var sb = new StringBuilder();
            sb.AppendLine(Asm.FullName + "  " + Asm.Location);
            Type[] all;
            try { all = Asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex) { all = ex.Types.Where(t => t != null).ToArray(); }
            foreach (var t in all.Where(x => x.IsPublic).OrderBy(x => x.Name))
            {
                string kind = t.IsEnum ? "enum" : t.IsInterface ? "interface" : "class";
                sb.AppendLine();
                sb.AppendLine(kind + " " + t.FullName + (t.GetInterfaces().Length > 0 && !t.IsEnum
                    ? " : " + string.Join(", ", t.GetInterfaces().Select(i => i.Name)) : ""));
                if (t.IsEnum) { sb.AppendLine("  " + string.Join(", ", Enum.GetNames(t))); continue; }
                foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                    sb.AppendLine("  prop " + p.PropertyType.Name + " " + p.Name +
                        (p.GetIndexParameters().Length > 0 ? "[" + string.Join(", ", p.GetIndexParameters().Select(x => x.ParameterType.Name)) + "]" : "") +
                        (p.CanRead ? " get" : "") + (p.CanWrite ? " set" : ""));
                foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly).Where(x => !x.IsSpecialName))
                    sb.AppendLine("  " + m.ReturnType.Name + " " + m.Name + "(" +
                        string.Join(", ", m.GetParameters().Select(x => x.ParameterType.Name + " " + x.Name)) + ")");
            }
            return sb.ToString();
        }
    }

    class Galaxy : IDisposable
    {
        // nazwy prymitywów rozszerzeń I/O dla AddExtensionPrimitive
        const string InputExt = "inputextension";
        const string InputOutputExt = "inputoutputextension";

        public readonly string Node, User;
        public string Name { get; private set; }
        public readonly bool ReadOnly, AllowDeploy;
        public readonly List<string> Allowed, Writable;
        readonly string password;
        Assembly asm;
        object app, galaxy;

        public Galaxy()
        {
            Node = Env("GALAXY_NODE", Environment.MachineName);
            Name = Env("GALAXY_NAME", "");
            User = Env("GALAXY_USER", "");
            password = Env("GALAXY_PASSWORD", "");
            ReadOnly = Flag("GALAXY_READONLY");
            AllowDeploy = Flag("GALAXY_ALLOW_DEPLOY");
            Allowed = SplitList(Env("GALAXY_ALLOWED", ""));
            Writable = SplitList(Env("GALAXY_WRITABLE", ""));
            if (Name != "" && Allowed.Count > 0 && !IsAllowed(Name)) Allowed.Add(Name);   // galaktyka startowa zawsze dozwolona
        }

        static List<string> SplitList(string v)
        {
            return v.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries)
                    .Select(x => x.Trim()).Where(x => x != "" && x != "*").ToList();
        }

        static bool InList(List<string> list, string name)
        {
            return list.Any(x => string.Equals(x, name, StringComparison.OrdinalIgnoreCase));
        }

        public bool IsAllowed(string name) { return Allowed.Count == 0 || InList(Allowed, name); }

        public bool CanWrite(string name)
        {
            return !ReadOnly && IsAllowed(name) && (Writable.Count == 0 || InList(Writable, name));
        }

        public string WriteBlockReason(string name)
        {
            if (ReadOnly) return "GALAXY_READONLY=1";
            if (!IsAllowed(name)) return "galaktyka spoza GALAXY_ALLOWED";
            if (Writable.Count > 0 && !InList(Writable, name)) return "galaktyka spoza GALAXY_WRITABLE";
            return "";
        }

        // Każdy zapis: aktywna galaktyka musi mieć prawo zapisu, a jeśli agent podał nazwę - musi się zgadzać.
        public void RequireWrite(string expected, string what)
        {
            // Od 0.2.5 parametr galaxy jest obowiązkowy przy każdym zapisie: model musi podać nazwę
            // galaktyki potwierdzoną przez użytkownika, a nie polegać na tym, która jest aktywna.
            expected = (expected ?? "").Trim();
            if (expected == "")
                throw new GrException(what + ": brak parametru galaxy. Zapis wymaga nazwy galaktyki potwierdzonej przez " +
                                      "użytkownika (równej aktywnej" + (Name == "" ? "" : ": '" + Name + "'") + "). Nic nie zapisano.");
            if (Name == "") throw new GrException("Nie wybrano galaktyki (select_galaxy).");
            if (!string.Equals(expected, Name, StringComparison.OrdinalIgnoreCase))
                throw new GrException(what + ": podano galaktykę '" + expected + "', a aktywna jest '" + Name +
                                      "'. Nic nie zapisano - najpierw select_galaxy albo popraw nazwę.");
            if (!CanWrite(Name))
                throw new GrException(what + ": zapis do galaktyki '" + Name + "' jest zablokowany (" + WriteBlockReason(Name) + ").");
        }

        public void Select(string name)
        {
            name = (name ?? "").Trim();
            if (name == "") throw new GrException("Podaj nazwę galaktyki.");
            if (!IsAllowed(name))
                throw new GrException("Galaktyka '" + name + "' nie jest na liście GALAXY_ALLOWED (" + string.Join(", ", Allowed) + ").");
            var names = GalaxyNames();
            string exact = names.FirstOrDefault(x => string.Equals(x, name, StringComparison.OrdinalIgnoreCase));
            if (exact == null)
                throw new GrException("Galaktyka '" + name + "' nie istnieje na węźle " + Node + ". Dostępne: " + string.Join(", ", names));
            if (string.Equals(exact, Name, StringComparison.OrdinalIgnoreCase) && galaxy != null) return;
            string previous = Name;
            Dispose();
            Name = exact;
            try { Connect(); }
            catch
            {
                Name = previous;   // nieudane przełączenie - wróć do poprzedniej nazwy (połączenie odtworzy się przy następnym użyciu)
                throw;
            }
            Log.Info("przełączono galaktykę: " + (previous == "" ? "(brak)" : previous) + " -> " + Name);
        }

        // Rozszerzenie .mcpb zostawia niewypełnione pola jako tekst "${user_config.x}" - traktujemy je jak puste.
        static string Env(string k, string d)
        {
            var v = (Environment.GetEnvironmentVariable(k) ?? "").Trim();
            if (v.StartsWith("${") && v.EndsWith("}")) v = "";
            return v == "" ? d : v;
        }

        // Przełącznik: 1/true/yes/tak = włączony (.mcpb przekazuje pola typu boolean jako "true"/"false").
        static bool Flag(string k)
        {
            switch (Env(k, "0").ToLowerInvariant())
            {
                case "1": case "true": case "yes": case "tak": return true;
                default: return false;
            }
        }

        public string DllPath()
        {
            var env = Env("GRACCESS_DLL", "");
            if (env != "") return env;
            foreach (var pf in new[] { Env("ProgramFiles(x86)", ""), Env("ProgramW6432", ""), Env("ProgramFiles", "") })
            {
                if (pf == "") continue;
                foreach (var rel in new[] { @"ArchestrA\Framework\Bin\ArchestrA.GRAccess.dll",
                                            @"ArchestrA\Framework\Bin\GRAccess\ArchestrA.GRAccess.dll",
                                            @"Common Files\ArchestrA\ArchestrA.GRAccess.dll" })
                {
                    var p = Path.Combine(pf, rel);
                    if (File.Exists(p)) return p;
                }
            }
            return null;
        }

#pragma warning disable 618
        public Assembly Asm()
        {
            if (asm != null) return asm;
            var p = DllPath();
            Log.Info("krok 1: ładuję GRAccess z " + (p ?? "GAC (LoadWithPartialName)"));
            try { asm = p != null ? Assembly.LoadFrom(p) : Assembly.LoadWithPartialName("ArchestrA.GRAccess"); }
            catch (Exception ex) { throw new GrException("Nie można załadować GRAccess (" + (p ?? "GAC") + "): " + ex.Message); }
            if (asm == null)
                throw new GrException("Nie znaleziono ArchestrA.GRAccess.dll. Ustaw GRACCESS_DLL na pełną ścieżkę do biblioteki.");
            Com.Asm = asm;
            Log.Info("krok 1 OK: " + asm.FullName + " (" + asm.ImageRuntimeVersion + ") z " + asm.Location);
            return asm;
        }
#pragma warning restore 618

        Type T(string name)
        {
            var t = Asm().GetType("ArchestrA.GRAccess." + name, false, true);
            if (t != null) return t;
            // typ może być w innej przestrzeni nazw lub w bibliotece zależnej
            foreach (var x in Com.Interfaces().Concat(SafeTypes(asm)))
                if (string.Equals(x.Name, name, StringComparison.OrdinalIgnoreCase)) return x;
            throw new GrException("W tej wersji GRAccess brak typu " + name + " (sprawdź GalaxyMcp.exe --dump-api)");
        }

        static IEnumerable<Type> SafeTypes(Assembly a)
        {
            try { return a.GetTypes(); }
            catch (ReflectionTypeLoadException ex) { return ex.Types.Where(t => t != null); }
        }

        object E(string enumType, string value)
        {
            try { return Enum.Parse(T(enumType), value, true); }
            catch (ArgumentException) { throw new GrException("W GRAccess brak wartości " + enumType + "." + value); }
        }

        object New(params string[] classNames)
        {
            foreach (var n in classNames)
            {
                Type t = Asm().GetType("ArchestrA.GRAccess." + n, false, true);
                if (t == null) t = SafeTypes(asm).FirstOrDefault(x => string.Equals(x.Name, n, StringComparison.OrdinalIgnoreCase));
                if (t != null && !t.IsInterface && !t.IsAbstract) return Activator.CreateInstance(t);
            }
            throw new GrException("W GRAccess brak klasy: " + string.Join(" / ", classNames));
        }

        // ---------------------------------------------------------- połączenie
        object Galaxies()
        {
            if (app == null)
            {
                Log.Info("krok 2: tworzę GRAccessAppClass (COM)");
                app = New("GRAccessAppClass");
                Log.Info("krok 2 OK");
            }
            Log.Info("krok 3: QueryGalaxies(" + Node + ")");
            object gals = Com.Call(app, "QueryGalaxies", Node);
            Check(app, "QueryGalaxies(" + Node + ")");
            Log.Info("krok 3 OK: " + Com.Describe(gals));
            return gals;
        }

        public List<string> GalaxyNames()
        {
            return Items(Galaxies()).Select(x => Prop(x, "Name")).ToList();
        }

        public object Connect()
        {
            if (galaxy != null) return galaxy;
            if (Name == "") throw new GrException("Nie wybrano galaktyki: użyj select_galaxy albo ustaw GALAXY_NAME.");
            object found = null;
            var names = new List<string>();
            foreach (var x in Items(Galaxies()))
            {
                string n = Prop(x, "Name");
                names.Add(n);
                if (string.Equals(n, Name, StringComparison.OrdinalIgnoreCase)) found = x;
            }
            if (found == null)
                throw new GrException("Galaktyka '" + Name + "' nie istnieje na węźle " + Node +
                                      ". Dostępne: " + (names.Count == 0 ? "(brak)" : string.Join(", ", names)));
            Log.Info("krok 4: Login do " + Name + " (" + Com.Describe(found) + ")");
            Com.Call(found, "Login", User, password);
            Check(found, "Login(" + (User == "" ? "bez użytkownika" : User) + ")");
            galaxy = found;
            Log.Info("krok 4 OK: zalogowano do " + Name + "@" + Node);
            return galaxy;
        }

        public void Dispose()
        {
            if (galaxy == null) return;
            try { Com.Call(galaxy, "Logout"); }
            catch (Exception ex) { Log.Info("Logout(" + Name + "): " + ex.Message); }
            try { Marshal.FinalReleaseComObject(galaxy); } catch { }
            galaxy = null;
            // Zwolnienie pozostałych referencji COM do obiektów galaktyki (RCW czekające na finalizację).
            GC.Collect();
            GC.WaitForPendingFinalizers();
        }

        // Zamknięcie sesji po narzędziu zapisującym: wylogowanie, następne wywołanie zaloguje się od nowa.
        public void EndSession(string what)
        {
            if (galaxy == null) return;
            Dispose();
            Log.Info("sesja zamknięta po " + what + " (wylogowano z " + Name + ")");
        }

        // ---------------------------------------------------------- zapytania
        public object Find(string name, bool template)
        {
            object gal = Connect();
            string[] names = { name };
            object kind = E("EgObjectIsTemplateOrInstance", template ? "gObjectIsTemplate" : "gObjectIsInstance");
            object res;
            try { res = Com.Call(gal, "QueryObjectsByName", kind, names); }
            catch (GrException) { throw; }                 // brak metody - błąd API, zgłoś
            catch (Exception ex) { Log.Info("QueryObjectsByName(" + name + "): " + ex.Message); return null; }
            foreach (var o in Items(res))
                if (string.Equals(Prop(o, "Tagname"), name, StringComparison.OrdinalIgnoreCase)) return o;
            return null;
        }

        public List<object> Query(string pattern, bool template)
        {
            object gal = Connect();
            object res = Com.Call(gal, "QueryObjects",
                E("EgObjectIsTemplateOrInstance", template ? "gObjectIsTemplate" : "gObjectIsInstance"),
                E("EConditionType", "namedLike"), pattern, E("EMatch", "MatchCondition"));
            Check(gal, "QueryObjects(" + pattern + ")");
            return Items(res);
        }

        // ---------------------------------------------------------- zapis
        // AddUDA działa na szablonie i na instancji (IgObject) - obiekt musi być pobrany (CheckOut).
        public void AddUda(object obj, string name, string type)
        {
            Com.Call(obj, "AddUDA", name, E("MxDataType", type), E("MxAttributeCategory", "MxCategoryWriteable_USC_Lockable"),
                     E("MxSecurityClassification", "MxSecurityOperate"), false, 0);
            Check(obj, "AddUDA(" + name + ", " + type + ")");
        }

        public void AddIoExtension(object obj, string name, string io)
        {
            Com.Call(obj, "AddExtensionPrimitive", io == "InputOutput" ? InputOutputExt : InputExt, name, false);
            Check(obj, "AddExtensionPrimitive(" + name + ", " + io + ")");
        }

        // Kontrola wartości początkowej ze specyfikacji (Spec.Parse) - ten sam zapis liczb co w SetValue.
        public static bool ValueParses(string type, string value)
        {
            double d; int i;
            switch (type)
            {
                case "MxBoolean":
                    var b = value.Trim().ToLowerInvariant();
                    return b == "true" || b == "false" || b == "1" || b == "0";
                case "MxInteger": return int.TryParse(value.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out i);
                case "MxFloat":
                case "MxDouble": return double.TryParse(value.Trim().Replace(',', '.'), NumberStyles.Float, CultureInfo.InvariantCulture, out d);
                default: return true;   // teksty, czas - sprawdzi GRAccess przy zapisie
            }
        }

        public void SetValue(object obj, string attr, string type, string value)
        {
            object a = Attr(obj, attr);
            if (a == null) throw new GrException("brak atrybutu " + attr);
            string dt = "";
            try { dt = Convert.ToString(Com.Get(a, "DataType"), CultureInfo.InvariantCulture); } catch { }
            if (dt == "MxReferenceType")
            {
                try { SetReference(a, attr, value); return; }
                catch (Exception ex) { Log.Info("PutMxReference(" + attr + "): " + ex.Message + " - próbuję PutString"); }
            }
            string num = value.Trim().Replace(',', '.');
            object mv = New("MxValueClass", "MxValue");
            switch (type)
            {
                case "MxBoolean":
                    var b = value.Trim().ToLowerInvariant();
                    Com.Call(mv, "PutBoolean", b == "true" || b == "1");
                    break;
                case "MxFloat": Com.Call(mv, "PutFloat", float.Parse(num, CultureInfo.InvariantCulture)); break;
                case "MxDouble": Com.Call(mv, "PutDouble", double.Parse(num, CultureInfo.InvariantCulture)); break;
                case "MxInteger": Com.Call(mv, "PutInteger", int.Parse(value.Trim(), CultureInfo.InvariantCulture)); break;
                // MxString, MxBigString, MxInternationalizedString, MxTime, MxElapsedTime: tekst - konwersję robi GRAccess
                // (czas np. 00:00:05.0000000, data 2026-09-24 12:00:00). Błąd = ostrzeżenie w raporcie (SoftSet).
                default: Com.Call(mv, "PutString", value); break;
            }
            Com.Call(a, "SetValue", mv);
            object cr = CR(a);
            if (cr != null) CheckResult(cr, "SetValue(" + attr + ")");
            else Check(obj, "SetValue(" + attr + ")");
        }

        // Atrybut typu referencja (np. InputSource): IMxReference.FullReferenceString + PutMxReference.
        void SetReference(object a, string attr, string value)
        {
            object cur = Com.Get(a, "value");
            object reference = Com.Call(cur, "GetMxReference");
            if (reference == null) throw new GrException("brak IMxReference");
            Com.Set(reference, "FullReferenceString", value);
            object mv = New("MxValueClass", "MxValue");
            Com.Call(mv, "PutMxReference", reference);
            Com.Call(a, "SetValue", mv);
            object cr = CR(a);
            if (cr != null) CheckResult(cr, "SetValue(" + attr + ")");
        }

        public void SetDescription(object obj, string uda, string description)
        {
            object a = Attr(obj, uda);
            if (a == null) throw new GrException("brak atrybutu " + uda);
            Com.Set(a, "Description", description);
            object cr = CR(a);
            if (cr != null) CheckResult(cr, "Description(" + uda + ")");
        }

        public static void SetSecurityGroup(object obj, string group)
        {
            Com.Set(Com.Get(obj, "ConfigurableAttributes"), "SecurityGroup", group);
        }

        // ---------------------------------------------------------- import / eksport CSV
        static readonly Dictionary<string, string> LoadModes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase) {
            { "ignore", "GRLoadModeIgnore" }, { "update", "GRLoadModeUpdate" },
            { "replace", "GRLoadModeReplace" }, { "terminate", "GRLoadModeTerminate" } };

        public string ImportCsv(string kind, string path, string mode)
        {
            string m;
            if (!LoadModes.TryGetValue(mode, out m)) throw new GrException("mode musi mieć wartość ignore, update, replace albo terminate.");
            object gal = Connect();
            string method = kind == "template" ? "ImportTemplateFromText" : "GRLoad";
            Log.Audit(method + "(" + path + ", " + m + ")");
            string head = method + " (" + m + ") z pliku " + path;
            try { Com.Call(gal, method, path, E("GRLoadMode", m)); }
            catch (GrException) { throw; }
            catch (Exception ex)
            {
                Log.Error(method + ": " + ex.Message);
                return "BŁĄD: " + head + ": " + ex.Message + Environment.NewLine + Results(gal);
            }
            // GRAccess zgłasza Success dla całej operacji, nawet gdy pojedynczy obiekt się nie zaimportował
            // (test 2026-11-23: E_FAIL dla szablonu z atrybutami Stan_X i stan_x, a wynik ogólny Success).
            // Wynik ogólny liczony więc także z komunikatów dla obiektów.
            var failed = new List<string>();
            string res = Results(gal, failed);
            if (failed.Count == 0) return head + Environment.NewLine + res;
            foreach (var f in failed) Log.Error(method + ": " + f);
            return "BŁĄD: " + head + ": " + failed.Count + " " + (failed.Count == 1 ? "komunikat" : "komunikaty") +
                   " z błędem - obiekty z błędem NIE zostały zaimportowane (szczegóły poniżej i w GalaxyMcp.log)." +
                   Environment.NewLine + res;
        }

        public string ExportCsv(string kind, string[] names)
        {
            object gal = Connect();
            string method = kind == "template" ? "ExportTemplateToText" : "GRDump";
            DateTime start = DateTime.Now.AddSeconds(-2);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            // GRAccess sam nadaje nazwy plikom - eksport do osobnego folderu i odczyt wszystkiego, co w nim powstanie.
            string dir = Path.Combine(Path.GetTempPath(), "GalaxyMcp_export_" + stamp);
            Directory.CreateDirectory(dir);
            // ExportTemplateToText: drugi parametr to FOLDER (plik <szablon>.csv tworzy GRAccess, test 2026-09-17);
            // GRDump: pełna ścieżka pliku.
            string path = kind == "template" ? dir : Path.Combine(dir, "instances.csv");
            Com.Call(gal, method, names, path);
            Check(gal, method + "(" + string.Join(", ", names) + ")");

            var files = new List<string>(Directory.GetFiles(dir, "*", SearchOption.AllDirectories));
            // awaryjnie: nowe pliki obok folderu (np. gdy GRAccess użył tylko katalogu nadrzędnego)
            foreach (var f in Directory.GetFiles(Path.GetTempPath(), "*.csv"))
            {
                string fn = Path.GetFileName(f);
                if (File.GetLastWriteTime(f) >= start &&
                    (fn.IndexOf(stamp, StringComparison.OrdinalIgnoreCase) >= 0 ||
                     names.Any(n => fn.IndexOf(n.TrimStart('$'), StringComparison.OrdinalIgnoreCase) >= 0)))
                    files.Add(f);
            }
            if (files.Count == 0)
                return method + ": nie znaleziono pliku wynikowego (folder " + dir + ")" + Environment.NewLine + Results(gal);

            var sb = new StringBuilder();
            const int max = 200000;
            foreach (var f in files.Distinct())
            {
                string text = File.ReadAllText(f);
                sb.AppendLine("=== Plik: " + f + " (" + text.Length + " znaków)" +
                              (text.Length == 0 ? " - PUSTY: obiekt prawdopodobnie nie istnieje w tej galaktyce" : ""));
                sb.AppendLine(text.Length > max ? text.Substring(0, max) + Environment.NewLine + "... (ucięto)" : text);
            }
            return sb.ToString();
        }

        // Wynik ostatniej operacji: CommandResult + lista CommandResults (komunikaty dla poszczególnych obiektów).
        static string Results(object gal, List<string> failed = null)
        {
            var sb = new StringBuilder();
            var items = new StringBuilder();
            int bad = 0;
            try
            {
                object list = Com.Get(gal, "CommandResults");
                int n = 0;
                foreach (var x in Items(list))
                {
                    bool ok = Prop(x, "Successful") == "True";
                    string msg = (Prop(x, "Text") + " " + Prop(x, "CustomMessage")).Trim();
                    if (!ok) { bad++; if (failed != null) failed.Add(msg); }
                    if (n < 300) items.AppendLine("  - " + (ok ? "OK   " : "BŁĄD ") + msg);
                    else if (n == 300) items.AppendLine("  ... (ucięto)");
                    n++;
                }
            }
            catch { }
            object cr = CR(gal);
            if (cr != null)
            {
                bool ok = Prop(cr, "Successful") == "True" && bad == 0;
                sb.AppendLine("Wynik: " + (ok ? "OK" : "BŁĄD") + " " +
                              (Prop(cr, "Text") + " " + Prop(cr, "CustomMessage")).Trim() +
                              (bad > 0 ? " (błędy dla obiektów: " + bad + ")" : ""));
            }
            sb.Append(items);
            return sb.ToString();
        }

        public void DeployInstance(string name)
        {
            object inst = Find(name, false);
            if (inst == null) throw new GrException("nie znaleziono instancji");
            Com.Call(inst, "Deploy",
                     E("EActionForCurrentlyDeployedObjects", "deployChanges"),
                     E("ESkipIfCurrentlyUndeployed", "dontSkipIfCurrentlyUndeployed"),
                     E("EDeployOnScan", "doDeployOnScan"),
                     E("EForceOffScan", "doForceOffScan"),
                     E("ECascade", "dontCascade"),
                     false);
            Check(inst, "Deploy(" + name + ")");
        }

        // ---------------------------------------------------------- pomocnicze (statyczne)
        public static object GetProp(object obj, string property) { return Com.Get(obj, property); }

        public static List<object> Items(object coll)
        {
            var list = new List<object>();
            if (coll == null) return list;
            int n = Convert.ToInt32(Com.Get(coll, "count"), CultureInfo.InvariantCulture);
            for (int i = 1; i <= n; i++) list.Add(Item(coll, i));   // kolekcje GRAccess są indeksowane od 1
            return list;
        }

        // Element kolekcji: akcesor indeksatora get_Item(index), awaryjnie metoda Item(index).
        static object Item(object coll, object index)
        {
            try { return Com.Call(coll, "get_Item", index); }
            catch (GrException) { return Com.Call(coll, "Item", index); }
        }

        public static object Attr(object obj, string name)
        {
            object attrs;
            try { attrs = Com.Get(obj, "ConfigurableAttributes"); }
            catch (Exception ex) { Log.Info("ConfigurableAttributes: " + ex.Message); return null; }
            try { return Item(attrs, name); }
            catch { return null; }
        }

        public static string Value(object attr)
        {
            try
            {
                object v = Com.Get(attr, "value");
                if (v == null) return "";
                try { return Convert.ToString(Com.Call(v, "GetString"), CultureInfo.InvariantCulture); }
                catch
                {
                    object reference = Com.Call(v, "GetMxReference");
                    return reference == null ? "" : Prop(reference, "FullReferenceString");
                }
            }
            catch { return "?"; }
        }

        public static string Prop(object obj, string property)
        {
            try
            {
                var v = Com.Get(obj, property);
                return v == null ? "" : Convert.ToString(v, CultureInfo.InvariantCulture);
            }
            catch { return ""; }
        }

        public static void SetProp(object obj, string property, object value)
        {
            Com.Set(obj, property, value);
        }

        static object CR(object obj)
        {
            try { return Com.Get(obj, "CommandResult"); }
            catch { return null; }
        }

        // Zwolnienie obiektu z sesji GRAccess po zapisie (CheckIn albo UndoCheckOut). Błąd tylko do logu.
        public static void Release(object obj)
        {
            if (obj == null) return;
            string name = Prop(obj, "Tagname");
            if (Prop(obj, "CheckoutStatus") == "checkedOutToMe")
            {
                Log.Error(name + ": po zapisie nadal pobrany (CheckOut) przez GalaxyMCP - cofam pobranie");
                UndoCheckOut(obj, name);
            }
            try { Com.Call(obj, "Unload"); }
            catch (Exception ex) { Log.Info("Unload(" + name + "): " + ex.Message); }
            try { Marshal.FinalReleaseComObject(obj); } catch { }
        }

        public static void UndoCheckOut(object obj, string name)
        {
            try
            {
                Com.Call(obj, "UndoCheckOut");
                Check(obj, "UndoCheckOut(" + name + ")");
            }
            catch (Exception ex)
            {
                var inner = ex is TargetInvocationException && ex.InnerException != null ? ex.InnerException : ex;
                Log.Error(name + ": nie cofnięto pobrania (UndoCheckOut): " + inner.Message +
                          " - obiekt może zostać pobrany; cofnij pobranie w ArchestrA IDE (Undo Check-Out)");
            }
        }

        // CheckOut; jeśli obiekt jest już pobrany przez nas (np. zaraz po utworzeniu) - kontynuuj.
        public static void CheckOut(object obj, string name)
        {
            Com.Call(obj, "CheckOut");
            try { Check(obj, "CheckOut(" + name + ")"); }
            catch (GrException)
            {
                string st = Prop(obj, "CheckoutStatus");
                if (st.IndexOf("ToMe", StringComparison.OrdinalIgnoreCase) < 0) throw;
            }
        }

        public static void Check(object obj, string what)
        {
            object cr = CR(obj);
            if (cr == null) return;   // obiekt bez CommandResult - brak informacji o błędzie
            CheckResult(cr, what);
        }

        static void CheckResult(object cr, string what)
        {
            bool ok;
            try { ok = Convert.ToBoolean(Com.Get(cr, "Successful"), CultureInfo.InvariantCulture); }
            catch { return; }
            if (ok) return;
            string text = Prop(cr, "Text"), custom = Prop(cr, "CustomMessage");
            throw new GrException(what + " nie powiodło się: " + (text + " " + custom).Trim());
        }
    }

    // ======================================================================= JSON / log
    static class J
    {
        public static string Str(IDictionary<string, object> d, string k, string def = null)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) && v != null ? Convert.ToString(v, CultureInfo.InvariantCulture) : def;
        }

        public static int Int(IDictionary<string, object> d, string k, int def)
        {
            object v;
            if (d == null || !d.TryGetValue(k, out v) || v == null) return def;
            try { return Convert.ToInt32(v, CultureInfo.InvariantCulture); }
            catch { return def; }
        }

        public static bool Bool(IDictionary<string, object> d, string k, bool def)
        {
            object v;
            if (d == null || !d.TryGetValue(k, out v) || v == null) return def;
            if (v is bool) return (bool)v;
            var s = Convert.ToString(v).Trim().ToLowerInvariant();
            return s == "true" || s == "1" ? true : s == "false" || s == "0" ? false : def;
        }

        public static Dictionary<string, object> Obj(IDictionary<string, object> d, string k)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) ? v as Dictionary<string, object> : null;
        }

        public static object[] Arr(IDictionary<string, object> d, string k)
        {
            object v;
            if (d == null || !d.TryGetValue(k, out v) || v == null) return null;
            var a = v as object[];
            if (a != null) return a;
            var l = v as IEnumerable;
            return l != null && !(v is string) ? l.Cast<object>().ToArray() : null;
        }
    }

    static class Log
    {
        static readonly string FilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "GalaxyMcp.log");

        static void Write(string level, string msg)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + level + " " + msg;
            try { Console.Error.WriteLine(line); } catch { }
            try { File.AppendAllText(FilePath, line + Environment.NewLine, Encoding.UTF8); } catch { }
        }

        public static void Info(string m) { Write("INFO ", m); }
        public static void Error(string m) { Write("ERROR", m); }
        public static void Audit(string m) { Write("ZAPIS", m); }
    }
}
