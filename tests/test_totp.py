import os
import unittest

os.environ.setdefault("TOTP_SECRET", "JBSWY3DPEHPK3PXP")

from app import TOTPConfig, app, generate_totp  # noqa: E402


class RFC6238Tests(unittest.TestCase):
    def test_sha1_vectors(self):
        config = TOTPConfig(
            secret="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
            label="test",
            issuer="test",
            digits=8,
            period=30,
            algorithm="SHA1",
        )
        vectors = {
            59: "94287082",
            1111111109: "07081804",
            1111111111: "14050471",
            1234567890: "89005924",
            2000000000: "69279037",
            20000000000: "65353130",
        }
        for timestamp, expected in vectors.items():
            with self.subTest(timestamp=timestamp):
                code, _ = generate_totp(config, timestamp)
                self.assertEqual(code, expected)

    def test_public_routes(self):
        client = app.test_client()
        self.assertEqual(client.get("/").status_code, 200)
        response = client.get("/api/code")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["code"].isdigit())
        self.assertEqual(len(payload["code"]), 6)

    def test_no_login_routes(self):
        client = app.test_client()
        self.assertEqual(client.get("/login").status_code, 404)
        self.assertEqual(client.post("/logout").status_code, 404)


if __name__ == "__main__":
    unittest.main()
