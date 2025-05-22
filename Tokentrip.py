import time


class Token:
    pass

class Node:
    def __init__(self, apelido: str, right_node: 'Node', msgs: list[str]):
        self.apelido = apelido
        self.right_node = right_node
        self.msgs = msgs


class Ring:
    def __init__(self, nodes: list[Node], token: Token):
        self.nodes = nodes
        self.token = token

    def _generate_token(self):
        token = "9000"
        self._send_message(token, self.config['next_ip'], self.config['next_port'])
        self.last_token_time = time.time()

    def _send_message(self, message: str, ip: str, port: int):
        pass

    def _receive_messages(self):
        pass


def main():
    pass

if __name__ == "__main__":
    main()