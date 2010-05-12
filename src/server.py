import select
import socket
import threading
import time

IP = ""
PORT = 0

class Server(object):
    def __init__(self, options):
        self._options = options
        self._sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM)
        self._events = EventPool()
        self._threads = ThreadPool(self._events)
        
        self._sock.bind((IP, PORT))
        self._sock.listen(self._options["Players"])
        
    def run(self):
        while len(self.Sockets > self._options["Players"]):
            (clientsocket, address) = self._sock.accept()
            self._threads.addThread(ClientThread, address, clientsocket)
            self._thread.runThread(address)


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



class EventPool(object):
    def __init__(self, threadpool):
        self._queues = {}
        self._shutdown = False
    
    def addThread(self, thread):
        self._queues[thread.id] = []
    
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
            self._checkinterupted()
    
    def interupt(self):
        self._interupted = True
    
    def resume(self):
        self._interupted = False
    
    def kill(self):
        self._killed = True
    
    def _checkinterupted(self):
        while self._interupted:
            time.sleep(0.1)
    
    def _read(self):
        if self.check()[0]:
            self._moving += 1
            if self._moving >= self._options["Timeout"]:
                raise RuntimeError
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
        
        if bool(errorable): raise RuntimeError
        
        return (bool(readable), bool(writeable))