"""
日志工具模块 - 增强版，支持彩色输出和 LLM 专用日志
"""
import sys
import json
from pathlib import Path
from loguru import logger
from src.config import config
from src.utils.action_protocol import normalize_action, is_close_action


class ColoredLogger:
    """彩色日志包装器"""
    
    def __init__(self, logger_instance):
        self._logger = logger_instance
    
    def __getattr__(self, name):
        """转发其他方法到原始 logger"""
        return getattr(self._logger, name)
    
    def llm_input(self, message: str, context: str = None):
        """记录 LLM 输入（青色背景）"""
        # 清理 XML 标签避免 rich 解析错误
        def clean_text(text):
            import re
            text = re.sub(r'<think[\s>][^<]*</think>', '', text, flags=re.DOTALL)
            text = re.sub(r'</?[a-zA-Z][^>]*>', '', text)
            return text
        
        self._logger.opt(colors=True).info(
            f"<bold><cyan>{'=' * 60}</cyan></bold>\n"
            f"<bold><cyan>🤖 LLM 输入</cyan></bold>\n"
            f"<bold><cyan>{'=' * 60}</cyan></bold>"
        )
        if context:
            # 截断过长的上下文
            if len(context) > 5000:
                display_context = context[:2000] + "\n... (省略中间部分) ...\n" + context[-2000:]
            else:
                display_context = context
            display_context = clean_text(display_context)
            self._logger.opt(colors=True).info(f"<cyan>{display_context}</cyan>")
        self._logger.opt(colors=True).info(f"<bold><cyan>{'=' * 60}</cyan></bold>\n")
    
    def llm_output(self, message: str, decision: dict = None):
        """记录 LLM 输出（浅黄色背景）"""
        from src.utils.json_utils import safe_json_dumps
        self._logger.opt(colors=True).info(
            f"<bold><light-yellow>{'=' * 60}</light-yellow></bold>\n"
            f"<bold><light-yellow>🧠 LLM 输出</light-yellow></bold>\n"
            f"<bold><light-yellow>{'=' * 60}</light-yellow></bold>"
        )
        if decision:
            formatted_json = safe_json_dumps(decision, indent=2, ensure_ascii=False)
            self._logger.opt(colors=True).info(f"<light-yellow>{formatted_json}</light-yellow>")
        self._logger.opt(colors=True).info(f"<bold><light-yellow>{'=' * 60}</light-yellow></bold>\n")
    
    def llm_decision(self, action: str, confidence: int, reasoning: str = None):
        """记录 LLM 决策（浅色调高亮）"""
        norm_action = normalize_action(action)
        if norm_action == 'open_long':
            color = 'light-green'
        elif norm_action == 'open_short':
            color = 'light-red'
        elif is_close_action(norm_action):
            color = 'light-yellow'
        elif norm_action in ('hold', 'wait'):
            color = 'light-blue'
        else:
            color = 'white'
        
        self._logger.opt(colors=True).info(
            f"<bold><{color}>{'=' * 60}</{color}></bold>\n"
            f"<bold><{color}>📊 交易决策</{color}></bold>\n"
            f"<bold><{color}>{'=' * 60}</{color}></bold>\n"
            f"<bold><{color}>动作: {action.upper()}</{color}></bold>\n"
            f"<bold><{color}>置信度: {confidence}%</{color}></bold>"
        )
        if reasoning:
            # 截断过长的理由
            if len(reasoning) > 500:
                display_reasoning = reasoning[:500] + "..."
            else:
                display_reasoning = reasoning
            self._logger.opt(colors=True).info(
                f"<{color}>理由: {display_reasoning}</{color}>"
            )
        self._logger.opt(colors=True).info(
            f"<bold><{color}>{'=' * 60}</{color}></bold>\n"
        )
    
    def risk_alert(self, message: str):
        """记录风险警报（浅红色）"""
        self._logger.opt(colors=True).warning(
            f"<bold><light-red>⚠️  风险警报: {message}</light-red></bold>"
        )
    
    # === AIF 语义化日志方法 (Adversarial Intelligence Framework) ===
    
    def oracle(self, message: str):
        """[THE ORACLE] 记录数据采样日志 (蓝色)"""
        self._logger.opt(colors=True).info(f"<blue>🕵️ [Oracle] {message}</blue>")
        
    def strategist(self, message: str):
        """[THE STRATEGIST] 记录策略假设日志 (紫色)"""
        self._logger.opt(colors=True).info(f"<magenta>👨‍🔬 [Strategist] {message}</magenta>")
        
    def critic(self, message: str, challenge: bool = False):
        """[THE CRITIC] 记录对抗审计日志 (橙色)"""
        icon = "⚖️" if not challenge else "⚔️"
        color = "yellow" if not challenge else "red"
        self._logger.opt(colors=True).info(f"<{color}>{icon} [Critic] {message}</{color}>")
        
    def guardian(self, message: str, blocked: bool = False):
        """[THE GUARDIAN] 记录风控审计日志 (绿色/红色)"""
        icon = "👮" if not blocked else "🚫"
        color = "green" if not blocked else "light-red"
        self._logger.opt(colors=True).info(f"<{color}>{icon} [Guardian] {message}</{color}>")
        
    def executor(self, message: str, success: bool = True):
        """[THE EXECUTOR] 记录执行指挥日志 (高亮)"""
        icon = "🚀" if success else "❌"
        color = "light-green" if success else "light-red"
        self._logger.opt(colors=True).info(f"<bold><{color}>{icon} [Executor] {message}</{color}></bold>")

    # 兼容性别名 (Alias for consistency)
    market_data = oracle
    trade_execution = executor


def setup_logger():
    """配置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出 - 启用彩色
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=config.logging.get('level', 'INFO'),
        colorize=True
    )
    
    # 文件输出 - 不使用彩色代码
    # 使用日期子目录: logs/YYYY-MM-DD/trading.log
    log_file = config.logging.get('file', 'logs/trading.log')
    log_path = Path(log_file)
    # 1. Dashboard Log (Clean) -> trading.log
    # 动态生成带日期的路径格式
    dynamic_log_file = str(log_path.parent / "{time:YYYY-MM-DD}" / log_path.name)
    
    logger.add(
        dynamic_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} {message}", 
        filter=lambda record: record["extra"].get("dashboard") is True,
        level="INFO",
        rotation="00:00",
        retention="30 days",
        compression="zip"
    )

    # 2. System Debug Log (Verbose) -> debug.log
    debug_log_file = str(log_path.parent / "{time:YYYY-MM-DD}" / "debug.log")
    logger.add(
        debug_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
        compression="zip"
    )
    
    return ColoredLogger(logger)


# 全局logger实例
log = setup_logger()
