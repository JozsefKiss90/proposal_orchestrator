# host-run.ps1 - send one fixed shell script to the host by Run Command and wait for it (ticket R15).
#
#   host-run.ps1 -AwsProfile <profile> -Outputs <R15_06_outputs.json> -Script <file.sh>
#                [-VarsFile <vars.json>] [-TimeoutSeconds <n>] -Out <result.json>
#
# The script is sent as AWS-RunShellScript, as root, with CRLF turned into LF. -VarsFile is a JSON
# object of PO_ names and string values; each becomes one export line before the script. The
# parameters pass through one temporary file outside the repository, deleted right after the send:
# Windows PowerShell 5.1 strips the quotes of inline JSON passed to aws. -TimeoutSeconds is the
# Run Command execution timeout. The script and the vars must be ASCII.
#
# -Out is written once, as JSON: the script and its LF sha256, the var names (never their values),
# the instance, the command id, sent and finished UTC, status, responseCode, stdout, stderr and
# stdout_truncated (SSM returns at most 24,000 characters of stdout). A file that exists is never
# overwritten. Exit 0 status Success, 1 any other status, 2 refused before any AWS call.
# Region comes from parameters/host.json. Pinned by tests/test_aws_host_run_script.py.
param(
  [Parameter(Mandatory = $true)][string]$AwsProfile,
  [Parameter(Mandatory = $true)][string]$Outputs,
  [Parameter(Mandatory = $true)][string]$Script,
  [string]$VarsFile = "",
  [ValidateRange(60, 172800)][int]$TimeoutSeconds = 600,
  [Parameter(Mandatory = $true)][string]$Out
)
$ErrorActionPreference = "Continue"

$Poll = 10
if ($env:PO_POLL_SECONDS) { $Poll = [int]$env:PO_POLL_SECONDS }
$StdoutLimit = 24000
$StderrLimit = 8000
$Terminal = @("Success", "Failed", "TimedOut", "Cancelled")

function Refuse([string]$Why) { Write-Host "REFUSED: $Why"; exit 2 }
function Utc { (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
function Ascii([string]$Text) { return -not ($Text -match '[^\x00-\x7F]') }

$HostJson = Join-Path (Join-Path (Split-Path $PSScriptRoot -Parent) "parameters") "host.json"
if (-not (Test-Path $HostJson)) { Refuse "host.json not found at $HostJson" }
$HostParams = @((Get-Content $HostJson -Raw | ConvertFrom-Json) | ForEach-Object { $_ })
$Region = ($HostParams | Where-Object { $_.ParameterKey -eq "ExpectedRegion" }).ParameterValue
if (-not $Region) { Refuse "host.json names no ExpectedRegion" }

if (Test-Path $Out) { Refuse "$Out exists; a run never overwrites" }
if (-not (Test-Path (Split-Path $Out -Parent) -PathType Container)) { Refuse "the folder of $Out does not exist" }
if (-not (Test-Path $Outputs -PathType Leaf)) { Refuse "$Outputs not found" }
$Instance = ((Get-Content $Outputs -Raw | ConvertFrom-Json) | ForEach-Object { $_ } | Where-Object { $_.OutputKey -eq "InstanceId" }).OutputValue
if (-not ("$Instance" -match '^i-[0-9a-f]{8,17}$')) { Refuse "$Outputs holds no InstanceId" }

if (-not (Test-Path $Script -PathType Leaf)) { Refuse "$Script not found" }
$Text = [IO.File]::ReadAllText((Resolve-Path $Script).Path, (New-Object Text.UTF8Encoding $false)).Replace("`r`n", "`n")
if (-not (Ascii $Text)) { Refuse "$Script holds a non-ASCII character" }
$Sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes($Text))).Replace("-", "").ToLower()

$Exports = @()
$Names = @()
if ($VarsFile) {
  if (-not (Test-Path $VarsFile -PathType Leaf)) { Refuse "$VarsFile not found" }
  $Vars = Get-Content $VarsFile -Raw | ConvertFrom-Json
  if ($null -eq $Vars -or $Vars -is [array] -or $Vars -isnot [PSCustomObject]) { Refuse "$VarsFile is not a JSON object" }
  foreach ($p in ($Vars.PSObject.Properties | Sort-Object Name)) {
    if (-not ($p.Name -cmatch '^PO_[A-Z0-9_]+$')) { Refuse "$VarsFile names $($p.Name); only PO_ names are sent" }
    if ($p.Value -isnot [string]) { Refuse "$VarsFile gives $($p.Name) a value that is not a string" }
    if (-not (Ascii $p.Value)) { Refuse "$VarsFile gives $($p.Name) a non-ASCII value" }
    $Exports += "export $($p.Name)='" + $p.Value.Replace("'", "'\''") + "'"
    $Names += $p.Name
  }
}

$AwsExe = (Get-Command aws -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $AwsExe) { Refuse "the AWS CLI (aws) is not on PATH" }
function Aws([string[]]$Argv) {
  $all = @($Argv + @("--region", $Region, "--profile", $AwsProfile))
  $o = & $AwsExe @all 2>&1 | ForEach-Object { "$_" }
  $script:Rc = $LASTEXITCODE
  return (($o -join "`n").Trim())
}

$Lines = @($Exports + ($Text.TrimEnd("`n") -split "`n"))
$Params = [ordered]@{ commands = $Lines; executionTimeout = @([string]$TimeoutSeconds) }
$Pf = Join-Path ([IO.Path]::GetTempPath()) ("po-host-run-" + [guid]::NewGuid().ToString("N") + ".json")
$Name = Split-Path $Script -Leaf
try {
  [IO.File]::WriteAllText($Pf, (ConvertTo-Json -InputObject $Params -Depth 3 -Compress), (New-Object Text.UTF8Encoding $false))
  $Sent = Utc
  $CommandId = Aws @("ssm", "send-command", "--instance-ids", $Instance, "--document-name", "AWS-RunShellScript",
    "--comment", "R15 host-run $Name", "--timeout-seconds", "120", "--parameters", "file://$Pf",
    "--query", "Command.CommandId", "--output", "text")
  $SendRc = $script:Rc
} finally {
  Remove-Item -LiteralPath $Pf -Force -ErrorAction SilentlyContinue
}

$Record = [ordered]@{
  script = $Script; script_sha256 = $Sha; vars_file = $VarsFile; vars_names = $Names
  instance_id = $Instance; timeout_seconds = $TimeoutSeconds; sent_utc = $Sent
}
if ($SendRc -ne 0 -or -not ($CommandId -match '^[0-9a-f-]{36}$')) {
  $Record.command_id = $null; $Record.finished_utc = Utc; $Record.status = "NotSent"
  $Record.send_error = $CommandId
  ConvertTo-Json -InputObject $Record -Depth 3 | Out-File -Encoding utf8 $Out
  Write-Host "status=NotSent"; Write-Host $CommandId; exit 1
}
$Record.command_id = $CommandId
Write-Host "command_id=$CommandId sent_utc=$Sent"

$Deadline = (Get-Date).AddSeconds($TimeoutSeconds + 300)
$Status = ""
while ($true) {
  Start-Sleep -Seconds $Poll
  $Status = Aws @("ssm", "get-command-invocation", "--command-id", $CommandId, "--instance-id", $Instance, "--query", "Status", "--output", "text")
  if ($script:Rc -eq 0 -and $Terminal -contains $Status) { break }
  if ((Get-Date) -gt $Deadline) { break }
}
$Raw = Aws @("ssm", "get-command-invocation", "--command-id", $CommandId, "--instance-id", $Instance, "--output", "json")
$Record.finished_utc = Utc
if ($script:Rc -ne 0) {
  $Record.status = "Unread"; $Record.read_error = $Raw
  ConvertTo-Json -InputObject $Record -Depth 3 | Out-File -Encoding utf8 $Out
  Write-Host "status=Unread"; Write-Host $Raw; exit 1
}
$Inv = $Raw | ConvertFrom-Json
$Stdout = [string]$Inv.StandardOutputContent
$Stderr = [string]$Inv.StandardErrorContent
$Record.status = $Inv.Status
$Record.status_details = $Inv.StatusDetails
$Record.responseCode = $Inv.ResponseCode
$Record.execution_start = $Inv.ExecutionStartDateTime
$Record.execution_end = $Inv.ExecutionEndDateTime
$Record.stdout = $Stdout
$Record.stderr = $Stderr
$Record.stdout_truncated = ($Stdout.Length -ge $StdoutLimit)
$Record.stderr_truncated = ($Stderr.Length -ge $StderrLimit)
ConvertTo-Json -InputObject $Record -Depth 3 | Out-File -Encoding utf8 $Out

Write-Host "status=$($Inv.Status) responseCode=$($Inv.ResponseCode) stdout_truncated=$($Record.stdout_truncated)"
Write-Host $Stdout
if ($Stderr) { Write-Host "--- stderr ---"; Write-Host $Stderr }
if ($Inv.Status -eq "Success") { exit 0 }
exit 1
