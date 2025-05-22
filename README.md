# Rede em Anel - Trabalho Final

Este projeto implementa uma rede em anel usando o protocolo UDP para comunicação entre os nós.

## Requisitos

- Python 3.7+
- Pacotes Python listados em `requirements.txt`

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `config.txt` para cada nó da rede com o seguinte formato:
```
<ip_destino_do_token>:porta <apelido_da_máquina_atual> <tempo_token> <token>
```

Exemplo para três nós:
```
# config.txt do Nó 1
127.0.0.1:6001 Node1 1 true

# config.txt do Nó 2
127.0.0.1:6002 Node2 1 false

# config.txt do Nó 3
127.0.0.1:6000 Node3 1 false
```

Onde:
- `ip_destino_do_token`: IP da máquina à direita no anel
- `porta`: Porta UDP para comunicação
- `apelido_da_máquina_atual`: Nome identificador da máquina
- `tempo_token`: Tempo em segundos que o token permanece em cada máquina
- `token`: "true" se a máquina é geradora do token, "false" caso contrário

## Execução

Para executar um nó da rede:
```bash
python ring_network.py
```

## Funcionalidades

- Envio de mensagens unicast e broadcast
- Detecção e correção de erros usando CRC32
- Simulação de erros aleatórios (10% de chance)
- Controle de token
- Fila de mensagens (máximo 10 mensagens)
- Detecção de token perdido e múltiplos tokens

## Comandos Disponíveis

Durante a execução:
- `enviar`: Inicia o processo de envio de mensagem
- `sair`: Encerra o programa

## Observações

- A rede deve ter pelo menos 3 máquinas para funcionar corretamente
- Apenas uma máquina deve ser configurada como geradora de token
- O tempo do token deve ser configurado adequadamente para evitar problemas de sincronização
- Para testar em uma única máquina, use diferentes portas para cada nó
- Para broadcast, use "TODOS" como destino da mensagem 