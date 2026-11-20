"""Topologia Mininet: servidor e três peers conectados a switch standalone."""

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel

def run():
    net = Mininet(controller=None)

    sw = net.addSwitch("s1", failMode="standalone")

    server = net.addHost("server", ip="10.0.0.10/24")
    p1 = net.addHost("peer1", ip="10.0.0.11/24")
    p2 = net.addHost("peer2", ip="10.0.0.12/24")
    p3 = net.addHost("peer3", ip="10.0.0.13/24")

    for host in (server, p1, p2, p3):
        net.addLink(host, sw)

    net.start()

    print("\n=== Topologia Mininet iniciada ===")
    print("Servidor: 10.0.0.10")
    print("Peer 1:  10.0.0.11")
    print("Peer 2:  10.0.0.12")
    print("Peer 3:  10.0.0.13")
    print("Switch:   s1 (standalone)")
    print("\nDigite pingall para testar a conectividade.\n")

    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run()
