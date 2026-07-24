from __future__ import annotations

import unittest

from cryptography.fernet import Fernet

from config import configuration_errors


def production_config() -> dict:
    return {
        "PRODUCTION": True,
        "SECRET_KEY": "secret",
        "ACCESS_KEY_PEPPER": "pepper",
        "DATA_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://user:pass@db/app",
        "PUBLIC_BASE_URL": "https://portal.example",
        "SESSION_COOKIE_SECURE": True,
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": "hash",
        "ADMIN_TOTP_SECRET": "JBSWY3DPEHPK3PXP",
        "ADMIN_TOTP_REQUIRED": True,
        "G2G_INTEGRATION_ENABLED": False,
    }


class ProductionConfigurationTests(unittest.TestCase):
    def test_production_requires_postgresql_https_and_admin_totp(self):
        config = production_config()
        config.update(
            {
                "SQLALCHEMY_DATABASE_URI": "sqlite:///unsafe.db",
                "PUBLIC_BASE_URL": "http://portal.example",
                "SESSION_COOKIE_SECURE": False,
                "ADMIN_TOTP_SECRET": "",
            }
        )
        errors = configuration_errors(config)
        self.assertTrue(any("PostgreSQL" in item for item in errors))
        self.assertTrue(any("must be HTTPS" in item for item in errors))
        self.assertTrue(any("SESSION_COOKIE_SECURE" in item for item in errors))
        self.assertTrue(any("ADMIN_TOTP_SECRET" in item for item in errors))

    def test_valid_production_baseline_passes(self):
        self.assertEqual(configuration_errors(production_config()), [])

    def test_production_can_explicitly_disable_admin_totp(self):
        config = production_config()
        config["ADMIN_TOTP_REQUIRED"] = False
        config["ADMIN_TOTP_SECRET"] = ""
        self.assertEqual(configuration_errors(config), [])


if __name__ == "__main__":
    unittest.main()
