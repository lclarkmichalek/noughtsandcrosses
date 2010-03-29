import socket
import select
import sys
import time
import pickle
import tempfile
import random

TESTING = True

global ip

if not TESTING:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('google.com',0))

    ip = s.getsockname()[0]

    del s
else:
    ip = '127.0.0.1'

global port
port = 1772


def log(*args):
    for arg in args:
        sys.stderr.write(str(arg))
    sys.stderr.write('\n')

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
        if length >= 1000:
            raise ToLong
        elif length < 100:
            length = '0' + str(length)
        elif length < 10:
            length = '00' + str(length)
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
        length = self.socket.recv(3)
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
        length = self.socket.recv(3)
        if length == '':
            return False
        length = int(length)
        content = self.socket.recv(length)
        log (content)
        return content
    
    def close(self):
        self.socket.close()


class SyList(list):
    def __init__(self, input):
        if type(input) == str:
            del self[:]
            for entry in SyList(self.decode(input)):
                self.append(entry)
        else:
            list.__init__(self, input)
        
    
    def encode(self, data=None):
        if data == None:
            data = self
            
        with tempfile.TemporaryFile('w+') as file:
            pickle.dump(data, file)
            file.flush()
            file.seek(0)
        
            return file.read().replace('\n','|')
        
    
    def decode(self, input):
        with tempfile.TemporaryFile('w+') as file:
            file.write(input.replace('|','\n'))
            file.flush()
            file.seek(0)
            decoded = pickle.load(file)
            return SyList(decoded)
        

class SyConn(connection):
    def __init__(self, list, type='Blocking', timeout=5):
        connection.__init__(self, timeout)
        self.list = SyList(list)
        self.ctype = type
    
    def __repr__(self):
        return '<connection: %s>\n<list: %s>' % (self.sock, self.list)
    
    def sendList(self):
        self.send(self.list.encode ())
    
    def recvList(self):
        if self.ctype == 'Blocking':
            input = self.recive()
            return SyList(input)
        else:
            input = self.reciveone()
            if input == '': return
            return SyList(input)

if TESTING:
    a = SyConn([random.randrange(x + 12) for x in range(0,4)])