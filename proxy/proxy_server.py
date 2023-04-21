import socket
import select
import threading
import requests


class ProxyServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.tunnel_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tunnel_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tunnel_socket.bind((self.host, 0))
        self.tunnel_socket.listen(10)

    def handle_client(self, client_socket, remote_socket):
        while True:
            r, _, _ = select.select([client_socket, remote_socket], [], [], 10)
            if not r:
                break

            for source, dest in [(client_socket, remote_socket), (remote_socket, client_socket)]:
                try:
                    data = source.recv(4096)
                    if data:
                        dest.sendall(data)
                    else:
                        break
                except:
                    break

        client_socket.close()
        remote_socket.close()

    def handle_tunnel(self, client_socket, remote_host, remote_port):
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))

        response = 'HTTP/1.1 200 Connection Established\r\nProxy-agent: PyProxy\r\n\r\n'
        client_socket.sendall(response.encode())

        t1 = threading.Thread(target=self.handle_client, args=(client_socket, remote_socket))
        t2 = threading.Thread(target=self.handle_client, args=(remote_socket, client_socket))
        t1.start()
        t2.start()

    def handle_request(self, client_socket, addr):
        data = client_socket.recv(4096)
        if not data:
            return

        first_line = data.decode().split('\r\n')[0]
        url = first_line.split(' ')[1]

        if url.startswith('https://'):
            remote_host, remote_port = url[8:].split(':')
            remote_port = int(remote_port)

            tunnel_client_socket, _ = self.tunnel_socket.accept()
            self.handle_tunnel(tunnel_client_socket, remote_host, remote_port)
        else:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            client_socket.sendall(response.content)

        client_socket.close()

    def serve_forever(self):
        print(f'Listening on {self.host}:{self.port}')

        while True:
            client_socket, addr = self.socket.accept()
            t = threading.Thread(target=self.handle_request, args=(client_socket, addr))
            t.start()


if __name__ == '__main__':
    proxy = ProxyServer()
    proxy.serve_forever()
