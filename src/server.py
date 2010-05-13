import select
import socket
import threading
import time
import json

IP = ""
PORT = 0

class Server(object):
    def __init__(self, options):
        self._options = options
        
        self._tpool = ThreadPool()
        self._epool = EventPool(self._tpool)
    
    def start(self):
        self._tpool.addThread(ServerThread, 'Server', self._options)

    

class ThreadPool(object):
    def __init__(self, eventpool):
        self._threads = {}
        self._epool = eventpool
    
    def addThread(self, thread, id, *args):
        self._threads[id] = thread(*args)
        self._threads[id].id = id
        self._threads[id]._tpool = self
        self._epool.addThread(self._threads[id])
    
    def startThread(self, id):
        self._threads[id].start()
        self._threads[id].status = "Running"
    
    def pauseThread(self, id):
        self._threads[id].interupt()
        self._threads[id].status = "Paused"
    
    def resumeThread(self, id):
        self._threads[id].resume()
        self._threads[id].status = "Running"
    
    def killThread(self, id, interval):
        self._threads[id].interupt()
        time.sleep(interval)
        self._threads[id].kill()
        time.sleep(interval)
        del self._threads[id]
        self._epool.removeThread(id)



class EventPool(object):
    def __init__(self, threadpool):
        self._queues = {}
        self._shutdown = False
    
    def addThread(self, thread):
        self._queues[thread.id] = []
    
    def removeThread(self, id):
        del self._queues[id]
    
    def addEvent(self, event):
        if self._shutdown: return
        
        for id in event.recipients:
            if not id in self._queues.keys():
                raise RuntimeError("Message addressed to unknown recipient")
        
        for id in event.recipients:
            self._queues[id].appent(event)
    
    def queuedEvents(self):
        id = threading.currentThread().id
        return len(self._queues[id])
    
    def nextEvent(self):
        id = threading.currentThread().id
        return self._queues[id].pop(0)
    
    def shutdown(self):
        self._shutdown = True
    
    def close(self, interval):
        self.shutdown()
        time.sleep(interval)
        del self



class Event(object):
    def __init__(self, Header="", Content="", Recipients=[], Priority=0):
        self.header = Header
        self.content = Content
        self.recipients = Recipients
        self.priority = Priority
    
    def toJson(self):
        message = json.dumps([self.header,self.content,self.recipients,self.priority])
        return message



class ServerThread(object):
    def __init__(self, options):
        self._sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM)
        
        self._sock.bind((IP, PORT))
        self._sock.listen(self._options["Players"])
        self._killed = False
        
    def run(self):
        while not self._killed:
            if len(self.Sockets > self._options["Players"]):
                (clientsocket, address) = self._sock.accept()
                self._tpool.addThread(ClientThread, address, clientsocket)
                self._tpool.runThread(address)
            else:
                time.sleep(1)
    
    def kill(self):
        self._killed = True



class ClientThread(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self._sock = socket
        self._sock.setblocking(0)
        self._moving = 0
    
    def run(self):
        self._interupted = False
        self._killed = False
        while not self._interupted:
            self._checkRun()
    
    def interupt(self):
        self._interupted = True
    
    def resume(self):
        self._interupted = False
    
    def kill(self):
        self._killed = True
    
    def _checkRun(self):
        while not (self._killed | self._interupted):
            if self._killed: return True
            elif self._interupted:
                time.sleep(0.1)
        return True
    
    def _read(self):
        if self.check()[0]:
            self._moving += 1
            if self._moving >= self._options["Timeout"]:
                raise RuntimeError("ClientThread %s timeout" % self.id)
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
        
        if bool(errorable): raise RuntimeError("ClientThread %s socket raised error" % self.id)
        
        return (bool(readable), bool(writeable))