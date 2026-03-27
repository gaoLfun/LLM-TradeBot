"""
外部量化输出 API 接入层
支持: Netflow (机构/个人), OI (Binance/ByBit), Price Change

注意: NOFX API 已迁移到 nofxos.ai (原 nofxaios.com:30006 已弃用)
"""
import os
import requests
from typing import Dict
from src.utils.logger import log

class QuantClient:
    """外部量化 API 客户端"""
    
    # NOFX API 新地址 (2026年迁移到 nofxos.ai)
    BASE_URL = "https://nofxos.ai/api"
    
    @property
    def auth_token(self) -> str:
        """从环境变量动态获取最新的认证令牌"""
        token = os.getenv('QUANT_AUTH_TOKEN', '')
        if not token:
            log.warning("QUANT_AUTH_TOKEN not set in environment, quant API calls may fail")
        return token

    def fetch_coin_data(self, symbol: str = "BTCUSDT") -> Dict:
        """
        获取指定币种的量化深度数据
        """
        clean_symbol = symbol.replace("USDT", "USDT")  # 兼容性处理
        url = f"{self.BASE_URL}/coin/{clean_symbol}?include=netflow,oi,price&auth={self.auth_token}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", {})
            if response.status_code == 401:
                log.error("Quant API 鉴权失败(401): 请检查 QUANT_AUTH_TOKEN 环境变量是否正确设置")
            else:
                log.error(f"Quant API 请求失败: {response.status_code}")
            return {}
        except Exception as e:
            log.error(f"Quant API 异常: {e}")
            return {}

    def fetch_ai500_list(self) -> Dict:
        """
        获取 AI500 优质币池列表
        """
        url = f"{self.BASE_URL}/ai500/list?auth={self.auth_token}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", [])
            log.error(f"AI500 List 请求失败: {response.status_code}")
            return []
        except Exception as e:
            log.error(f"AI500 API 异常: {e}")
            return []

    def fetch_oi_ranking(self, ranking_type: str = 'top', limit: int = 20, duration: str = '1h') -> Dict:
        """
        获取 OI 排行榜
        
        Args:
            ranking_type: 'top' (涨幅榜) 或 'low' (跌幅榜)
            limit: 返回数量
            duration: 时间周期 (1h, 4h, 24h)
        """
        endpoint = "top-ranking" if ranking_type == 'top' else "low-ranking"
        url = f"{self.BASE_URL}/oi/{endpoint}?limit={limit}&duration={duration}&auth={self.auth_token}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", [])
            log.error(f"OI Ranking 请求失败: {response.status_code}")
            return []
        except Exception as e:
            log.error(f"OI Ranking API 异常: {e}")
            return []

# 全局单例
quant_client = QuantClient()
