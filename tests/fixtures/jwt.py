from pathlib import Path

from app.core.config import AuthJWT

TEST_KEYS_DIR = Path(__file__).resolve().parent / "keys"
TEST_PRIVATE_KEY_PATH = TEST_KEYS_DIR / "jwt-private.pem"
TEST_PUBLIC_KEY_PATH = TEST_KEYS_DIR / "jwt-public.pem"
TEST_AUTH_JWT = AuthJWT(
    private_key_path=TEST_PRIVATE_KEY_PATH,
    public_key_path=TEST_PUBLIC_KEY_PATH,
)
