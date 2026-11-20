# Matriz de atendimento ao enunciado

| Requisito | Implementação/artefato | Situação |
|---|---|---|
| Servidor de controle, registro, catálogo e descoberta | `server.py` | Implementado |
| Solicitação, recepção e compartilhamento P2P | `peer.py`, `webapp.py` | Implementado |
| Sockets e protocolo próprio | `protocol.py`, `PROTOCOLO.md` | Implementado |
| IPv4 e IPv6 | sockets IPv4/IPv6; HTTP selecionável por `--web-host` | Suporte disponível; validar no ambiente |
| Streaming contínuo | endpoint `/stream/` e HLS | Implementado |
| Buffer/jitter/taxa | buffer do player e ABR do HLS.js | Controle básico no player; jitter de rede é observado indiretamente |
| Integridade e recuperação | SHA-256, HMAC, retomada por blocos e múltiplas fontes | Implementado; executar teste de interrupção |
| Segurança | segredo, HMAC e TLS opcional | Implementado; TLS exige certificados confiáveis |
| Detecção de peers offline | heartbeat e expiração | Implementado |
| Avaliação experimental | `benchmark.py`, `tcp_echo_benchmark.py`, `udp_benchmark.py`, `netem_experimento.sh` | Ferramentas fornecidas; resultados devem ser medidos e relatados |
| Multicast | `multicast_discovery.py` | Implementação auxiliar IPv4; executar em LAN |
| Controle adaptativo | HLS.js ABR com rendições FFmpeg | Implementado no player HLS |
| Monitoramento | `/api/status`, painel web e métricas de download/player | Básico |
| Interface web | `webapp.py` | Implementado |
| Docker/Mininet | `Dockerfile`, `docker-compose.yml`, `mininet_topology.py` | Configurações fornecidas; validar dependências |
| Relay de privacidade (ocultação do IP do consumidor perante o fornecedor) | `privacy_relay.py`, `ANONIMATO_RELAY.md` | Parcial/experimental; não é anonimato avançado completo |

## Observação sobre anonimato
Pseudônimos/IDs de peer não fornecem anonimato de rede. Anonimato avançado exigiria um modelo de ameaça e mecanismos de encaminhamento/relay (por exemplo, múltiplos saltos), que alteram a arquitetura, desempenho e segurança. Não foi simulado nem anunciado como funcionalidade entregue.


**Limitação:** a funcionalidade de relay é uma melhoria de privacidade parcial. Não afirmar anonimato forte ou bidirecional.
