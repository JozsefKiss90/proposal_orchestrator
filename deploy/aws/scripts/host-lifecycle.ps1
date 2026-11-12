# host-lifecycle.ps1 - start, stop or tear down the endpoints-and-host stack (ticket R14).
#
#   host-lifecycle.ps1 -Action start|stop|teardown|plan -AwsProfile <profile> -OutDir <dir> -Prefix <R14_NN>
#
# start     No stack: create change set, check it, wait for the typed word "create", execute.
#           Stack up with the host stopped: wait for the typed word "start", start the host.
#           Both paths wait for the host to be Online in SSM and write its outputs.
# stop      Stop the host. The six interface endpoints and the root volume stay, and still cost.
# teardown  Wait for the typed word "delete", delete the stack, check nothing of it remains.
# plan      Print every AWS command this script can run. Calls nothing, writes nothing.
#
# Every file is written as <OutDir>\<Prefix>_<name>; a prefix already used is refused. The last
# line of <Prefix>_log.txt is RESULT=<word>. Exit 0 done, 1 failed, 2 refused, 3 not confirmed.
# The CloudShell form is host-lifecycle.sh: same checks, same files. Pinned by
# tests/test_aws_host_lifecycle_scripts.py. Account and Region come from parameters/host.json.
param(
  [Parameter(Mandatory = $true)][ValidateSet("start", "stop", "teardown", "plan")][string]$Action,
  [Parameter(Mandatory = $true)][string]$AwsProfile,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_]+$')][string]$Prefix
)
$ErrorActionPreference = "Continue"

$Stack = "proposal-orchestrator-host"
$NetworkStack = "proposal-orchestrator-network"
$Expected = @("BedrockRuntimeEndpoint", "Ec2MessagesEndpoint", "Host", "SecretsManagerEndpoint",
  "SsmEndpoint", "SsmMessagesEndpoint", "StsEndpoint")
$Poll = 20
if ($env:PO_POLL_SECONDS) { $Poll = [int]$env:PO_POLL_SECONDS }

function Find-Input([string]$Name, [string]$Sub) {
  $here = Join-Path $PSScriptRoot $Name
  if (Test-Path $here) { return $here }
  return (Join-Path (Join-Path (Split-Path $PSScriptRoot -Parent) $Sub) $Name)
}
$Template = Find-Input "90-host.yaml" "templates"
$HostJson = Find-Input "host.json" "parameters"
if (-not ((Test-Path $Template) -and (Test-Path $HostJson))) {
  Write-Host "REFUSED: 90-host.yaml or host.json not found beside the script or in the repository"; exit 2
}
$HostParams = (Get-Content $HostJson -Raw | ConvertFrom-Json)
$HostParams = @($HostParams | ForEach-Object { $_ })  # 5.1 returns a JSON array as one object
function HostParam([string]$Key) { ($HostParams | Where-Object { $_.ParameterKey -eq $Key }).ParameterValue }
$Account = HostParam "ExpectedAccountId"
$Region = HostParam "ExpectedRegion"

# Every AWS call this script makes. {I} instance, {CS} change set, {VPC} VPC, {T} template, {P} parameters.
$C = [ordered]@{
  identity             = @("sts", "get-caller-identity", "--output", "json")
  stack_status         = @("cloudformation", "describe-stacks", "--stack-name", $Stack, "--query", "Stacks[0].StackStatus", "--output", "text")
  instance_id          = @("cloudformation", "describe-stacks", "--stack-name", $Stack, "--query", "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue | [0]", "--output", "text")
  instance_state       = @("ec2", "describe-instances", "--instance-ids", "{I}", "--query", "Reservations[0].Instances[0].State.Name", "--output", "text")
  create_change_set    = @("cloudformation", "create-change-set", "--stack-name", $Stack, "--change-set-name", "{CS}", "--change-set-type", "CREATE", "--template-body", "file://{T}", "--parameters", "file://{P}", "--tags", "Key=project,Value=proposal-orchestrator", "--output", "json")
  wait_change_set      = @("cloudformation", "wait", "change-set-create-complete", "--stack-name", $Stack, "--change-set-name", "{CS}")
  describe_change_set  = @("cloudformation", "describe-change-set", "--stack-name", $Stack, "--change-set-name", "{CS}", "--output", "json")
  execute_change_set   = @("cloudformation", "execute-change-set", "--stack-name", $Stack, "--change-set-name", "{CS}")
  wait_create          = @("cloudformation", "wait", "stack-create-complete", "--stack-name", $Stack)
  stack_record         = @("cloudformation", "describe-stacks", "--stack-name", $Stack, "--query", "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}", "--output", "json")
  stack_events         = @("cloudformation", "describe-stack-events", "--stack-name", $Stack, "--query", "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}", "--output", "json")
  outputs              = @("cloudformation", "describe-stacks", "--stack-name", $Stack, "--query", "Stacks[0].Outputs", "--output", "json")
  ping                 = @("ssm", "describe-instance-information", "--filters", "Key=InstanceIds,Values={I}", "--query", "InstanceInformationList[0].PingStatus", "--output", "text")
  instance_information = @("ssm", "describe-instance-information", "--filters", "Key=InstanceIds,Values={I}", "--query", "InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,resourceType:ResourceType}", "--output", "json")
  start_instances      = @("ec2", "start-instances", "--instance-ids", "{I}", "--output", "json")
  wait_running         = @("ec2", "wait", "instance-running", "--instance-ids", "{I}")
  stop_instances       = @("ec2", "stop-instances", "--instance-ids", "{I}", "--output", "json")
  wait_stopped         = @("ec2", "wait", "instance-stopped", "--instance-ids", "{I}")
  instance_record      = @("ec2", "describe-instances", "--instance-ids", "{I}", "--query", "Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,vpc:VpcId}", "--output", "json")
  volumes              = @("ec2", "describe-volumes", "--filters", "Name=attachment.instance-id,Values={I}", "--query", "Volumes[].{id:VolumeId,state:State,type:VolumeType,size:Size}", "--output", "json")
  vpc_id               = @("cloudformation", "describe-stacks", "--stack-name", $NetworkStack, "--query", "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue | [0]", "--output", "text")
  vpc_endpoints        = @("ec2", "describe-vpc-endpoints", "--filters", "Name=vpc-id,Values={VPC}", "--query", "VpcEndpoints[?State!='deleted'].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}", "--output", "json")
  delete_stack         = @("cloudformation", "delete-stack", "--stack-name", $Stack)
  wait_delete          = @("cloudformation", "wait", "stack-delete-complete", "--stack-name", $Stack)
  stack_after          = @("cloudformation", "describe-stacks", "--stack-name", $Stack, "--output", "json")
  network_interfaces   = @("ec2", "describe-network-interfaces", "--filters", "Name=vpc-id,Values={VPC}", "--query", "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,status:Status}", "--output", "json")
  instances_left       = @("ec2", "describe-instances", "--filters", "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down", "--query", "Reservations[].Instances[].{id:InstanceId,state:State.Name}", "--output", "json")
  volumes_left         = @("ec2", "describe-volumes", "--filters", "Name=tag:project,Values=proposal-orchestrator", "--query", "Volumes[].{id:VolumeId,state:State}", "--output", "json")
  base_stacks          = @("cloudformation", "describe-stacks", "--query", "Stacks[?starts_with(StackName, 'proposal-orchestrator-') && StackName != 'proposal-orchestrator-host'].{name:StackName,status:StackStatus}", "--output", "json")
}
$V = @{ "{T}" = $Template; "{P}" = $HostJson }

function Argv([string]$Key) {
  $out = @()
  foreach ($a in $C[$Key]) { foreach ($k in $V.Keys) { $a = $a.Replace($k, [string]$V[$k]) }; $out += $a }
  return @($out + @("--region", $Region, "--profile", $AwsProfile))
}

if ($Action -eq "plan") {
  foreach ($k in $C.Keys) { "{0,-21} aws {1}" -f $k, ((Argv $k) -join " ") }
  exit 0
}

if (-not (Test-Path $OutDir -PathType Container)) { Write-Host "REFUSED: $OutDir is not a folder"; exit 2 }
if (@(Get-ChildItem $OutDir -Filter "${Prefix}_*").Count -gt 0) { Write-Host "REFUSED: files ${Prefix}_* exist in $OutDir; a run never overwrites"; exit 2 }
$AwsExe = (Get-Command aws -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $AwsExe) { Write-Host "REFUSED: the AWS CLI (aws) is not on PATH"; exit 2 }
$LogFile = Join-Path $OutDir "${Prefix}_log.txt"
$script:Rc = 0

function Log([string]$Line) { Write-Host $Line; Add-Content -Encoding utf8 -Path $LogFile -Value $Line }
function Utc { (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
function Run([string]$Key) {
  $argv = Argv $Key
  $out = & $AwsExe @argv 2>&1 | ForEach-Object { "$_" }
  $script:Rc = $LASTEXITCODE
  return (($out -join "`n").Trim())
}
function Save([string]$Name, [string]$Text) { $Text | Out-File -Encoding utf8 (Join-Path $OutDir "${Prefix}_$Name") }
function Done([string]$Result, [int]$Code) { Log "end_utc=$(Utc)"; Log "RESULT=$Result"; exit $Code }
function Count-Json([string]$Text) { $o = $Text | ConvertFrom-Json; return @($o | Where-Object { $null -ne $_ }).Count }
function Ask([string]$Word, [string]$What) {
  Write-Host ""
  Write-Host "Type $Word and press Enter to $What. Anything else stops."
  $typed = [Console]::In.ReadLine()
  if ($null -eq $typed) { $typed = "" }
  if ($typed.Trim() -eq $Word) { Log "confirmed=$Word"; return $true }
  Log "confirmed=no"; return $false
}
function Wait-Online {
  for ($n = 0; $n -lt 30; $n++) {
    $s = Run "ping"
    Write-Host "ping try $n : $s"
    if ($s -eq "Online") { return $true }
    Start-Sleep -Seconds $Poll
  }
  return $false
}

Log "action=$Action"
Log "start_utc=$(Utc)"

$id = Run "identity"
Save "identity.json" $id
$caller = $null
if ($script:Rc -eq 0) { $caller = ($id | ConvertFrom-Json).Account }
if ($caller -ne $Account) { Log "refused: caller account is not ExpectedAccountId of host.json"; Done "refused-account" 2 }

$status = Run "stack_status"
$absent = ($script:Rc -ne 0) -and ($status -match "does not exist")
if (($script:Rc -ne 0) -and -not $absent) { Log "refused: describe-stacks failed: $status"; Done "refused-state" 2 }
if ($absent) { $status = "ABSENT" }
Save "stack-before.txt" $status
Log "stack_status=$status"

if ($Action -eq "start") {
  if ($status -eq "ABSENT") {
    Log "path=create"
    $V["{CS}"] = "session-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    Log "change_set=$($V['{CS}'])"
    Save "create-change-set.json" (Run "create_change_set")
    if ($script:Rc -ne 0) { Done "change-set-failed" 1 }
    $null = Run "wait_change_set"
    $csText = Run "describe_change_set"
    Save "change-set.json" $csText
    $problems = @()
    $cs = $null
    try { $cs = $csText | ConvertFrom-Json } catch { $problems += "change set is not JSON" }
    if ($null -ne $cs) {
      if ($cs.Status -ne "CREATE_COMPLETE") { $problems += "status $($cs.Status)" }
      if ($cs.ExecutionStatus -ne "AVAILABLE") { $problems += "execution status $($cs.ExecutionStatus)" }
      if (($cs.Capabilities | Measure-Object).Count -ne 0) { $problems += "capabilities requested" }
      $changes = @($cs.Changes | ForEach-Object { $_.ResourceChange })
      $adds = @($changes | Where-Object { $_.Action -eq "Add" } | ForEach-Object { $_.LogicalResourceId } | Sort-Object)
      if ($changes.Count -ne 7 -or (($adds -join ",") -ne ($Expected -join ","))) { $problems += "changes are not exactly the seven Add of the template: $($adds -join ',')" }
      if (-not ($cs.Tags | Where-Object { $_.Key -eq "project" -and $_.Value -eq "proposal-orchestrator" })) { $problems += "stack tag project missing" }
      foreach ($p in $HostParams) {
        $got = ($cs.Parameters | Where-Object { $_.ParameterKey -eq $p.ParameterKey }).ParameterValue
        if ($got -ne $p.ParameterValue) { $problems += "parameter $($p.ParameterKey) differs from host.json" }
      }
    }
    if ($problems.Count -gt 0) {
      foreach ($x in $problems) { Log "change_set_problem=$x" }
      $null = Run "delete_stack"
      Log "change set not executed; stack in review deleted (exit $($script:Rc))"
      Done "refused-change-set" 3
    }
    $type = ($cs.Parameters | Where-Object { $_.ParameterKey -eq "InstanceType" }).ParameterValue
    $ami = ($cs.Parameters | Where-Object { $_.ParameterKey -eq "LatestAmiId" }).ResolvedValue
    Log "change_set_ok=7 Add; instance_type=$type; image=$ami"
    if (-not (Ask "create" "create the stack (hourly charges start)")) {
      $null = Run "delete_stack"
      Log "change set not executed; stack in review deleted (exit $($script:Rc))"
      Done "not-confirmed" 3
    }
    Log "execute_utc=$(Utc)"
    $ex = Run "execute_change_set"
    Save "execute-exit.txt" ($ex + "`nexecute exit=$($script:Rc)")
    if ($script:Rc -ne 0) { Done "execute-failed" 1 }
    $null = Run "wait_create"
    $record = Run "stack_record"
    Save "stack-status.json" $record
    Save "stack-events.json" (Run "stack_events")
    $final = Run "stack_status"
    Log "stack_status=$final"
    if ($final -ne "CREATE_COMPLETE") { Log "creation failed: run teardown"; Done "create-failed" 1 }
  }
  elseif ($status -eq "CREATE_COMPLETE") {
    $V["{I}"] = Run "instance_id"
    $state = Run "instance_state"
    Log "instance_state=$state"
    if ($state -eq "running") { Log "path=none"; Done "already-running" 0 }
    if ($state -ne "stopped") { Log "refused: host is $state; wait and run again"; Done "refused-state" 2 }
    Log "path=resume"
    if (-not (Ask "start" "start the host (its hourly charge starts)")) { Done "not-confirmed" 3 }
    Save "start-instances.json" (Run "start_instances")
    if ($script:Rc -ne 0) { Done "start-failed" 1 }
    $null = Run "wait_running"
  }
  else {
    Log "refused: stack is $status. A stack in REVIEW_IN_PROGRESS holds no resource: run teardown to remove it"
    Done "refused-state" 2
  }
  $V["{I}"] = Run "instance_id"
  Save "outputs.json" (Run "outputs")
  $online = Wait-Online
  Save "instance-information.json" (Run "instance_information")
  if (-not $online) { Log "host not Online after 30 tries"; Done "not-online" 1 }
  Done "started" 0
}

if ($Action -eq "stop") {
  if ($status -ne "CREATE_COMPLETE") { Log "refused: stack is $status"; Done "refused-state" 2 }
  $V["{I}"] = Run "instance_id"
  $state = Run "instance_state"
  Log "instance_state=$state"
  if ($state -eq "running") {
    Save "stop-instances.json" (Run "stop_instances")
    if ($script:Rc -ne 0) { Done "stop-failed" 1 }
    $null = Run "wait_stopped"
  }
  elseif ($state -ne "stopped") { Log "refused: host is $state; wait and run again"; Done "refused-state" 2 }
  $rec = Run "instance_record"
  Save "instance.json" $rec
  Save "volumes.json" (Run "volumes")
  $V["{VPC}"] = ($rec | ConvertFrom-Json).vpc
  Save "vpc-endpoints.json" (Run "vpc_endpoints")
  $now = Run "instance_state"
  Log "instance_state=$now"
  Log "note=the interface endpoints and the root volume remain and still cost; teardown ends that"
  if ($now -ne "stopped") { Done "not-stopped" 1 }
  Done "stopped" 0
}

if ($Action -eq "teardown") {
  if ($status -eq "ABSENT") { Log "nothing to delete"; Done "absent" 0 }
  $V["{VPC}"] = Run "vpc_id"
  if (-not (Ask "delete" "delete the stack (the host and its disk are lost)")) { Done "not-confirmed" 3 }
  Log "delete_utc=$(Utc)"
  $d = Run "delete_stack"
  Save "delete-exit.txt" ($d + "`ndelete exit=$($script:Rc)")
  if ($script:Rc -ne 0) { Done "delete-failed" 1 }
  $null = Run "wait_delete"
  $after = Run "stack_after"
  Save "host-stack-after.txt" ($after + "`nexit=$($script:Rc)")
  $gone = ($script:Rc -ne 0) -and ($after -match "does not exist")
  $leftover = @()
  for ($n = 0; $n -lt 10; $n++) {
    $failed = 0
    $ep = Run "vpc_endpoints"; $failed += [int]($script:Rc -ne 0)
    $eni = Run "network_interfaces"; $failed += [int]($script:Rc -ne 0)
    $ins = Run "instances_left"; $failed += [int]($script:Rc -ne 0)
    $vol = Run "volumes_left"; $failed += [int]($script:Rc -ne 0)
    $leftover = @()
    if ($failed -gt 0) { $leftover += "lookups failed $failed"; Start-Sleep -Seconds $Poll; continue }
    $interface = @(($ep | ConvertFrom-Json) | Where-Object { $null -ne $_ -and $_.type -eq "Interface" }).Count
    if ($interface -gt 0) { $leftover += "interface endpoints $interface" }
    if ((Count-Json $eni) -gt 0) { $leftover += "network interfaces $(Count-Json $eni)" }
    if ((Count-Json $ins) -gt 0) { $leftover += "instances $(Count-Json $ins)" }
    if ((Count-Json $vol) -gt 0) { $leftover += "volumes $(Count-Json $vol)" }
    if ($leftover.Count -eq 0) { break }
    Write-Host "waiting for: $($leftover -join ', ')"
    Start-Sleep -Seconds $Poll
  }
  Save "after-vpc-endpoints.json" $ep
  Save "after-network-interfaces.json" $eni
  Save "after-instances.json" $ins
  Save "after-volumes.json" $vol
  $base = Run "base_stacks"
  Save "after-base-stacks.json" $base
  $ok = 0
  if ($script:Rc -eq 0) { $ok = @(($base | ConvertFrom-Json) | Where-Object { $null -ne $_ -and $_.status -in "CREATE_COMPLETE", "UPDATE_COMPLETE" }).Count }
  Log "base_stacks_complete=$ok"
  if ($ok -ne 5) { $leftover += "base stacks complete $ok of 5" }
  if (-not $gone) { $leftover += "host stack still exists" }
  foreach ($x in $leftover) { Log "leftover=$x" }
  if ($leftover.Count -gt 0) { Done "leftovers" 1 }
  Done "deleted" 0
}
