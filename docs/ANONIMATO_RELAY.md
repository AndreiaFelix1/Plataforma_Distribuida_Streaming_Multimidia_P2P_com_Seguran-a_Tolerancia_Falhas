# Relay de privacidade (experimento de anonimização parcial)

## O que faz
`privacy_relay.py` encaminha a conexão TCP do consumidor ao fornecedor sem alterar o protocolo P2P. O fornecedor observa o endereço IP do relay como origem da conexão, em vez do IP do consumidor. O relay aceita apenas destinos explicitamente autorizados com `--allow HOST:PORT` e exige HMAC no pedido de criação da rota.

## Limitações importantes
Isto **não é anonimato avançado completo**, nem Tor, mixnet ou onion routing:
- o relay conhece o IP do consumidor e o destino do fornecedor;
- o consumidor ainda pode conhecer o endereço do fornecedor porque a descoberta atual do servidor central retorna `host:port`;
- o servidor central conhece os endereços anunciados;
- não há proteção contra correlação temporal/volume de tráfego;
- o relay é um ponto único de confiança e falha.

Portanto, descreva no relatório como **encaminhamento por relay com ocultação do IP do consumidor perante o fornecedor**, não como anonimato forte. Para anonimato bidirecional real seria necessário substituir a descoberta por identificadores opacos e construir circuitos multi-hop, com análise de ameaças.

## Teste local
1. Inicie servidor central e fornecedor normalmente.
2. Descubra a porta P2P do fornecedor (por exemplo, `9101`).
3. Em outro terminal, execute o relay permitindo somente o destino do fornecedor:

```bash
export STREAM_SECRET='minha-chave-secreta'
python3 privacy_relay.py --host 127.0.0.1 --port 9200 --allow 127.0.0.1:9101
```

4. Inicie o consumidor com o relay habilitado:

```bash
export STREAM_SECRET='minha-chave-secreta'
python3 webapp.py --server 127.0.0.1 --advertise-host 127.0.0.1 \
  --listen-port 9102 --web-port 8082 --relay-host 127.0.0.1 --relay-port 9200
```

5. Acesse `http://127.0.0.1:8082`, selecione um arquivo e teste a reprodução/download.

O relay faz um túnel TCP opaco. Se utilizar TLS P2P, configure certificados confiáveis também no consumidor; o TLS é transportado dentro do túnel. Não exponha o relay à Internet sem autenticação forte, TLS, limitação de conexões e regras de firewall.
