from threading import Thread, Lock
import random
import socket
import time
import json
import sys


class Runner:
    def __init__(self, _id, host, port, chance, others):
        self.stop = False
        self.clock = 0
        self._id = _id
        self.chance = chance
        self.others = others
        self.size = len(others) - 1

        self.clock_lock = Lock()

        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender.bind((host, port+1))
        self.sender.settimeout(2)

        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind((host, port))

        self.synchronize()

        self.listener.settimeout(2)
        del self.others[self._id//2]

    def wait_oks(self):
        for _ in range(self.size):
            _, addr = self.listener.recvfrom(2)
            self.listener.sendto('.'.encode('utf-8'), addr)

    def synchronize(self):
        waiting_thread = Thread(target=self.wait_oks, daemon=True)
        waiting_thread.start()

        for other_id, other_addr in self.others:
            if other_id != self._id:
                while True:
                    try:
                        self.sender.sendto('..'.encode('utf-8'), other_addr)
                        self.sender.recv(1)
                        break
                    except:
                        pass

        waiting_thread.join()

    def start(self):
        listen_thread = Thread(target=self.listen, daemon=True)
        listen_thread.start()
        for _ in range(100):
            time.sleep(random.uniform(0.5, 1))

            local_time = time.time()
            if random.uniform(0, 1) < self.chance:
                choice = self.others[random.randrange(0, self.size)]

                self.clock_lock.acquire()
                self.clock += 1

                self.sender.sendto(f'{self._id}  {self.clock}'.encode('utf-8'), choice[1])
                print(f'{local_time}  {self._id}  `{self.clock}`{self._id}`  S  {choice[0]}')

            else:
                self.clock_lock.acquire()
                self.clock += 1

                print(f'{local_time}  {self._id} `{self.clock}`{self._id}`  L')

            self.clock_lock.release()

        self.stop = True
        listen_thread.join()

    def listen(self):
        while not self.stop:
            try:
                msg = self.listener.recv(4096).decode('utf-8')

                self.clock_lock.acquire()

                other_id, other_clock = map(int, msg.split('  '))
                if other_clock > self.clock:
                    self.clock = other_clock

                self.clock += 1
                print(f'{time.time()}  {self._id}  `{self.clock}`{self._id}`  R  {msg}')

                self.clock_lock.release()

            except socket.timeout:
                pass


def run_multiple(_id, _processes_number):
    others = [(j, ('127.0.0.1', 60000 + j)) for j in range(0, _processes_number*2, 2)]
    Runner(_id, '127.0.0.1', 60000 + _id, 0.2, others).start()


def run_config(config_file):
    with open(config_file, 'r') as file:
        json_file = json.load(file)
        _id = json_file['id']
        host = json_file['host']
        port = json_file['port']
        chance = json_file['chance']
        others = [(other_id, tuple(other_addr)) for other_id, other_addr in json_file['others']]

        Runner(_id, host, port, chance, others).start()


if __name__ == '__main__':
    processes_number = int(sys.argv[1])

    if processes_number == 0:
        run_config(sys.argv[2])
    else:
        import multiprocessing

        processes = []
        for i in range(0, processes_number * 2, 2):
            p = multiprocessing.Process(target=run_multiple, args=(i, processes_number), daemon=True)
            processes.append(p)
            p.start()

        for p in processes:
            p.join()
