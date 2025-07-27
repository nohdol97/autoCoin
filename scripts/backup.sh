#!/bin/bash

# AutoCoin 백업 스크립트

set -e

echo "🗄️  AutoCoin 백업 시작..."

# 백업 디렉토리 설정
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="autocoin_backup_${TIMESTAMP}"

# 백업 디렉토리 생성
mkdir -p "${BACKUP_DIR}"

# 백업할 디렉토리들
DIRS_TO_BACKUP=(
    "data"
    "logs"
    "config"
)

# 백업할 파일들
FILES_TO_BACKUP=(
    ".env"
    "config.json"
)

# 임시 백업 디렉토리 생성
TEMP_BACKUP_DIR="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "${TEMP_BACKUP_DIR}"

# 디렉토리 백업
for dir in "${DIRS_TO_BACKUP[@]}"; do
    if [ -d "$dir" ]; then
        echo "📁 ${dir} 백업 중..."
        cp -r "$dir" "${TEMP_BACKUP_DIR}/"
    else
        echo "⚠️  ${dir} 디렉토리가 없습니다. 건너뜁니다."
    fi
done

# 파일 백업
for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$file" ]; then
        echo "📄 ${file} 백업 중..."
        cp "$file" "${TEMP_BACKUP_DIR}/"
    else
        echo "⚠️  ${file} 파일이 없습니다. 건너뜁니다."
    fi
done

# 압축
echo "🗜️  백업 파일 압축 중..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

echo "✅ 백업 완료: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# 오래된 백업 파일 삭제 (30일 이상)
echo "🧹 오래된 백업 파일 정리 중..."
find . -name "autocoin_backup_*.tar.gz" -mtime +30 -delete

echo "🎉 백업 작업이 완료되었습니다!"