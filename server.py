import socket
from _thread import start_new_thread
from threading import Thread
import pickle


class ServerKeys:
    CONNECTED = 1
    MAKE_BULLET = 2
    CREATE_PLAYER = 3
    WAIT_FOR_INFORMATION = 4
    SUCCESS = 5
    NO_UPDATE = 6
    UPDATED = 7
    NEW_INFORMATION = 8
    NEW_INFORMATION_LOBBY = 9
    START_GAME = 10
    COUNT_FOR_START = 11
    PREPARATION_FOR_START = 12
    RESTART = 13
    NEED_RESTART = 14

    TURRET_CLASSIC = 1
    TURRET_SHOTGUN = 2
    TURRET_MINIGUN = 3

    BULLET_CLASSIC = 1
    BULLET_SHOTGUN = 2
    BULLET_MINIGUN = 3


class Server(Thread):
    def __init__(self, server="127.0.0.1", port=5555):
        super().__init__()
        self.daemon = True
        self.server = server
        self.port = port
        self.stopped = False
        self.ids = []
        self.last_id = 0
        self.players = dict()
        self.bullets = dict()
        self.players_lobby = dict()
        self.game_start = False
        self.s = None
        self.last_seed = None
        self.need_restart = False

    def run(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.bind((self.server, self.port))
        except socket.error as e:
            print(e)

        self.s.listen(4)
        print("Waiting for connection...")

        while not self.stopped:
            conn, addr = self.s.accept()
            print("Connected to", addr)

            start_new_thread(self.threaded_client, (conn,))

    def stop(self):
        self.stopped = True
        self.s.close()

    def send(self, conn, reply):
        return conn.send(str.encode(str(reply)))

    def send_bytes(self, conn, reply):
        return conn.send(pickle.dumps(reply))

    def create_player(self, player_id, player):
        self.players[player_id] = player

    def create_bullet(self, player_id, bullet):
        self.bullets[player_id] = self.bullets.get(player_id, []) + [bullet]

    def get_players(self, player_id):
        players = []
        for player_id_now, player in self.players.items():
            if player_id == player_id_now:
                continue
            players.append(player)
        return players

    def get_info(self, player_id):
        info_players = self.get_players(player_id)
        info_bullets = self.get_bullets(player_id)
        return {
            "players": info_players,
            "bullets": info_bullets
        }

    def update_player(self, player_id, player):
        self.players[player_id] = player

    def update_bullets(self, player_id, bullets):
        self.bullets[player_id] = bullets

    def update_all(self, player_id, info):
        self.update_player(player_id, info["player"])
        self.update_bullets(player_id, info["bullets"])

    def get_bullets(self, player_id):
        bullets_all = []
        for player_id_now, bullets in self.bullets.items():
            if player_id == player_id_now:
                continue
            bullets_all.extend(bullets)
        return bullets_all

    def add_player_lobby(self, player_id, nickname):
        self.players_lobby[player_id] = nickname

    def check_players_none(self):
        players = list(self.players.values())
        if len(players) < 2:
            if None in players:
                return True
            return False
        if players.count(None) >= len(players) - 1:
            return True
        return False

    def threaded_client(self, conn):
        self.last_id += 1
        self.ids.append(self.last_id)
        self.send_bytes(conn, {
            'key': ServerKeys.CONNECTED,
            'data': self.last_id,
        })
        while True:
            try:
                # self.send(conn, "123")
                data = conn.recv(131072)
                reply = pickle.loads(data)
                # if not data:
                #     break
                self.handle_reply(conn, reply)
                # conn.sendall(str.encode(reply))
            except Exception as e:
                print(e)
                break
        conn.close()

    def handle_reply(self, conn, reply: dict):
        if not reply:
            return
        key, response = reply['key'], reply['data']
        if key == ServerKeys.WAIT_FOR_INFORMATION:
            # player_id = int(response[:response.find(" ")])
            player_id = response['player_id']
            return
            pass
        elif key == ServerKeys.CREATE_PLAYER:
            self.need_restart = False
            player_id = reply['player_id']
            player = response
            self.create_player(player_id, player)
        elif key == ServerKeys.MAKE_BULLET:
            player_id = reply['player_id']
            bullet = response
            self.create_bullet(player_id, bullet)
            self.send_bytes(conn, {
                'key': ServerKeys.SUCCESS,
                'data': None
            })
        elif key == ServerKeys.NEW_INFORMATION:
            player_id = reply['player_id']
            info = response
            self.update_all(player_id, info)
            need_restart = False
            if self.check_players_none():
                need_restart = True
            if self.need_restart:
                self.send_bytes(conn, {
                    'key': ServerKeys.RESTART,
                    'data': self.last_seed,
                })
            else:
                self.send_bytes(conn, {
                    'key': ServerKeys.NEW_INFORMATION,
                    'data': self.get_info(player_id),
                    'player_id': player_id,
                    'need_restart': need_restart
                })
        elif key == ServerKeys.NEW_INFORMATION_LOBBY:
            if not self.game_start:
                player_id = reply['player_id']
                info = response
                nickname = info['nickname']
                self.add_player_lobby(player_id, nickname)
                if not self.game_start:
                    self.send_bytes(conn, {
                        'key': ServerKeys.NEW_INFORMATION_LOBBY,
                        'data': self.players_lobby
                    })
            else:
                self.send_bytes(conn, {
                    'key': ServerKeys.START_GAME,
                    'data': {
                        'players': self.players_lobby,
                        'seed': self.last_seed
                    }
                })
        elif key == ServerKeys.START_GAME:
            self.game_start = True
            self.last_seed = response
            self.send_bytes(conn, {
                'key': ServerKeys.START_GAME,
                'data': {
                    'players': self.players_lobby,
                    'seed': self.last_seed
                }
            })
        elif key == ServerKeys.RESTART:
            self.last_seed = response
            self.need_restart = True
            self.players = dict()
            self.bullets = dict()


if __name__ == '__main__':
    server = Server()
    server.start()
