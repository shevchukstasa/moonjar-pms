#!/bin/bash
# Moonjar PMS — Проверка деплоя на продакшн
# Запуск: bash scripts/verify_deploy.sh
# После каждого push в main — ОБЯЗАТЕЛЬНО проверить!

set -e

BASE_URL="${1:-https://moonjar-pms-production.up.railway.app}"
API_URL="${BASE_URL}/api"
PASS=0
FAIL=0
WARN=0

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }

check_endpoint() {
  local url="$1"
  local expected="$2"
  local label="$3"

  code=$(curl -s -o /dev/null -w "%{http_code}" "${url}" 2>/dev/null)

  if [ "$code" = "$expected" ]; then
    green "  ✅ ${label}: ${code}"
    PASS=$((PASS + 1))
  elif [ "$code" = "000" ]; then
    red "  ❌ ${label}: СОЕДИНЕНИЕ НЕ УСТАНОВЛЕНО (сервер не запустился?)"
    FAIL=$((FAIL + 1))
  else
    red "  ❌ ${label}: ${code} (ожидалось ${expected})"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "═══════════════════════════════════════════════"
echo "  Moonjar PMS — Проверка продакшн деплоя"
echo "  API: ${API_URL}"
echo "  Время: $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════"
echo ""

# 1. Health check
echo "▸ Базовые проверки"
health=$(curl -s "${API_URL}/health" 2>/dev/null)
if echo "$health" | grep -q '"status":"ok"'; then
  green "  ✅ Health: OK"
  PASS=$((PASS + 1))
else
  red "  ❌ Health: СЕРВЕР НЕ ОТВЕЧАЕТ"
  red "     Ответ: ${health:-'нет ответа'}"
  FAIL=$((FAIL + 1))
  echo ""
  red "⛔ Сервер недоступен. Проверьте логи Railway!"
  exit 1
fi

# 2. Основные эндпоинты (401 = ОК, 500 = ПЛОХО)
echo ""
echo "▸ Основные эндпоинты (401 = нормально, 500 = ошибка)"
check_endpoint "${API_URL}/orders"      "401" "Orders"
check_endpoint "${API_URL}/materials"   "401" "Materials"
check_endpoint "${API_URL}/kilns"       "401" "Kilns"
check_endpoint "${API_URL}/factories"   "401" "Factories"
check_endpoint "${API_URL}/users/me"    "401" "Users"
check_endpoint "${API_URL}/positions"   "401" "Positions"

# 3. Новые эндпоинты (после последних изменений)
echo ""
echo "▸ Новые/изменённые эндпоинты"
check_endpoint "${API_URL}/materials/consumption-adjustments" "401" "Consumption Adjustments"
check_endpoint "${API_URL}/reference/shape-coefficients"      "401" "Shape Coefficients"
check_endpoint "${API_URL}/reference/temperature-groups"      "401" "Temperature Groups"

# 4. Backup & Security эндпоинты (401 = существует и защищён)
echo ""
echo "▸ Безопасность и бэкапы"
check_endpoint "${API_URL}/health/backup"     "401" "Backup Health (защищён)"
check_endpoint "${API_URL}/security/sessions" "401" "Security Sessions"
check_endpoint "${API_URL}/security/audit-log" "401" "Audit Log"

# 5. OpenAPI docs (на корне, без /api)
echo ""
echo "▸ Документация"
check_endpoint "${BASE_URL}/docs" "200" "Swagger UI (/docs)"

# Итог
echo ""
echo "═══════════════════════════════════════════════"
if [ $FAIL -eq 0 ] && [ $WARN -eq 0 ]; then
  green "  ✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ (${PASS}/${PASS})"
elif [ $FAIL -eq 0 ]; then
  yellow "  ⚠️  ПРОЙДЕНО С ПРЕДУПРЕЖДЕНИЯМИ: ${PASS} OK, ${WARN} warnings"
else
  red "  ❌ ОШИБКИ: ${FAIL} из $((PASS + FAIL + WARN)) (warnings: ${WARN})"
fi
echo "═══════════════════════════════════════════════"
echo ""

exit $FAIL
