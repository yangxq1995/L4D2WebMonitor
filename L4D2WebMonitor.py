#!/usr/bin/env python3
"""
L4D2 RCON 监控 - 后端 API（Python 版）
作者：51青年
功能：
- 提供服务器列表查询（从 config.cfg 读取）
- 提供服务器状态查询（通过 RCON）
- 所有 RCON 操作均在后端完成
- 提供前端页面服务
- 无数据库依赖
- 支持 PyInstaller 打包成 EXE
"""

import configparser
import json
import os
import re
import socket
import sys
import time
import struct
import codecs
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session

# ==================== 路径处理（支持 PyInstaller 打包）====================
def get_exe_dir():
    """获取 EXE 文件所在目录（所有文件都在这里）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# EXE 目录（所有文件都在这里，包括 EXE、config.cfg、index.html、JSON 等）
EXE_DIR = get_exe_dir()

def resource_path(relative_path):
    """获取资源的绝对路径（相对于 EXE 目录）"""
    return os.path.join(EXE_DIR, relative_path)

def config_path():
    """获取 config.cfg 的路径（在 EXE 目录下）"""
    return os.path.join(EXE_DIR, 'config.cfg')

# Flask 静态文件服务目录（EXE 目录）
BASE_PATH = EXE_DIR

# ==================== 配置常量 ====================
# CONFIG_FILE 指向 EXE 目录下的 config.cfg（用户可编辑）
CONFIG_FILE = config_path()
MAX_RCON_PACKET_SIZE = 8192
RCON_TIMEOUT = 5

# ==================== 全局数据 ====================
chapters_info = []
map_info_data = []
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ==================== 配置加载 ====================
def load_json_file(filename):
    """通用 JSON 文件加载函数"""
    filepath = resource_path(filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f'[L4D2] 已加载 {filename}，共 {len(data)} 条记录')
        return data
    except Exception as e:
        print(f'[L4D2] 加载 {filename} 失败: {e}')
        return []

def load_config():
    """加载配置文件，自动检测编码"""
    config = configparser.ConfigParser()
    encodings = ['utf-8-sig', 'utf-8', 'gbk']
    
    for enc in encodings:
        try:
            filepath = CONFIG_FILE
            with codecs.open(filepath, 'r', encoding=enc) as f:
                config.read_file(f)
            print(f'[L4D2] {CONFIG_FILE} 读取成功，编码: {enc}')
            return config
        except Exception as e:
            print(f'[L4D2] {CONFIG_FILE} 编码 {enc} 尝试失败: {e}')
    
    print(f'[L4D2] 警告：无法读取 {CONFIG_FILE}，使用默认配置')
    return configparser.ConfigParser()

# 加载数据
chapters_info = load_json_file('chaptersinfo.json')
map_info_data = load_json_file('mapsinfo.json')
config = load_config()

# ==================== 配置项 ====================
RCON_PASS = config.get('rcon', 'password', fallback='').strip()
ADMIN_PASSWORD = config.get('admin', 'password', fallback='').strip()
DEBUGGING = config.getboolean('app_debug', 'enabled', fallback=False)

RATE_LIMIT_MAX_REQUESTS = config.getint('rate_limit', 'max_requests', fallback=120)
RATE_LIMIT_WINDOW = config.getint('rate_limit', 'window_seconds', fallback=60)

SERVER_HOST = config.get('server', 'host', fallback='0.0.0.0')
SERVER_PORT = config.getint('server', 'port', fallback=8080)
SERVER_DEBUG = config.getboolean('server', 'debug', fallback=False)

# ==================== 地图信息查询 ====================
def lookup_map_info(current_map):
    """根据当前地图名称查找章节和地图信息"""
    if not current_map:
        return None
    
    # 查找章节信息
    chapter = next(
        (c for c in chapters_info if c.get('chapterCode', '').lower() == current_map.lower()),
        None
    )
    
    if not chapter:
        return None
    
    # 查找地图信息
    map_id = chapter.get('mapID')
    chapter_order = chapter.get('chapterOrder')
    
    map_info = next(
        (m for m in map_info_data if m.get('mapID') == map_id),
        None
    )
    
    if not map_info:
        return None
    
    return {
        'mapNameCN': map_info.get('mapNameCN', ''),
        'modID': map_info.get('modID', ''),
        'gamemapsID': map_info.get('gamemapsID', ''),
        'mapCoopChapterN': map_info.get('mapCoopChapterN', 0),
        'isValue': map_info.get('isValue', '0'),
        'chapterOrder': chapter_order,
        'mapID': map_id
    }

# ==================== 服务器配置读取 ====================
def get_server_by_id(server_id):
    """从配置文件读取单个服务器信息，不存在或已禁用返回 None"""
    section = f'server.{server_id}'
    
    if not config.has_section(section):
        return None
    
    if not config.getboolean(section, 'enabled', fallback=True):
        return None
    
    return {
        'id': server_id,
        'host': config.get(section, 'host', fallback=''),
        'cport': config.get(section, 'cport', fallback='0'),
        'pport': config.getint(section, 'pport', fallback=0),
        'comment': config.get(section, 'comment', fallback=''),
    }

def load_all_enabled_servers():
    """返回配置文件中所有已启用服务器的列表"""
    servers = []
    
    for section in config.sections():
        if not section.startswith('server.') or section == 'server':
            continue
        
        try:
            sid = int(section.split('.', 1)[1])
        except ValueError:
            continue
        
        if not config.getboolean(section, 'enabled', fallback=True):
            continue
        
        servers.append({
            'id': sid,
            'host': config.get(section, 'host', fallback=''),
            'cport': config.get(section, 'cport', fallback='0'),
            'pport': config.getint(section, 'pport', fallback=0),
            'comment': config.get(section, 'comment', fallback=''),
        })
    
    servers.sort(key=lambda x: x['id'])
    return servers

# ==================== RCON 协议实现 ====================
def rcon_pack(packet_id, type_, body):
    """RCON 打包"""
    body = body + "\x00\x00"
    size = 4 + 4 + len(body)
    return struct.pack('<III', size, packet_id, type_) + body.encode('latin-1')

def rcon_unpack(data):
    """RCON 解包"""
    if len(data) < 12:
        return None
    
    size, packet_id, type_ = struct.unpack('<III', data[:12])
    
    if size < 8 or size > MAX_RCON_PACKET_SIZE:
        print(f"[L4D2] RCON 包大小异常: {size}")
        return None
    
    body_raw = data[12:12 + size - 8]
    body = fix_chinese(body_raw)
    
    return {'size': size, 'id': packet_id, 'type': type_, 'body': body}

def fix_chinese(s):
    """中文编码修复 - 优先 UTF-8（L4D2 服务器实际返回编码）"""
    if isinstance(s, bytes):
        for encoding in ['utf-8', 'gbk', 'latin-1']:
            try:
                return s.decode(encoding)
            except:
                pass
        return repr(s)
    return s

def clean_resp(s):
    """清理不可见字符"""
    s = fix_chinese(s)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    return s.strip()

def read_rcon(sock):
    """从 socket 读取一个完整 RCON 包"""
    data = b''
    
    # 读取包大小
    while len(data) < 4:
        chunk = sock.recv(4 - len(data))
        if not chunk:
            return None
        data += chunk
    
    size = struct.unpack('<I', data)[0]
    
    if size < 8 or size > MAX_RCON_PACKET_SIZE:
        print(f"[L4D2] RCON 包大小异常: {size}")
        return None
    
    # 读取完整包
    while len(data) < (4 + size):
        remaining = (4 + size) - len(data)
        chunk = sock.recv(remaining)
        if not chunk:
            return None
        data += chunk
    
    return rcon_unpack(data)

def rcon_exec(host, port, password, command):
    """执行 RCON 命令"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(RCON_TIMEOUT)
        sock.connect((host, port))
        
        # 认证
        sock.sendall(rcon_pack(1, 3, password))
        read_rcon(sock)  # 读取空响应
        auth_resp = read_rcon(sock)
        
        if not auth_resp:
            sock.close()
            return json.dumps({'error': '认证失败：无响应'})
        
        if auth_resp['id'] == -1:
            sock.close()
            return json.dumps({'error': 'RCON 认证失败'})
        
        # 执行命令
        sock.sendall(rcon_pack(2, 2, command))
        sock.sendall(rcon_pack(3, 2, ''))
        
        response = ''
        while True:
            packet = read_rcon(sock)
            if not packet:
                break
            if packet['id'] == 3:
                break
            if packet['body']:
                response += packet['body']
        
        sock.close()
        return json.dumps({'response': clean_resp(response)})
        
    except socket.timeout:
        return json.dumps({'error': '连接超时'})
    except ConnectionRefusedError:
        return json.dumps({'error': '连接被拒绝'})
    except Exception as e:
        return json.dumps({'error': f'无法连接服务器: {str(e)}'})

# ==================== 数据解析 ====================
def parse_status(resp):
    """解析 status 命令输出"""
    status = {
        'hostname': '',
        'map': '',
        'progress': '',
        'players': '0/0',
        'playerList': [],
        'ip': '',
        'version': '',
        'humanPlayers': 0,
        'maxPlayers': 4,  # 默认值，合作模式
    }
    
    lines = resp.split('\n')
    in_player_section = False
    
    for line in lines:
        line = line.rstrip()
        
        # 玩家列表段落
        if re.match(r'#\s+userid\s+name\s+uniqueid', line, re.IGNORECASE):
            in_player_section = True
            continue
        if line.strip() == '#end':
            in_player_section = False
            continue
        
        if in_player_section and line.startswith('#'):
            parse_player_line(line, status['playerList'])
            continue
        
        # 服务器信息
        line_lower = line.lower()
        
        if line_lower.startswith('hostname:'):
            status['hostname'] = line[9:].strip()
            match = re.search(r'\[进度?(\d+%?)\]', status['hostname'])
            if match:
                status['progress'] = match.group(1)
                
        elif line_lower.startswith('map     :'):
            status['map'] = line[9:].strip()
            
        elif line_lower.startswith('players :'):
            players_str = line[9:].strip()
            status['players'] = players_str
            
            # 解析人类玩家数
            m_human = re.search(r'(\d+)\s+humans?', players_str, re.IGNORECASE)
            if m_human:
                status['humanPlayers'] = int(m_human.group(1))
            
            # 解析最大玩家数
            m_max = re.search(r'\((\d+)\s+max\)', players_str, re.IGNORECASE)
            if m_max:
                status['maxPlayers'] = int(m_max.group(1))
                
        elif line_lower.startswith('udp/ip  :'):
            status['ip'] = line[9:].strip()
            
        elif line_lower.startswith('version :'):
            status['version'] = line[9:].strip()
    
    return status

def parse_player_line(line, player_list):
    """解析单行玩家信息"""
    trimmed = re.sub(r'^#\s*', '', line)
    
    match = re.match(r'^(\d+)', trimmed)
    if not match:
        return
    
    entity_id = match.group(1)
    rest = trimmed[len(match.group(0)):].strip()
    
    # BOT 玩家
    if rest.startswith('"'):
        match = re.match(r'^"([^"]+)"\s+BOT\s+(\w+)', rest)
        if match:
            bot_name = match.group(1)
            default_bots = ['Bill', 'Zoey', 'Louis', 'Francis', 'Coach', 'Ellis', 'Nick', 'Rochelle']
            
            if bot_name not in default_bots:
                return
            
            player_list.append({
                'id': entity_id,
                'name': bot_name,
                'steamid': 'BOT',
                'time': '0',
                'ping': '0',
                'loss': '0',
                'state': match.group(2),
                'rate': '0',
                'adr': '',
                'isBot': True
            })
    else:
        # 人类玩家
        match = re.match(
            r'^\d+\s+"([^"]+)"\s+(STEAM_[\d]:[\d]:[\d]+)\s+([\d:]+)\s+(\d+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(.+)',
            rest
        )
        if match:
            player_list.append({
                'id': entity_id,
                'name': match.group(1),
                'steamid': match.group(2),
                'time': match.group(3),
                'ping': match.group(4),
                'loss': match.group(5),
                'state': match.group(6),
                'rate': match.group(7),
                'adr': match.group(8).strip(),
                'isBot': False
            })

# ==================== 限流装饰器 ====================
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        if client_ip:
            session_key = f'l4d2_requests_{client_ip}'
            request_times = session.get(session_key, [])
            
            # 清理过期记录
            request_times = [
                timestamp for timestamp in request_times
                if current_time - timestamp <= RATE_LIMIT_WINDOW
            ]
            
            if len(request_times) >= RATE_LIMIT_MAX_REQUESTS:
                return jsonify({'error': '请求过于频繁，请稍后再试'}), 429
            
            request_times.append(current_time)
            session[session_key] = request_times
        
        return f(*args, **kwargs)
    return decorated_function

def check_password(password):
    """统一密码校验，返回 (ok: bool, error_response)"""
    if not password:
        return False, (jsonify({'error': '请输入密码'}), 400)
    
    if password.strip() != ADMIN_PASSWORD:
        client_ip = request.remote_addr
        fail_key = f'l4d2_reset_fail_{client_ip}'
        fail_count = session.get(fail_key, 0)
        
        session[fail_key] = fail_count + 1
        print(f'[L4D2] 密码错误，IP={client_ip}, 已失败{fail_count + 1}次')
        
        if fail_count >= 3:
            return False, (jsonify({'error': '密码错误次数过多，请1分钟后重试'}), 403)
        
        return False, (jsonify({'error': '密码错误'}), 401)
    
    # 密码正确，清除失败计数
    client_ip = request.remote_addr
    fail_key = f'l4d2_reset_fail_{client_ip}'
    session.pop(fail_key, None)
    
    return True, None

# ==================== API 端点 ====================
@app.route('/')
def index():
    """提供前端页面"""
    return send_from_directory(EXE_DIR, 'index.html')

@app.route('/api/servers', methods=['GET'])
@rate_limit
def api_get_servers():
    """获取服务器列表（复用 load_all_enabled_servers）"""
    servers = load_all_enabled_servers()
    return jsonify({'servers': servers})

@app.route('/api/status', methods=['GET'])
@rate_limit
def api_get_status():
    """获取单个服务器状态"""
    server_id = request.args.get('id', type=int)
    
    if not server_id or server_id <= 0:
        return jsonify({'error': '无效的服务器 ID'}), 400
    
    server = get_server_by_id(server_id)
    if not server:
        return jsonify({'error': '服务器不存在或已禁用'}), 404
    
    try:
        rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, 'status')
        rcon_array = json.loads(rcon_json)
        
        if 'error' in rcon_array:
            return jsonify({'error': '服务器离线或无法访问'}), 503
        
        status = parse_status(rcon_array['response'])
        response_data = {'status': status}
        
        map_info = lookup_map_info(status['map'])
        if map_info:
            response_data['mapinfo'] = map_info
        
        if DEBUGGING:
            response_data['raw'] = rcon_array['response']
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f'[L4D2] 获取服务器状态失败: {e}')
        return jsonify({'error': '服务暂时不可用'}), 500

@app.route('/api/all_status', methods=['GET'])
@rate_limit
def api_get_all_status():
    """获取所有服务器状态"""
    try:
        servers = load_all_enabled_servers()
        all_status = []
        
        for server in servers:
            rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, 'status')
            rcon_array = json.loads(rcon_json)
            
            if 'error' in rcon_array:
                all_status.append({'id': server['id'], 'error': '服务器离线或无法访问'})
            else:
                status = parse_status(rcon_array['response'])
                server_data = {'id': server['id'], 'status': status}
                
                map_info = lookup_map_info(status['map'])
                if map_info:
                    server_data['mapinfo'] = map_info
                
                if DEBUGGING:
                    server_data['raw'] = rcon_array['response']
                
                all_status.append(server_data)
        
        return jsonify({'servers': all_status})
        
    except Exception as e:
        print(f'[L4D2] 获取所有服务器状态失败: {e}')
        return jsonify({'error': '服务暂时不可用'}), 500

@app.route('/api/reset_server', methods=['POST'])
@rate_limit
def api_reset_server():
    """重置服务器（需要管理员密码）"""
    # 优先从 form 获取，其次从 args 获取
    password = request.form.get('password') or request.args.get('password', '')
    
    ok, err = check_password(password)
    if not ok:
        return err
    
    server_id = request.form.get('id', type=int) or request.args.get('id', type=int)
    if not server_id or server_id <= 0:
        return jsonify({'error': '无效的服务器 ID'}), 400
    
    server = get_server_by_id(server_id)
    if not server:
        return jsonify({'error': '服务器不存在或已禁用'}), 404
    
    try:
        rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, 'map c1m1')
        rcon_array = json.loads(rcon_json)
        
        if 'error' in rcon_array:
            return jsonify({'error': rcon_array['error']}), 500
        
        return jsonify({'success': True, 'message': '服务器已重置到第一关'})
        
    except Exception as e:
        print(f'[L4D2] 重置服务器失败: {e}')
        return jsonify({'error': '服务暂时不可用'}), 500

@app.route('/api/exec_command', methods=['POST'])
@rate_limit
def api_exec_command():
    """执行自定义 RCON 指令（需要密码）"""
    password = request.form.get('password') or request.args.get('password', '')
    
    print(f'[L4D2 DEBUG] 收到密码: "{password}" (长度: {len(password) if password else 0}), '
          f'期望: "{ADMIN_PASSWORD}" (长度: {len(ADMIN_PASSWORD)})')
    
    ok, err = check_password(password)
    if not ok:
        return err
    
    server_id = request.form.get('id', type=int) or request.args.get('id', type=int)
    command = request.form.get('command', '') or request.args.get('command', '')
    
    if not server_id or server_id <= 0:
        return jsonify({'error': '无效的服务器 ID'}), 400
    
    if not command:
        return jsonify({'error': '请输入要执行的指令'}), 400
    
    server = get_server_by_id(server_id)
    if not server:
        return jsonify({'error': '服务器不存在或已禁用'}), 404
    
    try:
        rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, command)
        rcon_array = json.loads(rcon_json)
        
        if 'error' in rcon_array:
            return jsonify({'error': rcon_array['error']}), 500
        
        return jsonify({'success': True, 'message': f'指令已执行: {command}'})
        
    except Exception as e:
        print(f'[L4D2] 执行指令失败: {e}')
        return jsonify({'error': '服务暂时不可用'}), 500

@app.route('/api/reset_server_quick', methods=['GET'])
@rate_limit
def api_reset_server_quick():
    """快速重置服务器（无需密码，条件：无人类玩家）"""
    server_id = request.args.get('id', type=int)
    
    if not server_id or server_id <= 0:
        return jsonify({'error': '无效的服务器 ID'}), 400
    
    server = get_server_by_id(server_id)
    if not server:
        return jsonify({'error': '服务器不存在或已禁用'}), 404
    
    try:
        # 先检查服务器状态
        rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, 'status')
        rcon_array = json.loads(rcon_json)
        
        if 'error' in rcon_array:
            return jsonify({'error': '获取服务器状态失败: ' + rcon_array['error']}), 503
        
        status = parse_status(rcon_array['response'])
        
        # 使用 humanPlayers 字段判断是否有真人玩家
        if status.get('humanPlayers', 0) > 0:
            return jsonify({
                'error': 'HUMAN_PLAYER_DETECTED',
                'message': '服务器上有非BOT玩家，需要管理员密码'
            })
        
        # 无真人玩家，执行重置
        rcon_json = rcon_exec(server['host'], server['pport'], RCON_PASS, 'map c1m1')
        rcon_array = json.loads(rcon_json)
        
        if 'error' in rcon_array:
            return jsonify({'error': rcon_array['error']}), 500
        
        return jsonify({'success': True, 'message': '该服务器已重置，请稍等片刻...'})
        
    except Exception as e:
        print(f'[L4D2] 快速重置服务器失败: {e}')
        return jsonify({'error': '服务暂时不可用'}), 500

@app.route('/api/clear_fail_count', methods=['GET'])
def api_clear_fail_count():
    """清除失败计数（仅限本地）"""
    client_ip = request.remote_addr
    
    if client_ip == '127.0.0.1' or client_ip.startswith('192.168.'):
        fail_key = f'l4d2_reset_fail_{client_ip}'
        session.pop(fail_key, None)
        return jsonify({'success': True, 'message': '失败计数已清除'})
    
    return jsonify({'error': '无权限'}), 403

# ==================== 主程序 ====================
if __name__ == '__main__':
    try:
        import flask
    except ImportError as e:
        print(f'缺少依赖: {e}')
        print('请运行: pip install flask')
        exit(1)
    
    print(f'启动 L4D2 监控服务...')
    print(f'程序目录: {BASE_PATH}')
    print(f'ADMIN_PASSWORD 已加载，长度: {len(ADMIN_PASSWORD)}')
    print(f'访问 http://{SERVER_HOST}:{SERVER_PORT}')
    
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=SERVER_DEBUG)
