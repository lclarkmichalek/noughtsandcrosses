import socket
import json
import time
import select

class Connection(object):
    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self, address):
        self._sock.connect(address)
    
    def sendMessage(self, message, recipients):
        message = json.dumps(["snd", message, recipients, 3])
        self._write(message)
    
    def storeData(self, key, value):
        message = json.dumps(['strdat', {key: value}, ['Self'], 4])
        self._write(message)
    
    def requestData(self, key):
        message = json.dumps(['rqstdat', key, ['Self'], 2])
    
    def _read(self):
        if self._check()[0]:
            self._moving += 1
            if self._moving >= self._options["Timeout"]:
                raise RuntimeError("Timeout")
        else:
            self._moving = 0
        while not self._check()[0]:
            time.sleep(0.1)
        length = self._sock.recv(2)
        try:
            length = int(length)
        except ValueError:
            raise RuntimeError
        content = self._sock.recv(length)
        return content
    
    def _write(self, content):
        class ToLong(Exception): pass
        length = len(content)
        if length > 100:
            raise ToLong
        if length < 10:
            length = '0' + str(length)
        else:
            length = str(length)
        self._sock.send(str(length) + content)
    
    def _check(self):
        timeout = self._options["Timeout"]
        readable, null, null = select.select([self._sock], [], [], timeout)
        null, writeable, null = select.select([], [self._sock], [], timeout)
        null, null, errorable = select.select([], [], [self._sock], timeout)
        del null
        
        if bool(errorable): raise RuntimeError(
                    "socket raised error")
        
        return (bool(readable), bool(writeable))