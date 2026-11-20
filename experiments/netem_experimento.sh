#!/usr/bin/env bash
set -euo pipefail
IFACE="${1:-lo}"
DELAY="${2:-50ms}"
LOSS="${3:-1%}"
echo "Aplicando delay=$DELAY loss=$LOSS em $IFACE"
echo 'ATENÇÃO: use somente em ambiente de laboratório; pode afetar todo o tráfego da interface.'
sudo tc qdisc replace dev "$IFACE" root netem delay "$DELAY" loss "$LOSS"
echo "Para remover: sudo tc qdisc del dev $IFACE root"
