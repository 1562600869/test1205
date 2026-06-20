import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from database import (
    init_db,
    get_all_players,
    add_player,
    update_player,
    delete_player,
    get_player,
    add_injury,
    confirm_recovery,
    get_injured_players,
    get_monthly_injury_stats,
    get_player_injuries,
)


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _get_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8')) if body else {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/' or path == '/index.html':
            self._serve_index()
        elif path == '/api/players':
            players = get_all_players()
            self._send_json(players)
        elif path.startswith('/api/players/') and path.endswith('/injuries'):
            player_id = int(path.split('/')[3])
            injuries = get_player_injuries(player_id)
            self._send_json(injuries)
        elif path.startswith('/api/players/'):
            player_id = int(path.split('/')[-1])
            player = get_player(player_id)
            if player:
                self._send_json(player)
            else:
                self._send_json({'error': '队员不存在'}, 404)
        elif path == '/api/injuries/injured':
            players = get_injured_players()
            self._send_json(players)
        elif path == '/api/injuries/stats/monthly':
            stats = get_monthly_injury_stats()
            self._send_json(stats)
        else:
            self._send_json({'error': '接口不存在'}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            data = self._get_body()
        except json.JSONDecodeError:
            self._send_json({'error': '请求体格式错误'}, 400)
            return

        if path == '/api/players':
            player_id = add_player(
                data.get('nickname', ''),
                data.get('phone', ''),
                data.get('position', ''),
                data.get('status', '可上场')
            )
            self._send_json({'id': player_id, 'message': '添加成功'}, 201)
        elif path == '/api/injuries':
            injury_id = add_injury(
                data.get('player_id'),
                data.get('injury_date', ''),
                data.get('description', ''),
                data.get('severity', ''),
                data.get('expected_recovery_date', None)
            )
            self._send_json({'id': injury_id, 'message': '伤病记录已添加，队员状态已更新为伤停'}, 201)
        elif path.startswith('/api/injuries/') and path.endswith('/recover'):
            injury_id = int(path.split('/')[3])
            success = confirm_recovery(injury_id)
            if success:
                self._send_json({'message': '康复确认成功，队员状态已恢复为可上场'})
            else:
                self._send_json({'error': '康复确认失败，队员不是伤停状态或记录不存在'}, 400)
        else:
            self._send_json({'error': '接口不存在'}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            data = self._get_body()
        except json.JSONDecodeError:
            self._send_json({'error': '请求体格式错误'}, 400)
            return

        if path.startswith('/api/players/'):
            player_id = int(path.split('/')[-1])
            success = update_player(
                player_id,
                data.get('nickname', ''),
                data.get('phone', ''),
                data.get('position', ''),
                data.get('status', '可上场')
            )
            if success:
                self._send_json({'message': '更新成功'})
            else:
                self._send_json({'error': '队员不存在'}, 404)
        else:
            self._send_json({'error': '接口不存在'}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/players/'):
            player_id = int(path.split('/')[-1])
            success = delete_player(player_id)
            if success:
                self._send_json({'message': '删除成功'})
            else:
                self._send_json({'error': '队员不存在'}, 404)
        else:
            self._send_json({'error': '接口不存在'}, 404)

    def _serve_index(self):
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            self._send_html(html)
        else:
            self._send_json({'error': '页面不存在'}, 404)

    def log_message(self, format, *args):
        pass


def run_server(port=6849):
    init_db()
    server = HTTPServer(('localhost', port), RequestHandler)
    print(f'服务器已启动: http://localhost:{port}')
    print('按 Ctrl+C 停止服务器')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器已停止')
        server.server_close()


if __name__ == '__main__':
    run_server()
