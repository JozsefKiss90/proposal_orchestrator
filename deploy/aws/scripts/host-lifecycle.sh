#!/usr/bin/env bash
# host-lifecycle.sh - start, stop or tear down the endpoints-and-host stack (ticket R14), CloudShell form.
#
#   bash host-lifecycle.sh start|stop|teardown|check <outdir> <prefix>
#
# Same checks and files as host-lifecycle.ps1; no profile (CloudShell signs with the console session).
# check     Records the CLI version, the caller account and the SHA-256 of the three uploaded files.
# start     No stack: create change set, check it, wait for the typed word "create", execute.
#           Stack up with the host stopped: wait for the typed word "start", start the host.
# stop      Stop the host. The six interface endpoints and the root volume stay, and still cost.
# teardown  Wait for the typed word "delete", delete the stack, check nothing of it remains.
#
# Reads 90-host.yaml and host.json beside itself, else from the repository layout. Every file is
# <outdir>/<prefix>_<name>; a prefix already used is refused. The last line of <prefix>_log.txt is
# RESULT=<word>. Exit 0 done, 1 failed, 2 refused, 3 not confirmed. Needs aws and python3 (CloudShell
# has both). Pinned by tests/test_aws_host_lifecycle_scripts.py.
set -u

ACTION="${1:-}"; OUTDIR="${2:-}"; PREFIX="${3:-}"
case "$ACTION" in start|stop|teardown|check) ;; *) echo "usage: host-lifecycle.sh start|stop|teardown|check <outdir> <prefix>"; exit 2 ;; esac
if [ -z "$OUTDIR" ] || [ ! -d "$OUTDIR" ]; then echo "REFUSED: <outdir> is not a folder"; exit 2; fi
case "$PREFIX" in ''|*[!A-Za-z0-9_]*) echo "REFUSED: <prefix> must be letters, digits and _"; exit 2 ;; esac
if ls "$OUTDIR"/"${PREFIX}"_* >/dev/null 2>&1; then echo "REFUSED: files ${PREFIX}_* exist in $OUTDIR; a run never overwrites"; exit 2; fi

STACK="proposal-orchestrator-host"
NETWORK_STACK="proposal-orchestrator-network"
POLL="${PO_POLL_SECONDS:-20}"
HERE="$(cd "$(dirname "$0")" && pwd)"
find_input() { if [ -f "$HERE/$1" ]; then echo "$HERE/$1"; else echo "$HERE/../$2/$1"; fi; }
TEMPLATE="$(find_input 90-host.yaml templates)"
HOSTJSON="$(find_input host.json parameters)"
if [ ! -f "$TEMPLATE" ] || [ ! -f "$HOSTJSON" ]; then echo "REFUSED: 90-host.yaml or host.json not found"; exit 2; fi

host_param() {
  python3 -c 'import json,sys; print({p["ParameterKey"]: p["ParameterValue"] for p in json.load(open(sys.argv[1], encoding="utf-8-sig"))}[sys.argv[2]])' "$HOSTJSON" "$1"
}
ACCOUNT="$(host_param ExpectedAccountId)"
REGION="$(host_param ExpectedRegion)"

LOG="$OUTDIR/${PREFIX}_log.txt"
log() { echo "$1"; echo "$1" >> "$LOG"; }
utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
save() { printf '%s\n' "$2" > "$OUTDIR/${PREFIX}_$1"; }
done_() { log "end_utc=$(utc)"; log "RESULT=$1"; exit "$2"; }
# run <var> <aws args...>: output into <var>, exit code into RC.
run() { local __v="$1"; shift; local __o; __o="$(aws "$@" --region "$REGION" 2>&1)"; RC=$?; printf -v "$__v" '%s' "$__o"; }
ask() {
  echo; echo "Type $1 and press Enter to $2. Anything else stops."
  local typed=""; read -r typed || true
  typed="$(echo "$typed" | tr -d '[:space:]')"
  if [ "$typed" = "$1" ]; then log "confirmed=$1"; return 0; fi
  log "confirmed=no"; return 1
}
count_json() {  # count_json <json> [type]: entries, or entries whose "type" equals [type]
  printf '%s' "$1" | python3 -c 'import json,sys; d=json.load(sys.stdin) or []; t=sys.argv[1] if len(sys.argv)>1 else None; print(len([x for x in d if x is not None and (t is None or x.get("type")==t)]))' ${2:+"$2"}
}
wait_online() {
  local n s
  for n in $(seq 0 29); do
    run s ssm describe-instance-information --filters "Key=InstanceIds,Values=$INSTANCE" --query "InstanceInformationList[0].PingStatus" --output text
    echo "ping try $n : $s"
    if [ "$s" = "Online" ]; then return 0; fi
    sleep "$POLL"
  done
  return 1
}

log "action=$ACTION"
log "start_utc=$(utc)"

run ID sts get-caller-identity --output json
save identity.json "$ID"
CALLER=""
if [ "$RC" -eq 0 ]; then CALLER="$(printf '%s' "$ID" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Account",""))')"; fi
if [ "$CALLER" != "$ACCOUNT" ]; then log "refused: caller account is not ExpectedAccountId of host.json"; done_ refused-account 2; fi

if [ "$ACTION" = "check" ]; then
  log "cli=$(aws --version 2>&1)"
  log "caller_account=$CALLER"
  log "region=$REGION"
  log "sha256_script=$(sha256sum "$0" | cut -d' ' -f1)"
  log "sha256_template=$(sha256sum "$TEMPLATE" | cut -d' ' -f1)"
  log "sha256_parameters=$(sha256sum "$HOSTJSON" | cut -d' ' -f1)"
  cp "$LOG" "$OUTDIR/${PREFIX}_check.txt"
  echo "RESULT=ready" >> "$OUTDIR/${PREFIX}_check.txt"
  done_ ready 0
fi

run STATUS cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].StackStatus" --output text
if [ "$RC" -ne 0 ]; then
  case "$STATUS" in *"does not exist"*) STATUS="ABSENT" ;; *) log "refused: describe-stacks failed: $STATUS"; done_ refused-state 2 ;; esac
fi
save stack-before.txt "$STATUS"
log "stack_status=$STATUS"

instance_id() { run INSTANCE cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue | [0]" --output text; }
instance_state() { run STATE ec2 describe-instances --instance-ids "$INSTANCE" --query "Reservations[0].Instances[0].State.Name" --output text; }

if [ "$ACTION" = "start" ]; then
  if [ "$STATUS" = "ABSENT" ]; then
    log "path=create"
    CS="session-$(date -u +%Y%m%dT%H%M%SZ)"
    log "change_set=$CS"
    run OUT cloudformation create-change-set --stack-name "$STACK" --change-set-name "$CS" --change-set-type CREATE --template-body "file://$TEMPLATE" --parameters "file://$HOSTJSON" --tags Key=project,Value=proposal-orchestrator --output json
    save create-change-set.json "$OUT"
    if [ "$RC" -ne 0 ]; then done_ change-set-failed 1; fi
    run OUT cloudformation wait change-set-create-complete --stack-name "$STACK" --change-set-name "$CS"
    run CSJSON cloudformation describe-change-set --stack-name "$STACK" --change-set-name "$CS" --output json
    save change-set.json "$CSJSON"
    CHECK="$(python3 - "$OUTDIR/${PREFIX}_change-set.json" "$HOSTJSON" <<'PY'
import json, sys
expected = ["BedrockRuntimeEndpoint", "Ec2MessagesEndpoint", "Host", "SecretsManagerEndpoint",
            "SsmEndpoint", "SsmMessagesEndpoint", "StsEndpoint"]
problems = []
try:
    cs = json.load(open(sys.argv[1], encoding="utf-8-sig"))
except ValueError:
    cs = None
    problems.append("change set is not JSON")
host = json.load(open(sys.argv[2], encoding="utf-8-sig"))
if cs is not None:
    if cs.get("Status") != "CREATE_COMPLETE":
        problems.append("status %s" % cs.get("Status"))
    if cs.get("ExecutionStatus") != "AVAILABLE":
        problems.append("execution status %s" % cs.get("ExecutionStatus"))
    if cs.get("Capabilities"):
        problems.append("capabilities requested")
    changes = [c.get("ResourceChange", {}) for c in cs.get("Changes", [])]
    adds = sorted(c.get("LogicalResourceId") for c in changes if c.get("Action") == "Add")
    if len(changes) != 7 or adds != expected:
        problems.append("changes are not exactly the seven Add of the template: %s" % ",".join(map(str, adds)))
    if not any(t.get("Key") == "project" and t.get("Value") == "proposal-orchestrator" for t in cs.get("Tags", [])):
        problems.append("stack tag project missing")
    got = {p.get("ParameterKey"): p for p in cs.get("Parameters", [])}
    for p in host:
        if got.get(p["ParameterKey"], {}).get("ParameterValue") != p["ParameterValue"]:
            problems.append("parameter %s differs from host.json" % p["ParameterKey"])
for x in problems:
    print("change_set_problem=" + x)
if not problems:
    print("change_set_ok=7 Add; instance_type=%s; image=%s" % (
        got.get("InstanceType", {}).get("ParameterValue"), got.get("LatestAmiId", {}).get("ResolvedValue")))
PY
)"
    while IFS= read -r line; do [ -n "$line" ] && log "$line"; done <<< "$CHECK"
    case "$CHECK" in
      *change_set_problem=*)
        run OUT cloudformation delete-stack --stack-name "$STACK"
        log "change set not executed; stack in review deleted (exit $RC)"
        done_ refused-change-set 3 ;;
    esac
    if ! ask create "create the stack (hourly charges start)"; then
      run OUT cloudformation delete-stack --stack-name "$STACK"
      log "change set not executed; stack in review deleted (exit $RC)"
      done_ not-confirmed 3
    fi
    log "execute_utc=$(utc)"
    run OUT cloudformation execute-change-set --stack-name "$STACK" --change-set-name "$CS"
    save execute-exit.txt "$OUT
execute exit=$RC"
    if [ "$RC" -ne 0 ]; then done_ execute-failed 1; fi
    run OUT cloudformation wait stack-create-complete --stack-name "$STACK"
    run OUT cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json
    save stack-status.json "$OUT"
    run OUT cloudformation describe-stack-events --stack-name "$STACK" --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json
    save stack-events.json "$OUT"
    run FINAL cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].StackStatus" --output text
    log "stack_status=$FINAL"
    if [ "$FINAL" != "CREATE_COMPLETE" ]; then log "creation failed: run teardown"; done_ create-failed 1; fi
  elif [ "$STATUS" = "CREATE_COMPLETE" ]; then
    instance_id; instance_state
    log "instance_state=$STATE"
    if [ "$STATE" = "running" ]; then log "path=none"; done_ already-running 0; fi
    if [ "$STATE" != "stopped" ]; then log "refused: host is $STATE; wait and run again"; done_ refused-state 2; fi
    log "path=resume"
    if ! ask start "start the host (its hourly charge starts)"; then done_ not-confirmed 3; fi
    run OUT ec2 start-instances --instance-ids "$INSTANCE" --output json
    save start-instances.json "$OUT"
    if [ "$RC" -ne 0 ]; then done_ start-failed 1; fi
    run OUT ec2 wait instance-running --instance-ids "$INSTANCE"
  else
    log "refused: stack is $STATUS. A stack in REVIEW_IN_PROGRESS holds no resource: run teardown to remove it"
    done_ refused-state 2
  fi
  instance_id
  run OUT cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs" --output json
  save outputs.json "$OUT"
  ONLINE=0; wait_online && ONLINE=1
  run OUT ssm describe-instance-information --filters "Key=InstanceIds,Values=$INSTANCE" --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,resourceType:ResourceType}" --output json
  save instance-information.json "$OUT"
  if [ "$ONLINE" -ne 1 ]; then log "host not Online after 30 tries"; done_ not-online 1; fi
  done_ started 0
fi

if [ "$ACTION" = "stop" ]; then
  if [ "$STATUS" != "CREATE_COMPLETE" ]; then log "refused: stack is $STATUS"; done_ refused-state 2; fi
  instance_id; instance_state
  log "instance_state=$STATE"
  if [ "$STATE" = "running" ]; then
    run OUT ec2 stop-instances --instance-ids "$INSTANCE" --output json
    save stop-instances.json "$OUT"
    if [ "$RC" -ne 0 ]; then done_ stop-failed 1; fi
    run OUT ec2 wait instance-stopped --instance-ids "$INSTANCE"
  elif [ "$STATE" != "stopped" ]; then log "refused: host is $STATE; wait and run again"; done_ refused-state 2; fi
  run REC ec2 describe-instances --instance-ids "$INSTANCE" --query "Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,vpc:VpcId}" --output json
  save instance.json "$REC"
  run OUT ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$INSTANCE" --query "Volumes[].{id:VolumeId,state:State,type:VolumeType,size:Size}" --output json
  save volumes.json "$OUT"
  VPC="$(printf '%s' "$REC" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("vpc",""))')"
  run OUT ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC" --query "VpcEndpoints[?State!='deleted'].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json
  save vpc-endpoints.json "$OUT"
  instance_state
  log "instance_state=$STATE"
  log "note=the interface endpoints and the root volume remain and still cost; teardown ends that"
  if [ "$STATE" != "stopped" ]; then done_ not-stopped 1; fi
  done_ stopped 0
fi

if [ "$ACTION" = "teardown" ]; then
  if [ "$STATUS" = "ABSENT" ]; then log "nothing to delete"; done_ absent 0; fi
  run VPC cloudformation describe-stacks --stack-name "$NETWORK_STACK" --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue | [0]" --output text
  if ! ask delete "delete the stack (the host and its disk are lost)"; then done_ not-confirmed 3; fi
  log "delete_utc=$(utc)"
  run OUT cloudformation delete-stack --stack-name "$STACK"
  save delete-exit.txt "$OUT
delete exit=$RC"
  if [ "$RC" -ne 0 ]; then done_ delete-failed 1; fi
  run OUT cloudformation wait stack-delete-complete --stack-name "$STACK"
  run AFTER cloudformation describe-stacks --stack-name "$STACK" --output json
  AFTER_RC=$RC
  save host-stack-after.txt "$AFTER
exit=$AFTER_RC"
  GONE=0
  if [ "$AFTER_RC" -ne 0 ]; then case "$AFTER" in *"does not exist"*) GONE=1 ;; esac; fi
  LEFT=""
  for n in $(seq 0 9); do
    LEFT=""; FAILED=0
    run EP ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC" --query "VpcEndpoints[?State!='deleted'].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json; [ "$RC" -ne 0 ] && FAILED=$((FAILED+1))
    run ENI ec2 describe-network-interfaces --filters "Name=vpc-id,Values=$VPC" --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,status:Status}" --output json; [ "$RC" -ne 0 ] && FAILED=$((FAILED+1))
    run INS ec2 describe-instances --filters "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json; [ "$RC" -ne 0 ] && FAILED=$((FAILED+1))
    run VOL ec2 describe-volumes --filters "Name=tag:project,Values=proposal-orchestrator" --query "Volumes[].{id:VolumeId,state:State}" --output json; [ "$RC" -ne 0 ] && FAILED=$((FAILED+1))
    if [ "$FAILED" -gt 0 ]; then LEFT="lookups failed $FAILED"; sleep "$POLL"; continue; fi
    c="$(count_json "$EP" Interface)"; [ "$c" -gt 0 ] && LEFT="$LEFT;interface endpoints $c"
    c="$(count_json "$ENI")"; [ "$c" -gt 0 ] && LEFT="$LEFT;network interfaces $c"
    c="$(count_json "$INS")"; [ "$c" -gt 0 ] && LEFT="$LEFT;instances $c"
    c="$(count_json "$VOL")"; [ "$c" -gt 0 ] && LEFT="$LEFT;volumes $c"
    [ -z "$LEFT" ] && break
    echo "waiting for:$LEFT"; sleep "$POLL"
  done
  save after-vpc-endpoints.json "$EP"
  save after-network-interfaces.json "$ENI"
  save after-instances.json "$INS"
  save after-volumes.json "$VOL"
  run BASE cloudformation describe-stacks --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-') && StackName != 'proposal-orchestrator-host'].{name:StackName,status:StackStatus}" --output json
  BASE_RC=$RC
  save after-base-stacks.json "$BASE"
  OK=0
  if [ "$BASE_RC" -eq 0 ]; then
    OK="$(printf '%s' "$BASE" | python3 -c 'import json,sys; print(len([s for s in json.load(sys.stdin) or [] if s.get("status") in ("CREATE_COMPLETE","UPDATE_COMPLETE")]))')"
  fi
  log "base_stacks_complete=$OK"
  [ "$OK" -ne 5 ] && LEFT="$LEFT;base stacks complete $OK of 5"
  [ "$GONE" -ne 1 ] && LEFT="$LEFT;host stack still exists"
  if [ -n "$LEFT" ]; then
    IFS=';' read -ra parts <<< "$LEFT"
    for x in "${parts[@]}"; do [ -n "$x" ] && log "leftover=$x"; done
    done_ leftovers 1
  fi
  done_ deleted 0
fi
