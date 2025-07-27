# AutoCoin 운영 매뉴얼

## 목차
1. [시스템 개요](#시스템-개요)
2. [일일 운영 절차](#일일-운영-절차)
3. [주간 운영 절차](#주간-운영-절차)
4. [월간 운영 절차](#월간-운영-절차)
5. [모니터링 가이드](#모니터링-가이드)
6. [문제 해결 가이드](#문제-해결-가이드)
7. [긴급 상황 대응](#긴급-상황-대응)
8. [성능 최적화](#성능-최적화)

---

## 시스템 개요

### 핵심 구성요소
- **Trading Engine**: 자동매매 실행
- **Telegram Bot**: 사용자 인터페이스
- **Exchange Client**: Binance API 연동
- **Monitoring System**: 상태 감시 및 알림

### 운영 환경
- **Production**: 실제 거래 환경
- **Testnet**: 테스트 환경
- **Docker**: 컨테이너 기반 배포

---

## 일일 운영 절차

### 오전 체크리스트 (09:00)

1. **시스템 상태 확인**
   ```bash
   ./scripts/health_check.sh
   ```

2. **전날 거래 내역 검토**
   ```bash
   docker exec autocoin_prod python -m src.reports.daily_summary
   ```

3. **에러 로그 확인**
   ```bash
   tail -n 100 logs/autocoin.log | grep ERROR
   ```

4. **잔고 확인**
   - Telegram에서 `/balance` 명령 실행
   - 예상 잔고와 실제 잔고 비교

5. **실행 중인 전략 확인**
   - Telegram에서 `/status` 명령 실행

### 오후 체크리스트 (18:00)

1. **포지션 확인**
   - Telegram에서 `/position` 명령 실행
   - 오픈 포지션의 손익 확인

2. **메트릭 확인**
   ```bash
   docker exec autocoin_prod python -c "from src.monitoring.metrics_collector import MetricsCollector; import asyncio; mc = MetricsCollector(); print(asyncio.run(mc.collect_metrics()))"
   ```

3. **디스크 사용량 확인**
   ```bash
   df -h | grep -E "logs|data|backups"
   ```

### 야간 점검 (22:00)

1. **백업 상태 확인**
   ```bash
   ls -lh backups/ | tail -5
   ```

2. **다음날 전략 검토**
   - 시장 상황 분석
   - 필요시 전략 변경 계획

---

## 주간 운영 절차

### 월요일
- 주간 성과 리포트 검토
- 전략 파라미터 조정 검토
- 시스템 업데이트 확인

### 수요일
- 백업 파일 무결성 검증
  ```bash
  ./scripts/verify_backups.sh
  ```
- 로그 파일 정리

### 금요일
- 주말 운영 계획 수립
- 긴급 연락처 확인
- 모니터링 알림 설정 점검

### 작업 스크립트
```bash
# 주간 성과 분석
docker exec autocoin_prod python -m src.analysis.weekly_performance

# 전략 백테스트
docker exec autocoin_prod python -m src.backtest.run_backtest --strategy all --days 30

# 시스템 리소스 분석
docker stats --no-stream autocoin_prod
```

---

## 월간 운영 절차

### 첫째 주
1. **전체 시스템 백업**
   ```bash
   ./scripts/full_system_backup.sh
   ```

2. **보안 점검**
   - API 키 로테이션 검토
   - 접근 로그 분석
   - 의심스러운 활동 확인

### 둘째 주
1. **성능 분석**
   - 거래 실행 속도 분석
   - API 응답 시간 측정
   - 리소스 사용 패턴 분석

2. **전략 최적화**
   - 월간 수익률 분석
   - 전략별 성과 비교
   - 파라미터 최적화

### 셋째 주
1. **시스템 업데이트**
   - 의존성 패키지 업데이트
   - Docker 이미지 업데이트
   - 보안 패치 적용

### 넷째 주
1. **재해 복구 훈련**
   - 백업 복원 테스트
   - 페일오버 시나리오 테스트
   - 비상 연락망 점검

---

## 모니터링 가이드

### 실시간 모니터링

1. **로그 모니터링**
   ```bash
   tail -f logs/autocoin.log
   ```

2. **Docker 상태**
   ```bash
   docker-compose ps
   watch docker stats autocoin_prod
   ```

3. **네트워크 모니터링**
   ```bash
   netstat -an | grep 443  # Binance API 연결
   ```

### Grafana 대시보드

1. **접속**
   - URL: http://localhost:3000
   - ID/PW: admin/admin

2. **주요 패널**
   - Trading Performance
   - System Resources
   - API Response Time
   - Error Rate

### 알림 설정

1. **Telegram 알림**
   - 포지션 오픈/클로즈
   - 에러 발생
   - 일일 리포트

2. **이메일 알림**
   - 시스템 다운
   - 백업 실패
   - 디스크 용량 부족

---

## 문제 해결 가이드

### 일반적인 문제

#### 1. API 연결 오류
```bash
# 연결 상태 확인
docker exec autocoin_prod python -c "from src.exchange.binance_client import BinanceClient; import asyncio; client = BinanceClient(); asyncio.run(client.test_connection())"

# 해결책
- API 키 확인
- 네트워크 연결 확인
- Binance 서버 상태 확인
```

#### 2. 메모리 부족
```bash
# 메모리 사용량 확인
docker stats --no-stream

# 해결책
- 컨테이너 재시작: docker-compose restart
- 로그 파일 정리
- 메모리 할당 증가
```

#### 3. 거래 실행 실패
```bash
# 최근 거래 로그 확인
grep "ORDER" logs/autocoin.log | tail -20

# 해결책
- 잔고 확인
- 주문 크기 확인
- API 권한 확인
```

### 디버깅 도구

```bash
# 실시간 로그 필터링
tail -f logs/autocoin.log | grep -E "ERROR|WARNING"

# 특정 시간대 로그 추출
grep "2024-01-15 14:" logs/autocoin.log > debug_1415.log

# 프로세스 상태 확인
docker exec autocoin_prod ps aux
```

---

## 긴급 상황 대응

### 긴급 정지 절차

1. **즉시 정지**
   ```bash
   docker-compose stop autocoin_prod
   ```

2. **포지션 확인**
   - Binance 웹/앱에서 직접 확인
   - 필요시 수동으로 포지션 청산

3. **원인 분석**
   ```bash
   # 최근 에러 로그
   tail -n 1000 logs/autocoin.log | grep -A 5 -B 5 ERROR
   
   # 시스템 상태
   docker-compose logs --tail=100
   ```

### 복구 절차

1. **백업에서 복원**
   ```bash
   ./scripts/restore_from_backup.sh [backup_file]
   ```

2. **설정 확인**
   ```bash
   # 환경 변수 확인
   docker-compose config
   
   # API 연결 테스트
   ./scripts/test_integration.py
   ```

3. **단계적 재시작**
   ```bash
   # Testnet에서 먼저 테스트
   ENV=testnet docker-compose up -d
   
   # 정상 작동 확인 후 Production 시작
   docker-compose up -d
   ```

### 비상 연락처

- **시스템 관리자**: [연락처]
- **Binance Support**: [지원 URL]
- **클라우드 제공자**: [지원 연락처]

---

## 성능 최적화

### 정기 점검 항목

1. **데이터베이스 최적화**
   ```bash
   # 오래된 거래 데이터 아카이브
   ./scripts/archive_old_trades.sh
   ```

2. **로그 로테이션**
   ```bash
   # logrotate 설정 확인
   cat /etc/logrotate.d/autocoin
   ```

3. **Docker 정리**
   ```bash
   # 미사용 이미지/컨테이너 제거
   docker system prune -a
   ```

### 성능 튜닝

1. **API Rate Limit 최적화**
   - 현재 사용량 모니터링
   - 버퍼 여유분 조정
   - 요청 배치 처리

2. **메모리 사용 최적화**
   - 캐시 크기 조정
   - 가비지 컬렉션 주기 조정
   - 메모리 누수 확인

3. **네트워크 최적화**
   - Keep-alive 연결 사용
   - 압축 활성화
   - CDN 활용 (가능한 경우)

---

## 부록

### 유용한 명령어 모음

```bash
# 시스템 상태 한눈에 보기
alias autocoin-status='docker-compose ps && df -h | grep -E "logs|data" && tail -5 logs/autocoin.log'

# 빠른 재시작
alias autocoin-restart='docker-compose restart && sleep 5 && docker-compose logs --tail=20'

# 일일 리포트
alias autocoin-report='docker exec autocoin_prod python -m src.reports.generate_report'
```

### 체크리스트 템플릿

```markdown
## 일일 점검 체크리스트 - [날짜]

- [ ] 시스템 헬스체크 완료
- [ ] 에러 로그 확인 (이상 없음)
- [ ] 포지션 상태 확인
- [ ] 잔고 일치 확인
- [ ] 백업 정상 수행
- [ ] 디스크 사용률 확인 (<80%)
- [ ] 특이사항: 

담당자: 
```

---

마지막 업데이트: 2024-01-15