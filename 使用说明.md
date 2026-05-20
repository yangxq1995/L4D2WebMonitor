# L4D2 服务器监控平台 - 使用说明

## 📋 项目简介

这是一个用于监控《求生之路2》(Left 4 Dead 2) 多级服务器状态的 Web 平台。

**主要功能**：
- 📊 实时监控多台 L4D2 服务器的状态（在线/离线）
- 👥 显示每个服务器的玩家列表、在线时间、延迟
- 🗺️ 自动识别当前地图并显示中文名称、章节信息
- 🔗 提供地图工坊链接，方便玩家下载
- 🔄 一键重置服务器（需要密码保护）
- 📈 统计在线玩家数、在线服务器数

**技术栈**：
- 后端：Python 3 + Flask
- 前端：HTML + CSS + JavaScript
- 通信协议：RCON (Remote Console)

---

## 🛠️ 环境准备

### 1. 安装 Python 3.8+

**Windows 用户**：
1. 访问 https://www.python.org/downloads/
2. 下载最新版 Python 3.x（例如 Python 3.12）
3. 运行安装程序，**务必勾选 "Add Python to PATH"**
4. 安装完成后，打开命令提示符（Win+R → 输入 `cmd`），验证安装：
   ```bash
   python --version
   # 或
   python3 --version
   ```
   应该显示类似 `Python 3.12.x`

**如果提示 "python 不是内部或外部命令"**：
- 重新安装 Python，确保勾选 "Add Python to PATH"
- 或手动添加 Python 安装目录到系统环境变量 PATH

### 2. 安装 Flask 框架

打开命令提示符，执行：
```bash
pip install flask
```

如果提示 "pip 不是内部或外部命令"，使用：
```bash
python -m pip install flask
```

验证安装：
```bash
python -c "import flask; print(flask.__version__)"
```

---

## 📁 项目文件结构

```
l4d2ServerMonitor/
├── config.cfg            # 核心配置文件（需要编辑）
├── serviceCore.py        # 后端主程序
├── index.html           # 前端页面
├── chaptersinfo.json    # 章节信息数据（自动加载）
├── mapsinfo.json       # 地图信息数据（自动加载）
└── 使用说明.md         # 本文件
```

---

## ⚙️ 配置文件说明（重要！）

`config.cfg` 是项目的核心配置文件，需要根据你的服务器情况修改。

### 配置文件示例

```ini
[rcon]
password = your_rcon_password_here

[admin]
password = your_admin_password_here

[app_debug]
enabled = false

[rate_limit]
max_requests = 120
window_seconds = 60

[server]
host = 0.0.0.0
port = 8080
debug = false

[server.1]
host = 192.168.1.100
cport = 27015
pport = 27016
comment = 主服务器

[server.2]
host = 192.168.1.101
cport = 27015
pport = 27016
comment = 备用服务器
enabled = true
```

### 配置项详细说明

#### 1. `[rcon]` 段 - RCON 密码
```ini
[rcon]
password = your_rcon_password_here
```
- **作用**：用于后端连接 L4D2 服务器的 RCON 端口
- **获取方式**：
  - 在 L4D2 服务器配置文件（`server.cfg`）中查找 `rcon_password`
  - 例如：`rcon_password "your_password"`
  - 将密码填入 `config.cfg` 的 `[rcon]` 段

#### 2. `[admin]` 段 - 管理员密码
```ini
[admin]
password = your_admin_password_here
```
- **作用**：用于 Web 界面执行重置服务器等操作时的密码验证
- **建议**：设置一个强密码，不要与 RCON 密码相同

#### 3. `[server]` 段 - Web 服务配置
```ini
[server]
host = 0.0.0.0
port = 8080
debug = false
```
- `host`：Web 服务监听地址
  - `0.0.0.0` = 监听所有网络接口（允许局域网访问）
  - `127.0.0.1` = 仅本地访问
- `port`：Web 服务端口（默认 8080）
- `debug`：是否开启调试模式（`true`/`false`）

#### 4. `[server.N]` 段 - L4D2 服务器列表
```ini
[server.1]
host = 192.168.1.100
cport = 27015
pport = 27016
comment = 主服务器
enabled = true
```
- `server.1`：`1` 是服务器 ID，可以任意整数，用于区分不同服务器
- `host`：L4D2 服务器 IP 地址
- `cport`：客户端连接端口（游戏内连接用）
- `pport`：RCON 端口（用于后端查询状态）
- `comment`：服务器备注名称（可选）
- `enabled`：是否启用该服务器（`true`/`false`，默认 `true`）

**如何添加更多服务器**：
- 复制 `[server.1]` 段，修改为 `[server.2]`、`[server.3]` 等
- 修改对应的 `host`、`cport`、`pport`

---

## 📊 数据文件说明

### 1. `chaptersinfo.json` - 章节信息

**作用**：存储地图章节代码与地图 ID 的对应关系

**格式示例**：
```json
[
  {
    "chapterCode": "c1m1_hotel",
    "mapID": "1001",
    "chapterOrder": 1
  },
  {
    "chapterCode": "c1m2_streets",
    "mapID": "1001",
    "chapterOrder": 2
  }
]
```

**如何获取**：
- 通常由地图作者或社区提供
- 可以根据 `mapID` 在 `mapsinfo.json` 中查找对应的地图信息

### 2. `mapsinfo.json` - 地图信息

**作用**：存储地图的详细信息（中文名、工坊 ID 等）

**格式示例**：
```json
[
  {
    "mapID": "1001",
    "mapNameCN": "死亡丧钟",
    "modID": "123456789",
    "gamemapsID": "abcd1234",
    "mapCoopChapterN": 5,
    "isValue": "0"
  }
]
```

**字段说明**：
- `mapID`：地图 ID（与 `chaptersinfo.json` 中的 `mapID` 对应）
- `mapNameCN`：地图中文名称
- `modID`：Steam 工坊 ID（用于生成下载链接）
- `gamemapsID`：GameMaps 网站 ID（备用下载链接）
- `mapCoopChapterN`：该地图的总章节数
- `isValue`：
  - `"0"` = 需要重置（地图已通关）
  - `"1"` = 不需要重置（地图未完成）

**如何获取**：
- 从 L4D2 社区或地图作者处获取
- 可以手动编辑添加新地图

---

## 🚀 启动项目

### 方法一：直接运行（推荐）

1. 打开命令提示符，切换到项目目录：
   ```bash
   cd /d G:\qClaw\l4d2ServerMonitor
   ```

2. 运行后端程序：
   ```bash
   python serviceCore.py
   ```

3. 看到类似以下输出表示启动成功：
   ```
   [L4D2] config.cfg 读取成功，编码: utf-8-sig
   [L4D2] 已加载 chaptersinfo.json，共 50 条记录
   [L4D2] 已加载 mapsinfo.json，共 30 条记录
   启动 L4D2 监控服务...
   ADMIN_PASSWORD 已加载，长度: 8
   访问 http://0.0.0.0:8080
   ```

4. 打开浏览器，访问：
   - 本地访问：http://127.0.0.1:8080
   - 局域网访问：http://你的IP地址:8080

### 方法二：作为后台服务运行（高级）

**Windows 用户**：
1. 创建启动脚本 `start.bat`：
   ```batch
   @echo off
   cd /d G:\qClaw\l4d2ServerMonitor
   python serviceCore.py
   pause
   ```

2. 双击 `start.bat` 运行

**Linux 用户**（如服务器在 Linux 上运行）：
1. 使用 `nohup` 后台运行：
   ```bash
   nohup python3 serviceCore.py > service.log 2>&1 &
   ```

2. 或使用 `systemd` 创建系统服务（推荐生产环境）

---

## 💡 使用指南

### 1. 查看服务器状态

- 打开浏览器访问 Web 界面
- 服务器卡片会显示：
  - 🟢 在线（绿色边框）
  - 🔴 离线（红色边框，脉冲动画）
- 自动刷新：
  - 在线服务器：每 60 秒刷新一次
  - 离线服务器：每 10 秒重试一次

### 2. 查看玩家列表

- 每个服务器卡片下方显示当前玩家列表
- 显示信息：
  - 玩家名称
  - 在线时间（分钟）
  - 延迟（ms）
  - BOT 玩家会标记 `[BOT]`

### 3. 加入服务器

- 点击 "加入服务器" 按钮
- 会自动调用 Steam 协议打开 L4D2 并连接到服务器
- 如果服务器满员，按钮会显示 "人数已满"

### 4. 重置服务器

**场景一：无玩家（快速重置）**
1. 点击 "重置服务器" 按钮
2. 系统检测到无真人玩家，自动执行 `map c1m1` 重置
3. 等待 6 秒后自动刷新状态

**场景二：有玩家（需要密码）**
1. 点击 "重置服务器" 按钮
2. 弹出密码对话框
3. 输入 RCON 指令（留空则执行 `map c1m1`）
4. 输入管理员密码（`config.cfg` 中 `[admin]` 段的 `password`）
5. 点击 "执行指令"
6. 等待 6 秒后自动刷新状态

**⚠️ 安全提示**：
- 连续 3 次密码错误会锁定 1 分钟
- 请在可信网络环境下使用

---

## 🔧 常见问题

### Q1：启动后无法访问 Web 界面

**可能原因**：
1. 端口被占用
   - 修改 `config.cfg` 中的 `[server]` 段 `port` 为其他端口（如 8081）
2. 防火墙阻止
   - Windows 防火墙：允许 Python 通过防火墙
   - 云服务器：在安全组中开放对应端口

### Q2：显示 "服务器离线或无法访问"

**可能原因**：
1. RCON 密码错误
   - 检查 `config.cfg` 中 `[rcon]` 段的 `password` 是否正确
2. 服务器 IP/端口错误
   - 检查 `config.cfg` 中 `[server.N]` 段的 `host` 和 `pport`
   - 确保 L4D2 服务器已启动 RCON（`server.cfg` 中设置了 `rcon_password`）
3. 网络不通
   - 在命令行执行 `telnet 服务器IP RCON端口` 测试连通性
   - 例如：`telnet 192.168.1.100 27016`

### Q3：地图名称显示为 "获取中..." 或 "-"

**可能原因**：
1. 服务器响应慢
   - 等待片刻，自动刷新后会更新
2. `chaptersinfo.json` 或 `mapsinfo.json` 数据不完整
   - 检查这两个文件是否存在
   - 确保 JSON 格式正确（可以用 JSON 校验工具检查）

### Q4：点击 "加入服务器" 无反应

**可能原因**：
1. 未安装 Steam 或 L4D2
   - 需要确保 Steam 客户端已安装并登录
2. 浏览器阻止了 `steam://` 协议
   - 允许浏览器打开 Steam 链接

### Q5：重置服务器失败，提示 "密码错误"

**解决方法**：
1. 检查 `config.cfg` 中 `[admin]` 段的 `password` 是否正确
2. 注意区分：
   - `[rcon]` 段密码 = RCON 密码（用于连接服务器）
   - `[admin]` 段密码 = 管理员密码（用于 Web 界面操作）

### Q6：如何修改刷新频率

编辑 `index.html`，找到以下常量（约第 344 行）：
```javascript
const REFRESH_INTERVAL_ONLINE = 60000;   // 在线服务器刷新间隔 60s
const REFRESH_INTERVAL_OFFLINE = 10000;  // 离线服务器重试间隔 10s
const UI_CHECK_INTERVAL = 3000;          // UI 检查间隔 3s
```
- 修改数值（单位：毫秒）
- 保存后刷新浏览器

---

## 📝 高级配置

### 1. 启用调试模式

编辑 `config.cfg`：
```ini
[app_debug]
enabled = true

[server]
debug = true
```
- 会显示详细的调试信息（包括 RCON 原始响应）
- **生产环境请关闭**

### 2. 限制访问频率

编辑 `config.cfg`：
```ini
[rate_limit]
max_requests = 120
window_seconds = 60
```
- 限制每个 IP 每 60 秒最多 120 次请求
- 防止恶意攻击

### 3. 自定义前端样式

编辑 `index.html`，修改 `<style>` 标签内的 CSS 变量（约第 21 行）：
```css
:root {
    --color-online: #4CAF50;    /* 在线颜色 */
    --color-offline: #f44336;   /* 离线颜色 */
    --color-warning: #FF9800;   /* 警告颜色 */
    /* 更多变量... */
}
```

---

## 🆘 获取帮助

如果遇到无法解决的问题，可以：
1. 查看命令行输出的错误信息
2. 检查 `config.cfg` 配置是否正确
3. 确保 `chaptersinfo.json` 和 `mapsinfo.json` 格式正确
4. 联系项目维护者

---

## 📃 更新日志

### v2.0（当前版本）
- ✅ 重构前端代码，提高可读性和可维护性
- ✅ 优化后端逻辑，消除重复代码
- ✅ 使用 CSS 变量统一管理样式
- ✅ 提取常量，方便配置
- ✅ 改进错误处理和日志输出

### v1.0（初始版本）
- 实现基本的服务器监控功能
- 支持 RCON 协议通信
- 提供 Web 界面

---

## 📄 许可证

本项目为开源项目，欢迎使用和贡献代码。

---

**祝使用愉快！** 🎮
