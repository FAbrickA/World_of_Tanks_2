import socket
from server import ServerKeys
from threading import Thread
import pickle


class Network(Thread):
    def __init__(self, server="127.0.0.1", port=5555):
        super().__init__()
        self.daemon = True
        self.delay = 0.1
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = server
        self.port = port
        self.addr = (self.server, self.port)
        # self.client.bind(self.addr)
        self.id = 0
        data = self.connect()
        if data and data['key'] == ServerKeys.CONNECTED:
            self.id = data['data']
        self.last_data = None
        self.data_to_send = None
        self.working = True

    def run(self):
        while self.working:
            response = self.get_info_pickle()
            if response:
                self.last_data = response
            # sleep(self.delay)

    def stop(self):
        self.working = False
        self.client.close()

    def get_last_data(self):
        data = self.last_data
        self.last_data = None
        return data

    def connect(self):
        try:
            self.client.connect(self.addr)
            return self.get_info_pickle()
        except:
            pass

    def get_info_pickle(self):
        try:
            return pickle.loads(self.client.recv(131072))
        except:
            pass

    def get_info_str(self):
        try:
            return self.client.recv(131072).decode()
        except:
            pass

    def send_str(self, *data):
        response = " ".join(map(str, data)) + "\n"
        try:
            self.client.send(str.encode(response))
            # return self.client.recv(2048).decode()
        except socket.error as e:
            print(e)
            raise Exception

    def send_pickle(self, data):
        try:
            self.client.send(pickle.dumps(data))
            # return self.client.recv(2048).decode()
        except socket.error as e:
            print(e)
            raise Exception


if __name__ == '__main__':
    n = Network()
    while True:
        print(n.get_info_pickle())
        n.send_str(input())
