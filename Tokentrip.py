import socket
import threading
import queue
import time
import random
import binascii
import json
from typing import Optional, Tuple
from datetime import datetime

# Constants
TOKEN_VALUE = "9000"
DATA_PACKET_VALUE = "7777"
MAX_QUEUE_SIZE = 10
BROADCAST_DESTINATION = "TODOS"

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

class TokenRingNode:
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self.message_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        
        # Extract port from next_node for binding
        next_ip, next_port = self.config['next_node'].split(':')
        self.next_port = int(next_port)
        
        # Create socket and bind to the port before the next node
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the port that comes before the next node's port
        bind_port = self.next_port - 1 if self.next_port > 6000 else 6002
        self.socket.bind(('', bind_port))
        print(f"\n[{get_timestamp()}] {'='*50}")
        print(f"[{get_timestamp()}] Node {self.config['nickname']} initialized")
        print(f"[{get_timestamp()}] Listening on port {bind_port}")
        print(f"[{get_timestamp()}] Next node: {self.config['next_node']}")
        print(f"[{get_timestamp()}] Token generator: {self.config['is_token_generator']}")
        print(f"[{get_timestamp()}] {'='*50}\n")
        
        self.running = True
        self.has_token = False
        self.last_token_time = 0
        self.token_timeout = 100  # Default timeout in seconds
        self.token_started = False
        
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from file."""
        with open(config_file, 'r') as f:
            lines = f.readlines()
            return {
                'next_node': lines[0].strip(),
                'nickname': lines[1].strip(),
                'token_time': int(lines[2].strip()),
                'is_token_generator': lines[3].strip().lower() == 'true'
            }
    
    def calculate_crc32(self, data: str) -> str:
        """Calculate CRC32 for the given data."""
        return str(binascii.crc32(data.encode()))
    
    def inject_error(self, data: str, probability: float = 0.1) -> str:
        """Randomly inject errors into the data with given probability."""
        if random.random() < probability:
            # Randomly change one character in the data
            pos = random.randint(0, len(data) - 1)
            data = data[:pos] + chr(ord(data[pos]) + 1) + data[pos + 1:]
        return data
    
    def create_data_packet(self, destination: str, message: str) -> str:
        """Create a data packet with the specified format."""
        data = f"{DATA_PACKET_VALUE}:naoexiste;{self.config['nickname']};{destination};{self.calculate_crc32(message)};{message}"
        return self.inject_error(data)
    
    def parse_data_packet(self, packet: str) -> Tuple[str, str, str, str, str, str]:
        """Parse a data packet into its components."""
        try:
            parts = packet.split(':')
            if len(parts) != 2 or parts[0] != DATA_PACKET_VALUE:
                return None
            
            fields = parts[1].split(';')
            if len(fields) != 5:
                return None
                
            return (fields[0], fields[1], fields[2], fields[3], fields[4])
        except:
            return None
    
    def send_token(self):
        """Send the token to the next node."""
        try:
            next_ip, next_port = self.config['next_node'].split(':')
            time.sleep(3)  # Adiciona um delay de 2 segundos antes de enviar o token
            self.socket.sendto(TOKEN_VALUE.encode(), (next_ip, int(next_port)))
            self.has_token = False
            print(f"[{get_timestamp()}] TOKEN: Sent to {next_ip}:{next_port}")
        except Exception as e:
            print(f"[{get_timestamp()}] ERROR: Failed to send token - {e}")
    
    def handle_token(self):
        """Handle receiving the token."""
        self.has_token = True
        self.last_token_time = time.time()
        print(f"[{get_timestamp()}] TOKEN: Received")
        
        if not self.message_queue.empty():
            # Get the next message from the queue
            destination, message = self.message_queue.get()
            packet = self.create_data_packet(destination, message)
            self.send_data_packet(packet)
            # Não envia o token aqui - ele será enviado quando receber o ACK
        else:
            # Se não tem mensagem para enviar, passa o token
            time.sleep(self.config['token_time'])  # Wait for the configured time
            self.send_token()
    
    def send_data_packet(self, packet: str):
        """Send a data packet to the next node."""
        try:
            next_ip, next_port = self.config['next_node'].split(':')
            self.socket.sendto(packet.encode(), (next_ip, int(next_port)))
            print(f"[{get_timestamp()}] DATA: Sent to {next_ip}:{next_port}")
        except Exception as e:
            print(f"[{get_timestamp()}] ERROR: Failed to send data - {e}")
    
    def handle_data_packet(self, packet: str):
        """Handle receiving a data packet."""
        parsed = self.parse_data_packet(packet)
        if not parsed:
            return
        
        status, origin, destination, crc, message = parsed
        
        # If we're the destination
        if destination == self.config['nickname'] or destination == BROADCAST_DESTINATION:
            # Recalculate CRC
            calculated_crc = self.calculate_crc32(message)
            
            # Check if there's an error
            if calculated_crc != crc:
                status = "NACK"
                print(f"[{get_timestamp()}] DATA: Error detected in message from {origin}")
            else:
                status = "ACK"
                print(f"[{get_timestamp()}] MESSAGE: From {origin}: {message}")
            
            # Atualiza o status no pacote antes de reenviar
            packet = f"{DATA_PACKET_VALUE}:{status};{origin};{destination};{crc};{message}"
        
        # If we're the origin
        if origin == self.config['nickname']:
            if status == "ACK":
                print(f"[{get_timestamp()}] MESSAGE: Successfully delivered to {destination}")
                # Só passa o token depois de receber o ACK
                time.sleep(self.config['token_time'])
                self.send_token()
            elif status == "NACK":
                print(f"[{get_timestamp()}] MESSAGE: Needs retransmission to {destination}")
                # Recoloca a mensagem na fila para retransmissão
                self.message_queue.put((destination, message))
                # Passa o token para tentar novamente
                time.sleep(self.config['token_time'])
                self.send_token()
            elif status == "naoexiste":
                print(f"[{get_timestamp()}] MESSAGE: Destination {destination} not found")
                # Passa o token já que o destino não existe
                time.sleep(self.config['token_time'])
                self.send_token()
        else:
            # Forward the packet
            self.send_data_packet(packet)
    
    def start(self):
        """Start the token ring node."""
        # Start listening for packets
        receive_thread = threading.Thread(target=self._receive_loop)
        receive_thread.daemon = True
        receive_thread.start()
        
        # Start token monitoring if we're the generator
        if self.config['is_token_generator']:
            monitor_thread = threading.Thread(target=self._monitor_token)
            monitor_thread.daemon = True
            monitor_thread.start()
        
        print(f"\n[{get_timestamp()}] {'='*50}")
        print(f"[{get_timestamp()}] Available commands:")
        print(f"[{get_timestamp()}] - start (only for token generator)")
        print(f"[{get_timestamp()}] - send <destination> <message>")
        print(f"[{get_timestamp()}] - quit")
        print(f"[{get_timestamp()}] {'='*50}\n")
        
        # Main loop for user input
        while self.running:
            try:
                command = input(f"[{self.config['nickname']}] > ")
                if command.lower() == 'quit':
                    self.running = False
                elif command.lower() == 'start' and self.config['is_token_generator'] and not self.token_started:
                    print(f"[{get_timestamp()}] {'='*50}")
                    print(f"[{get_timestamp()}] Starting token circulation...")
                    print(f"[{get_timestamp()}] {'='*50}")
                    self.token_started = True
                    self.has_token = True
                    self.last_token_time = time.time()
                    self.send_token()
                elif command.lower().startswith('send '):
                    parts = command.split(' ', 2)
                    if len(parts) == 3:
                        destination, message = parts[1], parts[2]
                        if self.message_queue.qsize() < MAX_QUEUE_SIZE:
                            self.message_queue.put((destination, message))
                            print(f"[{get_timestamp()}] MESSAGE: Queued for {destination}")
                        else:
                            print(f"[{get_timestamp()}] ERROR: Message queue is full")
            except KeyboardInterrupt:
                self.running = False
    
    def _receive_loop(self):
        """Main receive loop for handling incoming packets."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                packet = data.decode()
                
                if packet == TOKEN_VALUE:
                    self.handle_token()
                else:
                    self.handle_data_packet(packet)
            except Exception as e:
                if self.running:  # Only print error if we're still running
                    print(f"[{get_timestamp()}] ERROR: Failed to receive packet - {e}")
    
    def _monitor_token(self):
        """Monitor token circulation for the token generator."""
        while self.running:
            time.sleep(1)
            if self.token_started and time.time() - self.last_token_time > self.token_timeout:
                print(f"[{get_timestamp()}] {'='*50}")
                print(f"[{get_timestamp()}] WARNING: Token timeout detected")
                print(f"[{get_timestamp()}] Generating new token...")
                print(f"[{get_timestamp()}] {'='*50}")
                self.has_token = True
                self.last_token_time = time.time()
                self.send_token()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python Tokentrip.py <config_file>")
        sys.exit(1)
    
    node = TokenRingNode(sys.argv[1])
    node.start()
