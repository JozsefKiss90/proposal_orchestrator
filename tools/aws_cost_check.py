"""The weekly AWS cost check (ticket R14).

    py -3.10 -m tools.aws_cost_check prices --profile po-r1 --api-region eu-central-1 --out <file>
    py -3.10 -m tools.aws_cost_check report --profile po-r1 --prices <file> --budget <file> --out <folder>

``prices`` asks the AWS Price List API for the unit prices R14 needs in ``eu-north-1`` and keeps, per
price, the SKU, description, unit, USD amount, effective date and the offer's publication date. Its
output is evidence; the agent turns it into ``deploy/aws/pricing/eu-north-1.json``, where every price
carries its public pricing page URL and the date read (step sheet ``evidence_v2/R14/STEPS.md``,
point 4).

``report`` writes ``report.json`` and ``report.md`` into a new folder: the credits left, month-to-date
spend by service (Cost Explorer; "not available" when it answers nothing), the 10 USD budget, the
approved HUF amount ("pending" until ELTE approves, point 6), the cost of one running and one stopped
hour of the host stack, and per host creation (``ExecuteChangeSet`` to ``DeleteStack`` in CloudTrail)
its hours, priced cost and Bedrock tokens per model from the ``AWS/Bedrock`` CloudWatch metrics
(invocation logging stays off, point 12). It refuses a price file whose prices do not each cite a
page and a date. It reads no secret, prompt or model output: metadata and numbers only.

All AWS calls go through one injected runner (the R12a collector's), always with ``--profile``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from tools.collect_evidence_v2 import RunResult, Runner, subprocess_runner

REPO = Path(__file__).resolve().parents[1]
HOST_JSON = REPO / "deploy" / "aws" / "parameters" / "host.json"
REGION = "eu-north-1"
STACK = "proposal-orchestrator-host"
CE_REGION = "us-east-1"  # Cost Explorer answers in us-east-1 only
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_AWS_ERROR = re.compile(r"\(([A-Za-z]+)\)")

# name, service code, TERM_MATCH filters, keep(attributes) -> bool
PRICE_ITEMS: list[tuple[str, str, dict[str, str], Callable[[dict[str, str]], bool]]] = [
    ("host_hour", "AmazonEC2", {"regionCode": REGION, "instanceType": "c7i-flex.large", "operatingSystem": "Linux",
                                "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used",
                                "licenseModel": "No License required"}, lambda a: True),
    ("gp3_gb_month", "AmazonEC2", {"regionCode": REGION, "volumeApiName": "gp3", "productFamily": "Storage"},
     lambda a: True),
    ("endpoint_hour", "AmazonVPC", {"regionCode": REGION}, lambda a: a.get("usagetype", "").endswith("VpcEndpoint-Hours")),
    ("endpoint_gb", "AmazonVPC", {"regionCode": REGION}, lambda a: a.get("usagetype", "").endswith("VpcEndpoint-Bytes")),
    ("kms", "awskms", {"regionCode": REGION}, lambda a: True),
    ("secrets_manager", "AWSSecretsManager", {"regionCode": REGION}, lambda a: True),
    ("cloudwatch_logs", "AmazonCloudWatch", {"regionCode": REGION},
     lambda a: any(a.get("usagetype", "").endswith(s) for s in ("DataProcessing-Bytes", "TimedStorage-ByteHrs"))),
    ("bedrock_claude", "AmazonBedrock", {"regionCode": REGION},
     lambda a: any("claude" in str(v).lower() for v in a.values())),
]
REQUIRED_PRICES = ("host_hour", "gp3_gb_month", "endpoint_hour")


class CostCheckRefused(Exception):
    """A refusal: the reason is printed and the exit code is 2."""


def _run(runner: Runner, profile: str, region: str, *args: str) -> RunResult:
    return runner(["aws", *args, "--region", region, "--profile", profile, "--output", "json"])


def _error(result: RunResult) -> str:
    match = _AWS_ERROR.search(result.stderr or "")
    return match.group(1) if match else f"exit {result.returncode}"


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# prices
# ---------------------------------------------------------------------------


def capture_prices(runner: Runner, profile: str, api_region: str, clock: Callable[[], datetime]) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for name, service, filters, keep in PRICE_ITEMS:
        argv = ["pricing", "get-products", "--service-code", service, "--format-version", "aws_v1", "--filters"]
        argv += [f"Type=TERM_MATCH,Field={k},Value={v}" for k, v in filters.items()]
        result = _run(runner, profile, api_region, *argv)
        entry: dict[str, Any] = {"service_code": service, "filters": filters, "dimensions": []}
        if result.returncode != 0:
            entry["error"] = _error(result)
            items[name] = entry
            continue
        for raw in json.loads(result.stdout or "{}").get("PriceList", []):
            product = json.loads(raw) if isinstance(raw, str) else raw
            attributes = product.get("product", {}).get("attributes", {})
            if not keep(attributes):
                continue
            for term in product.get("terms", {}).get("OnDemand", {}).values():
                for dim in term.get("priceDimensions", {}).values():
                    entry["dimensions"].append({
                        "sku": product.get("product", {}).get("sku"),
                        "description": dim.get("description"),
                        "unit": dim.get("unit"),
                        "usd": dim.get("pricePerUnit", {}).get("USD"),
                        "begin_range": dim.get("beginRange"),
                        "effective_date": term.get("effectiveDate"),
                        "publication_date": product.get("publicationDate"),
                        "usagetype": attributes.get("usagetype"),
                        "regionCode": attributes.get("regionCode"),
                        "model": attributes.get("model") or attributes.get("modelName"),
                    })
        items[name] = entry
    return {"captured_utc": _iso(clock()), "api_region": api_region, "region": REGION, "items": items}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def _check_price(where: str, price: Any) -> float:
    if not isinstance(price, dict):
        raise CostCheckRefused(f"refused: {where} is not a price entry")
    usd = price.get("usd")
    if not isinstance(usd, (int, float)) or isinstance(usd, bool) or usd < 0:
        raise CostCheckRefused(f"refused: {where} has no USD amount")
    if not str(price.get("source_url", "")).startswith("https://"):
        raise CostCheckRefused(f"refused: {where} cites no pricing page (source_url)")
    if not _DATE.match(str(price.get("date_read", ""))):
        raise CostCheckRefused(f"refused: {where} has no date_read (YYYY-MM-DD)")
    return float(usd)


def load_prices(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("region") != REGION:
        raise CostCheckRefused(f"refused: the price file is not for {REGION}")
    prices = data.get("prices", {})
    for name in REQUIRED_PRICES:
        if name not in prices:
            raise CostCheckRefused(f"refused: the price file has no {name}")
    for name, price in prices.items():
        _check_price(f"prices.{name}", price)
    for model, pair in data.get("bedrock", {}).items():
        for side in ("input", "output"):
            _check_price(f"bedrock.{model}.{side}", pair.get(side))
            if not isinstance(pair[side].get("per_tokens"), int) or pair[side]["per_tokens"] <= 0:
                raise CostCheckRefused(f"refused: bedrock.{model}.{side} has no per_tokens")
    for key in ("root_volume_gb", "interface_endpoints", "hours_per_month"):
        if not isinstance(data.get(key, {}).get("value"), (int, float)) or not data[key].get("source"):
            raise CostCheckRefused(f"refused: the price file has no {key} with its source")
    return data


def hourly_costs(prices: dict[str, Any]) -> dict[str, float]:
    p = prices["prices"]
    hours = prices["hours_per_month"]["value"]
    volume = prices["root_volume_gb"]["value"] * p["gp3_gb_month"]["usd"] / hours
    endpoints = prices["interface_endpoints"]["value"] * p["endpoint_hour"]["usd"]
    return {"running_hour_usd": round(p["host_hour"]["usd"] + endpoints + volume, 6),
            "stopped_hour_usd": round(endpoints + volume, 6),
            "host_hour_usd": p["host_hour"]["usd"], "endpoints_hour_usd": round(endpoints, 6),
            "root_volume_hour_usd": round(volume, 6)}


def creations(runner: Runner, profile: str, since: datetime, now: datetime) -> tuple[list[dict[str, Any]], Optional[str]]:
    events: list[tuple[datetime, str, str]] = []
    for name in ("ExecuteChangeSet", "DeleteStack"):
        result = _run(runner, profile, REGION, "cloudtrail", "lookup-events", "--lookup-attributes",
                      f"AttributeKey=EventName,AttributeValue={name}", "--start-time", _iso(since),
                      "--query", "Events[].CloudTrailEvent")
        if result.returncode != 0:
            return [], _error(result)
        for raw in json.loads(result.stdout or "[]") or []:
            ev = json.loads(raw)
            params = ev.get("requestParameters") or {}
            if ev.get("errorCode") or STACK not in str(params.get("stackName", "")):
                continue
            events.append((_parse_time(ev["eventTime"]), name, str(params.get("changeSetName", ""))))
    events.sort()
    out: list[dict[str, Any]] = []
    for i, (t, name, change_set) in enumerate(events):
        if name != "ExecuteChangeSet":
            continue
        end = next((u for u, n, _ in events[i + 1:] if n == "DeleteStack"), None)
        out.append({"change_set": change_set, "start_utc": _iso(t), "end_utc": _iso(end) if end else None,
                    "open": end is None, "hours": round(((end or now) - t).total_seconds() / 3600, 3)})
    return out, None


def _floor5(t: datetime) -> datetime:
    return t.replace(second=0, microsecond=0) - timedelta(minutes=t.minute % 5)


def tokens(runner: Runner, profile: str, start: datetime, end: datetime, models: list[str]) -> dict[str, Any]:
    lo, hi = _floor5(start), _floor5(end) + timedelta(minutes=5)
    out: dict[str, Any] = {}
    for model in models:
        row: dict[str, Any] = {}
        for metric in ("InputTokenCount", "OutputTokenCount"):
            result = _run(runner, profile, REGION, "cloudwatch", "get-metric-statistics", "--namespace", "AWS/Bedrock",
                          "--metric-name", metric, "--dimensions", f"Name=ModelId,Value={model}",
                          "--start-time", _iso(lo), "--end-time", _iso(hi), "--period", "300", "--statistics", "Sum")
            if result.returncode != 0:
                row[metric] = f"not available: {_error(result)}"
                continue
            points = json.loads(result.stdout or "{}").get("Datapoints", [])
            row[metric] = int(sum(p.get("Sum", 0) for p in points))
        out[model] = row
    return out


def token_cost(row: dict[str, Any], price: Optional[dict[str, Any]]) -> Optional[float]:
    if price is None or not all(isinstance(row.get(m), int) for m in ("InputTokenCount", "OutputTokenCount")):
        return None
    return round(row["InputTokenCount"] * price["input"]["usd"] / price["input"]["per_tokens"]
                 + row["OutputTokenCount"] * price["output"]["usd"] / price["output"]["per_tokens"], 6)


def build_report(runner: Runner, profile: str, prices: dict[str, Any], budget: dict[str, Any], account: str,
                 now: datetime, since: datetime) -> dict[str, Any]:
    ident = _run(runner, profile, REGION, "sts", "get-caller-identity")
    caller = json.loads(ident.stdout or "{}").get("Account") if ident.returncode == 0 else None
    if caller != account:
        raise CostCheckRefused("refused: the caller account is not ExpectedAccountId of host.json")
    report: dict[str, Any] = {"generated_utc": _iso(now), "account": account, "region": REGION}

    plan = _run(runner, profile, REGION, "freetier", "get-account-plan-state")
    if plan.returncode == 0:
        p = json.loads(plan.stdout)
        report["plan"] = {"type": p.get("accountPlanType"), "status": p.get("accountPlanStatus"),
                          "credits_remaining_usd": (p.get("accountPlanRemainingCredits") or {}).get("amount"),
                          "expires": p.get("accountPlanExpirationDate")}
    else:
        report["plan"] = f"not available: {_error(plan)}"

    budgets = _run(runner, profile, REGION, "budgets", "describe-budgets", "--account-id", account, "--query",
                   "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}")
    report["budgets"] = json.loads(budgets.stdout) if budgets.returncode == 0 else f"not available: {_error(budgets)}"

    month_start = now.strftime("%Y-%m-01")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    spend: dict[str, Any] = {"period": f"{month_start} to {now.strftime('%Y-%m-%d')}"}
    for record_type in ("Usage", "Credit"):
        result = _run(runner, profile, CE_REGION, "ce", "get-cost-and-usage", "--time-period",
                      f"Start={month_start},End={tomorrow}", "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
                      "--group-by", "Type=DIMENSION,Key=SERVICE", "--filter",
                      json.dumps({"Dimensions": {"Key": "RECORD_TYPE", "Values": [record_type]}}))
        if result.returncode != 0:
            spend[record_type.lower()] = f"not available: {_error(result)}"
            continue
        by_service: dict[str, float] = {}
        for period in json.loads(result.stdout).get("ResultsByTime", []):
            for group in period.get("Groups", []):
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                by_service[group["Keys"][0]] = round(by_service.get(group["Keys"][0], 0.0) + amount, 6)
        spend[record_type.lower()] = {"by_service_usd": by_service, "total_usd": round(sum(by_service.values()), 6)}
    report["month_to_date"] = spend

    approved = budget.get("approved_huf")
    rate = budget.get("huf_per_usd")
    funding: dict[str, Any] = {"approved_huf": approved if approved is not None else "pending",
                               "approval_status": budget.get("approval_status")}
    if approved is not None and rate:
        funding["approved_usd"] = round(approved / rate, 2)
        funding["rate"] = {"huf_per_usd": rate, "source": budget.get("rate_source"), "date": budget.get("rate_date")}
    elif approved is not None:
        funding["approved_usd"] = "no rate given"
    report["funding"] = funding

    costs = hourly_costs(prices)
    report["hourly"] = costs
    models_result = _run(runner, profile, REGION, "cloudwatch", "list-metrics", "--namespace", "AWS/Bedrock",
                         "--metric-name", "InputTokenCount")
    models: list[str] = []
    if models_result.returncode == 0:
        for metric in json.loads(models_result.stdout or "{}").get("Metrics", []):
            for dim in metric.get("Dimensions", []):
                if dim.get("Name") == "ModelId" and dim.get("Value") not in models:
                    models.append(dim["Value"])
    report["bedrock_models_seen"] = sorted(models)

    runs, error = creations(runner, profile, since, now)
    if error:
        report["creations"] = f"not available: {error}"
    else:
        for run in runs:
            end = _parse_time(run["end_utc"]) if run["end_utc"] else now
            run["stack_cost_usd_upper"] = round(run["hours"] * costs["running_hour_usd"], 4)
            run["tokens"] = tokens(runner, profile, _parse_time(run["start_utc"]), end, models)
            run["token_cost_usd"] = {m: token_cost(row, prices.get("bedrock", {}).get(m))
                                     for m, row in run["tokens"].items()}
        report["creations"] = runs
    report["creations_since_utc"] = _iso(since)

    report["prices"] = [{"name": n, **{k: v for k, v in p.items()}} for n, p in prices["prices"].items()]
    report["bedrock_prices"] = prices.get("bedrock", {})
    report["assumptions"] = {k: prices[k] for k in ("hours_per_month", "root_volume_gb", "interface_endpoints")}
    report["notes"] = [
        "stack_cost_usd_upper prices every hour of a creation as running; stopped hours cost less.",
        "Token counts come from the AWS/Bedrock CloudWatch metrics, summed over 5-minute periods that cover the creation.",
        "The monthly KMS key and secret charges are base costs, not per creation.",
    ]
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# AWS cost check, {report['generated_utc']}", "",
             f"Account `{report['account']}`, Region `{report['region']}`.", "", "## Credits and budget", ""]
    plan = report["plan"]
    if isinstance(plan, dict):
        lines.append(f"- Plan {plan['type']} {plan['status']}, credits remaining {plan['credits_remaining_usd']} USD, "
                     f"expires {plan['expires']}.")
    else:
        lines.append(f"- Plan: {plan}.")
    budgets = report["budgets"]
    for b in budgets if isinstance(budgets, list) else []:
        lines.append(f"- Budget `{b.get('name')}`: limit {b.get('limit')} USD, spend {b.get('spend')} USD.")
    if not isinstance(budgets, list):
        lines.append(f"- Budgets: {budgets}.")
    f = report["funding"]
    lines.append(f"- Approved amount: {f['approved_huf']} HUF ({f.get('approval_status') or 'no status'})"
                 + (f", {f['approved_usd']} USD" if "approved_usd" in f else "") + ".")
    lines += ["", f"## Month to date ({report['month_to_date']['period']})", ""]
    for kind in ("usage", "credit"):
        part = report["month_to_date"].get(kind)
        if isinstance(part, dict):
            lines.append(f"- {kind.title()}: {part['total_usd']} USD.")
            for service, amount in sorted(part["by_service_usd"].items()):
                lines.append(f"  - {service}: {amount}")
        else:
            lines.append(f"- {kind.title()}: {part}.")
    h = report["hourly"]
    lines += ["", "## Host stack per hour", "",
              f"- Running: {h['running_hour_usd']} USD (host {h['host_hour_usd']}, endpoints {h['endpoints_hour_usd']}, "
              f"root volume {h['root_volume_hour_usd']}).",
              f"- Stopped: {h['stopped_hour_usd']} USD (endpoints and root volume).", "",
              f"## Host creations since {report['creations_since_utc']}", ""]
    runs = report["creations"]
    if isinstance(runs, list):
        lines += ["| Change set | Start | End | Hours | Stack cost (upper), USD | Tokens in / out per model | Token cost, USD |",
                  "|---|---|---|---|---|---|---|"]
        for r in runs:
            tok = "; ".join(f"{m}: {v['InputTokenCount']} / {v['OutputTokenCount']}" for m, v in r["tokens"].items()) or "none"
            cost = "; ".join(f"{m}: {'unpriced' if c is None else c}" for m, c in r["token_cost_usd"].items()) or "none"
            lines.append(f"| `{r['change_set']}` | {r['start_utc']} | {r['end_utc'] or 'open'} | {r['hours']} | "
                         f"{r['stack_cost_usd_upper']} | {tok} | {cost} |")
    else:
        lines.append(f"Not available: {runs}.")
    lines += ["", "## Prices", "", "| Item | USD | Unit | Page | Read |", "|---|---|---|---|---|"]
    for p in report["prices"]:
        lines.append(f"| {p['name']} | {p['usd']} | {p.get('unit', '')} | {p['source_url']} | {p['date_read']} |")
    for model, pair in report["bedrock_prices"].items():
        for side in ("input", "output"):
            q = pair[side]
            lines.append(f"| {model} {side} | {q['usd']} | per {q['per_tokens']} tokens | {q['source_url']} | {q['date_read']} |")
    lines += ["", "## Notes", ""] + [f"- {n}" for n in report["notes"]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _account() -> str:
    params = json.loads(HOST_JSON.read_text(encoding="utf-8-sig"))
    return next(p["ParameterValue"] for p in params if p["ParameterKey"] == "ExpectedAccountId")


def main(argv: Optional[Sequence[str]] = None, *, runner: Optional[Runner] = None,
         clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> int:
    parser = argparse.ArgumentParser(prog="tools.aws_cost_check", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prices", help="capture unit prices from the Price List API")
    p.add_argument("--profile", required=True)
    p.add_argument("--api-region", default="eu-central-1", choices=("us-east-1", "eu-central-1", "ap-south-1"))
    p.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("report", help="write the weekly cost check")
    r.add_argument("--profile", required=True)
    r.add_argument("--prices", type=Path, required=True)
    r.add_argument("--budget", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--days", type=int, default=90, help="creations looked up this many days back (CloudTrail keeps 90)")
    args = parser.parse_args(argv)
    run = runner or subprocess_runner()
    try:
        if args.out.exists():
            raise CostCheckRefused(f"refused: {args.out} exists; a run never overwrites")
        if not args.out.parent.is_dir():
            raise CostCheckRefused(f"refused: {args.out.parent} is not a folder")
        if args.command == "prices":
            data = capture_prices(run, args.profile, args.api_region, clock)
            args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            for name, item in data["items"].items():
                state = f"error {item['error']}" if "error" in item else (
                    f"found {len(item['dimensions'])}" if item["dimensions"] else "not in price list")
                print(f"{name}: {state}")
            return 0
        prices = load_prices(args.prices)
        budget = json.loads(args.budget.read_text(encoding="utf-8-sig"))
        now = clock()
        report = build_report(run, args.profile, prices, budget, _account(), now, now - timedelta(days=args.days))
        args.out.mkdir()
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (args.out / "report.md").write_text(render_markdown(report), encoding="utf-8")
        h = report["hourly"]
        print(f"running hour {h['running_hour_usd']} USD; stopped hour {h['stopped_hour_usd']} USD")
        runs = report["creations"]
        print(f"creations: {len(runs) if isinstance(runs, list) else runs}")
        print(f"written: {args.out}")
        return 0
    except CostCheckRefused as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
