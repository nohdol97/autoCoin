#!/bin/bash

# AutoCoin 긴급 정지 스크립트
# 이 스크립트는 긴급 상황에서 시스템을 안전하게 중지합니다

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/logs/emergency_stop.log"

# 로그 함수
log() {
    echo -e "${1}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ${1}" >> "$LOG_FILE"
}

# 헤더
echo -e "${RED}"
echo "========================================="
echo "    AutoCoin 긴급 정지 스크립트"
echo "========================================="
echo -e "${NC}"

# 확인 요청
echo -e "${YELLOW}⚠️  경고: 이 스크립트는 모든 거래를 즉시 중단합니다.${NC}"
echo -n "계속하시겠습니까? (yes/no): "
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    echo "긴급 정지가 취소되었습니다."
    exit 0
fi

log "${RED}=== 긴급 정지 시작 ===${NC}"

# 1. Trading Engine 즉시 중지
log "${YELLOW}1. Trading Engine 중지 중...${NC}"
docker exec autocoin_prod pkill -f "python main.py" 2>/dev/null || true
sleep 2

# 2. 현재 포지션 정보 저장
log "${YELLOW}2. 현재 포지션 정보 저장 중...${NC}"
POSITION_BACKUP="${PROJECT_ROOT}/emergency_backup_$(date +%Y%m%d_%H%M%S).json"
docker exec autocoin_prod python -c "
import json
from src.exchange.binance_client import BinanceClient
from src.config import Config
import asyncio

async def save_positions():
    config = Config()
    client = BinanceClient(config.binance_api_key, config.binance_api_secret, config.binance_testnet)
    await client.initialize()
    
    # 포지션 정보 가져오기
    positions = await client.get_positions()
    balance = await client.get_balance()
    
    # 저장
    data = {
        'timestamp': '$(date -Iseconds)',
        'positions': positions,
        'balance': balance,
        'reason': 'emergency_stop'
    }
    
    with open('/app/data/emergency_state.json', 'w') as f:
        json.dump(data, f, indent=2)
        
    print(json.dumps(data, indent=2))
    
    await client.close()

asyncio.run(save_positions())
" > "$POSITION_BACKUP" 2>/dev/null || log "${RED}포지션 정보 저장 실패${NC}"

# 3. Docker 컨테이너 중지
log "${YELLOW}3. Docker 컨테이너 중지 중...${NC}"
cd "$PROJECT_ROOT"
docker-compose stop autocoin_prod || docker stop autocoin_prod

# 4. 프로세스 확인
log "${YELLOW}4. 프로세스 상태 확인 중...${NC}"
if docker ps | grep -q autocoin_prod; then
    log "${RED}경고: 컨테이너가 여전히 실행 중입니다. 강제 종료 시도...${NC}"
    docker kill autocoin_prod || true
fi

# 5. 긴급 알림 발송
log "${YELLOW}5. 긴급 알림 발송 중...${NC}"
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
        MESSAGE="🚨 긴급 정지 실행됨

시간: $(date)
이유: 수동 긴급 정지
상태: 모든 거래 중단됨

포지션 백업: $POSITION_BACKUP

즉시 확인이 필요합니다!"

        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${MESSAGE}" > /dev/null || log "${RED}Telegram 알림 실패${NC}"
    fi
fi

# 6. 상태 요약
log "${GREEN}=== 긴급 정지 완료 ===${NC}"
echo -e "\n${GREEN}✅ 긴급 정지가 완료되었습니다.${NC}"
echo -e "\n다음 단계:"
echo "1. 포지션 확인: Binance 웹사이트/앱에서 직접 확인"
echo "2. 백업 파일 확인: $POSITION_BACKUP"
echo "3. 로그 분석: tail -n 100 $LOG_FILE"
echo "4. 원인 조사 후 재시작"

# 7. 체크리스트 생성
cat > "${PROJECT_ROOT}/emergency_checklist.txt" <<EOF
긴급 정지 후 체크리스트
========================
생성 시간: $(date)

[ ] Binance에서 열린 포지션 확인
[ ] 필요시 수동으로 포지션 청산
[ ] 에러 로그 분석 완료
[ ] 원인 파악 완료
[ ] 수정 사항 적용 완료
[ ] Testnet에서 테스트 완료
[ ] 재시작 준비 완료

재시작 명령:
cd $PROJECT_ROOT
./scripts/safe_restart.sh
EOF

echo -e "\n체크리스트가 생성되었습니다: ${PROJECT_ROOT}/emergency_checklist.txt"

exit 0