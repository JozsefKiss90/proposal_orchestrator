"""The R14 weekly cost check (``tools/aws_cost_check.py``) against recorded AWS answers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import pytest

from tools import aws_cost_check as cc
from tools.collect_evidence_v2 import RunResult

ACCOUNT = "797661577394"
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
OPUS = "eu.anthropic.claude-opus-4-6-v1"
PAGE = "https://aws.amazon.com/ec2/pricing/on-demand/"


def price(usd: float, **extra: Any) -> dict[str, Any]:
    return {"usd": usd, "unit": "Hrs", "sku": "SKU", "source_url": PAGE, "date_read": "2026-11-13", **extra}


def prices_file(tmp: Path, **over: Any) -> Path:
    data: dict[str, Any] = {
        "region": "eu-north-1",
        "hours_per_month": {"value": 730, "source": "AWS pricing pages convert monthly prices at 730 hours"},
        "root_volume_gb": {"value": 8, "source": "evidence_v2/R11/R11_09_root-volume.json"},
        "interface_endpoints": {"value": 6, "source": "deploy/aws/templates/90-host.yaml"},
        "prices": {"host_hour": price(0.1), "gp3_gb_month": price(0.0876), "endpoint_hour": price(0.01)},
        "bedrock": {OPUS: {"input": price(5.0, per_tokens=1_000_000), "output": price(25.0, per_tokens=1_000_000)}},
    }
    data.update(over)
    path = tmp / "prices.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def budget_file(tmp: Path, **over: Any) -> Path:
    data = {"approved_huf": None, "approval_status": "pending ELTE approval", "huf_per_usd": None,
            "rate_source": None, "rate_date": None}
    data.update(over)
    path = tmp / "budget.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def trail(name: str, when: str, change_set: str = "", error: str = "", stack: str = "proposal-orchestrator-host") -> str:
    ev: dict[str, Any] = {"eventTime": when, "eventName": name, "requestParameters": {"stackName": stack}}
    if change_set:
        ev["requestParameters"]["changeSetName"] = change_set
    if error:
        ev["errorCode"] = error
    return json.dumps(ev)


class Fake:
    def __init__(self, **over: Callable[[Sequence[str]], RunResult]) -> None:
        self.calls: list[list[str]] = []
        self.over = over

    def __call__(self, argv: Sequence[str]) -> RunResult:
        self.calls.append(list(argv))
        key = f"{argv[1]} {argv[2]}"
        if key in self.over:
            return self.over[key](argv)
        if key == "sts get-caller-identity":
            return RunResult(0, json.dumps({"Account": ACCOUNT}), "")
        if key == "freetier get-account-plan-state":
            return RunResult(0, json.dumps({"accountPlanType": "FREE", "accountPlanStatus": "ACTIVE",
                                            "accountPlanRemainingCredits": {"amount": 197.5, "unit": "USD"},
                                            "accountPlanExpirationDate": "2027-04-19T00:00:00Z"}), "")
        if key == "budgets describe-budgets":
            return RunResult(0, json.dumps([{"name": "My Monthly Cost Budget", "limit": "10.0", "spend": "1.2"}]), "")
        if key == "ce get-cost-and-usage":
            amount = "-1.5" if "Credit" in argv[argv.index("--filter") + 1] else "1.5"
            return RunResult(0, json.dumps({"ResultsByTime": [{"Groups": [
                {"Keys": ["Amazon Virtual Private Cloud"], "Metrics": {"UnblendedCost": {"Amount": amount}}}]}]}), "")
        if key == "cloudwatch list-metrics":
            return RunResult(0, json.dumps({"Metrics": [{"Dimensions": [{"Name": "ModelId", "Value": OPUS}]}]}), "")
        if key == "cloudwatch get-metric-statistics":
            n = 1000 if "InputTokenCount" in argv else 10
            return RunResult(0, json.dumps({"Datapoints": [{"Sum": n}, {"Sum": n}]}), "")
        if key == "cloudtrail lookup-events":
            if "AttributeKey=EventName,AttributeValue=ExecuteChangeSet" in argv:
                events = [trail("ExecuteChangeSet", "2026-11-11T20:00:00Z", "r11-create-01"),
                          trail("ExecuteChangeSet", "2026-11-12T00:10:00Z", "r12b-create-01", error="ChangeSetNotFound"),
                          trail("ExecuteChangeSet", "2026-11-12T00:34:46Z", "r12b-create-02"),
                          trail("ExecuteChangeSet", "2026-11-12T01:00:00Z", "other", stack="some-other-stack")]
            else:
                events = [trail("DeleteStack", "2026-11-11T21:30:00Z"), trail("DeleteStack", "2026-11-12T00:45:00Z")]
            return RunResult(0, json.dumps(events), "")
        if key == "pricing get-products":
            return RunResult(0, json.dumps({"PriceList": [json.dumps({
                "product": {"sku": "S1", "attributes": {"usagetype": "EUN1-VpcEndpoint-Hours", "regionCode": "eu-north-1"}},
                "publicationDate": "2026-11-01T00:00:00Z",
                "terms": {"OnDemand": {"t": {"effectiveDate": "2026-11-01", "priceDimensions": {"d": {
                    "description": "per hour", "unit": "Hrs", "pricePerUnit": {"USD": "0.0110000000"}}}}}}})]}), "")
        return RunResult(255, "", f"An error occurred (Unexpected) {key}")


def run_report(tmp: Path, fake: Fake, **budget: Any) -> tuple[int, dict[str, Any], str]:
    out = tmp / "report"
    rc = cc.main(["report", "--profile", "po-r1", "--prices", str(prices_file(tmp)), "--budget",
                  str(budget_file(tmp, **budget)), "--out", str(out)], runner=fake, clock=lambda: NOW)
    if rc != 0:
        return rc, {}, ""
    return rc, json.loads((out / "report.json").read_text(encoding="utf-8")), (out / "report.md").read_text(encoding="utf-8")


def test_report_prices_the_running_and_stopped_hour(tmp_path: Path) -> None:
    rc, report, _ = run_report(tmp_path, Fake())
    assert rc == 0
    volume = 8 * 0.0876 / 730
    assert report["hourly"]["running_hour_usd"] == pytest.approx(0.1 + 6 * 0.01 + volume, abs=1e-6)
    assert report["hourly"]["stopped_hour_usd"] == pytest.approx(6 * 0.01 + volume, abs=1e-6)


def test_report_pairs_each_creation_with_its_delete_and_counts_tokens(tmp_path: Path) -> None:
    _, report, md = run_report(tmp_path, Fake())
    runs = report["creations"]
    assert [r["change_set"] for r in runs] == ["r11-create-01", "r12b-create-02"]  # failed and other stacks dropped
    assert runs[0]["hours"] == 1.5 and runs[0]["end_utc"] == "2026-11-11T21:30:00Z"
    assert runs[1]["tokens"][OPUS] == {"InputTokenCount": 2000, "OutputTokenCount": 20}
    assert runs[1]["token_cost_usd"][OPUS] == pytest.approx(2000 * 5 / 1e6 + 20 * 25 / 1e6)
    assert "r12b-create-02" in md and "| Change set |" in md


def test_report_reads_tokens_over_whole_five_minute_periods(tmp_path: Path) -> None:
    fake = Fake()
    run_report(tmp_path, fake)
    stats = [c for c in fake.calls if c[2] == "get-metric-statistics"]
    assert stats and all(c[c.index("--period") + 1] == "300" for c in stats)
    second = [c for c in stats if c[c.index("--start-time") + 1] == "2026-11-12T00:30:00Z"]
    assert second and second[0][second[0].index("--end-time") + 1] == "2026-11-12T00:50:00Z"


def test_every_call_names_the_profile_and_a_region(tmp_path: Path) -> None:
    fake = Fake()
    run_report(tmp_path, fake)
    for call in fake.calls:
        assert call[call.index("--profile") + 1] == "po-r1"
        expected = "us-east-1" if call[1] == "ce" else "eu-north-1"
        assert call[call.index("--region") + 1] == expected


def test_huf_amount_stays_pending_until_approved(tmp_path: Path) -> None:
    _, report, md = run_report(tmp_path, Fake())
    assert report["funding"]["approved_huf"] == "pending"
    assert "approved_usd" not in report["funding"]
    assert "Approved amount: pending HUF" in md


def test_approved_huf_is_converted_only_with_a_rate(tmp_path: Path) -> None:
    _, report, _ = run_report(tmp_path, Fake(), approved_huf=300000, huf_per_usd=375.0, rate_source="MNB",
                              rate_date="2026-11-20", approval_status="approved")
    assert report["funding"]["approved_usd"] == 800.0
    assert report["funding"]["rate"]["source"] == "MNB"


def test_cost_explorer_failure_is_reported_not_zero(tmp_path: Path) -> None:
    fake = Fake(**{"ce get-cost-and-usage": lambda a: RunResult(254, "", "An error occurred (DataUnavailableException)")})
    rc, report, md = run_report(tmp_path, fake)
    assert rc == 0
    assert report["month_to_date"]["usage"] == "not available: DataUnavailableException"
    assert "Usage: not available" in md


def test_report_refuses_another_account(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake = Fake(**{"sts get-caller-identity": lambda a: RunResult(0, json.dumps({"Account": "111122223333"}), "")})
    rc, _, _ = run_report(tmp_path, fake)
    assert rc == 2
    assert not (tmp_path / "report").exists()
    assert len(fake.calls) == 1


@pytest.mark.parametrize("field", ["source_url", "date_read", "usd"])
def test_report_refuses_a_price_without_page_date_or_amount(tmp_path: Path, field: str,
                                                             capsys: pytest.CaptureFixture[str]) -> None:
    bad = price(0.1)
    del bad[field]
    path = prices_file(tmp_path, prices={"host_hour": bad, "gp3_gb_month": price(0.08), "endpoint_hour": price(0.01)})
    fake = Fake()
    rc = cc.main(["report", "--profile", "po-r1", "--prices", str(path), "--budget", str(budget_file(tmp_path)),
                  "--out", str(tmp_path / "r")], runner=fake, clock=lambda: NOW)
    assert rc == 2
    assert fake.calls == []
    assert "refused" in capsys.readouterr().out


def test_report_never_overwrites(tmp_path: Path) -> None:
    (tmp_path / "report").mkdir()
    fake = Fake()
    rc = cc.main(["report", "--profile", "po-r1", "--prices", str(prices_file(tmp_path)), "--budget",
                  str(budget_file(tmp_path)), "--out", str(tmp_path / "report")], runner=fake, clock=lambda: NOW)
    assert rc == 2 and fake.calls == []


def test_prices_keeps_only_the_needed_fields(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake = Fake()
    out = tmp_path / "prices.json"
    rc = cc.main(["prices", "--profile", "po-r1", "--out", str(out)], runner=fake, clock=lambda: NOW)
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    dims = data["items"]["endpoint_hour"]["dimensions"]
    assert dims == [{"sku": "S1", "description": "per hour", "unit": "Hrs", "usd": "0.0110000000", "begin_range": None,
                     "effective_date": "2026-11-01", "publication_date": "2026-11-01T00:00:00Z",
                     "usagetype": "EUN1-VpcEndpoint-Hours", "regionCode": "eu-north-1", "model": None}]
    assert data["items"]["endpoint_gb"]["dimensions"] == []  # the usage type filter dropped the hour price
    for call in fake.calls:
        assert call[1:3] == ["pricing", "get-products"]
        assert call[call.index("--region") + 1] == "eu-central-1"
        assert "Type=TERM_MATCH,Field=regionCode,Value=eu-north-1" in call
    printed = capsys.readouterr().out
    assert "endpoint_hour: found 1" in printed and "endpoint_gb: not in price list" in printed


def test_prices_reports_a_refused_api_region(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake = Fake(**{"pricing get-products": lambda a: RunResult(254, "", "An error occurred (AccessDeniedException)")})
    rc = cc.main(["prices", "--profile", "po-r1", "--out", str(tmp_path / "p.json")], runner=fake, clock=lambda: NOW)
    assert rc == 0
    assert "host_hour: error AccessDeniedException" in capsys.readouterr().out


def test_budget_file_in_the_repository_holds_no_approved_amount() -> None:
    budget = json.loads((cc.REPO / "deploy" / "aws" / "pricing" / "budget.json").read_text(encoding="utf-8"))
    assert budget["approved_huf"] is None and budget["huf_per_usd"] is None


def test_price_file_in_the_repository_loads_and_prices_every_host_profile() -> None:
    path = cc.REPO / "deploy" / "aws" / "pricing" / "eu-north-1.json"
    prices = cc.load_prices(path)
    params = json.loads((cc.REPO / "deploy" / "aws" / "parameters" / "host.json").read_text(encoding="utf-8"))
    arns = next(p["ParameterValue"] for p in params if p["ParameterKey"] == "InferenceProfileArns").split(",")
    assert sorted(prices["bedrock"]) == sorted(arn.rsplit("/", 1)[1] for arn in arns)
    assert prices["interface_endpoints"]["value"] == 6 and prices["root_volume_gb"]["value"] == 8
    extract = json.loads((cc.REPO / "docs" / "infrastructure_security" / "evidence_v2" / "R14"
                          / "R14_04_agent-offer-extract.json").read_text(encoding="utf-8"))
    skus = {item["sku"] for item in extract["items"]}
    entries = list(prices["prices"].values()) + [s for pair in prices["bedrock"].values() for s in pair.values()]
    assert all(e["sku"] in skus for e in entries)
