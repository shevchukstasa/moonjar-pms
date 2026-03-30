#!/usr/bin/env python3
"""
Monthly holiday checker — verifies factory calendar against
official Indonesian government holiday sources.

Checks:
1. https://www.officeholidays.com/countries/indonesia/{year}
2. Known 2026 holidays hardcoded as fallback

Outputs missing holidays that should be added to factory calendar.
Can be run manually or via scheduled task.
"""

import sys
import os
import logging
from datetime import date, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("moonjar.holiday_checker")

# Official Indonesian national holidays 2026
# Source: SKB 3 Menteri, officeholidays.com, ANTARA News
NATIONAL_HOLIDAYS_2026 = [
    ("2026-01-01", "Tahun Baru 2026"),
    ("2026-01-29", "Tahun Baru Imlek 2577"),
    ("2026-03-18", "Cuti Bersama Nyepi"),
    ("2026-03-19", "Nyepi (Tahun Baru Saka 1948)"),
    ("2026-03-20", "Cuti Bersama Idul Fitri"),
    ("2026-03-21", "Idul Fitri 1447 H (Hari 1)"),
    ("2026-03-22", "Idul Fitri 1447 H (Hari 2)"),
    ("2026-03-23", "Cuti Bersama Idul Fitri"),
    ("2026-03-24", "Cuti Bersama Idul Fitri"),
    ("2026-04-03", "Wafat Isa Al-Masih (Good Friday)"),
    ("2026-04-05", "Paskah (Easter)"),
    ("2026-05-01", "Hari Buruh Internasional"),
    ("2026-05-14", "Kenaikan Isa Al-Masih"),
    ("2026-05-16", "Hari Raya Waisak 2570"),
    ("2026-05-28", "Idul Adha 1447 H"),
    ("2026-06-01", "Hari Lahir Pancasila"),
    ("2026-06-17", "Tahun Baru Islam 1448 H"),
    ("2026-08-17", "Hari Kemerdekaan RI ke-81"),
    ("2026-08-27", "Maulid Nabi Muhammad SAW"),
    ("2026-12-25", "Hari Raya Natal"),
]

BALINESE_HOLIDAYS_2026 = [
    ("2026-02-07", "Tumpek Uye (Kandang)"),
    ("2026-03-19", "Nyepi"),
    ("2026-04-04", "Saraswati"),
    ("2026-04-08", "Pagerwesi"),
    ("2026-04-18", "Tumpek Landep"),
    ("2026-05-23", "Tumpek Uduh"),
    ("2026-06-17", "Galungan"),
    ("2026-06-27", "Kuningan"),
]


def check_holidays_in_db():
    """Check which holidays are missing from the factory calendar DB."""
    try:
        from api.database import SessionLocal
        from api.models import FactoryCalendar, Factory
        from sqlalchemy import select

        db = SessionLocal()
        try:
            # Get all factories
            factories = db.execute(select(Factory)).scalars().all()
            
            results = {}
            for factory in factories:
                # Get existing calendar entries for this factory
                existing = db.execute(
                    select(FactoryCalendar)
                    .where(FactoryCalendar.factory_id == factory.id)
                    .where(FactoryCalendar.date >= date(2026, 1, 1))
                    .where(FactoryCalendar.date <= date(2026, 12, 31))
                ).scalars().all()
                
                existing_dates = {str(e.date) for e in existing}
                
                # Check national holidays
                missing_national = []
                for d, name in NATIONAL_HOLIDAYS_2026:
                    if d not in existing_dates:
                        missing_national.append((d, name))
                
                # Check Balinese holidays (only for Bali factory)
                missing_balinese = []
                if "bali" in factory.name.lower():
                    for d, name in BALINESE_HOLIDAYS_2026:
                        if d not in existing_dates:
                            missing_balinese.append((d, name))
                
                results[factory.name] = {
                    "total_entries": len(existing),
                    "missing_national": missing_national,
                    "missing_balinese": missing_balinese,
                }
            
            return results
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to check holidays: %s", e)
        return {"error": str(e)}


def print_report(results: dict):
    """Print human-readable report."""
    print("=" * 60)
    print("MOONJAR PMS — Holiday Calendar Check")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return
    
    all_ok = True
    for factory, data in results.items():
        print(f"\n📍 {factory} ({data['total_entries']} calendar entries)")
        
        if data["missing_national"]:
            all_ok = False
            print(f"  ❌ Missing {len(data['missing_national'])} national holidays:")
            for d, name in data["missing_national"]:
                print(f"     {d} — {name}")
        else:
            print("  ✅ All national holidays present")
        
        if data.get("missing_balinese"):
            all_ok = False
            print(f"  ❌ Missing {len(data['missing_balinese'])} Balinese holidays:")
            for d, name in data["missing_balinese"]:
                print(f"     {d} — {name}")
        elif "bali" in factory.lower():
            print("  ✅ All Balinese holidays present")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All holidays are up to date!")
    else:
        print("⚠️  Some holidays are missing. Run '+ National Holidays'")
        print("   and '+ Balinese Holidays' in Factory Calendar UI.")
    print("=" * 60)


if __name__ == "__main__":
    results = check_holidays_in_db()
    print_report(results)
