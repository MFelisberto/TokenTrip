import socket
import threading
import time
import queue
import random
import crcmod
import json
from typing import Dict, Optional

class RingNode:
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self.message_queue = queue.Queue(maxsize=10)
        self.token_timeout = 5  # tempo máximo para o token voltar
        self.last_token_time = 0
        self.is_token_generator = self.config['is_token_generator']
        self.running = True
        
        # Configuração do CRC32
        self.crc32_func = crcmod.predefined.mkCrcFun('crc-32')
        
        # Configuração do socket UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.config['port']))
        
        # Iniciar threads
        self.receive_thread = threading.Thread(target=self._receive_messages)
        self.token_control_thread = threading.Thread(target=self._control_token)
        self.receive_thread.start()
        self.token_control_thread.start()
        
        if self.is_token_generator:
            self._generate_token()

    def _load_config(self, config_file: str) -> Dict:
        with open(config_file, 'r') as f:
            line = f.readline().strip().split()
            return {
                'next_ip': line[0].split(':')[0],
                'next_port': int(line[0].split(':')[1]),
                'nickname': line[1],
                'token_time': int(line[2]),
                'is_token_generator': line[3].lower() == 'true'
            }

    def _generate_token(self):
        token = "9000"
        self._send_message(token, self.config['next_ip'], self.config['next_port'])
        self.last_token_time = time.time()

    def _send_message(self, message: str, ip: str, port: int):
        self.socket.sendto(message.encode(), (ip, port))

    def _receive_messages(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                message = data.decode()
                
                if message == "9000":  # Token
                    self._handle_token()
                elif message.startswith("7777:"):  # Pacote de dados
                    self._handle_data_packet(message)
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")

    def _handle_token(self):
        current_time = time.time()
        
        if self.is_token_generator:
            if current_time - self.last_token_time < self.config['token_time']:
                print("ALERTA: Múltiplos tokens detectados!")
                return
            elif current_time - self.last_token_time > self.token_timeout:
                print("ALERTA: Token perdido detectado!")
                self._generate_token()
                return
        
        self.last_token_time = current_time
        
        if not self.message_queue.empty():
            message = self.message_queue.get()
            self._send_data_packet(message)
        else:
            time.sleep(self.config['token_time'])
            self._send_message("9000", self.config['next_ip'], self.config['next_port'])

    def _handle_data_packet(self, packet: str):
        parts = packet[5:].split(';')
        status, origin, destination, crc, message = parts
        
        if destination == self.config['nickname'] or destination == "TODOS":
            # Recalcular CRC
            calculated_crc = self.crc32_func(message.encode())
            if calculated_crc != int(crc):
                status = "NACK"
            else:
                status = "ACK"
                print(f"Mensagem de {origin}: {message}")
            
            # Enviar resposta
            response = f"7777:{status};{origin};{destination};{crc};{message}"
            self._send_message(response, self.config['next_ip'], self.config['next_port'])
        else:
            # Repassar o pacote
            self._send_message(packet, self.config['next_ip'], self.config['next_port'])

    def _send_data_packet(self, message_data: Dict):
        message = message_data['message']
        destination = message_data['destination']
        
        # Calcular CRC
        crc = self.crc32_func(message.encode())
        
        # Criar pacote
        packet = f"7777:naoexiste;{self.config['nickname']};{destination};{crc};{message}"
        
        # Simular erro aleatório (10% de chance)
        if random.random() < 0.1:
            packet = packet[:-1] + "X"  # Corromper último caractere
        
        self._send_message(packet, self.config['next_ip'], self.config['next_port'])

    def _control_token(self):
        while self.running:
            if self.is_token_generator:
                current_time = time.time()
                if current_time - self.last_token_time > self.token_timeout:
                    print("ALERTA: Token perdido detectado!")
                    self._generate_token()
            time.sleep(1)

    def send_message(self, message: str, destination: str):
        if self.message_queue.full():
            print("Fila de mensagens cheia!")
            return
        
        self.message_queue.put({
            'message': message,
            'destination': destination
        })

    def stop(self):
        self.running = False
        self.socket.close()
        self.receive_thread.join()
        self.token_control_thread.join()

if __name__ == "__main__":
    # Exemplo de uso
    node = RingNode("config.txt")
    
    try:
        while True:
            command = input("Digite 'enviar' para enviar uma mensagem ou 'sair' para terminar: ")
            if command == "enviar":
                message = input("Digite a mensagem: ")
                destination = input("Digite o destino (ou 'TODOS' para broadcast): ")
                node.send_message(message, destination)
            elif command == "sair":
                break
    finally:
        node.stop() 