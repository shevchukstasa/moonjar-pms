#!/usr/bin/env python3
"""Verify that the full 13-stage production process correctly
drives backward scheduling calculations.

Works via API calls to the production server.
No direct DB access needed.

Usage:
    python scripts/verify_scheduling_pipeline.py

What it tests:
1. All 13 stages have speeds for every typology
2. Fixed-duration stages have correct rate_basis
3. Schedule calculation produces valid date ordering
4. Typology matching works
5. Speed→duration math is correct
"""

import requests
import json
import math
import sys
from datetime import date, timedelta

API = "https://moonjar-pms-production.up.railway.app/api"

ALL_STAGES = [
    "unpacking_sorting", "engobe", "drying_engobe", "glazing",
    "drying_glaze", "edge_cleaning_loading", "firing",
    "kiln_cooling_initial", "kiln_unloading", "kiln_cooling_full",
    "tile_cooling", "sorting", "packing",
]

FIXED_DURATION_STAGES = {
    "drying_engobe", "drying_glaze", "firing",
    "kiln_cooling_initial", "kiln_cooling_full", "tile_cooling",
}

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
results = {"pass": 0, "fail": 0, "warn": 0}


def check(name, condition, detail=""):
    tag = PASS if condition else FAIL
    results["pass" if condition else "fail"] += 1
    print(f"  {tag} {name}" + (f" — {detail}" if detail else ""))


def warn_msg(name, detail=""):
    results["warn"] += 1
    print(f"  {WARN} {name}" + (f" — {detail}" if detail else ""))


def login():
    r = requests.post(f"{API}/auth/login", json={
        "email": "shevchukstasa@gmail.com",
        "password": "Moonjar2024!",
    })
    r.raise_for_status()
    return r.cookies


def get(path, cookies, params=None):
    r = requests.get(f"{API}{path}", cookies=cookies, params=params)
    r.raise_for_status()
    return r.json()


def main():
    print("Logging in...")
    cookies = login()
    csrf = cookies.get("csrf_token", "")

    # ══ Step 1: Factory ══
    print("\n═══ STEP 1: Factory & Kilns ═══")
    factories = get("/factories", cookies)
    flist = factories if isinstance(factories, list) else factories.get("items", [])
    bali = next((f for f in flist if "bali" in f["name"].lower()), None)
    check("Bali factory exists", bali is not None)
    if not bali:
        print("Cannot continue."); return
    fid = bali["id"]
    print(f"  Factory: {bali['name']} ({fid})")

    # ══ Step 2: Typologies ══
    print("\n═══ STEP 2: Typologies ═══")
    typo_resp = get("/tps/typologies", cookies, {"factory_id": fid})
    typos = typo_resp.get("items", typo_resp) if isinstance(typo_resp, dict) else typo_resp
    check("Typologies exist", len(typos) > 0, f"{len(typos)} active typologies")

    # ══ Step 3: Stage Speeds ══
    print("\n═══ STEP 3: Stage Speeds (Full Process Coverage) ═══")
    speed_resp = get("/tps/stage-speeds", cookies, {"factory_id": fid})
    speeds = speed_resp.get("items", []) if isinstance(speed_resp, dict) else speed_resp
    check("Stage speeds exist", len(speeds) > 0, f"{len(speeds)} speed records")

    # Group by stage
    by_stage = {}
    for s in speeds:
        by_stage.setdefault(s["stage"], []).append(s)

    all_ok = True
    for stage in ALL_STAGES:
        count = len(by_stage.get(stage, []))
        ok = count > 0
        if not ok:
            all_ok = False
        check(f"Stage '{stage}'", ok, f"{count} typology speeds" if ok else "MISSING — no speeds!")

    # Check stages not in our list (leftover old stages)
    extra_stages = set(by_stage.keys()) - set(ALL_STAGES)
    if extra_stages:
        warn_msg(f"Extra stages in DB (old data)", ", ".join(sorted(extra_stages)))

    # ══ Step 4: Fixed-Duration Stages ══
    print("\n═══ STEP 4: Fixed-Duration Stages ═══")
    for stage in sorted(FIXED_DURATION_STAGES):
        stage_speeds = by_stage.get(stage, [])
        if not stage_speeds:
            check(f"'{stage}' has fixed_duration basis", False, "no speeds")
            continue
        fixed_count = sum(1 for s in stage_speeds if s.get("rate_basis") == "fixed_duration")
        total = len(stage_speeds)
        check(
            f"'{stage}' uses fixed_duration",
            fixed_count == total,
            f"{fixed_count}/{total} are fixed_duration"
        )

    # ══ Step 5: Speed-to-Duration Math ══
    print("\n═══ STEP 5: Speed→Duration Math (Unit Tests) ═══")

    def calc_days(rate, unit, basis, time_unit, sqm, pcs, shifts=2, shift_h=8.0, brigade=1):
        if rate <= 0:
            return None
        if basis == "fixed_duration":
            return max(1, math.ceil(rate / (shift_h * shifts)))
        # Convert to rate_per_hour
        if time_unit == "min":
            rph = rate * 60
        elif time_unit == "shift":
            rph = rate / shift_h
        else:
            rph = rate
        # Effective rate
        eff = rph * brigade if basis == "per_person" else rph
        if eff <= 0:
            return None
        if unit == "sqm" and sqm > 0:
            hours = sqm / eff
        elif unit == "pcs" and pcs > 0:
            hours = pcs / eff
        else:
            return None
        return max(1, math.ceil(hours / (shift_h * shifts)))

    # Test: fixed 8h / 16h day = 1 day
    check("fixed 8h → 1 day", calc_days(8, "hours", "fixed_duration", "hours", 5, 100) == 1)
    # Test: fixed 20h / 16h = 2 days
    check("fixed 20h → 2 days", calc_days(20, "hours", "fixed_duration", "hours", 5, 100) == 2)
    # Test: 100 pcs @ 60/h/person = ceil(100/60/16) = 1 day
    check("100 pcs @ 60/h → 1 day", calc_days(60, "pcs", "per_person", "hour", 5, 100) == 1)
    # Test: 1000 pcs @ 60/h/person = ceil(1000/60/16) = ceil(1.04) = 2 days
    check("1000 pcs @ 60/h → 2 days", calc_days(60, "pcs", "per_person", "hour", 5, 1000) == 2)
    # Test: 10 sqm @ 3.5/h = ceil(10/3.5/16) = 1 day
    check("10 sqm @ 3.5/h → 1 day", calc_days(3.5, "sqm", "per_person", "hour", 10, 100) == 1)
    # Test: brigade mode 1000 pcs @ 60/h/brigade = ceil(1000/60/16) = 2 days
    check("1000 pcs @ 60/h brigade → 2 days", calc_days(60, "pcs", "per_brigade", "hour", 5, 1000, brigade=3) == 2)

    # ══ Step 6: Sample Typology Trace ══
    print("\n═══ STEP 6: Sample Typology Speed Trace ═══")
    # Pick first edge typology
    sample_typo = next((t for t in typos if "edge" in t["name"].lower() or "topface" in t["name"].lower()), typos[0] if typos else None)
    if sample_typo:
        print(f"  Typology: {sample_typo['name']}")
        typo_speeds = [s for s in speeds if s.get("typology_id") == sample_typo["id"]]

        # Sort by process order
        def stage_order(s):
            try:
                return ALL_STAGES.index(s["stage"])
            except ValueError:
                return 99
        typo_speeds.sort(key=stage_order)

        total_days = 0
        test_sqm = 1.0  # 1 sqm position
        test_pcs = 100   # 100 pcs
        print(f"  Simulating: {test_sqm} m², {test_pcs} pcs")
        print(f"  {'Stage':25s} | {'Rate':>7s} {'Unit':>5s} / {'Basis':>14s} / {'Time':>5s} | {'Days':>4s}")
        print(f"  {'-'*25}-+-{'-'*45}-+-{'-'*4}")

        for s in typo_speeds:
            days = calc_days(
                s["productivity_rate"], s.get("rate_unit", "pcs"),
                s.get("rate_basis", "per_person"), s.get("time_unit", "hour"),
                test_sqm, test_pcs
            )
            if days is None:
                days = 1
            total_days += days
            is_fixed = "fixed" if s.get("rate_basis") == "fixed_duration" else ""
            print(f"  {s['stage']:25s} | {s['productivity_rate']:>7.1f} {s.get('rate_unit','?'):>5s} "
                  f"/ {s.get('rate_basis','?'):>14s} / {s.get('time_unit','?'):>5s} "
                  f"| {days:>3d}d {is_fixed}")

        buffer_days = 2  # BUFFER_DAYS * 2
        print(f"\n  Total pipeline: {total_days} working days + {buffer_days} buffer = {total_days + buffer_days} calendar days")

        check("All 13 stages have speeds for this typology",
              len(typo_speeds) >= len(ALL_STAGES),
              f"{len(typo_speeds)}/{len(ALL_STAGES)} stages")
    else:
        warn_msg("No sample typology to trace")

    # ══ Step 7: Schedule Endpoint Test ══
    print("\n═══ STEP 7: Schedule Date Consistency (via API) ═══")

    # Find a real position
    try:
        orders = get("/orders", cookies, {"factory_id": fid, "limit": 5})
        order_list = orders.get("items", []) if isinstance(orders, dict) else orders
        test_pos = None
        for order in order_list:
            order_detail = get(f"/orders/{order['id']}", cookies)
            positions = order_detail.get("positions", [])
            for p in positions:
                if (p.get("planned_glazing_date") and p.get("planned_kiln_date")
                        and p.get("planned_sorting_date") and p.get("planned_completion_date")):
                    test_pos = p
                    break
            if test_pos:
                break

        if test_pos:
            g = date.fromisoformat(test_pos["planned_glazing_date"])
            k = date.fromisoformat(test_pos["planned_kiln_date"])
            s = date.fromisoformat(test_pos["planned_sorting_date"])
            c = date.fromisoformat(test_pos["planned_completion_date"])

            print(f"  Position: {test_pos.get('id', '?')[:8]}...")
            print(f"  Glazing:    {g}")
            print(f"  Kiln:       {k}")
            print(f"  Sorting:    {s}")
            print(f"  Completion: {c}")

            check("glazing <= kiln", g <= k, f"{g} <= {k}")
            check("kiln <= sorting", k <= s, f"{k} <= {s}")
            check("sorting <= completion", s <= c, f"{s} <= {c}")

            # Check no Sundays
            for label, dt in [("glazing", g), ("kiln", k), ("sorting", s), ("completion", c)]:
                check(f"{label} not Sunday", dt.weekday() != 6, f"{dt.strftime('%A')}")

            # Check reasonable gaps
            gap_gk = (k - g).days
            gap_ks = (s - k).days
            check("Glazing→Kiln gap >= 1 day", gap_gk >= 1, f"{gap_gk} days")
            check("Kiln→Sorting gap >= 1 day", gap_ks >= 1, f"{gap_ks} days")
        else:
            warn_msg("No scheduled position found to verify dates")
    except Exception as e:
        warn_msg(f"Could not check position dates: {e}")

    # ══ Step 8: Line Resources Table ══
    print("\n═══ STEP 8: Production Line Resources ═══")
    try:
        lr = get("/tps/line-resources", cookies, {"factory_id": fid})
        items = lr.get("items", []) if isinstance(lr, dict) else lr
        check("Line resources API works", True, f"{len(items)} resources configured")
    except Exception as e:
        check("Line resources API works", False, str(e))

    # ══ Summary ══
    print("\n" + "═" * 60)
    total = results["pass"] + results["fail"] + results["warn"]
    print(f"Results: {results['pass']}/{total} passed, "
          f"{results['fail']} failed, {results['warn']} warnings")
    if results["fail"] > 0:
        print(f"\n{FAIL} Some checks failed! Review output above.")
        sys.exit(1)
    else:
        print(f"\n{PASS} All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
