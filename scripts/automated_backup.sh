#!/bin/bash

# AutoCoin 자동 백업 스크립트
# cron으로 일일 실행 권장

set -e

# 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${PROJECT_ROOT}/logs/backup.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)

# 백업 설정
RETENTION_DAYS=30
S3_BUCKET="autocoin-backups"  # S3 사용 시
REMOTE_BACKUP=false  # true로 설정하면 S3에 백업

# 로그 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 에러 핸들러
error_handler() {
    log "ERROR: 백업 실패 - $1"
    
    # Telegram 알림 (설정되어 있는 경우)
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        source "${PROJECT_ROOT}/.env"
        if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
            curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
                -d "chat_id=${TELEGRAM_CHAT_ID}" \
                -d "text=⚠️ AutoCoin 백업 실패: $1" > /dev/null
        fi
    fi
    
    exit 1
}

# 트랩 설정
trap 'error_handler "예상치 못한 오류 발생"' ERR

# 시작
log "=== AutoCoin 백업 시작 ==="

# 디렉토리 생성
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# 백업 이름
BACKUP_NAME="autocoin_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "$BACKUP_PATH"

# 1. 데이터베이스/상태 파일 백업
log "상태 파일 백업 중..."
if [ -d "${PROJECT_ROOT}/data" ]; then
    cp -r "${PROJECT_ROOT}/data" "${BACKUP_PATH}/" || error_handler "데이터 백업 실패"
fi

# 2. 설정 파일 백업
log "설정 파일 백업 중..."
if [ -d "${PROJECT_ROOT}/config" ]; then
    # 민감한 정보 제외하고 백업
    mkdir -p "${BACKUP_PATH}/config"
    find "${PROJECT_ROOT}/config" -name "*.json" -o -name "*.yml" | while read file; do
        cp "$file" "${BACKUP_PATH}/config/" 2>/dev/null || true
    done
fi

# 3. 최근 로그 백업 (최근 24시간)
log "최근 로그 백업 중..."
mkdir -p "${BACKUP_PATH}/logs"
find "${PROJECT_ROOT}/logs" -name "*.log" -mtime -1 -exec cp {} "${BACKUP_PATH}/logs/" \; 2>/dev/null || true

# 4. 거래 내역 백업
if [ -f "${PROJECT_ROOT}/data/trades.json" ]; then
    log "거래 내역 백업 중..."
    cp "${PROJECT_ROOT}/data/trades.json" "${BACKUP_PATH}/trades_${DATE}.json"
fi

# 5. 메트릭 데이터 백업
if [ -d "${PROJECT_ROOT}/data/metrics" ]; then
    log "메트릭 데이터 백업 중..."
    cp -r "${PROJECT_ROOT}/data/metrics" "${BACKUP_PATH}/"
fi

# 백업 정보 파일 생성
cat > "${BACKUP_PATH}/backup_info.txt" <<EOF
Backup Information
==================
Date: $(date)
Version: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
Branch: $(git branch --show-current 2>/dev/null || echo "unknown")
Environment: ${ENV:-development}

Files Included:
- Data files
- Configuration files (without secrets)
- Recent logs (24h)
- Trade history
- Metrics data
EOF

# 압축
log "백업 파일 압축 중..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME" || error_handler "압축 실패"
rm -rf "$BACKUP_NAME"

# 백업 파일 크기 확인
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
log "백업 완료: ${BACKUP_NAME}.tar.gz (크기: ${BACKUP_SIZE})"

# 원격 백업 (S3)
if [ "$REMOTE_BACKUP" = true ]; then
    log "S3에 백업 업로드 중..."
    if command -v aws &> /dev/null; then
        aws s3 cp "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" "s3://${S3_BUCKET}/daily/${DATE}/" || log "WARNING: S3 업로드 실패"
    else
        log "WARNING: AWS CLI가 설치되지 않아 S3 백업을 건너뜁니다"
    fi
fi

# 오래된 백업 삭제
log "오래된 백업 파일 정리 중..."
find "$BACKUP_DIR" -name "autocoin_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
DELETED_COUNT=$(find "$BACKUP_DIR" -name "autocoin_backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)
if [ $DELETED_COUNT -gt 0 ]; then
    log "${DELETED_COUNT}개의 오래된 백업 파일을 삭제했습니다"
fi

# 백업 검증
log "백업 파일 검증 중..."
tar -tzf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" > /dev/null || error_handler "백업 파일 검증 실패"

# 디스크 사용량 확인
DISK_USAGE=$(df -h "$BACKUP_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    log "WARNING: 백업 디스크 사용량이 ${DISK_USAGE}%입니다. 정리가 필요합니다."
fi

# 성공 알림
log "=== 백업 완료 ==="

# Telegram 알림 (선택사항)
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=✅ AutoCoin 일일 백업 완료 (${BACKUP_SIZE})" > /dev/null
    fi
fi

exit 0