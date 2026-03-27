# LLM-TradeBot Docker 部署指南

## 快速开始

### 1. 准备环境变量

```bash
# 复制环境变量示例文件
cp docker/.env.docker.example .env.docker

# 编辑并填入你的 API 密钥
vim .env.docker
```

### 2. 启动服务

```bash
# 仅启动主应用
docker-compose --env-file .env.docker up -d

# 启动应用 + Redis
docker-compose --env-file .env.docker up -d

# 查看日志
docker-compose --env-file .env.docker logs -f
```

### 3. 访问

- Web Dashboard: http://localhost:8000
- 登录密码: admin123 (可在 .env.docker 中修改)

## 停止服务

```bash
docker-compose --env-file .env.docker down
```

## 完全清理 (包括数据)

```bash
docker-compose --env-file .env.docker down -v
```

## 服务架构

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                 │
│                                                 │
│   ┌──────────────────┐    ┌───────────────┐   │
│   │  llm-tradebot   │    │     redis     │   │
│   │   (Port 8000)   │◄──►│   (Port 6379) │   │
│   └──────────────────┘    └───────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
         │
         │ curl -f http://localhost:8000
         ▼
    ┌─────────────────┐
    │   Your Browser  │
    └─────────────────┘
```

## 配置说明

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `BINANCE_API_KEY` | 是 | - | Binance API Key |
| `BINANCE_SECRET_KEY` | 是 | - | Binance Secret Key |
| `BINANCE_TESTNET` | 否 | `true` | 是否使用测试网 |
| `LLM_PROVIDER` | 否 | `minimax` | LLM 提供商 |
| `MINIMAX_API_KEY` | 是* | - | MiniMax API Key (*使用 minimax 时必填) |
| `DEEPSEEK_API_KEY` | 是* | - | DeepSeek API Key |
| `TRADING_SYMBOLS` | 否 | `BTCUSDT,ETHUSDT,SOLUSDT` | 交易币种 |
| `WEB_PASSWORD` | 否 | `admin123` | Dashboard 密码 |

### LLM 提供商选项

- `minimax` - MiniMax (默认，推荐)
- `deepseek` - DeepSeek
- `openai` - OpenAI GPT
- `claude` - Claude
- `qwen` - 通义千问
- `gemini` - Google Gemini
- `kimi` - Kimi/Moonshot
- `glm` - 智谱 GLM

## 数据持久化

以下目录通过 Docker Volume 持久化：

| 主机目录 | 容器目录 | 说明 |
|----------|----------|------|
| `./data` | `/app/data` | K线数据、持仓、交易记录 |
| `./logs` | `/app/logs` | 日志文件 |
| `./models` | `/app/models` | ML 模型文件 |
| `redis_data` (named volume) | `/data` | Redis 数据 |

## 生产环境部署

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### HTTPS 配置 (使用 Let's Encrypt)

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 系统服务 (systemd)

创建 `/etc/systemd/system/llm-tradebot.service`:

```ini
[Unit]
Description=LLM-TradeBot Docker Container
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/docker-compose --env-file /opt/llm-tradebot/.env.docker -f /opt/llm-tradebot/docker-compose.yml up -d
ExecStop=/usr/local/bin/docker-compose --env-file /opt/llm-tradebot/.env.docker -f /opt/llm-tradebot/docker-compose.yml down
WorkingDirectory=/opt/llm-tradebot
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

启用服务:

```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-tradebot
sudo systemctl start llm-tradebot
```

## 故障排查

### 查看容器状态

```bash
docker-compose ps
```

### 查看应用日志

```bash
docker-compose logs -f llm-tradebot
```

### 进入容器调试

```bash
docker exec -it llm-tradebot bash
```

### 检查端口占用

```bash
lsof -i :8000
lsof -i :6379
```

### 重建镜像

```bash
docker-compose build --no-cache --env-file .env.docker
docker-compose up -d
```
