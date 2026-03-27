"""
Binance WebSocket Manager
管理 WebSocket 连接并维护实时 K 线缓存
"""
import threading
import time
from collections import deque
from typing import Dict, List, Callable, Optional
from binance import ThreadedWebsocketManager
from src.utils.logger import log


class BinanceWebSocketManager:
    """
    Binance WebSocket 管理器
    
    功能:
    1. 订阅多个时间周期的 K 线流 (5m, 15m, 1h)
    2. 维护线程安全的 K 线缓存
    3. 自动重连
    """
    
    def __init__(self, symbol: str, timeframes: List[str], cache_size: int = 500):
        """
        初始化 WebSocket 管理器
        
        Args:
            symbol: 交易对 (如 'BTCUSDT')
            timeframes: 时间周期列表 (如 ['5m', '15m', '1h'])
            cache_size: 每个时间周期缓存的 K 线数量
        """
        self.symbol = symbol.upper()
        self.timeframes = timeframes
        self.cache_size = cache_size
        
        # K 线缓存: {timeframe: deque([kline_dict, ...])}
        self.kline_cache: Dict[str, deque] = {
            tf: deque(maxlen=cache_size) for tf in timeframes
        }
        
        # 线程锁，保证缓存访问安全
        self._cache_lock = threading.Lock()
        
        # WebSocket 管理器
        self.ws_manager: Optional[ThreadedWebsocketManager] = None
        self._is_running = False
        
        log.info(f"WebSocket Manager 初始化: {symbol} | 周期: {timeframes}")
    
    def start(self):
        """启动 WebSocket 连接"""
        if self._is_running:
            log.warning("WebSocket 已经在运行中")
            return
        
        try:
            self.ws_manager = ThreadedWebsocketManager()
            self.ws_manager.start()
            
            # 订阅各个时间周期的 K 线流
            for timeframe in self.timeframes:
                stream_name = f"{self.symbol.lower()}@kline_{timeframe}"
                
                self.ws_manager.start_kline_socket(
                    callback=self._handle_kline_message,
                    symbol=self.symbol,
                    interval=timeframe
                )
                
                log.info(f"✅ 订阅 WebSocket 流: {stream_name}")
            
            self._is_running = True
            log.info(f"🚀 WebSocket Manager 启动成功: {self.symbol}")
            
        except RuntimeError as e:
            # Re-raise event loop conflicts so caller can handle fallback
            if "event loop" in str(e).lower():
                log.warning(f"⚠️ WebSocket 事件循环冲突: {e}")
                self.stop()
                raise
            log.error(f"❌ WebSocket 启动失败: {e}")
            self.stop()
        except Exception as e:
            log.error(f"❌ WebSocket 启动失败: {e}")
            self.stop()
    
    def _handle_kline_message(self, msg: dict):
        """
        处理 WebSocket K 线消息
        
        消息格式:
        {
            'e': 'kline',
            'E': 1640000000000,
            's': 'BTCUSDT',
            'k': {
                't': 1640000000000,  # 开盘时间
                'T': 1640000300000,  # 收盘时间
                's': 'BTCUSDT',
                'i': '5m',           # 时间周期
                'o': '50000.00',     # 开盘价
                'c': '50100.00',     # 收盘价
                'h': '50200.00',     # 最高价
                'l': '49900.00',     # 最低价
                'v': '100.5',        # 成交量
                'x': False           # 是否完成
            }
        }
        """
        try:
            if msg.get('e') != 'kline':
                return
            
            kline = msg['k']
            timeframe = kline['i']
            is_closed = kline['x']  # K 线是否已完成
            
            # 转换为标准格式 (与 REST API 一致)
            kline_data = {
                'timestamp': kline['t'],     # 开盘时间 (毫秒时间戳)
                'open_time': kline['t'],     # 保持对旧代码的兼容性
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
                'close_time': kline['T'],
                'is_closed': is_closed
            }
            
            # 更新缓存 (线程安全)
            with self._cache_lock:
                cache = self.kline_cache[timeframe]
                
                if cache and cache[-1]['timestamp'] == kline_data['timestamp']:
                    # 如果时间戳相同，无论是否已完成，都直接更新（覆盖旧数据或更新未完成数据）
                    cache[-1] = kline_data
                    if is_closed:
                        log.debug(f"📊 K 线已关闭: {self.symbol} {timeframe} | Close: {kline_data['close']}")
                else:
                    # 如果是新时间戳，追加到缓存
                    cache.append(kline_data)
                    if is_closed:
                        log.debug(f"📊 新 K 线开启且已完成: {self.symbol} {timeframe}")
                        
        except Exception as e:
            log.error(f"处理 WebSocket 消息失败: {e}")
    
    def get_klines(self, timeframe: str, limit: int = 300) -> List[Dict]:
        """
        获取缓存的 K 线数据
        
        Args:
            timeframe: 时间周期 ('5m', '15m', '1h')
            limit: 返回的 K 线数量
            
        Returns:
            K 线数据列表 (按时间升序)
        """
        with self._cache_lock:
            cache = self.kline_cache.get(timeframe, deque())
            # 返回最近 N 根 K 线
            return list(cache)[-limit:] if cache else []
    
    def get_cache_size(self, timeframe: str) -> int:
        """获取指定时间周期的缓存大小"""
        with self._cache_lock:
            return len(self.kline_cache.get(timeframe, deque()))
    
    def is_running(self) -> bool:
        """检查 WebSocket 是否正在运行"""
        return self._is_running and self.ws_manager is not None
    
    def is_ready(self, timeframe: str, min_klines: int = 100) -> bool:
        """
        检查缓存是否已准备好
        
        Args:
            timeframe: 时间周期
            min_klines: 最小 K 线数量
            
        Returns:
            True if cache has enough data
        """
        return self.get_cache_size(timeframe) >= min_klines
    
    def restart(self):
        """重启 WebSocket 连接（用于断线重连）"""
        log.info(f"🔄 重启 WebSocket: {self.symbol}")
        self.stop()
        time.sleep(1)  # 等待资源释放
        self.start()
    
    def stop(self):
        """停止 WebSocket 连接"""
        if not self._is_running:
            return
        
        try:
            if self.ws_manager:
                self.ws_manager.stop()
                log.info("🛑 WebSocket Manager 已停止")
            
            self._is_running = False
            
        except Exception as e:
            log.error(f"停止 WebSocket 失败: {e}")
    
    def __del__(self):
        """析构函数，确保资源释放"""
        self.stop()


# 测试代码
if __name__ == "__main__":
    import time
    
    # 创建 WebSocket 管理器
    ws_manager = BinanceWebSocketManager(
        symbol="BTCUSDT",
        timeframes=['5m', '15m', '1h']
    )
    
    # 启动
    ws_manager.start()
    
    # 等待数据积累
    print("等待 WebSocket 数据...")
    time.sleep(10)
    
    # 检查缓存
    for tf in ['5m', '15m', '1h']:
        klines = ws_manager.get_klines(tf, limit=5)
        print(f"\n{tf} K线缓存: {len(klines)} 根")
        if klines:
            latest = klines[-1]
            print(f"最新价格: {latest['close']}")
    
    # 停止
    ws_manager.stop()
