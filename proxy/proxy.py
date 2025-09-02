import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import argparse
import ssl
import socket
import sys
import logging
import os
import ipaddress
import re
import time
import json
from datetime import datetime

# 尝试导入YAML配置文件
try:
    import yaml
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    SERVER_CONFIG = config['server_config']
    ACCESS_CONTROL = config['access_control']
    TARGET_FILTER = config['target_filter']
    LOGGING = config['logging']
    ADVANCED = config['advanced']
except (ImportError, FileNotFoundError, KeyError):
    # 默认配置
    SERVER_CONFIG = {'host': '0.0.0.0', 'port': 6777, 'timeout': 30, 'max_connections': 100}
    ACCESS_CONTROL = {'enable_whitelist': False, 'whitelist': ['127.0.0.1'], 'enable_blacklist': False, 'blacklist': []}
    TARGET_FILTER = {'blocked_domains': [], 'blocked_ips': []}
    LOGGING = {'level': 'DEBUG', 'log_to_file': False, 'log_file': 'proxy.log', 'log_format': '%(asctime)s - %(levelname)s - %(message)s'}
    ADVANCED = {'enable_cache': False, 'cache_size': 100, 'enable_compression': False, 'anonymous_mode': True}

# 配置日志
log_level = getattr(logging, LOGGING['level'], logging.INFO)
log_handlers = [logging.StreamHandler()]

if LOGGING['log_to_file']:
    log_handlers.append(logging.FileHandler(LOGGING['log_file']))

logging.basicConfig(
    level=log_level,
    format=LOGGING['log_format'],
    handlers=log_handlers
)
logger = logging.getLogger('enhanced_proxy')

# 简单的缓存实现
class SimpleCache:
    def __init__(self, max_size_mb=100):
        self.cache = {}
        self.max_size = max_size_mb * 1024 * 1024  # 转换为字节
        self.current_size = 0
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        if key in self.cache:
            item = self.cache[key]
            # 检查是否过期
            if item['expires'] > time.time():
                self.hits += 1
                # 更新最后访问时间
                item['last_access'] = time.time()
                return item['data'], item['headers']
            else:
                # 过期了，删除
                self.remove(key)
        self.misses += 1
        return None, None
    
    def set(self, key, data, headers, ttl=3600):
        # 如果缓存已满，清理一些空间
        if self.current_size + len(data) > self.max_size:
            self._cleanup()
        
        # 如果单个项目太大，不缓存
        if len(data) > self.max_size * 0.1:  # 不缓存超过缓存大小10%的项目
            return
        
        # 存储项目
        self.cache[key] = {
            'data': data,
            'headers': headers,
            'size': len(data),
            'expires': time.time() + ttl,
            'last_access': time.time()
        }
        self.current_size += len(data)
    
    def remove(self, key):
        if key in self.cache:
            self.current_size -= self.cache[key]['size']
            del self.cache[key]
    
    def _cleanup(self):
        """清理缓存中最旧的或最少使用的项目"""
        if not self.cache:
            return
        
        # 按最后访问时间排序
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['last_access'])
        
        # 删除最旧的项目，直到有足够空间
        for key, _ in sorted_items:
            self.remove(key)
            # 如果已经清理了一半的空间，停止
            if self.current_size < self.max_size * 0.5:
                break
    
    def get_stats(self):
        return {
            'items': len(self.cache),
            'size': self.current_size,
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_ratio': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

# 创建缓存实例
cache = SimpleCache(ADVANCED['cache_size']) if ADVANCED['enable_cache'] else None

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """处理多线程请求的HTTP服务器"""
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = SERVER_CONFIG['max_connections']

class EnhancedProxyHandler(http.server.BaseHTTPRequestHandler):
    timeout = SERVER_CONFIG['timeout']
    server_version = "EnhancedProxy/1.0"
    
    def log_message(self, format, *args):
        """重写日志方法，使用我们的日志配置"""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def _is_ip_allowed(self, ip):
        """检查IP是否被允许访问"""
        # 检查黑名单
        if ACCESS_CONTROL['enable_blacklist']:
            for blocked in ACCESS_CONTROL['blacklist']:
                if '/' in blocked:  # CIDR格式
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(blocked):
                        return False
                elif ip == blocked:  # 精确匹配
                    return False
        
        # 检查白名单
        if ACCESS_CONTROL['enable_whitelist']:
            for allowed in ACCESS_CONTROL['whitelist']:
                if '/' in allowed:  # CIDR格式
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(allowed):
                        return True
                elif ip == allowed:  # 精确匹配
                    return True
            return False  # 如果启用了白名单但IP不在其中，拒绝访问
        
        return True  # 默认允许
    
    def _is_target_allowed(self, host):
        """检查目标主机是否被允许访问"""
        # 检查被阻止的域名
        for domain in TARGET_FILTER['blocked_domains']:
            if domain in host or host.endswith('.' + domain):
                return False
        
        # 尝试解析主机名为IP
        try:
            ip = socket.gethostbyname(host)
            # 检查被阻止的IP
            for blocked_ip in TARGET_FILTER['blocked_ips']:
                if '/' in blocked_ip:  # CIDR格式
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(blocked_ip):
                        return False
                elif ip == blocked_ip:  # 精确匹配
                    return False
        except:
            pass  # 解析失败，忽略
        
        return True
    
    def _get_cache_key(self, method, url, headers):
        """生成缓存键"""
        # 只缓存GET请求
        if method != 'GET':
            return None
        
        # 提取可能影响响应的头部
        cache_headers = {}
        for header in ['Accept', 'Accept-Encoding', 'Accept-Language']:
            if header in headers:
                cache_headers[header] = headers[header]
        
        # 生成缓存键
        return f"{method}:{url}:{json.dumps(cache_headers)}"
    
    def _send_request(self, method, url, headers, body=None):
        """发送请求到目标服务器"""
        start_time = time.time()
        host = urllib.parse.urlparse(url).netloc.split(':')[0]
        
        # 检查目标是否被允许
        if not self._is_target_allowed(host):
            self.send_error(403, f"Forbidden: Access to {host} is blocked")
            logger.warning(f"Blocked request to {host} from {self.client_address[0]}")
            return False
        
        # 检查缓存
        cache_key = None
        if cache and method == 'GET':
            cache_key = self._get_cache_key(method, url, headers)
            cached_data, cached_headers = cache.get(cache_key) if cache_key else (None, None)
            if cached_data:
                self.send_response(200)
                for name, value in cached_headers.items():
                    self.send_header(name, value)
                self.send_header('X-Cache', 'HIT')
                self.end_headers()
                self.wfile.write(cached_data)
                logger.debug(f"Cache hit for {url}")
                return True
        
        # 准备请求头
        request_headers = dict(headers)
        
        # 匿名模式：移除可能泄露客户端信息的头部
        if ADVANCED['anonymous_mode']:
            for header in ['X-Forwarded-For', 'Referer', 'Cookie', 'User-Agent']:
                if header in request_headers:
                    del request_headers[header]
            # 使用通用User-Agent
            request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        try:
            # 创建请求对象
            req = urllib.request.Request(
                url=url,
                data=body,
                headers=request_headers,
                method=method
            )
            
            # 处理SSL证书验证
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # 发送请求并获取响应
            response = urllib.request.urlopen(req, context=ctx, timeout=self.timeout)
            
            # 读取响应数据
            data = response.read()
            
            # 发送响应状态码和头部
            self.send_response(response.status)
            
            # 保存响应头部用于缓存
            response_headers = {}
            for header in response.getheaders():
                header_name = header[0].lower()
                header_value = header[1]
                
                # 跳过特定的头部
                if header_name not in ('transfer-encoding', 'connection'):
                    self.send_header(header[0], header_value)
                    response_headers[header[0]] = header_value
            
            # 添加代理标识和处理时间
            self.send_header('Via', f'{self.server_version}')
            self.send_header('X-Proxy-Time', f'{(time.time() - start_time):.6f}')
            self.send_header('X-Cache', 'MISS')
            self.end_headers()
            
            # 发送响应体
            self.wfile.write(data.encode('utf-8') if isinstance(data, str) else data)
            
            # 缓存响应
            if cache and cache_key and response.status == 200:
                # 从Cache-Control头部获取TTL
                ttl = 3600  # 默认1小时
                cache_control = response.getheader('Cache-Control')
                if cache_control:
                    max_age_match = re.search(r'max-age=(\d+)', cache_control)
                    if max_age_match:
                        ttl = int(max_age_match.group(1))
                
                # 只缓存内容类型为文本、图像等的响应
                content_type = response.getheader('Content-Type', '')
                cacheable_types = ['text/', 'image/', 'application/javascript', 'application/json', 'application/xml']
                if any(ct in content_type for ct in cacheable_types):
                    cache.set(cache_key, data, response_headers, ttl)
            
            logger.info(f"{method} {url} - {response.status} - {len(data)} bytes - {(time.time() - start_time):.3f}s")
            return True
            
        except (urllib.error.URLError, socket.timeout) as e:
            logger.error(f"Error accessing {url}: {str(e)}")
            self.send_error(504, f"Gateway Timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Proxy error for {url}: {str(e)}")
            self.send_error(502, f"Bad Gateway: {str(e)}")
        return False
    
    def _get_request_body(self):
        """获取请求体内容"""
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length) if content_length > 0 else None
    
    def _get_target_url(self):
        """获取目标URL"""
        if self.path.startswith('http'):
            return self.path
        return 'http://' + self.path[1:]  # 移除开头的'/'并添加http://
    
    def _handle_request(self, method):
        """通用请求处理方法"""
        # 检查客户端IP是否被允许
        client_ip = self.client_address[0]
        if not self._is_ip_allowed(client_ip):
            self.send_error(403, "Forbidden: Your IP is not allowed to use this proxy")
            logger.warning(f"Blocked request from {client_ip}")
            return
        
        url = self._get_target_url()
        body = self._get_request_body() if method in ('POST', 'PUT', 'PATCH') else None
        self._send_request(method, url, self.headers, body)
    
    def do_GET(self):
        # 处理特殊路径
        if self.path == '/proxy-status':
            self._handle_status_request()
            return
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def do_PUT(self):
        self._handle_request('PUT')
    
    def do_DELETE(self):
        self._handle_request('DELETE')
    
    def do_HEAD(self):
        self._handle_request('HEAD')
    
    def do_OPTIONS(self):
        self._handle_request('OPTIONS')
    
    def do_PATCH(self):
        self._handle_request('PATCH')
    
    def _handle_status_request(self):
        """处理代理状态请求"""
        status = {
            'server': {
                'version': self.server_version,
                'uptime': int(time.time() - server_start_time),
                'start_time': datetime.fromtimestamp(server_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                'connections': self.server.request_queue_size,
            },
            'config': {
                'host': SERVER_CONFIG['host'],
                'port': SERVER_CONFIG['port'],
                'timeout': SERVER_CONFIG['timeout'],
                'anonymous_mode': ADVANCED['anonymous_mode'],
                'cache_enabled': ADVANCED['enable_cache'],
            }
        }
        
        # 添加缓存统计信息
        if cache:
            status['cache'] = cache.get_stats()
        
        # 发送响应
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
    
    def do_CONNECT(self):
        """处理HTTPS隧道连接请求"""
        # 检查客户端IP是否被允许
        client_ip = self.client_address[0]
        if not self._is_ip_allowed(client_ip):
            self.send_error(403, "Forbidden: Your IP is not allowed to use this proxy")
            logger.warning(f"Blocked CONNECT request from {client_ip}")
            return
        
        host_port = self.path.split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 443
        
        # 检查目标是否被允许
        if not self._is_target_allowed(host):
            self.send_error(403, f"Forbidden: Access to {host} is blocked")
            logger.warning(f"Blocked CONNECT to {host} from {client_ip}")
            return
        
        try:
            # 连接到目标服务器
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(self.timeout)
            server_socket.connect((host, port))
            
            # 告诉客户端连接已建立
            self.send_response(200, 'Connection Established')
            self.send_header('Proxy-Agent', self.server_version)
            self.end_headers()
            
            # 开始在客户端和服务器之间转发数据
            self._tunnel(server_socket)
            
        except Exception as e:
            logger.error(f"CONNECT error to {host}:{port}: {str(e)}")
            self.send_error(502, f"Bad Gateway: {str(e)}")
            return
    
    def _tunnel(self, server_socket):
        """在客户端和服务器之间建立隧道"""
        client_socket = self.connection
        
        # 设置非阻塞模式
        client_socket.setblocking(0)
        server_socket.setblocking(0)
        
        client_buffer = b''
        server_buffer = b''
        
        is_active = True
        while is_active:
            # 等待数据可读/可写
            import select
            inputs = [client_socket, server_socket]
            outputs = []
            
            if client_buffer:
                outputs.append(server_socket)
            if server_buffer:
                outputs.append(client_socket)
            
            try:
                readable, writable, exceptional = select.select(inputs, outputs, inputs, 1)
            except Exception as e:
                logger.error(f"Select error: {str(e)}")
                break
            
            # 处理异常
            if exceptional:
                is_active = False
                continue
            
            # 从客户端读取数据
            if client_socket in readable:
                try:
                    data = client_socket.recv(8192)
                    if not data:
                        is_active = False
                    else:
                        client_buffer += data
                except Exception as e:
                    logger.error(f"Error reading from client: {str(e)}")
                    is_active = False
            
            # 从服务器读取数据
            if server_socket in readable:
                try:
                    data = server_socket.recv(8192)
                    if not data:
                        is_active = False
                    else:
                        server_buffer += data
                except Exception as e:
                    logger.error(f"Error reading from server: {str(e)}")
                    is_active = False
            
            # 发送数据到服务器
            if server_socket in writable and client_buffer:
                try:
                    sent = server_socket.send(client_buffer)
                    client_buffer = client_buffer[sent:]
                except Exception as e:
                    logger.error(f"Error sending to server: {str(e)}")
                    is_active = False
            
            # 发送数据到客户端
            if client_socket in writable and server_buffer:
                try:
                    sent = client_socket.send(server_buffer)
                    server_buffer = server_buffer[sent:]
                except Exception as e:
                    logger.error(f"Error sending to client: {str(e)}")
                    is_active = False
        
        # 关闭连接
        if server_socket:
            server_socket.close()

def parse_args():
    parser = argparse.ArgumentParser(description='Enhanced HTTP/HTTPS Proxy Server')
    parser.add_argument('--host', default=SERVER_CONFIG['host'], help=f'Host to bind (default: {SERVER_CONFIG["host"]})')
    parser.add_argument('--port', type=int, default=SERVER_CONFIG['port'], help=f'Port to bind (default: {SERVER_CONFIG["port"]})')
    parser.add_argument('--timeout', type=int, default=SERVER_CONFIG['timeout'], help=f'Connection timeout in seconds (default: {SERVER_CONFIG["timeout"]})')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--config', help='Path to configuration file')
    return parser.parse_args()

def print_banner():
    banner = f"""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║   Enhanced HTTP/HTTPS Proxy Server v1.0       ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    
    Server running on {SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}
    
    Features:
    - HTTP/HTTPS Proxy with SSL tunneling
    - Access control with IP whitelist/blacklist
    - Target filtering with domain/IP blocking
    - {'Caching enabled' if ADVANCED['enable_cache'] else 'Caching disabled'}
    - {'Anonymous mode enabled' if ADVANCED['anonymous_mode'] else 'Anonymous mode disabled'}
    
    Access proxy status at: http://localhost:{SERVER_CONFIG['port']}/proxy-status
    
    Press Ctrl+C to stop the server
    """
    print(banner)


def run_proxy():
    args = parse_args()
    server_start_time = time.time()
    
    # 更新配置
    SERVER_CONFIG['host'] = args.host
    SERVER_CONFIG['port'] = args.port
    SERVER_CONFIG['timeout'] = args.timeout
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        print_banner()
        with ThreadedHTTPServer((SERVER_CONFIG['host'], SERVER_CONFIG['port']), EnhancedProxyHandler) as httpd:
            logger.info(f"Starting enhanced proxy server on {SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    run_proxy()