#!/bin/bash

# AutoCoin 헬스 체크 스크립트

echo "🏥 AutoCoin 헬스 체크..."

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Docker 컨테이너 상태 확인
echo -e "\n1. Docker 컨테이너 상태:"
if docker-compose ps | grep -q "autocoin.*Up"; then
    echo -e "${GREEN}✅ 컨테이너 실행 중${NC}"
else
    echo -e "${RED}❌ 컨테이너가 실행되고 있지 않습니다${NC}"
    exit 1
fi

# 2. 컨테이너 헬스 상태 확인
echo -e "\n2. 컨테이너 헬스 체크:"
HEALTH_STATUS=$(docker inspect autocoin --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ 헬스 체크 정상${NC}"
elif [ "$HEALTH_STATUS" = "none" ]; then
    echo -e "${YELLOW}⚠️  헬스 체크가 설정되지 않음${NC}"
else
    echo -e "${RED}❌ 헬스 체크 실패: $HEALTH_STATUS${NC}"
fi

# 3. 로그 확인 (최근 에러)
echo -e "\n3. 최근 에러 로그:"
ERROR_COUNT=$(docker-compose logs --tail=100 | grep -i "error" | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ 최근 에러 없음${NC}"
else
    echo -e "${YELLOW}⚠️  최근 에러 $ERROR_COUNT 건 발견${NC}"
    echo "최근 에러 내용:"
    docker-compose logs --tail=100 | grep -i "error" | tail -5
fi

# 4. 리소스 사용량
echo -e "\n4. 리소스 사용량:"
docker stats --no-stream autocoin

# 5. 디스크 사용량
echo -e "\n5. 디스크 사용량:"
echo "로그 디렉토리: $(du -sh logs 2>/dev/null || echo "N/A")"
echo "데이터 디렉토리: $(du -sh data 2>/dev/null || echo "N/A")"

# 6. 프로세스 상태
echo -e "\n6. 프로세스 상태:"
docker-compose exec -T autocoin ps aux | grep python || echo "프로세스 정보를 가져올 수 없습니다"

echo -e "\n📊 헬스 체크 완료"