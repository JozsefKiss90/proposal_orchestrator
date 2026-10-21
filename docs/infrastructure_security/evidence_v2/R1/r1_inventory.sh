#!/usr/bin/env bash
# R1 — read-only inventory of resources that cost money or are Explore AWS leftovers,
# in every Region enabled for the account. Run in CloudShell as po-admin:
#   bash r1_inventory.sh R1_19_inventory-before.json
# It only calls describe/list/get operations. It changes nothing.
set -uo pipefail
out="${1:?usage: bash r1_inventory.sh <output.json>}"

# Run one read-only AWS CLI call; print its JSON, or {"error": "..."} if it failed.
q() {
  local res
  if res=$(aws "$@" --output json 2>&1); then
    [ -n "$res" ] && printf '%s' "$res" || printf '[]'
  else
    jq -n --arg e "$(printf '%s' "$res" | head -c 300)" '{error: $e}'
  fi
}

regions=$(aws ec2 describe-regions --query 'Regions[].RegionName' --output text)
tmp=$(mktemp)
for r in $regions; do
  echo "scanning $r" >&2
  jq -n --arg region "$r" \
    --argjson instances  "$(q ec2 describe-instances --region "$r" --filters Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,state:State.Name,launched:LaunchTime}')" \
    --argjson volumes    "$(q ec2 describe-volumes --region "$r" --query 'Volumes[].{id:VolumeId,size:Size,state:State}')" \
    --argjson snapshots  "$(q ec2 describe-snapshots --region "$r" --owner-ids self --query 'Snapshots[].{id:SnapshotId,size:VolumeSize}')" \
    --argjson key_pairs  "$(q ec2 describe-key-pairs --region "$r" --query 'KeyPairs[].{name:KeyName,id:KeyPairId}')" \
    --argjson security_groups "$(q ec2 describe-security-groups --region "$r" --query "SecurityGroups[?GroupName!='default'].{id:GroupId,name:GroupName,vpc:VpcId}")" \
    --argjson elastic_ips "$(q ec2 describe-addresses --region "$r" --query 'Addresses[].{ip:PublicIp,alloc:AllocationId}')" \
    --argjson nat_gateways "$(q ec2 describe-nat-gateways --region "$r" --filter Name=state,Values=pending,available --query 'NatGateways[].{id:NatGatewayId,state:State}')" \
    --argjson vpc_endpoints "$(q ec2 describe-vpc-endpoints --region "$r" --query 'VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}')" \
    --argjson non_default_vpcs "$(q ec2 describe-vpcs --region "$r" --filters Name=is-default,Values=false --query 'Vpcs[].{id:VpcId,cidr:CidrBlock}')" \
    --argjson load_balancers "$(q elbv2 describe-load-balancers --region "$r" --query 'LoadBalancers[].{name:LoadBalancerName,type:Type}')" \
    --argjson lambda_functions "$(q lambda list-functions --region "$r" --query 'Functions[].{name:FunctionName,runtime:Runtime}')" \
    --argjson rds_instances "$(q rds describe-db-instances --region "$r" --query 'DBInstances[].{id:DBInstanceIdentifier,class:DBInstanceClass,status:DBInstanceStatus}')" \
    --argjson rds_clusters "$(q rds describe-db-clusters --region "$r" --query 'DBClusters[].{id:DBClusterIdentifier,status:Status}')" \
    --argjson rds_snapshots "$(q rds describe-db-snapshots --region "$r" --query 'DBSnapshots[].{id:DBSnapshotIdentifier,type:SnapshotType}')" \
    --argjson rds_cluster_snapshots "$(q rds describe-db-cluster-snapshots --region "$r" --query 'DBClusterSnapshots[].{id:DBClusterSnapshotIdentifier,type:SnapshotType}')" \
    '{region: $region, instances: $instances, volumes: $volumes, snapshots: $snapshots, key_pairs: $key_pairs,
      security_groups: $security_groups, elastic_ips: $elastic_ips, nat_gateways: $nat_gateways,
      vpc_endpoints: $vpc_endpoints, non_default_vpcs: $non_default_vpcs, load_balancers: $load_balancers,
      lambda_functions: $lambda_functions, rds_instances: $rds_instances, rds_clusters: $rds_clusters,
      rds_snapshots: $rds_snapshots, rds_cluster_snapshots: $rds_cluster_snapshots}' >> "$tmp"
done

jq -s --arg account "$(aws sts get-caller-identity --query Account --output text)" \
      --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{account: $account, collected_utc: $at, regions_scanned: length,
    regions_with_findings: [ .[] | select([.[] | arrays | length] | add > 0) | .region ],
    regions_with_errors:   [ .[] | select([.[] | objects | has("error")] | any) | .region ],
    by_region: . }' "$tmp" > "$out"
rm -f "$tmp"
jq '{regions_scanned, regions_with_findings, regions_with_errors}' "$out"
