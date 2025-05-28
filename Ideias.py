def parse_data_packet(self, packet: str) -> Tuple[str, str, str, str, str, str]:
        """Analisar um pacote de dados em seus componentes"""
        
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

    from typing import Optional, Tuple
