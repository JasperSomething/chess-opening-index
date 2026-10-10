from pathlib import Path
import tempfile
import unittest

from chess_memoriser.config import load_lichess_token


class CredentialTests(unittest.TestCase):
    def test_private_explicit_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("secret-for-test\n")
            path.chmod(0o600)
            self.assertEqual(load_lichess_token(path), "secret-for-test")

    def test_rejects_permissive_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("secret-for-test\n")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                load_lichess_token(path)


if __name__ == "__main__":
    unittest.main()
