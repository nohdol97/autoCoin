#!/usr/bin/env python3
"""
AutoCoin 통합 테스트 스크립트
모든 컴포넌트가 올바르게 연결되고 작동하는지 확인
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.exchange.binance_client import BinanceClient
from src.strategies.strategy_manager import StrategyManager
from src.recommendation.strategy_recommender import StrategyRecommender
from src.monitoring.health_checker import HealthChecker
from src.monitoring.metrics_collector import MetricsCollector
from src.utils.error_handler import ErrorHandler


class IntegrationTester:
    def __init__(self):
        self.config = Config()
        self.results = {}
        
    async def test_exchange_connection(self):
        """거래소 연결 테스트"""
        print("\n1. 거래소 연결 테스트...")
        try:
            exchange = BinanceClient(
                api_key=self.config.binance_api_key,
                api_secret=self.config.binance_api_secret,
                testnet=self.config.binance_testnet
            )
            await exchange.initialize()
            
            # 연결 테스트
            await exchange.test_connection()
            
            # 잔고 조회 테스트
            balance = await exchange.get_balance()
            
            print("✅ 거래소 연결 성공")
            print(f"   - Testnet 모드: {self.config.binance_testnet}")
            print(f"   - USDT 잔고: {balance.get('USDT', {}).get('free', 0)}")
            
            self.results['exchange'] = True
            return exchange
            
        except Exception as e:
            print(f"❌ 거래소 연결 실패: {e}")
            self.results['exchange'] = False
            return None
            
    async def test_strategy_manager(self):
        """전략 매니저 테스트"""
        print("\n2. 전략 매니저 테스트...")
        try:
            manager = StrategyManager()
            
            # 사용 가능한 전략 확인
            strategies = manager.get_available_strategies()
            print(f"✅ 전략 매니저 초기화 성공")
            print(f"   - 사용 가능한 전략: {', '.join(strategies)}")
            
            # 각 전략 로드 테스트
            for strategy_name in strategies:
                strategy = manager.get_strategy(strategy_name)
                print(f"   - {strategy_name} 전략 로드 성공")
                
            self.results['strategy_manager'] = True
            return manager
            
        except Exception as e:
            print(f"❌ 전략 매니저 테스트 실패: {e}")
            self.results['strategy_manager'] = False
            return None
            
    async def test_strategy_recommender(self, exchange):
        """전략 추천 시스템 테스트"""
        print("\n3. 전략 추천 시스템 테스트...")
        if not exchange:
            print("⚠️  거래소 연결이 필요합니다. 건너뜁니다.")
            self.results['recommender'] = False
            return None
            
        try:
            recommender = StrategyRecommender(exchange)
            
            # 시장 분석 테스트
            analysis = await recommender.analyze_market()
            print("✅ 전략 추천 시스템 초기화 성공")
            print(f"   - 현재 변동성: {analysis.get('volatility', 0):.2f}%")
            print(f"   - 추세 강도: {analysis.get('trend_strength', 0):.2f}")
            
            # 전략 추천 테스트
            recommended = await recommender.recommend_strategy()
            print(f"   - 추천 전략: {recommended}")
            
            self.results['recommender'] = True
            return recommender
            
        except Exception as e:
            print(f"❌ 전략 추천 시스템 테스트 실패: {e}")
            self.results['recommender'] = False
            return None
            
    async def test_health_checker(self, components):
        """헬스 체커 테스트"""
        print("\n4. 헬스 체커 테스트...")
        try:
            health_checker = HealthChecker()
            
            # 컴포넌트 등록
            for name, component in components.items():
                if component:
                    health_checker.register_component(name, component)
                    
            # 헬스 체크 실행
            results = await health_checker.check_all()
            
            print("✅ 헬스 체커 테스트 성공")
            for name, status in results.items():
                emoji = "✅" if status.is_healthy else "❌"
                print(f"   {emoji} {name}: {status.message}")
                
            self.results['health_checker'] = True
            return health_checker
            
        except Exception as e:
            print(f"❌ 헬스 체커 테스트 실패: {e}")
            self.results['health_checker'] = False
            return None
            
    async def test_error_handler(self):
        """에러 핸들러 테스트"""
        print("\n5. 에러 핸들러 테스트...")
        try:
            error_handler = ErrorHandler()
            
            # 테스트 에러 생성 및 처리
            test_error = ValueError("테스트 에러")
            handled = await error_handler.handle_error(test_error, {"test": True})
            
            # 에러 요약 확인
            summary = error_handler.get_error_summary(hours=1)
            
            print("✅ 에러 핸들러 테스트 성공")
            print(f"   - 에러 처리 완료: {handled}")
            print(f"   - 총 에러 수: {summary['total_errors']}")
            
            self.results['error_handler'] = True
            return error_handler
            
        except Exception as e:
            print(f"❌ 에러 핸들러 테스트 실패: {e}")
            self.results['error_handler'] = False
            return None
            
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*50)
        print("통합 테스트 결과 요약")
        print("="*50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        for component, result in self.results.items():
            emoji = "✅" if result else "❌"
            print(f"{emoji} {component}: {'성공' if result else '실패'}")
            
        print(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 성공")
        
        if passed_tests == total_tests:
            print("\n🎉 모든 테스트를 통과했습니다! 시스템이 정상적으로 작동합니다.")
        else:
            print("\n⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")
            
    async def run_tests(self):
        """모든 테스트 실행"""
        print("🚀 AutoCoin 통합 테스트 시작...")
        
        # 1. 거래소 연결 테스트
        exchange = await self.test_exchange_connection()
        
        # 2. 전략 매니저 테스트
        strategy_manager = await self.test_strategy_manager()
        
        # 3. 전략 추천 시스템 테스트
        recommender = await self.test_strategy_recommender(exchange)
        
        # 4. 헬스 체커 테스트
        components = {
            'exchange': exchange,
            'strategy_manager': strategy_manager,
            'recommender': recommender
        }
        health_checker = await self.test_health_checker(components)
        
        # 5. 에러 핸들러 테스트
        error_handler = await self.test_error_handler()
        
        # 결과 요약
        self.print_summary()
        
        # 리소스 정리
        if exchange:
            await exchange.close()


async def main():
    tester = IntegrationTester()
    await tester.run_tests()


if __name__ == "__main__":
    # .env 파일 확인
    if not os.path.exists('.env'):
        print("❌ .env 파일이 없습니다. .env.example을 참고하여 생성해주세요.")
        sys.exit(1)
        
    asyncio.run(main())