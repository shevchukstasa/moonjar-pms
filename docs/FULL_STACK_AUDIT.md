# Full-Stack Architecture Audit

Generated: 2026-04-16 13:02

## Summary

| Layer | Count |
|-------|-------|
| Backend endpoints | 662 |
| Frontend API calls | 395 |
| Frontend pages | 54 |
| Frontend hooks | 35 |
| ORM models | 154 |
| Business services | 67 |
| Role guides | 19 |

## Issues Found

### A. Backend endpoints without frontend consumer (2)

| Method | Path | Router |
|--------|------|--------|
| GET | `/api/transcription` | transcription |
| GET | `/api/transcription/{log_id}` | transcription |

### B. Frontend API calls to non-existent backend (0)

*None — all frontend calls resolve to existing endpoints.*

### C. ORM models without API exposure (20)

| Model | Notes |
|-------|-------|
| `BufferStatus` | Not referenced in any router |
| `CompetitionEntry` | Not referenced in any router |
| `CompetitionTeam` | Not referenced in any router |
| `DailyChallenge` | Not referenced in any router |
| `DailyTaskDistribution` | Not referenced in any router |
| `EdgeHeightRule` | Not referenced in any router |
| `KilnActualLoad` | Not referenced in any router |
| `MasterAchievement` | Not referenced in any router |
| `OrderStageHistory` | Not referenced in any router |
| `PointTransaction` | Not referenced in any router |
| `PrizeRecommendation` | Not referenced in any router |
| `QualityAssignmentConfig` | Not referenced in any router |
| `RagEmbedding` | Not referenced in any router |
| `RecipeKilnConfig` | Not referenced in any router |
| `RecipeVerification` | Not referenced in any router |
| `ScheduleSlot` | Not referenced in any router |
| `StageReconciliationLog` | Not referenced in any router |
| `UserPoints` | Not referenced in any router |
| `UserSkill` | Not referenced in any router |
| `UserStreak` | Not referenced in any router |

### D. Documented endpoints missing from code (0)

*None — all documented endpoints exist in code.*

### E. Code endpoints missing from API docs (0)

*None — all code endpoints are documented.*

### F. Business logic docs referencing missing code (0)

*None — all doc references resolve to existing code.*

### G. Business services without doc coverage (0)

*None — all services are documented.*

### H. Guide coverage (19 guides)

| Guide | Role | Lang | API refs | Page refs |
|-------|------|------|----------|-----------|
| GUIDE_ADMIN_EN.md | ADMIN | EN | 0 | 0 |
| GUIDE_ADMIN_ID.md | ADMIN | ID | 0 | 0 |
| GUIDE_CEO_EN.md | CEO | EN | 0 | 0 |
| GUIDE_CEO_ID.md | CEO | ID | 0 | 0 |
| GUIDE_OWNER_EN.md | OWNER | EN | 1 | 0 |
| GUIDE_OWNER_ID.md | OWNER | ID | 1 | 0 |
| GUIDE_PM_EN.md | PM | EN | 0 | 0 |
| GUIDE_PM_ID.md | PM | ID | 0 | 0 |
| GUIDE_PRODUCTION_MANAGER.md | PRODUCTION_MANAGER | EN | 0 | 0 |
| GUIDE_PURCH_EN.md | PURCH | EN | 0 | 0 |
| GUIDE_PURCH_ID.md | PURCH | ID | 0 | 0 |
| GUIDE_QM_EN.md | QM | EN | 0 | 0 |
| GUIDE_QM_ID.md | QM | ID | 0 | 0 |
| GUIDE_QUALITY_MANAGER.md | QUALITY_MANAGER | EN | 16 | 0 |
| GUIDE_SORTER_PACKER.md | SORTER_PACKER | EN | 0 | 0 |
| GUIDE_SP_EN.md | SP | EN | 0 | 0 |
| GUIDE_SP_ID.md | SP | ID | 0 | 0 |
| GUIDE_WH_EN.md | WH | EN | 0 | 0 |
| GUIDE_WH_ID.md | WH | ID | 0 | 0 |

---
**Total issues: 22**
