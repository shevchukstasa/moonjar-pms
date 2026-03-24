# Indonesia Payroll Rules — Moonjar PMS

> Based on PP 35/2021, UU Cipta Kerja, and current BPJS regulations (2025-2026)

---

## 1. Hourly Rate

```
Hourly Rate = Monthly Salary / 173
```

The divisor 173 is the legal standard (PP 35/2021).
Used for overtime calculations and partial month proration.

---

## 2. Overtime (Lembur) — PP 35/2021

### Weekday Overtime (after 8h/day or 40h/week):
| Hour | Multiplier |
|------|-----------|
| 1st hour | **1.5x** hourly rate |
| 2nd+ hour | **2x** hourly rate |

**Max:** 3 hours/day, 14 hours/week

### Rest Day / Holiday Overtime (5-day work week):
| Hour | Multiplier |
|------|-----------|
| 1st-8th hour | **2x** hourly rate |
| 9th hour | **3x** hourly rate |
| 10th+ hour | **4x** hourly rate |

### Rest Day / Holiday Overtime (6-day work week):
| Hour | Multiplier |
|------|-----------|
| 1st-7th hour | **2x** hourly rate |
| 8th hour | **3x** hourly rate |
| 9th+ hour | **4x** hourly rate |

### Hourly Rate for Overtime:
- If salary = base + fixed allowance only: `1/173 x 100% monthly salary`
- If salary = base + fixed + non-fixed: `1/173 x 75% monthly salary`

---

## 3. BPJS Contributions

### BPJS Kesehatan (Health Insurance — JKN):
| | Rate | Cap |
|--|------|-----|
| Employer | **4%** | Max IDR 480,000/month |
| Employee | **1%** | Max IDR 120,000/month |
| Wage base cap | | IDR 12,000,000/month |

### BPJS Ketenagakerjaan (Employment):

| Program | Employer | Employee | Cap |
|---------|----------|----------|-----|
| **JKK** (Work Accident) | 0.24%-1.74%* | 0% | No cap |
| **JKM** (Life Insurance) | 0.30% | 0% | No cap |
| **JHT** (Old Age Savings) | 3.70% | 2.00% | No cap |
| **JP** (Pension) | 2.00% | 1.00% | IDR 10,547,400/month |

*JKK rate by risk level:
- Very low risk: 0.24% (office work)
- Low risk: 0.54% (retail, hospitality)
- Medium risk: 0.89% (light manufacturing)
- High risk: 1.27% (heavy manufacturing)
- Very high risk: 1.74% (mining, construction)

**For Moonjar (ceramic/stone manufacturing): Medium risk = 0.89%**

### Total BPJS Summary:
| | Employer pays | Employee pays |
|--|--------------|---------------|
| JKN | 4.00% | 1.00% |
| JKK | 0.89% | 0% |
| JKM | 0.30% | 0% |
| JHT | 3.70% | 2.00% |
| JP | 2.00% | 1.00% |
| **TOTAL** | **10.89%** | **4.00%** |

---

## 4. THR (Tunjangan Hari Raya — Religious Holiday Bonus)

- **Mandatory** for all employees
- Paid **at least 7 days before** the major religious holiday
- **Amount:**
  - Worked >= 12 months: **1 full month salary** (base + fixed allowances)
  - Worked < 12 months: **prorated** = months_worked / 12 x monthly salary
- THR is **NOT subject to BPJS** but IS subject to **PPh 21**

---

## 5. Annual Leave

- **12 working days** per year (after 12 months of continuous employment)
- Unused leave may be carried over (max varies by company policy)
- Leave pay = regular salary (no deduction)

---

## 6. PPh 21 (Income Tax)

### Progressive Tax Brackets:
| Taxable Income (annual) | Rate |
|------------------------|------|
| Up to IDR 60,000,000 | **5%** |
| IDR 60M - 250M | **15%** |
| IDR 250M - 500M | **25%** |
| IDR 500M - 5B | **30%** |
| Above IDR 5B | **35%** |

### PTKP (Non-Taxable Income):
| Status | Annual PTKP |
|--------|------------|
| TK/0 (single, no dependents) | IDR 54,000,000 |
| TK/1 or K/0 | IDR 58,500,000 |
| TK/2 or K/1 | IDR 63,000,000 |
| TK/3 or K/2 | IDR 67,500,000 |
| K/3 (married + 3 dependents) | IDR 72,000,000 |

### Monthly Tax Calculation:
- Jan-Nov: Use TER (effective rate) tables
- December: Reconcile using annual progressive rates

---

## 7. Proration (Partial Month)

```
Partial salary = (Working days attended / Total working days in month) x Monthly salary
```

Working days = per factory calendar (excluding Sundays and holidays)

---

## 8. Payroll Calculation Formula

### Gross Salary:
```
Gross = Base Salary
      + Allowance (bike + housing + food + BPJS employee + other)
      + Overtime Pay
      + THR (if applicable month)
```

### Deductions:
```
Deductions = BPJS Employee (JKN 1% + JHT 2% + JP 1%)
           + PPh 21
           + Absence deductions (if applicable)
```

### Net Salary (Take Home Pay):
```
THP = Gross - Deductions
```

### Employer Cost (Total Cost to Company):
```
TCC = Gross + BPJS Employer (JKN 4% + JKK 0.89% + JKM 0.30% + JHT 3.70% + JP 2%)
```

---

## Sources

- [PP 35/2021 — Overtime regulations](https://www.reqruitasia.com/compensation-and-benefits-of-indonesian-employees-overtime-wage-calculation-in-indonesia-upah-lembur)
- [BPJS Ketenagakerjaan rates](https://www.aseanbriefing.com/doing-business-guide/indonesia/human-resources-and-payroll/social-insurance)
- [BPJS Kesehatan contribution rates 2025](https://www.bfi.co.id/en/blog/iuran-bpjs-kesehatan)
- [PPh 21 tax brackets](https://procapita.co.id/our-insights/indonesia-income-tax-a-quick-summary-of-the-local-rules/)
- [Pension insurance cap increase 2025](https://eosglobalexpansion.com/indonesia-pension-insurance-contributions/)
- [Mekari — Payroll and Employment Laws](https://mekari.com/en/blog/payroll-and-employment-laws-indonesia/)
- [InCorp — Indonesia Payroll Calculation](https://indonesia.incorp.asia/blogs/indonesia-payroll-calculation)
