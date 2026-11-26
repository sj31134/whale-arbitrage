import errno
import queue
import socket
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from private_accounts import view


@pytest.fixture
def dashboard_transport(monkeypatch):
    """Run real HTTP over TCP when available, otherwise use connected local sockets."""
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", 0))
        except PermissionError as exc:
            if exc.errno not in (errno.EACCES, errno.EPERM):
                raise
        else:
            return

    listeners = {}
    local_host = "127.0.0.1"
    test_port = 49152

    class PairedHTTPServer(ThreadingHTTPServer):
        # Keep serve_forever, dispatch and shutdown. Wake the selector for each client.
        def __init__(self, address, handler):
            host, port = address
            assert host == local_host
            self.server_port = port or test_port
            address = (host, self.server_port)
            if address in listeners:
                raise OSError(errno.EADDRINUSE, "test listener is already running")
            super().__init__(address, handler, bind_and_activate=False)
            self.socket.close()
            self.socket, self.wakeup = socket.socketpair()
            self.pending = queue.Queue()
            listeners[address] = self

        def get_request(self):
            self.socket.recv(1)
            return self.pending.get_nowait(), (local_host, 1)

        def server_close(self):
            listeners.pop(self.server_address, None)
            self.wakeup.close()
            super().server_close()

    def connect(connection):
        address = (connection.host, connection.port)
        assert address == (local_host, test_port)
        listener = listeners.get(address)
        if listener is None:
            raise ConnectionRefusedError(errno.ECONNREFUSED, "test listener is closed")
        client, peer = socket.socketpair()
        if connection.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            client.settimeout(connection.timeout)
        listener.pending.put(peer)
        listener.wakeup.sendall(b"x")
        connection.sock = client

    monkeypatch.setattr(view, "ThreadingHTTPServer", PairedHTTPServer)
    monkeypatch.setattr(HTTPConnection, "connect", connect)


@pytest.fixture
def listener(dashboard_transport):
    return view.server


@pytest.fixture
def dashboard_http(listener):
    from contextlib import contextmanager, closing
    from http.client import HTTPConnection
    from threading import Thread

    @contextmanager
    def open_dashboard(directory, package):
        server, url = listener(directory, 0, package)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as client:
                yield url, client
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    return open_dashboard
