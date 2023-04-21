import socket
import threading
import select


class Proxy:
    def __init__(self, proxy_host, proxy_port):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def handle_client(self, connection):
        # receive data from client
        data = connection.recv(4096)

        # determine whether request is for HTTP or HTTPS
        is_https = data.startswith(b"CONNECT")

        # if request is for HTTPS, establish a tunnel to the remote host
        if is_https:
            try:
                # get remote host and port from the request
                remote_host, remote_port = data.split(b" ")[1].split(b":")
                remote_port = int(remote_port)

                # connect to the remote host and port
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((remote_host, remote_port))

                # send "200 Connection established" response to client
                connection.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")

                # start data exchange between client and remote
                self.exchange_loop(connection, remote)
            except Exception as e:
                # return "502 Bad Gateway" error to client
                connection.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                connection.close()
        else:
            try:
                # get remote host and port from the HTTP request
                remote_host, remote_port = self.get_remote_host_port(data)

                # connect to the remote host and port
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((remote_host, remote_port))

                # send the HTTP request to the remote server
                remote.sendall(data)

                # start data exchange between client and remote
                self.exchange_loop(connection, remote)
            except Exception as e:
                # return "500 Internal Server Error" to client
                connection.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
                connection.close()

    def exchange_loop(self, client, remote):
        while True:
            # wait until client or remote is available for read
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break

            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break

    def get_remote_host_port(self, data):
        # parse the HTTP request to get the remote host and port
        host_start = data.find(b"Host: ") + 6
        host_end = data.find(b"\r\n", host_start)
        host = data[host_start:host_end].decode("utf-8")

        port = 80
        if ":" in host:
            host, port = host.split(":")
            port = int(port)

        return host, port

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.proxy_host, self.proxy_port))
        s.listen()

        print(f"* HTTP proxy server is running on {self.proxy_host}:{self.proxy_port}")

        while True:
            conn, addr = s.accept()
            print(f"* new connection from {addr}")
            t = threading.Thread(target=self.handle_client, args=(conn,))
            t.start()


if __name__ == "__main__":
    proxy = Proxy("127.0.0.1", 8080)
    proxy.run()
