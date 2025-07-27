#!/bin/bash

# AutoCoin Testnet 배포 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "========================================"
echo "    AutoCoin Testnet 배포 스크립트"
echo "========================================"
echo -e "${NC}"

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

# 1. 환경 확인
echo -e "\n${YELLOW}1. 환경 확인 중...${NC}"

# .env.testnet 파일 확인
if [ ! -f .env.testnet ]; then
    echo -e "${RED}❌ .env.testnet 파일이 없습니다.${NC}"
    echo "다음 명령으로 생성하세요:"
    echo "cp .env.testnet .env.testnet"
    echo "그리고 API 키를 입력하세요."
    exit 1
fi

# API 키 설정 확인
if grep -q "your_testnet_api_key_here" .env.testnet; then
    echo -e "${RED}❌ .env.testnet 파일에 실제 API 키를 입력해주세요.${NC}"
    echo "Binance Testnet에서 API 키를 생성하세요:"
    echo "https://testnet.binance.vision/"
    exit 1
fi

echo -e "${GREEN}✅ 환경 설정 확인 완료${NC}"

# 2. 기존 컨테이너 정리
echo -e "\n${YELLOW}2. 기존 컨테이너 정리 중...${NC}"
docker-compose -f docker-compose.testnet.yml down 2>/dev/null || true

# 3. Docker 이미지 빌드
echo -e "\n${YELLOW}3. Docker 이미지 빌드 중...${NC}"
docker-compose -f docker-compose.testnet.yml build

# 4. 컨테이너 시작
echo -e "\n${YELLOW}4. Testnet 컨테이너 시작 중...${NC}"
docker-compose -f docker-compose.testnet.yml up -d

# 5. 시작 대기
echo -e "\n${YELLOW}5. 컨테이너 시작 대기 중...${NC}"
echo -n "시작 중"
for i in {1..20}; do
    if docker ps | grep -q "autocoin_testnet.*Up"; then
        echo -e " ${GREEN}✅${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# 6. 상태 확인
echo -e "\n${YELLOW}6. 상태 확인 중...${NC}"
sleep 5

if docker ps | grep -q "autocoin_testnet.*Up"; then
    echo -e "${GREEN}✅ AutoCoin Testnet이 성공적으로 시작되었습니다!${NC}"
else
    echo -e "${RED}❌ 컨테이너 시작에 실패했습니다.${NC}"
    echo "로그를 확인해주세요:"
    docker-compose -f docker-compose.testnet.yml logs --tail=20
    exit 1
fi

# 7. 연결 테스트
echo -e "\n${YELLOW}7. API 연결 테스트 중...${NC}"
sleep 10

# API 연결 테스트
if docker exec autocoin_testnet python -c "
from src.exchange.binance_client import BinanceClient
from src.config import Config
import asyncio

async def test():
    config = Config()
    client = BinanceClient(config.binance_api_key, config.binance_api_secret, True)
    await client.initialize()
    await client.test_connection()
    print('✅ API 연결 성공')
    await client.close()

asyncio.run(test())
" 2>/dev/null; then
    echo -e "${GREEN}✅ Binance Testnet API 연결 성공${NC}"
else
    echo -e "${RED}❌ API 연결 실패. API 키를 확인해주세요.${NC}"
fi

# 8. 결과 출력
echo -e "\n${GREEN}========================================"
echo "✅ Testnet 배포 완료!"
echo "========================================"
echo -e "${NC}"

echo -e "\n📋 다음 단계:"
echo "1. Telegram 봇 테스트: /start 명령 전송"
echo "2. 상태 확인: /status"
echo "3. 전략 목록: /strategies"
echo "4. 로그 확인: docker-compose -f docker-compose.testnet.yml logs -f"

echo -e "\n🔧 유용한 명령어:"
echo "• 로그 보기: docker-compose -f docker-compose.testnet.yml logs -f"
echo "• 재시작: docker-compose -f docker-compose.testnet.yml restart"
echo "• 중지: docker-compose -f docker-compose.testnet.yml down"
echo "• 컨테이너 진입: docker exec -it autocoin_testnet bash"

echo -e "\n💰 Testnet 잔고 확인:"
echo "https://testnet.binance.vision/ 에서 잔고를 확인하세요."

echo -e "\n⚠️  주의사항:"
echo "• 이것은 Testnet입니다 - 실제 돈이 아닙니다"
echo "• 테스트 완료 후 Production 배포를 고려하세요"
echo "• 문제 발생 시 logs/autocoin.log를 확인하세요"