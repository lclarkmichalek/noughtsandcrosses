import select
import socket
import threading
import time
import json
class Server(object):
    def __init__(self, address, options):
        self._options = options
        self._address = address
        
        self._epool = EventPool()
        self._tpool = ThreadPool(self._epool)
    
    def start(self):
        self._tpool.addThread(ServerThread, 'Server', self._address,
                              self._options)
        self._tpool.runThread('Server')
    
    def stop(self):
        self._tpool.killAll()

    

class ThreadPool(object):
    def __init__(self, eventpool):
        self._threads = {}
        self._epool = eventpool
    
    def addThread(self, thread, id, *args, **kwargs):
        self._threads[id] = thread(*args, **kwargs)
        self._threads[id].id = id
        self._threads[id]._tpool = self
        self._threads[id]._epool = self._epool
        self._epool.addThread(self._threads[id])
    
    def runThread(self, id):
        self._threads[id].start()
    
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
    
    def killAll(self):
        #Can't use iterations because dict changes size when
        #threads are deleted
        while len(self._threads):
            self.killThread(self._threads.keys()[0], 1)



class EventPool(object):
    def __init__(self):
        self._queues = {}
        self._shutdown = False
    
    def addThread(self, thread):
        self._queues[thread.id] = []
    
    def removeThread(self, id):
        del self._queues[id]
    
    def addEvent(self, event):
        if self._shutdown: return
        
        print event.toJson()
        
        for id in event.recipients:
            if not id in self._queues.keys():
                raise RuntimeError("Message addressed to unknown recipient")
        
        event.sender = threading.currentThread().id
        
        for id in event.recipients:
            self._queues[id].appent(event)
        
        del event.recipients
        del event.priority
    
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
    def __init__(self, Header="", Content=[], Recipients=[], Priority=0):
        self.header = Header
        self.content = Content
        self.recipients = Recipients
        self.priority = Priority
    
    def toJson(self):
        message = json.dumps([self.header,self.content,self.recipients,
                              self.priority])
        return message

class ServerThread(threading.Thread):
    def __init__(self, address, options):
        threading.Thread.__init__(self)
        self._options = options
        
        self._sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM)
        
        self._sock.bind(address)
        self._sock.listen(self._options["Players"])
        self._killed = False
        
        self._noConnected = 0
        
    def run(self):
        while not self._killed:
            if self._noConnected < self._options["Players"]:
                (clientsocket, address) = self._sock.accept()
                self._tpool.addThread(ClientThread, address, clientsocket)
                self._tpool.runThread(address)
                self._noConnected += 1
            else:
                time.sleep(1)
    
    def threadDisconnected(self):
        self._noConnected -= 1
    
    def interupt(self):
        pass
    
    def kill(self):
        self._killed = True



class ClientThread(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self._sock = socket
        self._sock.setblocking(0)
        self._moving = 0
        self._options = {'Timeout': 1}
    
    def run(self):
        self._interupted = False
        self._killed = False
        
        
        while not self._checkRun():
            
            input = self._read()
            if input is not '':
                print input
                self._addEvent(input)
            
            if self._checkRun(): break
            
            if self._epool.queuedEvents() > 0:
                event = self._epool.nextEvent()
                if event.header == "snd":
                    self._write(event.toJson())
                elif event.header == "strdat":
                    self._data[event.content["key"]] = event.content["value"]
                elif event.header == "rqstdat":
                    key = event.content["key"]
                    value = event.content["value"]
                    ev = Event(Header = "snddat", recipients = [event.sender])
                    ev.content = {value: key}
                    self._epool.addEvent(ev)
                elif event.header == "snddat":
                    self._write(event.toJson())
                
                
    
    def interupt(self):
        self._interupted = True
    
    def resume(self):
        self._interupted = False
    
    def kill(self):
        self._killed = True
    
    def _addEvent(self, input):
        ev = json.loads(input)
        self._epool.addEvent(Event(Header = ev[0], Content = ev[1],
                                   Recipients = ev[2], Priority = ev[3]))
    
    def _checkRun(self):
        while not (self._killed | self._interupted):
            if self._killed: return True
            elif self._interupted:
                time.sleep(0.1)
        return False
    
    def _read(self):
        if self._check()[0]:
            self._moving += 1
            if self._moving >= self._options["Timeout"]:
                raise RuntimeError("ClientThread %s timeout" % str(self.id))
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
                    "ClientThread %s socket raised error" % self.id)
        
        return (bool(readable), bool(writeable))
