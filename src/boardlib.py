import socket
import select
import sys
import time
import pickle
import tempfile
import random

TESTING = True
LOGLEVEL = "Verbose"

global IP

if not TESTING:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('google.com',0))

    IP = s.getsockname()[0]

    del s
else:
    IP = '127.0.0.1'

global port
port = 1772


def log(*args):
    for arg in args:
        sys.stderr.write(str(arg))
    sys.stderr.write('\n')

def funcDec(f):
    if LOGLEVEL == "Verbose":
        log("Running " + str(f))
    return f


class NetworkError(Exception): pass

class Shutdown(Exception): pass

class connection(socket.socket):
    @funcDec
    def __init__(self, timeout = 5):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.timeout = timeout
        self.moving = 0
    
    @funcDec
    def setServer(self):
        self.Type = 'Server'
        self.bind((IP, port))
        self.listen(1)
        (self, null) = self.accept()
        del null
        self.setblocking(0)
    
    @funcDec
    def setClient(self, address):
        self.Type = 'Client'
        self.connect((address, port))
        self.setblocking(0)
    
    @funcDec
    def check(self, timeout = 0):
        readable, null, null = select.select([self], [], [], timeout)
        null, writeable, null = select.select([], [self], [], timeout)
        null, null, errorable = select.select([], [], [self], timeout)
        del null
        
        if bool(errorable): raise NetworkError
        
        return (bool(readable), bool(writeable))
    
    @funcDec
    def send(self, content):
        class ToLong(Exception): pass
        length = len(content)
        if length > 100:
            raise ToLong
        if length < 10:
            length = '0' + str(length)
        else:
            length = str(length)
        log(content)
        socket.socket.send(self, str(length) + content)
    
    @funcDec
    def recive(self):
        if self.check()[0]:
            self.moving += 1
            log(self.moving)
            if self.moving >= self.timeout:
                raise Shutdown
        else:
            self.moving = 0
        while not self.check()[0]:
            time.sleep(0.1)
        length = self.recv(2)
        try:
            length = int(length)
        except ValueError:
            raise Shutdown
        content = self.recv(length)
        log (content)
        return content
    
    @funcDec
    def reciveone(self):
        if self.check()[0]:
            self.moving += 1
            log(self.moving)
            if self.moving >= self.timeout:
                raise Shutdown
        else:
            self.moving = 0
            return False
        length = self.recv(2)
        if length == '':
            return False
        length = int(length)
        content = self.recv(length)
        log (content)
        return content
    
    @funcDec
    def close(self):
        socket.socket.close(self)


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
            data = self[:]
            
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
        

class SyConn(SyList, connection):
    def __init__(self, list, type='Blocking', timeout=5):
        SyList.__init__(self, list)
        connection.__init__(self, timeout)
        
        self.ctype = type
    
    def __repr__(self):
        return '<connection: %s>\n<list: %s>' % (self.sock, self[:])
    
    def sendList(self):
        self.send(self.encode())
    
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