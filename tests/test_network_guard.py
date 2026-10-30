import unittest

from deploy.network_guard import is_trusted_client, parse_trusted_networks


class NetworkGuardTests(unittest.TestCase):
    def test_client_inside_office_subnet_is_allowed(self):
        self.assertTrue(is_trusted_client("192.168.10.25", ["192.168.10.0/24"]))

    def test_client_outside_office_subnet_is_denied(self):
        self.assertFalse(is_trusted_client("192.168.11.25", ["192.168.10.0/24"]))

    def test_empty_allowlist_fails_closed(self):
        self.assertFalse(is_trusted_client("192.168.10.25", []))

    def test_missing_or_malformed_ip_fails_closed(self):
        self.assertFalse(is_trusted_client(None, ["192.168.10.0/24"]))
        self.assertFalse(is_trusted_client("not-an-ip", ["192.168.10.0/24"]))

    def test_ipv6_network_supported(self):
        self.assertTrue(is_trusted_client("fd00::12", ["fd00::/64"]))

    def test_network_parser_normalizes_host_bits(self):
        networks = parse_trusted_networks(["192.168.10.25/24"])
        self.assertEqual(str(networks[0]), "192.168.10.0/24")


if __name__ == "__main__":
    unittest.main()
