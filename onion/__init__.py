#!/usr/bin/env python3

"""OnI/On version 0.1"""

import collections
import threading
import socket
import select
import time

try:
    import ssl
except ImportError:
    ssl = None

from onion.events import irc_events

events = collections.defaultdict(list)

class TokenBucket:
    """An implementation of the token bucket algorithm.

    >>> bucket = TokenBucket(80, 0.5)
    >>> bucket.consume(1)
    """
    def __init__(self, tokens, fill_rate):
        """tokens is the total tokens in the bucket. fill_rate is the
        rate in tokens/second that the bucket will be refilled."""
        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)
        self.timestamp = time.time()

    def consume(self, tokens):
        """Consume tokens from the bucket. Returns True if there were
        sufficient tokens otherwise False."""
        if tokens <= self.tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def tokens(self):
        now = time.time()
        if self._tokens < self.capacity:
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
        self.timestamp = now
        return self._tokens

    def __repr__(self):
        return "{self.__class__.__name__}(capacity={self.capacity}, fill_rate={self.fill_rate}, tokens={self.tokens})".format(self=self)

class Onion:
    def __init__(self, addr, port, num, *, tokens=23, fill_rate=1.73, encoding="utf-8", use_ssl=False):
        self.sockets = []
        self.lock = threading.RLock()
        self.encoding = encoding
        if use_ssl and ssl is None:
            raise RuntimeError("The ssl library could not be imported, cannot use SSL")
        for i in range(num):
            sock = socket.create_connection((addr, port))
            if use_ssl:
                sock = ssl.wrap_socket(sock)
            self.sockets.append((sock, TokenBucket(tokens, fill_rate)))

        self.lastused = collections.OrderedDict(self.sockets)

    def run(self):
        if "setup" not in events:
            raise RuntimeError("Need a 'setup' event for connection setup")
        for i in range(len(self.sockets)):
            for event, kwargs in events["setup"]:
                event(self, i, **kwargs)

        while True:
            for sock in select.select(self.lastused, [], [])[0]:
                for i, stuff in enumerate(self.sockets):
                    if stuff[0] is sock:
                        break
                else:
                    raise RuntimeError("Proper socket could not be found")

                buffer = b""
                while True:
                    buffer += sock.recv(1024)
                    data = buffer.split(b"\n")
                    buffer = data.pop()
                    for elem in data:
                        if elem.strip().startswith(b":"):
                            prefix, command, *args = elem.strip()[1:].decode(self.encoding).split()
                        else:
                            prefix = None
                            command, *args = elem.strip().decode(self.encoding).split()
                        command = command.lower()
                        command = irc_events.get(command, command)
                        for j, arg in enumerate(args):
                            if arg.startswith(":"):
                                args = args[:j] + [" ".join(args[j:])[1:]]
                                break

                        print("<--- receive {0} {1} -> {2} ({3})".format(prefix, command, i, ", ".join(args)))

                        if "" in events:
                            for event, kwargs in events[""]:
                                event(self, i, prefix, *args, **kwargs)

                        if command in events:
                            for event, kwargs in events[command]:
                                event(self, i, prefix, *args, **kwargs)

                    if not buffer:
                        break

    def send(self, *data, target=None, encoding=None):
        with self.lock:
            if target is None:
                sock, bucket = self.lastused.popitem(last=False)
            else:
                sock, bucket = self.sockets[target]
                del self.lastused[sock]

            self.lastused[sock] = bucket # last socket is always the one most recently used

            if encoding is None:
                encoding = self.encoding

            args = []
            for arg in data:
                if isinstance(arg, bytes):
                    args.append(arg)
                elif isinstance(arg, str):
                    args.append(arg.encode(encoding))
                elif arg is None:
                    continue
                else:
                    raise TypeError("invalid argument type: {0}".format(type(arg).__name__))

            while not bucket.consume(1):
                time.sleep(0.3)

            sock.send(b" ".join(args) + b"\r\n")

    def ring(self, _name, **kwargs):
        _name = _name.lower()
        if isinstance(_name, bytes):
            _name = _name.decode(self.encoding)
        def register(func):
            events[_name].append((func, kwargs))
            return func
        return register



















