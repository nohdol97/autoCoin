# 🚀 AutoCoin Testnet 배포 가이드

## 빠른 시작 (Quick Start)

### 1단계: Binance Testnet API 키 생성
1. **https://testnet.binance.vision/** 접속
2. GitHub 계정으로 로그인
3. 우측 상단 사용자 아이콘 → **API Management**
4. **Create API** 클릭
5. 이름 입력 (예: "AutoCoin-Test")
6. **Enable Reading** ✅ **Enable Spot & Margin Trading** ✅ 체크
7. **API Key**와 **Secret Key** 복사하여 안전하게 저장

### 2단계: Telegram Bot 설정 (기존 봇 사용 가능)
1. Telegram에서 **@BotFather** 검색
2. `/newbot` → 봇 이름 입력 → Bot Token 저장
3. 봇과 대화 시작 후 `/start` 전송
4. **https://api.telegram.org/bot<BOT_TOKEN>/getUpdates** 접속
5. `"chat":{"id":숫자}` 에서 Chat ID 확인

### 3단계: 환경 변수 설정
```bash
# 환경 파일 편집
nano .env.testnet
```

다음 값들을 실제 값으로 변경:
```bash
BINANCE_API_KEY=실제_API_키_입력
BINANCE_API_SECRET=실제_시크릿_키_입력
TELEGRAM_BOT_TOKEN=실제_봇_토큰_입력
TELEGRAM_CHAT_ID=실제_채팅_ID_입력
```

### 4단계: Testnet 배포
```bash
./scripts/deploy_testnet.sh
```

### 5단계: 테스트
Telegram에서 봇에게 다음 명령어 전송:
```
/start
/status
/balance
/strategies
```

---

## 📋 상세 가이드

### 🔧 배포 전 준비사항

#### 시스템 요구사항
- Docker 및 Docker Compose 설치
- 최소 1GB RAM
- 10GB 여유 디스크 공간
- 안정적인 인터넷 연결

#### 필수 계정
- Binance Testnet 계정
- Telegram 계정 (봇 생성용)

---

## 🚀 배포 과정

### 자동 배포 (권장)
```bash
# 실행 권한 확인
chmod +x scripts/deploy_testnet.sh

# 배포 실행
./scripts/deploy_testnet.sh
```

### 수동 배포
```bash
# 1. 환경 파일 확인
cat .env.testnet

# 2. 기존 컨테이너 정리
docker-compose -f docker-compose.testnet.yml down

# 3. 이미지 빌드
docker-compose -f docker-compose.testnet.yml build

# 4. 컨테이너 시작
docker-compose -f docker-compose.testnet.yml up -d

# 5. 로그 확인
docker-compose -f docker-compose.testnet.yml logs -f
```

---

## 🧪 기능 테스트 체크리스트

### ✅ 기본 연결 테스트
- [ ] `/start` - 봇 시작 메시지 확인
- [ ] `/help` - 도움말 표시
- [ ] `/status` - 시스템 상태 확인

### ✅ API 연결 테스트
- [ ] `/balance` - Testnet 잔고 표시
- [ ] API 에러 없이 응답 확인

### ✅ 전략 시스템 테스트
- [ ] `/strategies` - 전략 목록 표시
- [ ] `/recommend` - 전략 추천 기능
- [ ] `/select breakout` - 전략 선택

### ✅ 거래 시스템 테스트 (신중하게!)
- [ ] `/run` - 자동매매 시작
- [ ] `/stop` - 자동매매 중지
- [ ] `/position` - 포지션 확인

### ✅ 모니터링 테스트
- [ ] `/report` - 일일 리포트
- [ ] 에러 알림 작동 확인
- [ ] 로그 정상 기록 확인

---

## 📊 모니터링

### 실시간 로그 모니터링
```bash
# 전체 로그
docker-compose -f docker-compose.testnet.yml logs -f

# 에러만 필터링
docker-compose -f docker-compose.testnet.yml logs | grep ERROR

# 거래 로그만
docker-compose -f docker-compose.testnet.yml logs | grep TRADE
```

### 시스템 상태 확인
```bash
# 컨테이너 상태
docker-compose -f docker-compose.testnet.yml ps

# 리소스 사용량
docker stats autocoin_testnet

# 헬스 체크
./scripts/health_check.sh
```

---

## 🎯 테스트 시나리오

### 시나리오 1: 기본 기능 테스트 (30분)
1. 봇 시작 및 상태 확인
2. 잔고 조회
3. 전략 목록 확인
4. 전략 추천 테스트

### 시나리오 2: 전략 시뮬레이션 (2시간)
1. 돌파매매 전략 선택
2. 자동매매 시작
3. 포지션 모니터링
4. 자동매매 중지

### 시나리오 3: 장시간 운영 테스트 (24시간)
1. 자동매매 24시간 연속 실행
2. 에러 발생 여부 확인
3. 메모리 누수 확인
4. 성능 지표 수집

### 시나리오 4: 스트레스 테스트 (1주일)
1. 여러 전략 번갈아 실행
2. 네트워크 장애 시뮬레이션
3. API 한도 테스트
4. 긴급 정지/재시작 테스트

---

## 🚨 문제 해결

### 일반적인 문제들

#### 1. API 연결 실패
```
❌ API 연결 실패. API 키를 확인해주세요.
```
**해결책:**
- API 키와 시크릿 키 재확인
- Testnet 환경인지 확인
- API 권한 확인 (Reading, Trading 필요)

#### 2. Telegram Bot 무응답
**해결책:**
```bash
# 봇 토큰 확인
grep TELEGRAM_BOT_TOKEN .env.testnet

# 채팅 ID 확인
curl https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

#### 3. 컨테이너 시작 실패
```bash
# 상세 에러 확인
docker-compose -f docker-compose.testnet.yml logs

# 포트 충돌 확인
lsof -i :8081

# 강제 재시작
docker-compose -f docker-compose.testnet.yml down
docker-compose -f docker-compose.testnet.yml up -d --force-recreate
```

#### 4. 메모리 부족
```bash
# 메모리 사용량 확인
docker stats autocoin_testnet

# 컨테이너 재시작
docker-compose -f docker-compose.testnet.yml restart
```

### 긴급 상황 대응
```bash
# 즉시 중지
docker-compose -f docker-compose.testnet.yml down

# 긴급 정지 스크립트
./scripts/emergency_stop.sh

# 로그 확인
tail -n 100 logs/autocoin.log
```

---

## 📈 성공 지표

### 기술적 지표
- [ ] API 연결 성공률 99% 이상
- [ ] 메모리 사용량 1GB 이하 유지
- [ ] 응답 시간 5초 이하
- [ ] 24시간 무중단 운영

### 기능적 지표
- [ ] 모든 Telegram 명령어 정상 작동
- [ ] 전략 전환 정상 작동
- [ ] 에러 발생 시 자동 복구
- [ ] 알림 시스템 정상 작동

---

## 🔄 다음 단계

### Testnet 테스트 완료 후
1. **1주일 안정성 테스트 완료**
2. **모든 기능 검증 완료**
3. **성능 최적화 완료**
4. **Production 배포 준비**

### Production 전환 체크리스트
- [ ] Testnet에서 최소 1주일 안정적 운영
- [ ] 모든 전략 수익성 확인
- [ ] 에러 처리 검증 완료
- [ ] 백업/복구 절차 테스트 완료
- [ ] Production API 키 준비
- [ ] 실 거래 전 최종 검토

---

## 📞 지원 및 문의

### 문서 참조
- **상세 설정 가이드**: `docs/TESTNET_SETUP_GUIDE.md`
- **운영 매뉴얼**: `docs/OPERATIONS_MANUAL.md`
- **문제 해결**: 각 문서의 troubleshooting 섹션

### 로그 및 디버깅
```bash
# 실시간 로그
docker-compose -f docker-compose.testnet.yml logs -f

# 에러 로그만
docker-compose -f docker-compose.testnet.yml logs | grep -i error

# 컨테이너 상태
docker-compose -f docker-compose.testnet.yml ps
```

---

**⚠️ 중요한 알림**
- Testnet은 실제 돈을 사용하지 않습니다
- 충분한 테스트 후 Production 전환하세요
- 문제 발생 시 즉시 중지하고 로그를 확인하세요
- 실제 거래 전 모든 기능을 검증하세요

**🎉 성공적인 테스트를 위해 준비완료!**