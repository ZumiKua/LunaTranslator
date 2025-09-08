from textio.textsource.textsourcebase import basetext
from myutils.wrapper import threader
import socket, time, errno, struct, json, select, os, gobject

class vieetext(basetext):
    def init(self):
        self.startsql(gobject.gettranslationrecorddir("0_viee.sqlite"))
        self.tcpthread()
        pass

    def connect(self, sock, address):
        try:
            sock.connect(address)
        except socket.error as e:
            if(e.errno != errno.EINPROGRESS and e.errno != errno.WSAEWOULDBLOCK):
                raise e
        
        while not self.ending:
            _, writable, __ = select.select([], [sock], [], 0)
            if(writable):
                err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err == 0:
                    return True
                else:
                    raise socket.error(err, os.strerror(err))
            
        return False;

    def recv_all(self, sock, n):
        buffer = bytearray(n)
        view = memoryview(buffer)
        total_received = 0        
        while not self.ending and total_received < n:
            try:
                bytes_received = sock.recv_into(view[total_received:])
                if not bytes_received:
                    raise ConnectionAbortedError("EOF Reached")
                total_received += bytes_received
            except socket.error as e:
                if(e.errno == errno.EINPROGRESS or e.errno == errno.WSAEWOULDBLOCK):
                    continue;
        if(total_received < n):
            return None
        # 将 bytearray 转换为不可变的 bytes 对象并返回
        return buffer


    @threader
    def tcpthread(self):
        client_socket = None
        server_address = ("127.0.0.1", 42184)
    
        try:
            while not self.ending:
                try:
                    if(client_socket == None):
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.setblocking(False)
                        if(not self.connect(client_socket, server_address)):
                            continue;
                    sizeBuf = self.recv_all(client_socket, 4)
                    if(sizeBuf == None):
                        continue
                    len = struct.unpack('i', sizeBuf)[0]
                    contentBuf = self.recv_all(client_socket, len)
                    if(contentBuf == None):
                        continue
                    json_string = contentBuf.decode('utf-8')
                    data = json.loads(json_string)
                    if(data['Type'] == 0 and data['Text']):
                        # is it safe to call dispatchtext in another thread? ocrtext did this too...
                        self.dispatchtext(data['Text'])
                except (socket.error, UnicodeDecodeError, json.JSONDecodeError) as e:
                    print(e)
                    client_socket.close()
                    client_socket = None
                    if(not self.ending):
                        time.sleep(0.1) 
        finally:
            if(client_socket != None):
                client_socket.close()
                

