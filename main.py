from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket
import concurrent.futures

UDP_IP = '127.0.0.1'
UDP_PORT = 5000

class DataSaver:
    def update_json_file(self,data:dict):
        from datetime import datetime
        import json
        from pathlib import Path
        file = Path('storage/data.json')
        file_contents = {}
        if not file.exists():
            with open(file, 'w') as storage:
                pass
        else:
            if file.stat().st_size != 0:
                with open(file, 'r') as storage:
                    file_contents = json.load(storage)

        file_contents[str(datetime.now())] = data
        with open(file, 'w') as storage:
            json.dump(file_contents,storage, indent=2)

        return file_contents

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parse = urllib.parse.unquote_plus(data.decode())
        data_string = ''.join(f"{key}!br!{value}!=!" for key, value in [el.split('=') for el in data_parse.split('&')])
        to_send_encoded = data_string.encode()
        
        if len(to_send_encoded) > 1024:
            to_send_encoded = data_string[0:1024].encode()
            print(f"\033[91mReceived str length exceeded max limit. Was: \033[93m{len(data_string)}\033[91m bytes, cut: \033[93m{len(to_send_encoded)} bytes.\033[0m")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server = UDP_IP, UDP_PORT

        sock.sendto(to_send_encoded, server)
        sock.close()

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()
        

def run(serv_type):
    if serv_type == 'http':
        http = HTTPServer(('', 3000), HttpHandler)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            http.server_close()
    elif serv_type == 'socket':
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server = UDP_IP, UDP_PORT
        sock.bind(server)
        try:
            while True:
                data, address = sock.recvfrom(1024)
                data_dict = {}
                for item in data.decode().split('!=!'):
                    if item != '':
                        data_dict[item.split('!br!')[0]] = item.split('!br!')[1]

                save = DataSaver()
                result = save.update_json_file(data_dict)
                print(f"Received, processed and saved data: {data_dict}")

        except KeyboardInterrupt:
            print(f'Destroy server')
        finally:
            print('socket_ended!')
            sock.close()


if __name__ == '__main__':
    serv_list = ['http', 'socket']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(run, serv_list)
    