# 비트코인 자동매매 프로그램 PRD (Product Requirements Document)

## 📋 목차
1. [개요](#개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [핵심 기능](#핵심-기능)
4. [매매 전략](#매매-전략)
5. [Telegram Bot 인터페이스](#telegram-bot-인터페이스)
6. [데이터 구조](#데이터-구조)
7. [보안 및 운영 요구사항](#보안-및-운영-요구사항)
8. [단계별 개발 계획](#단계별-개발-계획)

---

## 개요

### 제품 목적
개인 사용자를 위한 간단하고 직관적인 비트코인 자동매매 시스템으로, Telegram Bot을 통해 제어하며 다양한 매매 전략을 자동으로 실행합니다.

### 핵심 특징
- **언어**: Python 3.8+
- **거래소**: Binance (Testnet/Live)
- **거래 유형**: 현물 및 선물 거래 지원
- **인터페이스**: Telegram Bot (GUI 없음)
- **사용자**: 1인용 (로그인/회원가입 불필요)
- **전략**: 다중 전략 지원 및 자동 추천
- **리스크 관리**: 자동 손절/익절 설정
- **레버리지**: 선물 거래 시 1x~20x 레버리지 지원

### 시스템 요구사항
- Python 3.8 이상
- 24/7 실행 가능한 서버 또는 클라우드 환경
- 안정적인 인터넷 연결
- Telegram 계정
- Binance 계정 및 API Key

---

## 시스템 아키텍처

### 전체 구조도
```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Bot                          │
│                  (사용자 인터페이스)                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                   Bot Controller                         │
│              (명령어 처리 및 응답)                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                  Trading Engine                          │
│            (전략 실행 및 주문 관리)                      │
├─────────────────────────────────────────────────────────┤
│  Strategy Manager │ Order Manager │ Risk Manager        │
└───────┬───────────┴───────┬───────┴────────┬────────────┘
        │                   │                 │
┌───────┴───────┐   ┌───────┴───────┐   ┌────┴────────────┐
│   Strategies  │   │ Binance API   │   │ Data Storage    │
│  - 돌파매매   │   │   Wrapper     │   │ - 거래 내역     │
│  - 스캘핑     │   │               │   │ - 설정 정보     │
│  - 추세추종   │   │               │   │ - 로그          │
└───────────────┘   └───────────────┘   └─────────────────┘
```

### 주요 컴포넌트

#### 1. Telegram Bot Interface
- 사용자 명령 수신 및 처리
- 거래 상태 및 결과 알림
- 에러 알림

#### 2. Bot Controller
- 명령어 파싱 및 검증
- Trading Engine과의 통신
- 응답 메시지 생성

#### 3. Trading Engine
- 전략 실행 루프
- 주문 생성 및 관리
- 포지션 모니터링

#### 4. Strategy Manager
- 전략 로드 및 관리
- 시장 상황 기반 전략 추천
- 전략별 파라미터 관리

#### 5. Order Manager
- Binance API를 통한 주문 실행
- 주문 상태 추적
- 체결 내역 기록

#### 6. Risk Manager
- 손절/익절 자동 설정
- 포지션 크기 계산
- 리스크 한도 관리

---

## 핵심 기능

### 1. 거래 유형 선택
- **현물 거래**: 기본 비트코인 매매 (레버리지 없음)
- **선물 거래**: USDT-M 선물 계약 (1x~20x 레버리지)
- **레버리지 설정**: 선물 거래 시 자동/수동 레버리지 조정
- **마진 모드**: Cross/Isolated 마진 모드 선택

### 2. 전략 관리
- **전략 목록 조회**: 사용 가능한 모든 전략 표시
- **전략 선택**: 특정 전략 활성화
- **전략 추천**: AI 기반 현재 시장에 적합한 전략 추천
- **전략 설정**: 전략별 파라미터 조정

### 3. 자동매매 제어
- **시작/정지**: 자동매매 on/off
- **일시정지**: 긴급 상황 시 모든 거래 중단
- **상태 확인**: 현재 실행 중인 전략 및 포지션 확인
- **포지션 전환**: Long/Short 포지션 자동 전환

### 4. 리스크 관리
- **손절 설정**: 전략별 기본값 + 수동 조정
- **익절 설정**: 전략별 기본값 + 수동 조정
- **포지션 크기**: 자본의 일정 비율로 자동 계산
- **레버리지 제한**: 선물 거래 시 최대 레버리지 제한
- **청산 가격 모니터링**: 선물 거래 시 청산 위험 감시

### 5. 모니터링 및 알림
- **실시간 알림**: 주문 체결, 손익 발생 시 Telegram 알림
- **일일 리포트**: 매일 정해진 시간에 수익률 리포트
- **에러 알림**: API 오류, 네트워크 장애 등 즉시 알림
- **선물 전용 알림**: 첲산 경고, 레버리지 변경 알림

---

## 매매 전략

### 1. 크리스티안 콜로마기의 돌파매매법 (Breakout Strategy)

#### 전략 개요
일정 기간의 고점을 돌파할 때 매수, 저점을 하향 돌파할 때 매도하는 모멘텀 전략

#### 진입 조건
- **매수**: 20일 최고가 돌파 시
- **매도**: 10일 최저가 하향 돌파 시

#### 손절/익절 기준
- **손절**: 진입가 대비 -2% (기본값, 조정 가능)
- **익절**: 진입가 대비 +5% (기본값, 조정 가능)

#### 전략 실행 흐름도
```
시작
  │
  ├─→ [20일 최고가 계산]
  │
  ├─→ [현재가 > 20일 최고가?]
  │     │
  │     ├─ Yes → [매수 주문 실행]
  │     │         │
  │     │         ├─→ [손절가 설정 (진입가 -2%)]
  │     │         ├─→ [익절가 설정 (진입가 +5%)]
  │     │         └─→ [포지션 모니터링]
  │     │
  │     └─ No → [10일 최저가 계산]
  │               │
  │               └─→ [현재가 < 10일 최저가?]
  │                     │
  │                     ├─ Yes → [매도/청산]
  │                     └─ No → [대기]
  │
  └─→ [1분 대기 후 반복]
```

### 2. 스캘핑 전략 (Scalping Strategy)

#### 전략 개요
짧은 시간 내 작은 가격 변동을 이용한 고빈도 매매 전략

#### 진입 조건
- **매수**: RSI < 30 & 볼린저밴드 하단 터치
- **매도**: RSI > 70 & 볼린저밴드 상단 터치

#### 손절/익절 기준
- **손절**: 진입가 대비 -0.5% (기본값)
- **익절**: 진입가 대비 +1% (기본값)

#### 전략 실행 흐름도
```
시작
  │
  ├─→ [RSI(14) 계산]
  ├─→ [볼린저밴드(20,2) 계산]
  │
  ├─→ [RSI < 30 AND 현재가 <= BB 하단?]
  │     │
  │     ├─ Yes → [매수 주문]
  │     │         └─→ [손절 -0.5%, 익절 +1%]
  │     │
  │     └─ No → [RSI > 70 AND 현재가 >= BB 상단?]
  │               │
  │               ├─ Yes → [매도/청산]
  │               └─ No → [대기]
  │
  └─→ [30초 대기 후 반복]
```

### 3. 추세추종 전략 (Trend Following Strategy)

#### 전략 개요
이동평균선을 이용한 중장기 추세 추종 전략

#### 진입 조건
- **매수**: 단기 EMA(12) > 장기 EMA(26) 골든크로스
- **매도**: 단기 EMA(12) < 장기 EMA(26) 데드크로스

#### 손절/익절 기준
- **손절**: 진입가 대비 -3% (기본값)
- **익절**: 추세 반전 시까지 (Trailing Stop 적용)

#### 전략 실행 흐름도
```
시작
  │
  ├─→ [EMA(12), EMA(26) 계산]
  │
  ├─→ [이전 EMA12 < EMA26 AND 현재 EMA12 > EMA26?]
  │     │
  │     ├─ Yes → [골든크로스 - 매수]
  │     │         └─→ [Trailing Stop 3% 설정]
  │     │
  │     └─ No → [이전 EMA12 > EMA26 AND 현재 EMA12 < EMA26?]
  │               │
  │               ├─ Yes → [데드크로스 - 매도/청산]
  │               └─ No → [포지션 있음?]
  │                       │
  │                       ├─ Yes → [Trailing Stop 업데이트]
  │                       └─ No → [대기]
  │
  └─→ [5분 대기 후 반복]
```

### 4. 펀딩비 차익거래 전략 (Funding Rate Arbitrage)

#### 전략 개요
선물 거래소의 펀딩비를 이용한 중립적 수익 창출 전략 (선물 전용)

#### 진입 조건
- **Long 헤지**: 펀딩비 > +0.1% 시 현물 매수 + 선물 매도
- **Short 헤지**: 펀딩비 < -0.1% 시 현물 매도 + 선물 매수
- **최소 보유기간**: 8시간 (펀딩비 지급 주기)

#### 손절/익절 기준
- **손절**: 헤지 포지션 간 가격 차이 > 1%
- **익절**: 펀딩비 수익 + 스프레드 수익
- **자동 청산**: 펀딩비 방향 전환 시

### 5. 그리드 거래 전략 (Grid Trading)

#### 전략 개요
일정 구간에서 여러 가격대에 매수/매도 주문을 배치하는 전략

#### 진입 조건
- **그리드 설정**: 현재가 ±10% 구간에 20개 주문 배치
- **매수 그리드**: 현재가 하방 5% 구간에 10개 매수 주문
- **매도 그리드**: 현재가 상방 5% 구간에 10개 매도 주문

#### 손절/익절 기준
- **손절**: 그리드 범위 이탈 시 (-15%)
- **익절**: 각 그리드당 0.5% 수익 목표
- **재조정**: 6시간마다 그리드 범위 재설정

### 6. 롱숏 스위칭 전략 (Long-Short Switching)

#### 전략 개요
시장 방향성에 따라 Long/Short 포지션을 동적으로 전환하는 전략 (선물 전용)

#### 진입 조건
- **Long 진입**: RSI > 50 AND EMA12 > EMA26 AND 거래량 증가
- **Short 진입**: RSI < 50 AND EMA12 < EMA26 AND 거래량 증가
- **레버리지**: 확신도에 따라 1x~10x 동적 조정

#### 손절/익절 기준
- **손절**: 진입가 대비 ±2%
- **익절**: 추세 지속 시 Trailing Stop
- **포지션 전환**: 신호 반전 시 즉시 반대 포지션

#### 전략 실행 흐름도
```
시작
  │
  ├─→ [현재 포지션 확인]
  │
  ├─→ [시장 신호 분석]
  │     │
  │     ├─ Strong Bull → [Long 포지션 + 높은 레버리지]
  │     ├─ Weak Bull → [Long 포지션 + 낮은 레버리지]
  │     ├─ Strong Bear → [Short 포지션 + 높은 레버리지]
  │     ├─ Weak Bear → [Short 포지션 + 낮은 레버리지]
  │     └─ Neutral → [포지션 청산]
  │
  ├─→ [포지션 크기 및 레버리지 조정]
  │
  └─→ [1분 대기 후 반복]
```

### 7. 변동성 돌파 전략 (Volatility Breakout)

#### 전략 개요
변동성 확장 구간에서 방향성 돌파를 포착하는 전략

#### 진입 조건
- **변동성 측정**: ATR(14) > 20일 평균 ATR * 1.5
- **Long 진입**: 상위 볼린저밴드 돌파 + 거래량 급증
- **Short 진입**: 하위 볼린저밴드 하향 돌파 + 거래량 급증

#### 손절/익절 기준
- **손절**: ATR의 1.5배
- **익절**: ATR의 3배 또는 볼린저밴드 중심선 복귀
- **레버리지**: 변동성에 반비례 (높은 변동성일수록 낮은 레버리지)

### 전략 추천 로직

#### 전략별 특징 요약

| 전략명 | 거래 유형 | 적합한 시장 | 레버리지 | 리스크 |
|--------|-----------|-------------|-----------|--------|
| 돌파매매 | 현물/선물 | 트렌드 시장 | 1-3x | 중간 |
| 스캘핑 | 현물/선물 | 횡보장 | 1-2x | 낮음 |
| 추세추종 | 현물/선물 | 강한 트렌드 | 1-5x | 중간 |
| 펀딩비 차익거래 | 선물 전용 | 모든 시장 | 1-2x | 매우낮음 |
| 그리드 거래 | 선물 권장 | 횡보장 | 3-5x | 낮음 |
| 롱숏 스위칭 | 선물 전용 | 변동성 시장 | 5-10x | 높음 |
| 변동성 돌파 | 선물 전용 | 급변동 시장 | 10-20x | 매우높음 |

#### 추천 기준

##### 현물 거래 전략 추천
1. **변동성 기반**
   - 고변동성 (>3%): 돌파매매 전략
   - 중변동성 (1-3%): 추세추종 전략
   - 저변동성 (<1%): 스캘핑 전략

2. **거래량 기반**
   - 거래량 급증: 돌파매매 전략
   - 평균 거래량: 추세추종 전략
   - 거래량 감소: 스캘핑 전략

3. **추세 강도**
   - 강한 상승/하락: 추세추종 전략
   - 횡보장: 스캘핑 전략
   - 변동성 확대: 돌파매매 전략

##### 선물 거래 전략 추천
1. **시장 상황 기반**
   - 강한 트렌드: 롱숏 스위칭 전략 (높은 레버리지)
   - 횡보장: 그리드 거래 전략
   - 높은 펀딩비: 펀딩비 차익거래 전략
   - 급격한 변동성: 변동성 돌파 전략

2. **리스크 선호도 기반**
   - 보수적: 펀딩비 차익거래 (1-2x 레버리지)
   - 중립적: 그리드 거래 (3-5x 레버리지)
   - 공격적: 롱숏 스위칭 (5-10x 레버리지)
   - 초공격적: 변동성 돌파 (10-20x 레버리지)

3. **자본 규모 기반**
   - 대규모 자본: 펀딩비 차익거래 + 그리드 전략
   - 중간 자본: 롱숏 스위칭 전략
   - 소규모 자본: 변동성 돌파 전략 (높은 레버리지)

---

## Telegram Bot 인터페이스

### 명령어 목록

#### 기본 명령어
- `/start` - 봇 시작 및 환영 메시지
- `/help` - 사용 가능한 명령어 목록
- `/status` - 현재 봇 상태 및 실행 중인 전략

#### 전략 관리
- `/strategies` - 사용 가능한 전략 목록
- `/select [strategy_name]` - 전략 선택
- `/recommend` - 현재 시장에 적합한 전략 추천
- `/params` - 현재 전략의 파라미터 확인

#### 자동매매 제어
- `/run` - 선택된 전략으로 자동매매 시작
- `/stop` - 자동매매 중지
- `/pause` - 자동매매 일시정지
- `/resume` - 자동매매 재개

#### 거래 유형 설정
- `/mode spot` - 현물 거래 모드
- `/mode futures` - 선물 거래 모드
- `/leverage [1-20]` - 레버리지 설정 (선물 전용)
- `/margin cross|isolated` - 마진 모드 설정

#### 리스크 관리
- `/sl [percentage]` - 손절 비율 설정 (예: /sl 2.5)
- `/tp [percentage]` - 익절 비율 설정 (예: /tp 5.0)
- `/risk` - 현재 리스크 설정 확인
- `/liquidation` - 청산 가격 확인 (선물 전용)

#### 모니터링
- `/position` - 현재 포지션 상태
- `/balance` - 계좌 잔고 확인
- `/funding` - 펀딩비 현황 (선물 전용)
- `/history` - 최근 거래 내역 (최대 10건)
- `/report` - 일일/주간/월간 수익률 리포트

### 메시지 예시

#### 전략 목록 응답
```
📊 사용 가능한 전략:

🔵 현물 거래 전략:
1️⃣ breakout - 돌파매매 전략
   • 20일 고점 돌파 시 매수
   • 손절: -2%, 익절: +5%

2️⃣ scalping - 스캘핑 전략
   • RSI + 볼린저밴드
   • 손절: -0.5%, 익절: +1%

3️⃣ trend - 추세추종 전략
   • EMA 크로스
   • 손절: -3%, Trailing Stop

🔴 선물 거래 전략:
4️⃣ funding - 펀딩비 차익거래
   • 펀딩비 헤지 전략
   • 레버리지: 1-2x, 리스크: 매우낮음

5️⃣ grid - 그리드 거래
   • 구간 매매 전략
   • 레버리지: 3-5x, 리스크: 낮음

6️⃣ longshort - 롱숏 스위칭
   • 동적 포지션 전환
   • 레버리지: 5-10x, 리스크: 높음

7️⃣ volatility - 변동성 돌파
   • 고변동성 돌파 전략
   • 레버리지: 10-20x, 리스크: 매우높음

선택: /select [전략명]
거래모드: /mode [spot|futures]
```

#### 자동매매 시작 응답
```
✅ 자동매매 시작됨

전략: 돌파매매 (breakout)
거래 모드: 현물 거래
손절: -2.0%
익절: +5.0%
투자금액: 1,000 USDT

⚡️ 실시간 모니터링 중...
```

#### 선물 거래 시작 응답
```
✅ 선물 자동매매 시작됨

전략: 롱숏 스위칭 (longshort)
거래 모드: USDT-M 선물
레버리지: 5x
마진 모드: Cross Margin
손절: -2.0%
익절: Trailing Stop
포지션 크기: 5,000 USDT (명목가치)

⚡️ Long/Short 동적 전환 대기 중...
```

#### 포지션 알림
```
🔔 새로운 포지션 오픈!

종류: 매수 (BUY)
가격: $45,230
수량: 0.022 BTC
전략: breakout

손절가: $44,325 (-2.0%)
익절가: $47,492 (+5.0%)
```

#### 선물 포지션 알림
```
🔔 선물 포지션 오픈!

종류: 롱 포지션 (LONG)
진입가: $45,230
포지션 크기: 0.11 BTC (5,000 USDT)
레버리지: 5x
전략: longshort

손절가: $44,325 (-2.0%)
익절가: Trailing Stop
청산가: $40,706 (-10.0%)

현재 수익: +$226 (+2.1%)
```

#### 펀딩비 알림
```
💰 펀딩비 수익 발생!

수익 금액: +$12.45
펀딩비율: +0.0125%
다음 지급: 4시간 32분 후

총 펀딩비 수익: +$156.78
```

---

## 데이터 구조

### 1. 설정 파일 (config.json)
```json
{
  "exchange": {
    "name": "binance",
    "testnet": true,
    "api_key": "${BINANCE_API_KEY}",
    "api_secret": "${BINANCE_API_SECRET}"
  },
  "telegram": {
    "bot_token": "${TELEGRAM_BOT_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}"
  },
  "trading": {
    "mode": "spot",
    "symbol": "BTCUSDT",
    "base_amount": 1000,
    "max_positions": 1
  },
  "futures": {
    "enabled": true,
    "leverage": 5,
    "margin_mode": "cross",
    "max_leverage": 20,
    "position_size_percentage": 10.0,
    "liquidation_buffer": 5.0
  },
  "strategies": {
    "breakout": {
      "enabled": true,
      "lookback_buy": 20,
      "lookback_sell": 10,
      "stop_loss": 2.0,
      "take_profit": 5.0
    },
    "scalping": {
      "enabled": true,
      "rsi_period": 14,
      "rsi_oversold": 30,
      "rsi_overbought": 70,
      "bb_period": 20,
      "bb_std": 2,
      "stop_loss": 0.5,
      "take_profit": 1.0
    },
    "trend": {
      "enabled": true,
      "ema_fast": 12,
      "ema_slow": 26,
      "stop_loss": 3.0,
      "trailing_stop": 3.0
    },
    "funding": {
      "enabled": true,
      "min_funding_rate": 0.001,
      "hedge_threshold": 0.1,
      "min_hold_hours": 8,
      "max_spread": 1.0
    },
    "grid": {
      "enabled": true,
      "grid_count": 20,
      "price_range": 10.0,
      "profit_per_grid": 0.5,
      "rebalance_hours": 6
    },
    "longshort": {
      "enabled": true,
      "base_leverage": 5,
      "max_leverage": 10,
      "confidence_threshold": 0.7,
      "switch_cooldown": 300
    },
    "volatility": {
      "enabled": true,
      "atr_multiplier": 1.5,
      "volume_spike_threshold": 2.0,
      "max_leverage": 20,
      "min_volatility": 3.0
    }
  }
}
```

### 2. 거래 내역 (trades.json)
```json
{
  "trades": [
    {
      "id": "uuid-1234",
      "timestamp": "2024-01-15T10:30:00Z",
      "strategy": "breakout",
      "trade_type": "spot",
      "side": "BUY",
      "price": 45230,
      "quantity": 0.022,
      "status": "FILLED",
      "pnl": null,
      "pnl_percentage": null
    },
    {
      "id": "uuid-5678",
      "timestamp": "2024-01-15T14:45:00Z",
      "strategy": "breakout",
      "trade_type": "spot",
      "side": "SELL",
      "price": 46123,
      "quantity": 0.022,
      "status": "FILLED",
      "pnl": 19.65,
      "pnl_percentage": 1.97
    },
    {
      "id": "uuid-9999",
      "timestamp": "2024-01-15T16:20:00Z",
      "strategy": "longshort",
      "trade_type": "futures",
      "side": "LONG",
      "price": 46500,
      "quantity": 0.11,
      "leverage": 5,
      "margin_mode": "cross",
      "position_size": 5115,
      "liquidation_price": 41850,
      "status": "FILLED",
      "funding_fee": 2.85,
      "pnl": 127.50,
      "pnl_percentage": 12.75
    }
  ]
}
```

### 3. 선물 포지션 정보 (futures_positions.json)
```json
{
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "LONG",
      "size": 0.11,
      "entry_price": 46500,
      "mark_price": 47650,
      "liquidation_price": 41850,
      "leverage": 5,
      "margin_mode": "cross",
      "unrealized_pnl": 126.50,
      "unrealized_pnl_percentage": 12.65,
      "margin_balance": 1023.00,
      "maintenance_margin": 23.25,
      "strategy": "longshort",
      "timestamp": "2024-01-15T16:20:00Z"
    }
  ],
  "funding_history": [
    {
      "timestamp": "2024-01-15T16:00:00Z",
      "funding_rate": 0.0125,
      "funding_fee": 2.85,
      "position_size": 5115
    }
  ]
}
```

### 4. 전략 상태 (strategy_state.json)
```json
{
  "active_strategy": "longshort",
  "trading_mode": "futures",
  "is_running": true,
  "last_update": "2024-01-15T15:00:00Z",
  "current_position": {
    "trade_type": "futures",
    "side": "LONG",
    "entry_price": 46500,
    "quantity": 0.11,
    "leverage": 5,
    "margin_mode": "cross",
    "liquidation_price": 41850,
    "stop_loss": 45570,
    "take_profit": "trailing",
    "unrealized_pnl": 126.50,
    "unrealized_pnl_percentage": 12.65
  },
  "statistics": {
    "total_trades": 42,
    "winning_trades": 28,
    "losing_trades": 14,
    "win_rate": 66.7,
    "total_pnl": 834.56,
    "total_pnl_percentage": 83.46,
    "spot_trades": 28,
    "futures_trades": 14,
    "total_funding_fees": 45.30,
    "max_leverage_used": 10,
    "liquidations": 0
  }
}
```

---

## 보안 및 운영 요구사항

### 보안 요구사항

#### 1. API Key 관리
- 환경 변수 또는 별도 암호화된 파일로 관리
- 코드에 직접 하드코딩 금지
- 정기적인 API Key 교체 권장

```python
# 예시: 환경 변수 사용
import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

#### 2. Telegram Bot 보안
- Chat ID 검증으로 인증된 사용자만 접근
- 명령어 실행 로그 기록
- Rate Limiting 적용

```python
# 예시: 사용자 인증
AUTHORIZED_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def is_authorized(update):
    return str(update.effective_chat.id) == AUTHORIZED_CHAT_ID
```

#### 3. 거래 보안
- Testnet에서 충분한 테스트 후 실거래 전환
- 일일 최대 거래 한도 설정
- 긴급 정지 기능 구현

#### 4. 선물 거래 전용 보안
- **레버리지 제한**: 최대 20x 레버리지 하드 리미트
- **청산 모니터링**: 청산가 5% 이내 접근 시 자동 경고
- **포지션 크기 제한**: 총 자본의 일정 비율 이하로 제한
- **마진 콜 보호**: 마진 콜 발생 시 자동 포지션 축소
- **펀딩비 모니터링**: 비정상적 펀딩비 발생 시 알림

### 운영 요구사항

#### 1. 로깅
- 모든 거래 활동 기록
- 에러 및 예외 상황 상세 로깅
- 일별 로그 파일 분리

```python
# 로깅 설정 예시
import logging
from logging.handlers import RotatingFileHandler

# 로거 설정
logger = logging.getLogger('autoCoin')
logger.setLevel(logging.INFO)

# 파일 핸들러 (일별 로테이션)
file_handler = RotatingFileHandler(
    'logs/autocoin.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=30
)

# 포맷 설정
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
```

#### 2. 에러 처리
- API 연결 실패 시 재시도 로직
- 네트워크 장애 대응
- 예상치 못한 종료 시 포지션 보호

```python
# 재시도 로직 예시
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise
                    logger.warning(f"Retry {i+1}/{max_retries} after error: {e}")
                    time.sleep(delay * (2 ** i))  # Exponential backoff
            return None
        return wrapper
    return decorator
```

#### 3. 모니터링
- 시스템 상태 주기적 체크
- 메모리 사용량 모니터링
- API Rate Limit 관리

#### 4. 백업 및 복구
- 거래 내역 정기 백업
- 전략 설정 백업
- 시스템 재시작 시 이전 상태 복원

```python
# 상태 저장 및 복원 예시
import json
import os

class StateManager:
    def __init__(self, state_file='state/strategy_state.json'):
        self.state_file = state_file
        self.ensure_directory()
        
    def ensure_directory(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
    def save_state(self, state):
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return None
```

---

## 단계별 개발 계획

### Phase 1: 기초 인프라 구축

#### 목표
- 프로젝트 구조 설정
- Binance API 연동
- 기본 로깅 시스템

#### 구성요소
```
autoCoin/
├── src/
│   ├── __init__.py
│   ├── config.py          # 설정 관리
│   ├── logger.py          # 로깅 시스템
│   └── exchange/
│       ├── __init__.py
│       └── binance_client.py  # Binance API 래퍼
├── tests/
│   └── test_binance.py
├── logs/
├── data/
├── requirements.txt
├── .env.example
└── README.md
```

#### 예제 코드: Binance Client
```python
# src/exchange/binance_client.py
import ccxt
from typing import Dict, List, Optional
import logging

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.logger = logging.getLogger(__name__)
        
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'test': True,
                }
            })
            self.exchange.set_sandbox_mode(True)
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            
    def get_balance(self) -> Dict:
        """계좌 잔고 조회"""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            self.logger.error(f"Failed to fetch balance: {e}")
            raise
            
    def get_ticker(self, symbol: str) -> Dict:
        """현재가 조회"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.logger.error(f"Failed to fetch ticker: {e}")
            raise
```

#### 테스트 방법
```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 테스트 실행
python -m pytest tests/test_binance.py
```

### Phase 2: Telegram Bot 구현

#### 목표
- Telegram Bot 기본 구조
- 명령어 처리 시스템
- 사용자 인증

#### 구성요소
```
src/
├── telegram_bot/
│   ├── __init__.py
│   ├── bot.py             # 메인 봇 클래스
│   ├── handlers.py        # 명령어 핸들러
│   └── keyboards.py       # 인라인 키보드
```

#### 예제 코드: Telegram Bot
```python
# src/telegram_bot/bot.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

class AutoCoinBot:
    def __init__(self, token: str, authorized_chat_id: str):
        self.token = token
        self.authorized_chat_id = authorized_chat_id
        self.logger = logging.getLogger(__name__)
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 시작 명령어"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        welcome_message = """
🤖 AutoCoin Bot에 오신 것을 환영합니다!

사용 가능한 명령어:
/help - 도움말
/status - 현재 상태
/strategies - 전략 목록
/run - 자동매매 시작
/stop - 자동매매 중지

자세한 사용법은 /help를 입력하세요.
"""
        await update.message.reply_text(welcome_message)
        
    def is_authorized(self, update: Update) -> bool:
        """사용자 인증 확인"""
        return str(update.effective_chat.id) == self.authorized_chat_id
        
    def run(self):
        """봇 실행"""
        application = Application.builder().token(self.token).build()
        
        # 핸들러 등록
        application.add_handler(CommandHandler("start", self.start))
        
        # 봇 실행
        application.run_polling()
```

#### 사용자 입력 예시
```
사용자: /start
봇: 🤖 AutoCoin Bot에 오신 것을 환영합니다! ...

사용자: /strategies
봇: 📊 사용 가능한 전략:
    1️⃣ breakout - 돌파매매 전략
    2️⃣ scalping - 스캘핑 전략
    3️⃣ trend - 추세추종 전략

사용자: /select breakout
봇: ✅ 돌파매매 전략이 선택되었습니다.

사용자: /run
봇: ✅ 자동매매가 시작되었습니다.
    전략: 돌파매매 (breakout)
    손절: -2.0%
    익절: +5.0%
```

### Phase 3: 전략 시스템 구현

#### 목표
- 전략 인터페이스 정의
- 3가지 기본 전략 구현
- 백테스트 기능 (선택사항)

#### 구성요소
```
src/
├── strategies/
│   ├── __init__.py
│   ├── base.py           # 전략 추상 클래스
│   ├── breakout.py       # 돌파매매 전략
│   ├── scalping.py       # 스캘핑 전략
│   └── trend.py          # 추세추종 전략
```

#### 예제 코드: 전략 베이스 클래스
```python
# src/strategies/base.py
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import pandas as pd

class Strategy(ABC):
    def __init__(self, params: Dict):
        self.params = params
        self.position = None
        self.stop_loss = params.get('stop_loss', 2.0)
        self.take_profit = params.get('take_profit', 5.0)
        
    @abstractmethod
    def should_buy(self, data: pd.DataFrame) -> bool:
        """매수 신호 판단"""
        pass
        
    @abstractmethod
    def should_sell(self, data: pd.DataFrame) -> bool:
        """매도 신호 판단"""
        pass
        
    def calculate_position_size(self, capital: float, price: float) -> float:
        """포지션 크기 계산"""
        # 자본의 95% 사용 (수수료 고려)
        return (capital * 0.95) / price
        
    def get_sl_tp_prices(self, entry_price: float) -> Tuple[float, float]:
        """손절/익절 가격 계산"""
        sl_price = entry_price * (1 - self.stop_loss / 100)
        tp_price = entry_price * (1 + self.take_profit / 100)
        return sl_price, tp_price
```

#### 예제 코드: 돌파매매 전략
```python
# src/strategies/breakout.py
import pandas as pd
from .base import Strategy

class BreakoutStrategy(Strategy):
    def __init__(self, params: Dict):
        super().__init__(params)
        self.lookback_buy = params.get('lookback_buy', 20)
        self.lookback_sell = params.get('lookback_sell', 10)
        
    def should_buy(self, data: pd.DataFrame) -> bool:
        """20일 최고가 돌파 시 매수"""
        if len(data) < self.lookback_buy:
            return False
            
        current_price = data['close'].iloc[-1]
        highest_price = data['high'].iloc[-self.lookback_buy:].max()
        
        return current_price > highest_price
        
    def should_sell(self, data: pd.DataFrame) -> bool:
        """10일 최저가 하향 돌파 시 매도"""
        if len(data) < self.lookback_sell:
            return False
            
        current_price = data['close'].iloc[-1]
        lowest_price = data['low'].iloc[-self.lookback_sell:].min()
        
        return current_price < lowest_price
```

### Phase 4: Trading Engine 구현

#### 목표
- 전략 실행 엔진
- 주문 관리 시스템
- 리스크 관리

#### 구성요소
```
src/
├── trading/
│   ├── __init__.py
│   ├── engine.py          # 메인 트레이딩 엔진
│   ├── order_manager.py   # 주문 관리
│   └── risk_manager.py    # 리스크 관리
```

#### 예제 코드: Trading Engine
```python
# src/trading/engine.py
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

class TradingEngine:
    def __init__(self, exchange, strategy, bot_notifier):
        self.exchange = exchange
        self.strategy = strategy
        self.bot = bot_notifier
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """자동매매 시작"""
        self.is_running = True
        self.logger.info("Trading engine started")
        await self.bot.send_message("✅ 자동매매가 시작되었습니다.")
        
        while self.is_running:
            try:
                await self.run_cycle()
                await asyncio.sleep(60)  # 1분 대기
            except Exception as e:
                self.logger.error(f"Trading cycle error: {e}")
                await self.bot.send_message(f"⚠️ 에러 발생: {e}")
                
    async def stop(self):
        """자동매매 중지"""
        self.is_running = False
        self.logger.info("Trading engine stopped")
        await self.bot.send_message("🛑 자동매매가 중지되었습니다.")
        
    async def run_cycle(self):
        """매매 사이클 실행"""
        # 1. 시장 데이터 가져오기
        data = await self.get_market_data()
        
        # 2. 현재 포지션 확인
        position = await self.get_position()
        
        # 3. 매매 신호 확인
        if position is None:
            if self.strategy.should_buy(data):
                await self.open_position('BUY', data)
        else:
            if self.strategy.should_sell(data):
                await self.close_position(position)
                
        # 4. 손절/익절 체크
        if position:
            await self.check_sl_tp(position)
```

### Phase 5: 전략 추천 시스템

#### 목표
- 시장 상황 분석
- 전략별 적합도 계산
- 추천 알고리즘

#### 구성요소
```
src/
├── recommender/
│   ├── __init__.py
│   ├── market_analyzer.py  # 시장 분석
│   └── strategy_recommender.py  # 전략 추천
```

#### 예제 코드: 전략 추천 시스템
```python
# src/recommender/strategy_recommender.py
import pandas as pd
import numpy as np
from typing import Dict, List

class StrategyRecommender:
    def __init__(self):
        self.strategies = ['breakout', 'scalping', 'trend']
        
    def analyze_market(self, data: pd.DataFrame) -> Dict:
        """시장 상황 분석"""
        # 변동성 계산
        volatility = data['close'].pct_change().std() * 100
        
        # 추세 강도 계산
        sma20 = data['close'].rolling(20).mean()
        sma50 = data['close'].rolling(50).mean()
        trend_strength = abs(sma20.iloc[-1] - sma50.iloc[-1]) / sma50.iloc[-1] * 100
        
        # 거래량 변화
        volume_ratio = data['volume'].iloc[-1] / data['volume'].rolling(20).mean().iloc[-1]
        
        return {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'volume_ratio': volume_ratio
        }
        
    def recommend(self, market_data: Dict) -> str:
        """최적 전략 추천"""
        scores = {}
        
        # 전략별 점수 계산
        # 돌파매매: 높은 변동성, 거래량 증가 시 유리
        scores['breakout'] = (
            market_data['volatility'] * 2 +
            market_data['volume_ratio'] * 3
        )
        
        # 스캘핑: 낮은 변동성, 횡보장에 유리
        scores['scalping'] = (
            (5 - market_data['volatility']) * 2 +
            (2 - market_data['trend_strength']) * 3
        )
        
        # 추세추종: 강한 추세, 중간 변동성에 유리
        scores['trend'] = (
            market_data['trend_strength'] * 4 +
            abs(market_data['volatility'] - 2) * 1
        )
        
        # 최고 점수 전략 반환
        return max(scores, key=scores.get)
```

### Phase 6: 통합 및 최적화

#### 목표
- 모든 컴포넌트 통합
- 성능 최적화
- 전체 시스템 테스트

#### 주요 작업
1. **메인 애플리케이션 작성**
```python
# main.py
import asyncio
import logging
from src.config import Config
from src.exchange.binance_client import BinanceClient
from src.telegram_bot.bot import AutoCoinBot
from src.trading.engine import TradingEngine
from src.strategies import load_strategy

async def main():
    # 설정 로드
    config = Config()
    
    # 컴포넌트 초기화
    exchange = BinanceClient(
        config.api_key,
        config.api_secret,
        config.testnet
    )
    
    bot = AutoCoinBot(
        config.telegram_token,
        config.chat_id
    )
    
    # 전략 로드
    strategy = load_strategy(config.default_strategy)
    
    # 트레이딩 엔진 생성
    engine = TradingEngine(exchange, strategy, bot)
    
    # 봇과 엔진 실행
    await asyncio.gather(
        bot.run(),
        engine.start()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

2. **Docker 컨테이너화**
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

3. **시스템 모니터링**
```python
# src/monitoring/health_check.py
class HealthChecker:
    def __init__(self, components):
        self.components = components
        
    async def check_all(self):
        """모든 컴포넌트 상태 확인"""
        status = {}
        
        # API 연결 확인
        status['exchange'] = await self.check_exchange()
        
        # 봇 상태 확인
        status['bot'] = await self.check_bot()
        
        # 전략 상태 확인
        status['strategy'] = await self.check_strategy()
        
        return status
```

### Phase 7: 배포 및 운영

#### 목표
- 프로덕션 환경 설정
- 모니터링 시스템
- 백업 및 복구 절차

#### 배포 체크리스트
- [ ] Testnet에서 최소 1주일 테스트
- [ ] 모든 전략 백테스트 완료
- [ ] 에러 처리 및 복구 로직 검증
- [ ] API Key 보안 설정
- [ ] 로깅 및 모니터링 설정
- [ ] 일일 백업 스크립트 설정
- [ ] 긴급 정지 절차 문서화

#### 운영 가이드
1. **일일 체크리스트**
   - 시스템 상태 확인
   - 거래 내역 검토
   - 에러 로그 확인
   - 수익률 모니터링

2. **주간 작업**
   - 전략 성과 분석
   - 파라미터 조정 검토
   - 시스템 업데이트

3. **월간 작업**
   - 전체 백테스트
   - 전략 최적화
   - 보안 감사

---

## 예외 처리 가이드

### API 관련 예외
```python
class APIException(Exception):
    """API 관련 예외"""
    pass

class RateLimitException(APIException):
    """Rate Limit 초과"""
    pass

class NetworkException(APIException):
    """네트워크 연결 오류"""
    pass

# 사용 예시
try:
    order = await exchange.create_order(...)
except RateLimitException:
    await asyncio.sleep(60)  # 1분 대기
    retry_order()
except NetworkException:
    await bot.send_message("⚠️ 네트워크 연결 오류")
    await reconnect()
```

### 거래 관련 예외
```python
class TradingException(Exception):
    """거래 관련 예외"""
    pass

class InsufficientBalanceException(TradingException):
    """잔고 부족"""
    pass

class InvalidOrderException(TradingException):
    """잘못된 주문"""
    pass

# 사용 예시
try:
    await engine.open_position()
except InsufficientBalanceException:
    await bot.send_message("⚠️ 잔고가 부족합니다")
except InvalidOrderException as e:
    await bot.send_message(f"⚠️ 주문 오류: {e}")
```

---

## 확장 가능성

### 향후 추가 가능한 기능
1. **고급 전략**
   - 머신러닝 기반 예측 모델
   - 멀티 타임프레임 분석
   - 상관관계 분석

2. **리스크 관리**
   - 포트폴리오 분산
   - 동적 포지션 사이징
   - 최대 손실 한도 설정

3. **분석 도구**
   - 백테스트 시스템
   - 성과 분석 대시보드
   - 전략 최적화 도구

4. **알트코인 지원**
   - 다중 코인 거래
   - 코인간 상관관계 분석
   - 포트폴리오 리밸런싱

---

이 PRD는 비트코인 자동매매 프로그램의 전체 개발 과정을 단계별로 안내합니다. 각 Phase를 순차적으로 진행하면서 안정적이고 확장 가능한 시스템을 구축할 수 있습니다.