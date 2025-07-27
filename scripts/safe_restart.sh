#!/bin/bash

# AutoCoin 안전 재시작 스크립트
# 긴급 정지 후 또는 정기 재시작 시 사용

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}"
echo "========================================="
echo "    AutoCoin 안전 재시작 스크립트"
echo "========================================="
echo -e "${NC}"

# 함수: 단계별 확인
check_step() {
    echo -n -e "${2}"
    if eval "$1"; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return 1
    fi
}

# 1. 시스템 상태 확인
echo -e "\n${YELLOW}1. 시스템 상태 확인${NC}"

check_step "[ -f '${PROJECT_ROOT}/.env' ]" "환경 설정 파일 확인..."
check_step "docker --version > /dev/null 2>&1" "Docker 설치 확인..."
check_step "docker-compose --version > /dev/null 2>&1" "Docker Compose 설치 확인..."

# 2. 기존 컨테이너 정리
echo -e "\n${YELLOW}2. 기존 컨테이너 정리${NC}"

if docker ps -a | grep -q autocoin; then
    echo "기존 컨테이너 발견. 정리 중..."
    docker-compose down || true
    sleep 2
fi

# 3. 설정 검증
echo -e "\n${YELLOW}3. 설정 검증${NC}"

# API 연결 테스트
echo -n "API 연결 테스트 중..."
python3 - <<EOF
import os
import sys
sys.path.append('${PROJECT_ROOT}')
from src.config import Config

try:
    config = Config()
    if not config.binance_api_key or not config.binance_api_secret:
        print("API 키가 설정되지 않았습니다.")
        sys.exit(1)
    print(" ✓")
except Exception as e:
    print(f" ✗ - {e}")
    sys.exit(1)
EOF

# 4. Testnet 모드 확인
echo -e "\n${YELLOW}4. 실행 모드 확인${NC}"

source "${PROJECT_ROOT}/.env"
if [ "$BINANCE_TESTNET" = "true" ]; then
    echo -e "${GREEN}Testnet 모드로 실행됩니다.${NC}"
    MODE="testnet"
else
    echo -e "${RED}⚠️  Production 모드로 실행됩니다!${NC}"
    echo -n "계속하시겠습니까? (yes/no): "
    read -r confirmation
    if [ "$confirmation" != "yes" ]; then
        echo "재시작이 취소되었습니다."
        exit 0
    fi
    MODE="production"
fi

# 5. 통합 테스트 실행
echo -e "\n${YELLOW}5. 시스템 통합 테스트${NC}"

echo "통합 테스트를 실행하시겠습니까? (권장) (yes/no): "
read -r run_test

if [ "$run_test" = "yes" ]; then
    cd "$PROJECT_ROOT"
    python scripts/test_integration.py || {
        echo -e "${RED}통합 테스트 실패. 문제를 해결한 후 다시 시도하세요.${NC}"
        exit 1
    }
fi

# 6. 백업 실행
echo -e "\n${YELLOW}6. 재시작 전 백업${NC}"

"${SCRIPT_DIR}/backup.sh" || echo -e "${YELLOW}백업 실패 - 계속 진행합니다.${NC}"

# 7. 컨테이너 시작
echo -e "\n${YELLOW}7. AutoCoin 시작${NC}"

cd "$PROJECT_ROOT"
if [ "$MODE" = "production" ]; then
    docker-compose -f docker-compose.prod.yml up -d
else
    docker-compose up -d
fi

# 8. 시작 확인
echo -e "\n${YELLOW}8. 시작 확인${NC}"

echo -n "컨테이너 시작 대기 중"
for i in {1..10}; do
    echo -n "."
    sleep 2
    if docker ps | grep -q "autocoin.*Up"; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
done

# 9. 헬스 체크
echo -e "\n${YELLOW}9. 헬스 체크${NC}"

sleep 5
"${SCRIPT_DIR}/health_check.sh" || echo -e "${YELLOW}헬스 체크 경고${NC}"

# 10. 최종 상태
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ AutoCoin이 성공적으로 시작되었습니다!${NC}"
echo -e "${GREEN}=========================================${NC}"

echo -e "\n유용한 명령어:"
echo "- 로그 확인: docker-compose logs -f"
echo "- 상태 확인: docker-compose ps"
echo "- 헬스 체크: ./scripts/health_check.sh"
echo "- 긴급 정지: ./scripts/emergency_stop.sh"

# Telegram 알림
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=✅ AutoCoin이 성공적으로 재시작되었습니다. (모드: $MODE)" > /dev/null
    fi
fi

exit 0