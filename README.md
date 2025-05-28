# 💍Token Ring Network Simulation💍

This is a Python implementation of a token ring network simulation that uses UDP for communication between nodes. The program implements a token-based protocol for message transmission in a ring network topology.

## Features 🧾

- Token-based message transmission
- UDP communication between nodes
- Message queue with maximum size
- CRC32 error checking
- Random error injection
- Support for unicast and broadcast messages
- Token monitoring and regeneration
- Configurable node settings

## Requirements 📕

- Python 3.6 or higher
- No external dependencies required (uses only standard library)

## Configuration ⚙

Each node requires a configuration file with the following format:

```
<ip_destino_do_token>:porta
<apelido_da_máquina_atual>
<tempo_token>
<token>
```

Example:
```
10.32.143.12:6000
Bob
1
true
```

## How to run 🤔💭

1. Create a configuration file for each node in your network
2. Run the program for each node:
   ```bash
   python Tokentrip.py <config_file>
   ```

## Message Format

The program uses two types of packets:

1. Token Packet:
   ```
   9000
   ```

2. Data Packet:
   ```
   7777:<status>;<origin>;<destination>;<CRC>;<message>
   ```
   
## Network Topology

The network operates in a ring topology where:
- Each node knows only its right neighbor
- Messages travel clockwise around the ring
- The token circulates to control message transmission
- Only one message can be transmitted at a time
- Messages return to their origin before the token is passed (ACK)

## Broadcast Messages
To send a message to all nodes, use "TODOS" as the destination
