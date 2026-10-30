import unittest
from unittest.mock import patch

from sync.protocol import exchange, SyncProtocolError


class SyncProtocolTests(unittest.TestCase):
    def test_rejects_non_https_endpoint(self):
        with self.assertRaises(SyncProtocolError):
            exchange(endpoint="http://example.test", token="x", node_id="node", events=[])

    def test_requires_token_and_node_identity(self):
        with self.assertRaises(SyncProtocolError):
            exchange(endpoint="https://example.test", token="", node_id="node", events=[])

    @patch("sync.protocol.requests.post")
    def test_sends_bearer_token_and_returns_response(self, post):
        class Response:
            status_code = 200
            def json(self):
                return {"accepted": [], "events": []}
        post.return_value = Response()
        result = exchange(endpoint="https://sync.example.test", token="secret",
                          node_id="node-a", events=[])
        self.assertEqual(result["accepted"], [])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    @patch("sync.protocol.requests.post")
    def test_rejects_invalid_response(self, post):
        class Response:
            status_code = 200
            def json(self):
                return []
        post.return_value = Response()
        with self.assertRaises(SyncProtocolError):
            exchange(endpoint="https://sync.example.test", token="secret",
                     node_id="node-a", events=[])


if __name__ == "__main__":
    unittest.main()
