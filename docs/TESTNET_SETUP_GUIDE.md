# AutoCoin Testnet 설정 가이드

## 📋 목차
1. [Binance Testnet API 키 생성](#binance-testnet-api-키-생성)
2. [Telegram Bot 설정](#telegram-bot-설정)
3. [환경 변수 설정](#환경-변수-설정)
4. [Testnet 배포](#testnet-배포)
5. [기능 테스트](#기능-테스트)
6. [문제 해결](#문제-해결)

---

## Binance Testnet API 키 생성

### 1. Testnet 계정 생성
1. **Binance Testnet 접속**: https://testnet.binance.vision/
2. **계정 생성** 또는 **GitHub로 로그인**
3. 로그인 후 대시보드 확인

### 2. API 키 생성
1. 우측 상단 **사용자 아이콘** 클릭
2. **API Management** 선택
3. **Create API** 버튼 클릭
4. API 키 이름 입력 (예: "AutoCoin-Test")
5. **Create** 클릭

### 3. API 키 권한 설정
- ✅ **Enable Reading** 체크
- ✅ **Enable Spot & Margin Trading** 체크
- ❌ **Enable Withdrawals** 체크 해제 (보안상)

### 4. API 키 정보 저장
```
API Key: 생성된 API 키 복사
Secret Key: 생성된 시크릿 키 복사 (한 번만 표시됨!)
```

⚠️ **중요**: Secret Key는 한 번만 표시되므로 반드시 안전한 곳에 저장하세요.

---

## Telegram Bot 설정

### 1. Bot 생성 (이미 있다면 건너뛰기)
1. Telegram에서 **@BotFather** 검색
2. `/newbot` 명령 입력
3. 봇 이름 입력 (예: "AutoCoin Test Bot")
4. 봇 사용자명 입력 (예: "autocoin_test_bot")
5. **Bot Token** 저장

### 2. Chat ID 확인
1. 생성한 봇과 대화 시작
2. `/start` 메시지 전송
3. 다음 URL 접속: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
4. 응답에서 `"chat":{"id":숫자}` 찾기
5. 해당 숫자가 **Chat ID**

---

## 환경 변수 설정

### 1. 환경 파일 복사
```bash
cp .env.testnet .env.testnet
```

### 2. API 키 입력
`.env.testnet` 파일을 편집하여 다음 값들을 입력:

```bash
# Exchange Configuration (Testnet)
BINANCE_API_KEY=여기에_실제_API_키_입력
BINANCE_API_SECRET=여기에_실제_시크릿_키_입력
BINANCE_TESTNET=true

# Telegram Configuration
TELEGRAM_BOT_TOKEN=여기에_봇_토큰_입력
TELEGRAM_CHAT_ID=여기에_채팅_ID_입력
```

### 3. 설정 확인
```bash
# API 키가 제대로 설정되었는지 확인
grep -E "BINANCE_API_KEY|TELEGRAM_BOT_TOKEN" .env.testnet
```

---

## Testnet 배포

### 1. 배포 스크립트 실행
```bash
./scripts/deploy_testnet.sh
```

### 2. 배포 과정 확인
스크립트는 다음 단계를 수행합니다:
1. ✅ 환경 설정 확인
2. 🧹 기존 컨테이너 정리
3. 🔨 Docker 이미지 빌드
4. 🚀 컨테이너 시작
5. ⏱️ 시작 대기
6. 🔍 상태 확인
7. 🔌 API 연결 테스트

### 3. 성공 확인
다음 메시지가 표시되면 성공:
```
✅ AutoCoin Testnet이 성공적으로 시작되었습니다!
✅ Binance Testnet API 연결 성공
```

---

## 기능 테스트

### 1. Telegram Bot 연결 테스트
```
/start
```
**예상 응답**: 환영 메시지와 사용 가능한 명령어 목록

### 2. 시스템 상태 확인
```
/status
```
**예상 응답**: 현재 봇 상태 및 실행 중인 전략

### 3. 잔고 확인
```
/balance
```
**예상 응답**: Testnet 계정의 USDT 잔고

### 4. 전략 목록 확인
```
/strategies
```
**예상 응답**: 사용 가능한 매매 전략 목록

### 5. 전략 추천 테스트
```
/recommend
```
**예상 응답**: 현재 시장 상황에 적합한 전략 추천

### 6. 전략 선택 테스트
```
/select breakout
```
**예상 응답**: 돌파매매 전략 선택 완료

### 7. 자동매매 시작 테스트 (신중하게!)
```
/run
```
**예상 응답**: 자동매매 시작 메시지

⚠️ **주의**: 이 명령은 실제로 거래를 시작합니다 (Testnet이지만).

### 8. 자동매매 중지
```
/stop
```
**예상 응답**: 자동매매 중지 메시지

---

## 로그 및 모니터링

### 1. 실시간 로그 확인
```bash
docker-compose -f docker-compose.testnet.yml logs -f
```

### 2. 특정 로그 필터링
```bash
# 에러 로그만
docker-compose -f docker-compose.testnet.yml logs | grep ERROR

# 거래 로그만
docker-compose -f docker-compose.testnet.yml logs | grep TRADE
```

### 3. 컨테이너 상태 확인
```bash
docker-compose -f docker-compose.testnet.yml ps
```

### 4. 리소스 사용량 확인
```bash
docker stats autocoin_testnet
```

---

## 문제 해결

### API 연결 오류
```
❌ API 연결 실패. API 키를 확인해주세요.
```

**해결 방법**:
1. `.env.testnet` 파일의 API 키 확인
2. Binance Testnet에서 API 키 상태 확인
3. API 키 권한 확인 (Reading, Trading 필요)

### Telegram Bot 응답 없음
**해결 방법**:
1. Bot Token 확인
2. Chat ID 확인
3. 봇이 차단되지 않았는지 확인

### 컨테이너 시작 실패
```bash
# 상세 로그 확인
docker-compose -f docker-compose.testnet.yml logs

# 컨테이너 재시작
docker-compose -f docker-compose.testnet.yml restart
```

### 메모리 부족
```bash
# 컨테이너 리소스 확인
docker stats autocoin_testnet

# 필요시 재시작
docker-compose -f docker-compose.testnet.yml restart
```

---

## 고급 테스트

### 1. 통합 테스트 실행
```bash
python scripts/test_integration.py
```

### 2. 헬스 체크
```bash
./scripts/health_check.sh
```

### 3. 백업 테스트
```bash
./scripts/backup.sh
```

### 4. 성능 테스트
- 여러 전략 동시 실행
- 장시간 운영 (24시간+)
- 높은 빈도 거래 테스트

---

## 정리 및 다음 단계

### Testnet 중지
```bash
docker-compose -f docker-compose.testnet.yml down
```

### 로그 및 데이터 백업
```bash
cp -r logs/ testnet_logs_backup/
cp -r data/ testnet_data_backup/
```

### Production 배포 준비
1. ✅ Testnet에서 최소 1주일 안정적 운영
2. ✅ 모든 기능 정상 작동 확인
3. ✅ 에러 처리 검증 완료
4. ✅ 성능 최적화 완료

### 다음 단계
Testnet 테스트가 성공적으로 완료되면:
1. Production API 키 생성
2. Production 환경 설정
3. `docker-compose.prod.yml`로 배포
4. 실제 운영 시작

---

## 📞 지원

문제 발생 시:
1. 로그 확인: `docker-compose -f docker-compose.testnet.yml logs`
2. 운영 매뉴얼 참조: `docs/OPERATIONS_MANUAL.md`
3. 긴급 상황: `./scripts/emergency_stop.sh`

---

**⚠️ 중요**: Testnet은 실제 돈을 사용하지 않지만, Production 배포 전 충분한 테스트가 필요합니다!