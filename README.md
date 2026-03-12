# 简化版在线聊天应用后端

## 项目简介
该项目提供一个简化版在线聊天后端服务，目标是实现类似 chatgpt.com 的基础交互体验，包含多用户登录、个人对话、多轮问答、对话标签、AI 模拟回复，以及多用户多机器人参与的群组对话功能。

## 技术选型
- Python 3.11
- FastAPI 0.111.0
- Next.js: 15.0.3
- React: 18.3.1
- SQLAlchemy 2.0
- SQLite（默认）
- JWT 认证（python-jose）
- bcrypt 密码哈希（passlib）

## 目录结构
- `backend/app/main.py`：API 路由与核心业务逻辑 # 项目目录结构如下，包含后端应用和前端资源：
- `backend/app/models.py`：数据库模型
- `backend/app/schemas.py`：请求/响应数据结构
- `backend/app/auth.py`：认证与密码哈希
- `backend/app/ai_client.py`：AI 模拟调用
- `backend/app/config.py`：配置项 # 配置管理
- `backend/requirements.txt`：依赖列表
- `frontend/index.html`：前端交互页面
- `Dockerfile` / `docker-compose.yml`：部署配置
- `.env.example`：环境变量示例

## 本地启动
1. 创建虚拟环境并安装依赖：
   - `python3.11 -m venv .venv`
   - `./.venv/Scripts/activate`
   - `pip install -r backend/requirements.txt`
2. 启动服务：
   - `uvicorn backend.app.main:app --reload`
3. 打开页面：
   - `http://127.0.0.1:3000/` # 访问前端页面
4. 打开 API 文档：
   - `http://127.0.0.1:8000/docs` # 访问Swagger UI API文档页面

5. 前端安装运行
   - `cd frontend`  #访问目录
   - `npm install`  #安装依赖
   -  `npm run dev`  #运行前端代码
6. 打开前端页面
   - ` http://localhost:3000`

默认数据库文件生成在 `backend/app.db`。 # SQLite数据库文件默认位置

## 前端功能
前端页面支持：
- 注册 / 登录
- 创建对话、编辑标题与标签、删除对话
- 发送个人消息与查看历史消息
- 创建群组、添加成员
- 发送群组消息与查看历史消息

## API 端点
### 认证
- POST `/auth/register` // 用户注册接口
- POST `/auth/login` // 用户登录接口

### 个人对话
- POST `/conversations` // 创建新对话
- GET `/conversations` // 获取对话列表
- PATCH `/conversations/{id}` // 更新指定对话
- DELETE `/conversations/{id}` // 删除指定对话

### 个人消息
- POST `/conversations/{id}/messages` // 创建会话消息的POST请求
- GET `/conversations/{id}/messages` // 获取会话消息的GET请求

### 机器人
- GET `/bots` //获取机器人列表 

### 群组
- POST `/groups`
- GET `/groups`
- GET `/groups/{id}`
- POST `/groups/{id}/members`
- DELETE `/groups/{id}/members/{user_id}`

### 群组消息
- POST `/groups/{id}/messages`
- GET `/groups/{id}/messages`

## 数据库设计要点
- `users`：用户账号
- `conversations`：个人对话
- `messages`：个人消息
- `tags`：用户标签
- `conversation_tags`：对话与标签多对多关联
- `groups`：群组
- `group_members`：群组成员
- `bots`：机器人角色
- `group_bots`：群组与机器人关联
- `group_messages`：群组消息



## 关键设计说明
### 对话标签
标签按用户隔离存储，使用 `(user_id, name)` 唯一约束，通过关联表实现多对多关系。



### 群组机器人交互逻辑
- 群组创建时必须包含至少一个机器人；若客户端自定义机器人为空，后端会自行创建机器人。
- 机器人回复采用关键词检索策略：先根据消息内容与机器人角色/设定匹配打分，优先选 1~N 个机器人回复（默认上限 2）。
- 当没有关键词命中时，会随机选择 1 个机器人回复，避免多机器人回答。
- 机器人只对人类消息响应，避免机器人间循环对话。
- 保证至少一个机器人回复。

### 用户安全
- 所有个人数据均按用户 ID 校验，确保数据隔离。
- 群组访问必须通过成员关系校验。
- SQL 注入由 SQLAlchemy 参数化查询规避。
- 密码使用 bcrypt 哈希存储。

## 配置
- `DATABASE_URL`：默认 `sqlite:///./app.db`
- `JWT_SECRET`：默认 `dev_secret_password`
- `JWT_EXPIRES_MINUTES`：默认 `120` // JWT令牌的有效期，单位为分钟，默认为2小时
- `AI_MAX_RETRIES`：默认 `2`
- `AI_REPLY_STRATEGY`：`all` 或 `random`
- `AI_MAX_GROUP_BOT_RESPONSES`：群组机器人单次最大回复数量，默认 `2`
- `SEED_USERS`：预置用户（格式 `user:pass,user2:pass2`）

## 示例测试账号
通过环境变量 `SEED_USERS` 预置，默认建议值：
- `test1 / test1234`
- `test2 / test1234`

## 部署方式（Docker）
1. 构建并启动：
   - `docker compose up --build`
2. 访问：
   - `http://127.0.0.1:8000/`





