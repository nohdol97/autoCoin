import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import asyncio
from pathlib import Path


@dataclass
class TradingMetrics:
    """거래 메트릭"""
    timestamp: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percentage: float
    average_win: float
    average_loss: float
    max_drawdown: float
    sharpe_ratio: float
    active_positions: int
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """메트릭 수집 및 관리"""
    
    def __init__(self, data_dir: str = "data/metrics"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: List[TradingMetrics] = []
        self.components = {}
        
    def register_component(self, name: str, component: Any):
        """메트릭 수집할 컴포넌트 등록"""
        self.components[name] = component
        
    async def collect_metrics(self) -> TradingMetrics:
        """현재 메트릭 수집"""
        engine = self.components.get('trading_engine')
        if not engine:
            self.logger.warning("Trading Engine이 등록되지 않음")
            return self._create_empty_metrics()
            
        try:
            # 거래 통계 가져오기
            stats = engine.get_statistics() if hasattr(engine, 'get_statistics') else {}
            
            # PnL 계산
            trades = stats.get('trades', [])
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
            
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            total_pnl_percentage = sum(t.get('pnl_percentage', 0) for t in trades)
            
            # 평균 손익
            average_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
            average_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            # 최대 낙폭 계산
            max_drawdown = self._calculate_max_drawdown(trades)
            
            # 샤프 비율 계산
            sharpe_ratio = self._calculate_sharpe_ratio(trades)
            
            # 활성 포지션 수
            active_positions = stats.get('active_positions', 0)
            
            metrics = TradingMetrics(
                timestamp=datetime.now(),
                total_trades=len(trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                win_rate=len(winning_trades) / len(trades) * 100 if trades else 0,
                total_pnl=total_pnl,
                total_pnl_percentage=total_pnl_percentage,
                average_win=average_win,
                average_loss=average_loss,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                active_positions=active_positions
            )
            
            # 메트릭 저장
            self.metrics_history.append(metrics)
            await self._save_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"메트릭 수집 중 오류: {e}")
            return self._create_empty_metrics()
            
    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """최대 낙폭 계산"""
        if not trades:
            return 0.0
            
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in sorted(trades, key=lambda x: x.get('timestamp', '')):
            cumulative_pnl += trade.get('pnl', 0)
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            else:
                drawdown = (peak - cumulative_pnl) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
                
        return max_drawdown
        
    def _calculate_sharpe_ratio(self, trades: List[Dict], risk_free_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        if len(trades) < 2:
            return 0.0
            
        returns = [t.get('pnl_percentage', 0) / 100 for t in trades]
        
        if not returns:
            return 0.0
            
        # 연간화된 수익률과 표준편차 계산
        avg_return = sum(returns) / len(returns)
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_dev == 0:
            return 0.0
            
        # 샤프 비율 계산 (일일 거래 기준으로 연간화)
        annualized_return = avg_return * 252  # 거래일 기준
        annualized_std = std_dev * (252 ** 0.5)
        
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std
        
        return round(sharpe_ratio, 2)
        
    def _create_empty_metrics(self) -> TradingMetrics:
        """빈 메트릭 생성"""
        return TradingMetrics(
            timestamp=datetime.now(),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_pnl_percentage=0.0,
            average_win=0.0,
            average_loss=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            active_positions=0
        )
        
    async def _save_metrics(self, metrics: TradingMetrics):
        """메트릭 파일로 저장"""
        try:
            # 일별 파일로 저장
            date_str = metrics.timestamp.strftime("%Y%m%d")
            file_path = self.data_dir / f"metrics_{date_str}.json"
            
            # 기존 데이터 로드
            existing_data = []
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
                    
            # 새 메트릭 추가
            existing_data.append(metrics.to_dict())
            
            # 저장
            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"메트릭 저장 실패: {e}")
            
    async def get_daily_report(self) -> str:
        """일일 리포트 생성"""
        try:
            # 오늘 메트릭 로드
            today = datetime.now().date()
            date_str = today.strftime("%Y%m%d")
            file_path = self.data_dir / f"metrics_{date_str}.json"
            
            if not file_path.exists():
                return "오늘의 거래 데이터가 없습니다."
                
            with open(file_path, 'r') as f:
                today_metrics = json.load(f)
                
            if not today_metrics:
                return "오늘의 거래 데이터가 없습니다."
                
            # 최신 메트릭
            latest = today_metrics[-1]
            
            report = f"""
📊 일일 거래 리포트 ({today})

총 거래: {latest['total_trades']}건
승률: {latest['win_rate']:.1f}%
수익 거래: {latest['winning_trades']}건
손실 거래: {latest['losing_trades']}건

💰 손익 현황
총 손익: ${latest['total_pnl']:.2f} ({latest['total_pnl_percentage']:.2f}%)
평균 수익: ${latest['average_win']:.2f}
평균 손실: ${latest['average_loss']:.2f}

📈 성과 지표
최대 낙폭: {latest['max_drawdown']:.2f}%
샤프 비율: {latest['sharpe_ratio']:.2f}
활성 포지션: {latest['active_positions']}개
"""
            
            return report
            
        except Exception as e:
            self.logger.error(f"일일 리포트 생성 실패: {e}")
            return f"일일 리포트 생성 중 오류 발생: {str(e)}"
            
    async def get_weekly_report(self) -> str:
        """주간 리포트 생성"""
        try:
            # 지난 7일간의 메트릭 수집
            all_metrics = []
            today = datetime.now().date()
            
            for i in range(7):
                date = today - timedelta(days=i)
                date_str = date.strftime("%Y%m%d")
                file_path = self.data_dir / f"metrics_{date_str}.json"
                
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        daily_metrics = json.load(f)
                        all_metrics.extend(daily_metrics)
                        
            if not all_metrics:
                return "주간 거래 데이터가 없습니다."
                
            # 주간 통계 계산
            total_trades = sum(m['total_trades'] for m in all_metrics)
            total_winning = sum(m['winning_trades'] for m in all_metrics)
            total_losing = sum(m['losing_trades'] for m in all_metrics)
            total_pnl = sum(m['total_pnl'] for m in all_metrics)
            
            win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
            
            report = f"""
📊 주간 거래 리포트 ({(today - timedelta(days=6)).strftime('%Y.%m.%d')} ~ {today.strftime('%Y.%m.%d')})

총 거래: {total_trades}건
승률: {win_rate:.1f}%
수익 거래: {total_winning}건
손실 거래: {total_losing}건

💰 주간 총 손익: ${total_pnl:.2f}

일별 성과:
"""
            
            # 일별 성과 추가
            daily_summary = {}
            for metric in all_metrics:
                date = datetime.fromisoformat(metric['timestamp']).date()
                if date not in daily_summary:
                    daily_summary[date] = {'trades': 0, 'pnl': 0}
                daily_summary[date]['trades'] += metric['total_trades']
                daily_summary[date]['pnl'] += metric['total_pnl']
                
            for date in sorted(daily_summary.keys(), reverse=True):
                report += f"\n{date}: {daily_summary[date]['trades']}건, ${daily_summary[date]['pnl']:.2f}"
                
            return report
            
        except Exception as e:
            self.logger.error(f"주간 리포트 생성 실패: {e}")
            return f"주간 리포트 생성 중 오류 발생: {str(e)}"