# Test dymny serwera GalaxyMCP bez AVEVA (bez GRAccess): protokół MCP, lista narzędzi, walidacja specyfikacji
# i blokady zapisu. Użycie:  pwsh tests/test_serwer.ps1 -Exe <ścieżka do GalaxyMcp.exe> -Spec <Spec_*.json>
param([Parameter(Mandatory)] [string]$Exe, [Parameter(Mandatory)] [string]$Spec)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$fail = 0
function Check($ok, $msg) { if ($ok) { Write-Host "OK    $msg" } else { Write-Host "BŁĄD  $msg"; $script:fail++ } }

$manifest = Get-Content (Join-Path (Split-Path $Exe) 'manifest.json') -Raw | ConvertFrom-Json
$ver = (& $Exe --version).Trim()
Check ($ver -eq $manifest.version) "--version = $ver (manifest: $($manifest.version))"

$specJson = (Get-Content $Spec -Raw -Encoding utf8 | ConvertFrom-Json | ConvertTo-Json -Depth 20 -Compress)
$bad = '{"spec_version":1,"template":{"name":"bez_dolara","attributes":[{"name":"1zla nazwa","type":"MxFoo","io":"Output","default":"x"}]},"instances":[{"name":"Zła instancja"}]}'
$req = @(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}',
  '{"jsonrpc":"2.0","method":"notifications/initialized"}',
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}',
  ('{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"apply_spec","arguments":{"spec":' + $bad + ',"dry_run":true}}}'),
  ('{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"apply_spec","arguments":{"spec":' + $specJson + ',"dry_run":false,"galaxy":"test"}}}'),
  ('{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"apply_spec","arguments":{"spec":' + $specJson + ',"dry_run":true}}}'),
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"deploy","arguments":{"names":["X"]}}}',
  'to nie jest JSON'
)
$env:GALAXY_NAME = ''; $env:GALAXY_WRITABLE = ''
$out = ($req -join "`n") | & $Exe 2>$null
$resp = @{}
foreach ($l in $out) { if ($l.Trim()) { $o = $l | ConvertFrom-Json; $resp["$($o.id)"] = $o } }
function Text($id) { ($resp["$id"].result.content | ForEach-Object { $_.text }) -join "`n" }

Check ($resp['1'].result.serverInfo -ne $null) "initialize: serverInfo $($resp['1'].result.serverInfo.name) $($resp['1'].result.serverInfo.version)"
$names = @($resp['2'].result.tools | ForEach-Object { $_.name })
Check ($names.Count -eq 9) "tools/list: $($names.Count) narzędzi ($($names -join ', '))"
$t3 = Text 3
Check ($resp['3'].result.isError -and $t3 -match 'niepoprawna' -and $t3 -match 'musi zaczynać się od \$' -and $t3 -match 'io musi być' -and $t3 -match 'nieobsługiwany typ') "apply_spec: zła specyfikacja odrzucona przed połączeniem z galaktyką"
Check ($resp['4'].result.isError -and (Text 4) -match 'Nie wybrano galaktyki') "apply_spec dry_run=false bez wybranej galaktyki: zapis zablokowany"
$t5 = Text 5
Check ($t5 -notmatch 'niepoprawna') "apply_spec dry_run: specyfikacja z generatora przechodzi walidację serwera (dalej brak GRAccess/galaktyki: $(($t5 -split "`n")[0]))"
Check ($resp['6'].result.isError) "deploy bez galaktyki i bez zgody: zablokowany"
Check ($resp.ContainsKey('') -or ($out -match '-32700')) "zła linia JSON: błąd Parse error, serwer działa dalej"

if ($fail) { Write-Host "Nieudane testy: $fail"; exit 1 } else { Write-Host 'Wszystkie testy serwera OK' }
