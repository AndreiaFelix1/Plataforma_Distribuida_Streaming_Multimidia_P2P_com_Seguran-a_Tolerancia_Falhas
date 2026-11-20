# Especificação do protocolo StreamP2P

## Transporte e enquadramento
O plano de controle e as transferências P2P usam TCP. Cada mensagem de controle é JSON UTF-8 precedido por um inteiro sem sinal de 32 bits em ordem de rede (`!I`) que informa o tamanho do JSON. O cabeçalho é limitado a 1 MiB. Após a resposta JSON de `GET_CHUNK`, o peer envia exatamente `length` bytes binários.

## Mensagens de controle
Todas as mensagens incluem `command` e `secret`.

| Comando | Campos adicionais | Resposta |
|---|---|---|
| `REGISTER` | `host`, `port`, `files` | `peer_id`, `catalog` |
| `HEARTBEAT` | `peer_id`, `files` | `ok` |
| `LIST` | — | `catalog` |
| `DISCOVER` | `filename` | lista `peers` com `id`, `host`, `port` |
| `STATUS` | — | `active_peers`, `catalog_items` |
| `UNREGISTER` | `peer_id` | `ok` |

## Transferência P2P
O consumidor envia `GET_CHUNK` com `filename`, `index` e `signature`. A assinatura é HMAC-SHA256 sobre a representação JSON canônica (chaves ordenadas e separadores compactos). O fornecedor responde com `ok`, `length`, `sha256` e `hmac`; em seguida envia o bloco binário. O consumidor verifica o HMAC do cabeçalho e o SHA-256 dos bytes recebidos.

## Integridade e recuperação
O tamanho do bloco é 256 KiB. Os downloads são gravados em `.part`; um arquivo lateral JSON registra hashes dos blocos concluídos. Ao retomar, os blocos persistidos são relidos e validados antes de serem reutilizados. Blocos ausentes podem ser solicitados a outra fonte descoberta. O arquivo só é renomeado para o nome final quando todos os blocos foram recebidos.

## Segurança
O segredo compartilhado autentica comandos e HMACs. TLS 1.2+ pode proteger os sockets de controle e P2P. Para uso real fora do laboratório, gere certificados individuais por nó, valide hostname/SAN e proteja as chaves. A configuração de certificado compartilhado é apenas didática.

## Endereçamento
O código de sockets de controle e P2P aceita IPv4 e IPv6 conforme o endereço informado. Para IPv6, use endereço alcançável no parâmetro `--advertise-host` e libere as portas no firewall.
