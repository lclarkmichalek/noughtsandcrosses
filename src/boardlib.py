import socket
import select
import sys
import time
import pickle
import tempfile

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('google.com',0))

global ip
ip = s.getsockname()[0]

del s

global port
port = 1770

def log(*inputs):
    sys.stderr.write(''.join(input))
    sys.stderr.flush()

class NetworkError(Exception): pass

class Shutdown(Exception): pass

class connection():
    def __init__(self, timeout = 5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.timeout = timeout
        self.moving = 0
    
    def setServer(self):
        self.type = 'Server'
        self.sock.bind((ip, port))
        self.sock.listen(1)
        (self.socket, self.address) = self.sock.accept()
        self.socket.setblocking(0)
    
    def setClient(self, address):
        self.type = 'Client'
        self.sock.connect((address, port))
        self.socket = self.sock
        self.socket.setblocking(0)
    
    def check(self, timeout = 0):
        readable, null, null = select.select([self.socket], [], [], timeout)
        null, writeable, null = select.select([], [self.socket], [], timeout)
        null, null, errorable = select.select([], [], [self.socket], timeout)
        del null
        
        if bool(errorable): raise NetworkError
        
        return (bool(readable), bool(writeable), bool(errorable))
    
    def send(self, content):
        if self.check()[2]:
            self.socket.close()
            raise RuntimeError
        class ToLong(Exception): pass
        length = len(content)
        if length > 100:
            raise ToLong
        if length < 10:
            length = '0' + str(length)
        else:
            length = str(length)
        log(content)
        self.socket.send(str(length) + content)
    
    def recive(self):
        if self.check()[2]:
            self.socket.close()
            raise RuntimeError
        if self.check()[0]:
            self.moving += 1
            log(self.moving)
            if self.moving >= self.timeout:
                raise Shutdown
        else:
            self.moving = 0
        while not self.check()[0]:
            time.sleep(0.1)
            if self.check()[2]:
                self.socket.close()
                raise RuntimeError
        length = self.socket.recv(2)
        try:
            length = int(length)
        except ValueError:
            raise Shutdown
        content = self.socket.recv(length)
        log (content)
        return content
    
    def reciveone(self):
        if self.check()[2]:
            self.socket.close()
            raise RuntimeError
        if self.check()[0]:
            self.moving += 1
            log(self.moving)
            if self.moving >= self.timeout:
                raise Shutdown
        else:
            self.moving = 0
            return False
        length = self.socket.recv(2)
        if length == '':
            return False
        length = int(length)
        content = self.socket.recv(length)
        log (content)
        return content
    
    def close(self):
        self.socket.close()


class SyList(list):
    def __init__(self, input = None):
        if type(list) == type(str):
            input = self.decode(input)
        self.list = input
        
    def encode(self, data=-1):
        if data == -1:
            data = self.list
            
        file = tempfile.NamedTemporaryFile('w+')
        pickle.dump(data, file)
        file.flush()
        file.seek(0)
        
        return file.read()
        
    
    def decoede(self, input):
        file = tempfile.NamedTemporaryFile('w+')
        file.write(input)
        file.flush()
        file.seek(0)
        return pickle.load(file)

class SyConn(connection):
    def __init__(self, list, timeout=5):
        connection.__init__(self, timeout)
        self.list = SyList(list)
    
    def __repr__(self):
        print '<connection: %s>\n<list: %l>' % (self.sock, self.list)
    
    def sendList(self):
        self.send(self.list.encode())
    
    def recvList(self):
        return SyList(self.recive())
    