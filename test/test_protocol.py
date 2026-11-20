import socket
import threading
import unittest
from protocol import send_json, recv_json, sha256, request_signature, verify_signature

class ProtocolTests(unittest.TestCase):
    def test_json_framing(self):
        a,b=socket.socketpair()
        try:
            send_json(a, {"command":"PING","value":42})
            self.assertEqual(recv_json(b), {"command":"PING","value":42})
        finally:
            a.close(); b.close()

    def test_hmac(self):
        payload={"command":"GET_CHUNK","filename":"video.mp4","index":3}
        sig=request_signature("test-secret",payload)
        import json
        canonical=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
        self.assertTrue(verify_signature("test-secret",canonical,sig))
        self.assertEqual(len(sha256(b"abc")),64)

if __name__=="__main__": unittest.main()
