import socket
import threading
import queue
import time
import random
import binascii
import json
from typing import Optional, Tuple, Any
from datetime import datetime

TOKEN_VALUE = "9000"
DATA_PACKET_VALUE = "7777"
MAX_QUEUE_SIZE = 10
TOKE_TIMEOUT = 100
BROADCAST_DESTINATION = "TODOS"

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

class TokenRingNode:
    def __init__(self, config_file: str, my_addr: str): 
        """Construtor"""
        # ===== Atributos =====
        self.config = self.load_config(config_file)
        self.message_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.next_port = int(self.config['next_node'].split(':')[1])
        
        # socket -> bind na porta que vem antes da porta do proximo nó
        # supondo que nao estamos usando nada reservado
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((my_addr.split(':')[0], int(my_addr.split(':')[1])))

        self.running = True
        self.has_token = False
        self.last_token_time = 0
        self.token_timeout = TOKE_TIMEOUT
        self.token_started = False 
        # =====================
        
        print(f"[{get_timestamp()}] {'='*50}")
        print(f"[{get_timestamp()}] Node {self.config['apelido']} inicializado")
        print(f"[{get_timestamp()}] Escutando na porta: {self.next_port - 1}")
        print(f"[{get_timestamp()}] Próximo node: {self.config['next_node']}")
        print(f"[{get_timestamp()}] Gerador de token: {self.config['is_token_generator']}")
        print(f"[{get_timestamp()}] {'='*50}")
        print("\n")
        
    
    def load_config(self, config_file: str) -> dict[str, Any]:
        """Carregar config do arquivo"""

        with open(config_file, 'r') as f:
            linhas = f.readlines()
            return {
                'next_node': linhas[0].strip(),
                'apelido': linhas[1].strip(),
                'token_time': int(linhas[2].strip()),
                'is_token_generator': linhas[3].strip().lower() == 'true'
            }
    
    
    def calculate_crc32(self, data: str) -> str:
        """Calcula o CRC32 para os dados fornecidos"""
        return str(binascii.crc32(data.encode()))
    

    def create_data_packet(self, destination: str, message: str) -> str:
        """Cria um pacote de dados com o formato especificado"""
        
        data = (
            f"{DATA_PACKET_VALUE}:naoexiste;"
            f"{self.config['apelido']};"
            f"{destination};"
            f"{self.calculate_crc32(message)};"
            f"{message}"
        )

        return self.inject_error(data)
    
    
    def parse_data_packet(self, packet: str) -> Optional[Tuple[str, str, str, str, str]]:
        """Analisa um pacote de dados no formato 'DATA:<campo1>;<campo2>;<campo3>;<campo4>;<campo5>'"""

        try:
            prefix, data = packet.split(':', 1)
            if prefix != DATA_PACKET_VALUE: return None

            campos = data.split(';')
            if len(campos) != 5: return None

            return tuple(campos)
        except Exception:
            return None


    
    def send_token(self):
        """Enviar o token para o próximo node"""

        try:
            next_ip, next_port = self.config['next_node'].split(':')
            
            time.sleep(3)  # DELAY PARA TESTE
            
            # Envia o token
            self.socket.sendto(TOKEN_VALUE.encode(), (next_ip, int(next_port)))
            self.has_token = False # agora n tenho mais o token
            
            print(f"[{get_timestamp()}] TOKEN: Enviado para {next_ip}:{next_port}")
        except Exception as e:
            print(f"[{get_timestamp()}] ERROR: Erro ao enviar token - {e}")
    

    def handle_token(self):
        """Controle de recebimento do token"""

        # agora tenho o token
        # tempo vai para 0
        self.has_token = True
        self.last_token_time = time.time()
        print(f"[{get_timestamp()}] TOKEN: Recebido")
        
        if not self.message_queue.empty():
            destination, message = self.message_queue.get()          # proximo destino e mensagem
            packet = self.create_data_packet(destination, message)   # cria o pacote de dados
            self.send_data_packet(packet)                            # envia o pacote de dados
            # segura o token até receber o ACK ou NACK
        else:
            # Se não tem mensagem para enviar, passa o token
            # espera o tempo do token
            time.sleep(self.config['token_time'])
            self.send_token()               
    
    
    def send_data_packet(self, packet: str):
        """Envia um pacote de dados para o próximo node no anel"""

        try:
            next_ip, next_port = self.config['next_node'].split(':')

            # Envia o pacote de dados
            self.socket.sendto(packet.encode(), (next_ip, int(next_port)))

            print(f"[{get_timestamp()}] DATA: Enviado para {next_ip}:{next_port}")
        except Exception as e:
            print(f"[{get_timestamp()}] ERROR: Falha ao enviar os dados - {e}")
    
    def handle_data_packet(self, packet: str):
        """Processa um pacote de dados recebido"""

        parsed = self.parse_data_packet(packet)  # parse do pacote
        if not parsed: return                    # vazio ou inválido
        
        status, origin, destination, crc, message = parsed 
        
        # Estamos no destino ou é um broadcast
        # Verifica se o CRC está correto
        # atualiza o status do pacote
        # e envia ACK ou NACK
        if destination == self.config['apelido'] or destination == BROADCAST_DESTINATION:
            calculated_crc = self.calculate_crc32(message) 
            if calculated_crc != crc:                      
                status = "NACK"
                print(f"[{get_timestamp()}] DATA: Erro detectado na menssagem de {origin}")
            else:
                status = "ACK"
                print(f"[{get_timestamp()}] MESSAGE: De {origin}: {message}")
            
            packet = f"{DATA_PACKET_VALUE}:{status};{origin};{destination};{crc};{message}"
        
        # Nao estamos no destino, mas recebemos o pacote
        # se formos nos que enviamos, processamos
        # senao encaminhamos para o próximo node
        if origin == self.config['apelido']:
            
            if status == "ACK":
                print(f"[{get_timestamp()}] MESSAGE ACK: Enviada com sucesso para {destination}")    
                
                # Só passa o token depois de receber o ACK
                time.sleep(self.config['token_time'])
                self.send_token()
            
            elif status == "NACK":
                print(f"[{get_timestamp()}] MESSAGE NACK: Precisa de retransmissao para {destination}")
                
                # Recoloca a mensagem na fila para retransmissão
                self.message_queue.put((destination, message))
                
                # Passa o token para tentar novamente
                time.sleep(self.config['token_time'])
                self.send_token()
            
            elif status == "naoexiste":
                print(f"[{get_timestamp()}] MESSAGE: Destino {destination} nao encontrado")
                
                # Passa o token já que o destino não existe
                time.sleep(self.config['token_time'])
                self.send_token()
        else:
            # Envia o pacote para o proximo node
            self.send_data_packet(packet)
    
    def start(self):
        """START"""

        # Começa a ouvir pacotes em uma thread separada
        receive_thread = threading.Thread(target=self._receive_loop)
        receive_thread.daemon = True
        receive_thread.start()
        
        # Começa a monitorar o token se for o gerador
        # em outra thread
        if self.config['is_token_generator']:
            monitor_thread = threading.Thread(target=self._monitor_token)
            monitor_thread.daemon = True
            monitor_thread.start()
        
        print(f"[{get_timestamp()}] {'='*50}")
        print(f"[{get_timestamp()}] Comandos disponiveis:")
        print(f"[{get_timestamp()}] - start (apenas o gerador de token)")
        print(f"[{get_timestamp()}] - send <destino> <menssagem>")
        print(f"[{get_timestamp()}] - quit")
        print(f"[{get_timestamp()}] {'='*50}")
        print("\n")


        # Loop principal para receber comandos do usuario
        while self.running:
            
            try:
                # linha de comando
                command = input(f"[{self.config['apelido']}] > ")
                
                # quit
                if command.lower() == 'quit':
                    self.running = False
                
                # start
                elif command.lower() == 'start' and self.config['is_token_generator'] and not self.token_started:
                    print(f"[{get_timestamp()}] {'='*50}")
                    print(f"[{get_timestamp()}] Starting token circulation...")
                    print(f"[{get_timestamp()}] {'='*50}")
                    
                    self.token_started = True
                    self.has_token = True
                    self.last_token_time = time.time()
                    self.send_token()
                
                # send <destination> <message>
                elif command.lower().startswith('send '):
                    parts = command.split(' ', 2)
                    
                    if len(parts) == 3:
                        destination, message = parts[1], parts[2]
                        
                        if self.message_queue.qsize() < MAX_QUEUE_SIZE:
                            self.message_queue.put((destination, message))
                            print(f"[{get_timestamp()}] MESSAGE: na fila para {destination}")
                        else:
                            print(f"[{get_timestamp()}] ERROR: Fila de mensagens cheia (max {MAX_QUEUE_SIZE})")
            except KeyboardInterrupt:
                self.running = False
    
    def _receive_loop(self):
        """Loop principal para receber pacotes"""
        
        while self.running:
            
            try:
                data, addr = self.socket.recvfrom(1024)
                packet = data.decode()
                
                # se o pacote é o token
                if packet == TOKEN_VALUE:
                    self.handle_token()
                # se o pacote é um pacote de dados
                else:
                    self.handle_data_packet(packet)
            except Exception as e:
                if self.running:
                    print(f"[{get_timestamp()}] ERROR: Falha ao recever o pacote - {e}")
    

    def _monitor_token(self):
        """Monitora a circulação do token para o gerador de token"""


        while self.running:
            
            time.sleep(1)
            
            # Token iniciado
            # mas o timeout para o token foi passado
            # geramos um novo
            if self.token_started and time.time() - self.last_token_time > self.token_timeout:
                
                print(f"[{get_timestamp()}] {'='*50}")
                print(f"[{get_timestamp()}] WARNING: Tempo do token expirado!")
                print(f"[{get_timestamp()}] Gerando um novo token...")
                print(f"[{get_timestamp()}] {'='*50}")
                self.has_token = True
                self.last_token_time = time.time()
                self.send_token()

    
    def inject_error(self, data: str, probability: float = 0.1) -> str:
        """Aleatoriamente injeta erros nos dados com a probabilidade fornecida"""

        if random.random() < probability:
            # troca uma caracter aleatório
            pos = random.randint(0, len(data) - 1)
            data = data[:pos] + chr(ord(data[pos]) + 1) + data[pos + 1:]
        return data


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Uso: python Tokentrip.py <config_file> <meu_ip:meu_porta>")
        sys.exit(1)

    node = TokenRingNode(sys.argv[1], sys.argv[2])

    node.start()