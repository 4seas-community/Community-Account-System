# Community Account System (CAS)

Community Account System, open source.

4Seas 生态的统一账户与资产层:邮箱注册与验证、Telegram 绑定、服务密钥、积分账本(append-only)、活动签到令牌(一次性领取网址 + HMAC 签名)、NFT 领取登记(V2 占位)。业务系统(CommunityOS、booking、coliving 等)只通过接口消费 CAS,不自建账户。

接口需求文档(由 CommunityOS 项目提出):见 4Seas-CommunityOS 仓库 docs/06-community-account-system.md。

## 功能

| 模块 | 端点 | 说明 |
| --- | --- | --- |
| 账户 | POST /v1/auth/register, /verify-email, /login/request, /login/verify, /logout | 邮箱注册;验证 token 24h 一次性;登录为 magic link(token 15min 一次性);JWT 会话 |
| 我的 | GET/PATCH /v1/me; POST/DELETE /v1/me/telegram | 资料;Telegram initData 官方算法验签绑定 |
| 服务密钥 | POST/DELETE /v1/service-keys | Admin key 管理;secret 仅返回一次,库中只存 SHA-256;按 scope 鉴权 |
| 用户 | GET /v1/users/{id} | scope: users:read |
| 积分 | GET /v1/users/{id}/points; POST .../points/adjust; GET /v1/points/ledger | append-only 流水;余额 = sum(delta);扣减不足返回 422;seq 游标分页 |
| 签到 | POST /v1/checkin/tokens, /claim; GET /tokens/{id}; POST /tokens/{id}/nft-claim | 一次性 claim_url(event_url + ck + sig);重放 409、过期 410、坏签名 401 |
| Webhooks | POST /v1/webhooks/subscriptions | CAS 到业务系统推送(user.verified / user.updated / points.changed / telegram.bound),X-CAS-Signature = HMAC-SHA256(secret, body),指数退避重试 |
| 运维 | GET /healthz; /docs | OpenAPI 文档 |

安全要点:token/密钥不明文落库;所有账户、积分、签到、密钥变更写 audit_logs。

## Quickstart(本地)

    git clone git@github.com:4seas-community/Community-Account-System.git
    cd Community-Account-System
    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    cp .env.example .env
    .venv/bin/alembic upgrade head
    .venv/bin/uvicorn app.main:app --reload --port 8000

开发默认 SQLite;生产用 PostgreSQL:DATABASE_URL=postgresql+psycopg://user:pass@host:5432/cas。

邮件默认 console 后端(验证链接打进日志);生产设置 EMAIL_BACKEND=smtp 并配置 SMTP_*。

Telegram 绑定需要设置 TELEGRAM_BOT_TOKEN(与 4Seas Bot 同一个 bot);为空时仅限本地开发。

## Docker

    docker compose up --build
    # API: http://localhost:8000  文档: http://localhost:8000/docs

## 测试

    .venv/bin/pytest -q      # 23 个测试:认证全流程、token 一次性/过期、Telegram 验签、
                             # service key scope/吊销、积分扣减与流水、签到重放/过期/坏签名、webhook 签名
    .venv/bin/ruff check .   # lint

## 目录结构

    app/
      main.py            FastAPI 入口、统一错误格式
      config.py          pydantic-settings 配置
      db.py              SQLAlchemy engine/session/Base
      security.py        token 哈希、JWT、HMAC 签名、naive-UTC 时间
      models.py          users / tokens / service_keys / points_entries / checkin_tokens /
                         webhook_subscriptions / webhook_deliveries / audit_logs
      schemas.py         Pydantic 模型
      deps.py            用户态 / 服务态 / admin 认证依赖
      audit.py           审计写入
      email_backend.py   console / smtp
      api/               路由(auth, me, service_keys, users, points, checkin, webhooks)
      services/          auth_service, points_service, checkin_service, telegram, webhook_service
    alembic/             迁移
    tests/               pytest 套件

## Roadmap

- M1(已交付):账户 + service keys + 积分账本 + 签到令牌 + webhooks + Docker
- V2:链上积分(SIWE 钱包绑定、链上权威同步)、NFT claim 对接外部 NFT 系统、多账本

详见 4Seas-CommunityOS docs/06 与 docs/07。

## License

Apache-2.0
