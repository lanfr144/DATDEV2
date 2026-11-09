#!/usr/bin/env python3
"""
Book&Ride - Unit 04 - the four DORA metrics (DEVOP2 U04a §6), computed from the
REAL release history written by release.sh (docs/release_history.ndjson).

    python3 scripts/dora_metrics.py [history.ndjson]   -> table + docs/dora_report.md

How each event is read: after every action we know which versions receive user
traffic (the "live set"):
    bluegreen -> the active slot only   canary  -> active + canary slot
    rolling   -> both slots

    exposure   a version ENTERS the live set   = a change reaches users
    deployment a version becomes the ONLY one live, and is newer than the one
               it replaces                     = deployed to production
    failure    a version LEAVES the live set before ever being the only one
               (canary rolled back), or is replaced by an OLDER version
               (blue/green switched back)      = a change that needed remediation
    restore    the moment of that removal: users are back on a good version

Indicators:
    deployment frequency   deployments / observed period
    lead time for changes  first `deploy` of a version (image built and started on
                           the idle slot) -> that version is in production.
                           A real pipeline measures from the COMMIT: same idea.
    change failure rate    failed changes / changes exposed to users
    MTTR                   exposure of a failed change -> restore
"""
import json
import sys
from datetime import datetime
from pathlib import Path

UNIT = Path(__file__).resolve().parents[1]


def semver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def live(e: dict) -> set[str]:
    v = {"blue": e["blue"], "green": e["green"]}
    if e["mode"] == "canary":
        return {v[e["active"]], v[e["canary"]]}
    if e["mode"] == "rolling":
        return {e["blue"], e["green"]}
    return {v[e["active"]]}


def ts(e: dict) -> datetime:
    return datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))


def fmt(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    return f"{seconds:.0f} s" if seconds < 120 else f"{seconds / 60:.1f} min"


def analyse(events: list[dict]) -> dict:
    first_deploy, exposed_at, was_sole = {}, {}, set()
    deployments, lead_times, changes, failures, restore_times = [], [], 0, [], []
    prev_live, prod = set(), None
    for e in events:
        if e["event"] == "deploy":
            version = e["detail"].split(":")[1]
            first_deploy.setdefault(version, ts(e))
        now = live(e)
        for v in now - prev_live:                       # exposure
            exposed_at[v] = ts(e)
            was_sole.discard(v)
            # a change = a NEWER version than production reaches users (going back
            # to an older one is the remedy, not a change; the first state is neither)
            changes += prod is not None and semver(v) > semver(prod)
        for v in prev_live - now:                       # a version stops receiving traffic
            if v not in was_sole and prod and semver(v) > semver(prod):   # canary never promoted
                failures.append(v)
                restore_times.append((ts(e) - exposed_at[v]).total_seconds())
        if len(now) == 1:
            (v,) = now
            if v != prod:
                if prod is not None and semver(v) < semver(prod):   # back to an older version
                    failures.append(prod)
                    restore_times.append((ts(e) - exposed_at[prod]).total_seconds())
                elif prod is not None:                               # a real deployment
                    deployments.append(ts(e))
                    if v in first_deploy:
                        lead_times.append((ts(e) - first_deploy[v]).total_seconds())
                prod = v
            was_sole.add(v)
        prev_live = now
    period = (ts(events[-1]) - ts(events[0])).total_seconds() if len(events) > 1 else 0
    return {
        "period_s": period,
        "deployments": len(deployments),
        "per_hour": len(deployments) / (period / 3600) if period else None,
        "lead_time_s": sum(lead_times) / len(lead_times) if lead_times else None,
        "changes": changes,
        "failures": failures,
        "cfr": len(failures) / changes if changes else None,
        "mttr_s": sum(restore_times) / len(restore_times) if restore_times else None,
        "prod": prod,
    }


def report(m: dict) -> str:
    cfr = "n/a" if m["cfr"] is None else f"{m['cfr']:.0%} ({len(m['failures'])}/{m['changes']}: {', '.join(m['failures']) or '-'})"
    freq = "n/a" if m["per_hour"] is None else f"{m['deployments']} in {fmt(m['period_s'])} ({m['per_hour']:.0f}/hour)"
    return "\n".join([
        "| DORA indicator | Value | Read as |",
        "|---|---|---|",
        f"| Deployment frequency | {freq} | how often a new version reaches 100 % of users |",
        f"| Lead time for changes | {fmt(m['lead_time_s'])} | deploy on the idle slot -> in production (average) |",
        f"| Change failure rate | {cfr} | changes rolled back after reaching users |",
        f"| Mean time to recover | {fmt(m['mttr_s'])} | bad version exposed -> users back on a good one |",
        "",
        f"Version in production at the end: **{m['prod']}**.",
    ])


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else UNIT / "docs" / "release_history.ndjson"
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not events:
        print("empty history: run ./scripts/release_demo.sh first")
        return 1
    text = report(analyse(events))
    print(text)
    (UNIT / "docs" / "dora_report.md").write_text(
        "# DORA metrics of the release scenario\n\n"
        f"Computed by `scripts/dora_metrics.py` from `{path.name}` ({len(events)} events).\n\n"
        + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
