# sb_fetch.ps1 - bring one archive from the host through a Session Manager port-forward (Stage B ticket B02).
#
#   sb_fetch.ps1 -AwsProfile <profile> -Outputs <stack outputs file> -Dest <private folder> -Out <evidence json>
#                [-HostPort 8765] [-WindowSeconds 300] [-ServeScript <B01's sb_outbound_serve.sh>]
#
# One call: make a 64-hex token and a neutral archive name; start B01's serve script by host-run.ps1 with a
# vars file in the temp folder (Run Command timeout = window + 120 s); open an AWS-StartPortForwardingSession
# tunnel from a free local port to -HostPort; poll http://127.0.0.1:<local port>/<token>/<archive> every
# 2 seconds into <Dest>\<archive>.part until it arrives, the host ends or the window ends; wait for the host;
# keep the file only when the host says RESULT=expected and the size and sha256 equal the host's. A finally
# block ends the session, kills the session's process tree and any host child still running, and deletes
# the vars file, the parameters file, the child logs and any .part file. No fetch is retried: a failed call
# ends with exit 1, and the operator runs it again, which makes a new token.
#
# The token never reaches the console, -Out or the repository. -Out is written once, as JSON, metadata only:
# no token and no listing of -Dest. Exit 0 fetched and equal, 1 anything else after an AWS call, 2 refused
# before any AWS call. Needs Windows PowerShell 5.1, the AWS CLI and the Session Manager plugin. Region comes
# from deploy/aws/parameters/host.json. Pinned by tests/test_stageb_outbound_tunnel.py.
param(
  [Parameter(Mandatory = $true)][string]$AwsProfile,
  [Parameter(Mandatory = $true)][string]$Outputs,
  [Parameter(Mandatory = $true)][string]$Dest,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$HostPort = 8765,
  [int]$WindowSeconds = 300,
  [string]$ServeScript = ""
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Document = "AWS-StartPortForwardingSession"

function Refuse([string]$Why) { Write-Host "REFUSED: $Why"; exit 2 }
function Utc { (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
function Full([string]$P) { return [IO.Path]::GetFullPath($P).TrimEnd("\") }
function Inside([string]$Child, [string]$Parent) {
  return ((Full $Child) + "\").StartsWith((Full $Parent) + "\", [StringComparison]::OrdinalIgnoreCase)
}
function InWorkTree([string]$Dir) {
  $d = Full $Dir
  while ($d) {
    if (Test-Path -LiteralPath (Join-Path $d ".git")) { return $true }
    $up = Split-Path $d -Parent
    if (-not $up -or $up -eq $d) { break }
    $d = $up
  }
  return $false
}
function Quote([string]$A) {
  # One Start-Process argument: quoted when it holds a space or a quote, with a trailing backslash doubled.
  if ($A -match '[\s"]') { return '"' + ($A.Replace('"', '\"') -replace '(\\+)$', '$1$1') + '"' }
  return $A
}
function WriteAscii([string]$Path, [string]$Text) { [IO.File]::WriteAllText($Path, $Text, [Text.Encoding]::ASCII) }
function Shared([string]$Path) {
  # Read a child's log while the child still holds it open.
  if (-not (Test-Path -LiteralPath $Path)) { return "" }
  try {
    $fs = [IO.File]::Open($Path, "Open", "Read", "ReadWrite")
    try { return (New-Object IO.StreamReader $fs).ReadToEnd() } finally { $fs.Close() }
  } catch { return "" }
}
function KillTree($Proc) {
  if ($Proc -and -not $Proc.HasExited) {
    & taskkill.exe /T /F /PID $Proc.Id 2>&1 | Out-Null
    $Proc.WaitForExit(10000) | Out-Null
  }
}

$Repo = Full (Join-Path $PSScriptRoot "..\..\..\..\..")
$HostRun = Join-Path $Repo "deploy\aws\scripts\host-run.ps1"
if (-not $ServeScript) { $ServeScript = Join-Path $Repo "docs\infrastructure_security\evidence_v2\SB\host\sb_outbound_serve.sh" }

if (Test-Path -LiteralPath $Out) { Refuse "$Out exists; a run never overwrites" }
if (-not (Test-Path -LiteralPath (Split-Path (Full $Out) -Parent) -PathType Container)) { Refuse "the folder of $Out does not exist" }
if ($HostPort -lt 1024 -or $HostPort -gt 65535) { Refuse "-HostPort must be 1024-65535" }
if ($WindowSeconds -lt 30 -or $WindowSeconds -gt 900) { Refuse "-WindowSeconds must be 30-900" }
if (-not (Test-Path -LiteralPath $Dest -PathType Container)) { Refuse "$Dest is not a folder" }
$Dest = Full $Dest
if (Inside $Dest $Repo) { Refuse "$Dest lies under this repository" }
if (InWorkTree $Dest) { Refuse "$Dest lies inside a git work tree" }
$AwsExe = (Get-Command aws -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $AwsExe) { Refuse "the AWS CLI (aws) is not on PATH" }
if (-not (Get-Command session-manager-plugin -CommandType Application -ErrorAction SilentlyContinue)) {
  Refuse "the Session Manager plugin (session-manager-plugin) is not on PATH"
}
if (-not (Test-Path -LiteralPath $Outputs -PathType Leaf)) { Refuse "$Outputs not found" }
$Outputs = Full $Outputs
$Instance = ((Get-Content -LiteralPath $Outputs -Raw | ConvertFrom-Json) | ForEach-Object { $_ } | Where-Object { $_.OutputKey -eq "InstanceId" }).OutputValue
if (-not ("$Instance" -match '^i-[0-9a-f]{8,17}$')) { Refuse "$Outputs holds no InstanceId" }
if (-not (Test-Path -LiteralPath $ServeScript -PathType Leaf)) { Refuse "$ServeScript not found" }
$ServeScript = Full $ServeScript
if (-not (Test-Path -LiteralPath $HostRun -PathType Leaf)) { Refuse "$HostRun not found" }
$HostJson = Join-Path $Repo "deploy\aws\parameters\host.json"
if (-not (Test-Path -LiteralPath $HostJson)) { Refuse "host.json not found at $HostJson" }
$Region = (@((Get-Content -LiteralPath $HostJson -Raw | ConvertFrom-Json) | ForEach-Object { $_ }) | Where-Object { $_.ParameterKey -eq "ExpectedRegion" }).ParameterValue
if (-not $Region) { Refuse "host.json names no ExpectedRegion" }

function Aws([string[]]$Argv) {
  $all = @($Argv + @("--region", $Region, "--profile", $AwsProfile))
  $o = & $AwsExe @all 2>&1 | ForEach-Object { "$_" }
  $script:AwsRc = $LASTEXITCODE
  return (($o -join "`n").Trim())
}

$Rng = New-Object Security.Cryptography.RNGCryptoServiceProvider
function RandomHex([int]$N) { $b = New-Object byte[] $N; $Rng.GetBytes($b); return (($b | ForEach-Object { $_.ToString("x2") }) -join "") }
$Token = RandomHex 32
$Archive = "out-" + (Get-Date).ToUniversalTime().ToString("yyyyMMdd") + "-" + (RandomHex 3) + ".tar.gz"
$Temp = [IO.Path]::GetTempPath()
$Tag = [guid]::NewGuid().ToString("N")
$VarsFile = Join-Path $Temp "po-sb-vars-$Tag.json"
$ParamsFile = Join-Path $Temp "po-sb-session-$Tag.json"
$HostRecord = Join-Path $Temp "po-sb-hostrun-$Tag.json"
$Log = [ordered]@{}
foreach ($n in @("hostrun_out", "hostrun_err", "session_out", "session_err")) { $Log[$n] = Join-Path $Temp "po-sb-$Tag-$n.txt" }
$Part = Join-Path $Dest "$Archive.part"
$Final = Join-Path $Dest $Archive

$Record = [ordered]@{
  archive = $Archive; bytes = $null; host_bytes = $null; local_sha256 = $null; host_sha256 = $null
  sha256_match = $false; kept = $false; instance_id = $Instance; command_id = $null; session_id = $null
  session_terminated = $false
  document_name = $Document; host_port = $HostPort; local_port = $null; window_seconds = $WindowSeconds
  host_status = $null; host_lines = [ordered]@{}; start_utc = (Utc); end_utc = $null; failure = $null
}
$Rc = 1
$StartedUtc = (Get-Date).ToUniversalTime()
$HostProc = $null
$SessProc = $null
$SessionId = $null
$Terminated = $false

function DropVars {
  # The vars file holds the token: delete it as soon as host-run has sent it.
  if ((Test-Path -LiteralPath $VarsFile) -and ((Shared $Log.hostrun_out) -match "command_id=" -or $HostProc.HasExited)) {
    Remove-Item -LiteralPath $VarsFile -Force -ErrorAction SilentlyContinue
  }
}
function EndSession {
  if ($SessionId -and -not $script:Terminated) {
    Aws @("ssm", "terminate-session", "--session-id", $SessionId) | Out-Null
    $script:Terminated = $true
    $Record.session_terminated = ($script:AwsRc -eq 0)
  }
  KillTree $SessProc
}
function Fetch([string]$Url) {
  $resp = $null
  $fs = $null
  try {
    $req = [Net.HttpWebRequest][Net.WebRequest]::Create($Url)
    $req.Proxy = $null
    $req.KeepAlive = $false
    $req.Timeout = 10000
    $req.ReadWriteTimeout = 30000
    $resp = $req.GetResponse()
    if ([int]$resp.StatusCode -ne 200) { return $false }
    $fs = [IO.File]::Open($Part, "Create", "Write", "None")
    $resp.GetResponseStream().CopyTo($fs)
    $fs.Close()
    $fs = $null
    if ($resp.ContentLength -ge 0 -and (Get-Item -LiteralPath $Part).Length -ne $resp.ContentLength) { throw "short" }
    Move-Item -LiteralPath $Part -Destination $Final
    return $true
  } catch {
    # The message may hold the URL, and so the token: it is never shown.
    return $false
  } finally {
    if ($fs) { $fs.Close() }
    if ($resp) { $resp.Close() }
    Remove-Item -LiteralPath $Part -Force -ErrorAction SilentlyContinue
  }
}

try {
  $Vars = [ordered]@{ PO_TOKEN = $Token; PO_ARCHIVE = $Archive; PO_PORT = [string]$HostPort; PO_WINDOW_SECONDS = [string]$WindowSeconds }
  WriteAscii $VarsFile (ConvertTo-Json -InputObject $Vars -Compress)
  $HostArgs = @("-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", $HostRun, "-AwsProfile", $AwsProfile,
    "-Outputs", $Outputs, "-Script", $ServeScript, "-VarsFile", $VarsFile, "-TimeoutSeconds", [string]($WindowSeconds + 120),
    "-Out", $HostRecord)
  $HostProc = Start-Process -FilePath (Join-Path $PSHOME "powershell.exe") -ArgumentList (($HostArgs | ForEach-Object { Quote $_ }) -join " ") `
    -NoNewWindow -PassThru -RedirectStandardOutput $Log.hostrun_out -RedirectStandardError $Log.hostrun_err
  $null = $HostProc.Handle
  Write-Host "archive=$Archive host_port=$HostPort window_seconds=$WindowSeconds"

  $Listener = New-Object Net.Sockets.TcpListener ([Net.IPAddress]::Loopback), 0
  $Listener.Start()
  $LocalPort = $Listener.LocalEndpoint.Port
  $Listener.Stop()
  $Record.local_port = $LocalPort
  $Params = [ordered]@{ portNumber = @([string]$HostPort); localPortNumber = @([string]$LocalPort) }
  WriteAscii $ParamsFile (ConvertTo-Json -InputObject $Params -Compress)
  # Start-Process bypasses the Aws wrapper, so region and profile are named here.
  $SessArgs = @("ssm", "start-session", "--target", $Instance, "--document-name", $Document, "--parameters", "file://$ParamsFile",
    "--region", $Region, "--profile", $AwsProfile)
  $SessProc = Start-Process -FilePath $AwsExe -ArgumentList (($SessArgs | ForEach-Object { Quote $_ }) -join " ") `
    -NoNewWindow -PassThru -RedirectStandardOutput $Log.session_out -RedirectStandardError $Log.session_err
  $null = $SessProc.Handle
  $Ready = $false
  $Until = (Get-Date).AddSeconds(60)
  while ((Get-Date) -lt $Until) {
    DropVars
    $SessText = Shared $Log.session_out
    $m = [regex]::Match($SessText, "SessionId: (\S+)")
    if ($m.Success) { $SessionId = $m.Groups[1].Value.TrimEnd(".") }  # kept as soon as seen, so the finally can end it
    if ($SessionId -and $SessText -match "Waiting for connections") { $Ready = $true; break }
    if ($SessProc.HasExited) { break }
    Start-Sleep -Milliseconds 500
  }
  $Record.session_id = $SessionId
  if (-not $Ready) {
    $Record.failure = "the session did not open"
  } else {
    Remove-Item -LiteralPath $ParamsFile -Force -ErrorAction SilentlyContinue
    Write-Host "session_id=$SessionId local_port=$LocalPort"
    $Url = "http://127.0.0.1:$LocalPort/$Token/$Archive"
    # The host's window ends when host-run exits; the host may start serving late, so the poll follows host-run.
    # The deadline only backstops a host-run that outlives its own timeout.
    $Deadline = $HostProc.StartTime.AddSeconds($WindowSeconds + 180)
    $Got = $false
    while ((Get-Date) -lt $Deadline) {
      DropVars
      if (Fetch $Url) { $Got = $true; break }
      if ($HostProc.HasExited -or $SessProc.HasExited) { break }
      Start-Sleep -Seconds 2
    }
    EndSession
    if (-not $Got) { $Record.failure = "no archive arrived" }
  }

  if (-not $HostProc.WaitForExit(($WindowSeconds + 480) * 1000)) { KillTree $HostProc }
  if (Test-Path -LiteralPath $HostRecord) {
    $HostOut = Get-Content -LiteralPath $HostRecord -Raw | ConvertFrom-Json
    $Record.command_id = $HostOut.command_id
    $Record.host_status = $HostOut.status
    foreach ($line in ([string]$HostOut.stdout -split "`n")) {
      if ($line.TrimEnd("`r") -match '^([A-Za-z][A-Za-z0-9_]*)=(.*)$') { $Record.host_lines[$Matches[1]] = $Matches[2] }
    }
  } elseif (-not $Record.failure) {
    $Record.failure = "host-run wrote no record"
  }
  $Record.host_sha256 = $Record.host_lines["archive_sha256"]
  $Record.host_bytes = $Record.host_lines["archive_bytes"]
  if (Test-Path -LiteralPath $Final) {
    $Record.bytes = (Get-Item -LiteralPath $Final).Length
    $Record.local_sha256 = (Get-FileHash -LiteralPath $Final -Algorithm SHA256).Hash.ToLower()
    $Record.sha256_match = ($Record.local_sha256 -eq $Record.host_sha256)
    if ($Record.sha256_match -and [string]$Record.bytes -eq $Record.host_bytes -and $Record.host_lines["RESULT"] -eq "expected") {
      $Record.kept = $true
      $Rc = 0
    } else {
      $Record.failure = "the local file differs from the host's report"
    }
  } elseif ($Record.host_lines["RESULT"] -eq "expected" -and -not $Record.failure) {
    $Record.failure = "the host served the archive, but no file arrived"
  }
} finally {
  EndSession
  if ($HostProc -and -not $HostProc.HasExited) {
    KillTree $HostProc
    # A host-run killed during its send leaves its own parameters file, which holds the token.
    Get-ChildItem -LiteralPath $Temp -Filter "po-host-run-*.json" -ErrorAction SilentlyContinue |
      Where-Object { $_.CreationTimeUtc -ge $StartedUtc } | Remove-Item -Force -ErrorAction SilentlyContinue
  }
  if (-not $Record.kept) { Remove-Item -LiteralPath $Final -Force -ErrorAction SilentlyContinue }
  foreach ($f in @($VarsFile, $ParamsFile, $HostRecord, $Part) + @($Log.Values)) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
  $Record.end_utc = Utc
  ConvertTo-Json -InputObject $Record -Depth 3 | Out-File -Encoding utf8 $Out
}
$Line = "result=" + $(if ($Rc -eq 0) { "fetched" } else { "failed" })
if ($Record.failure) { $Line += " failure=$($Record.failure)" }
Write-Host "$Line sha256_match=$($Record.sha256_match) host_result=$($Record.host_lines['RESULT'])"
exit $Rc
