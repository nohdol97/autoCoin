#!/bin/bash

# AutoCoin 배포 스크립트

set -e  # 오류 발생 시 스크립트 중단

echo "🚀 AutoCoin 배포 시작..."

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수: 성공 메시지
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 함수: 오류 메시지
error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 함수: 경고 메시지
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. 환경 확인
echo "1. 환경 확인 중..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    error "Docker가 설치되어 있지 않습니다. Docker를 먼저 설치해주세요."
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose가 설치되어 있지 않습니다. Docker Compose를 먼저 설치해주세요."
fi

# .env 파일 확인
if [ ! -f .env ]; then
    error ".env 파일이 없습니다. .env.example을 참고하여 .env 파일을 생성해주세요."
fi

success "환경 확인 완료"

# 2. 필수 디렉토리 생성
echo -e "\n2. 필수 디렉토리 생성 중..."
mkdir -p logs data config
success "디렉토리 생성 완료"

# 3. Docker 이미지 빌드
echo -e "\n3. Docker 이미지 빌드 중..."
docker-compose build --no-cache || error "Docker 이미지 빌드 실패"
success "Docker 이미지 빌드 완료"

# 4. 기존 컨테이너 정리
echo -e "\n4. 기존 컨테이너 정리 중..."
docker-compose down || warning "기존 컨테이너가 없습니다"
success "기존 컨테이너 정리 완료"

# 5. 컨테이너 시작
echo -e "\n5. 컨테이너 시작 중..."
docker-compose up -d || error "컨테이너 시작 실패"
success "컨테이너 시작 완료"

# 6. 상태 확인
echo -e "\n6. 컨테이너 상태 확인 중..."
sleep 5  # 컨테이너가 완전히 시작될 때까지 대기

if docker-compose ps | grep -q "Up"; then
    success "AutoCoin이 성공적으로 시작되었습니다!"
    echo -e "\n컨테이너 상태:"
    docker-compose ps
    echo -e "\n로그 확인: docker-compose logs -f"
    echo -e "중지: docker-compose down"
else
    error "컨테이너 시작에 실패했습니다. 로그를 확인해주세요: docker-compose logs"
fi