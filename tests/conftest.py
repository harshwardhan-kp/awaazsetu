import os, tempfile, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet

_test_dir = tempfile.mkdtemp(prefix="awaazsetu-test-")
os.environ.update(
    DATABASE_URL="sqlite:///" + _test_dir + "/test.db",
    ADMIN_PASSWORD="test-coordinator-password",
    JWT_SECRET="test-jwt-secret-with-sufficient-length-000000",
    CONTACT_HASH_SECRET="test-contact-hash-secret",
    CONTACT_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    AI_ENABLED="false",
    DELIVERY_ENABLED="false",
    SMS_WEBHOOK_SECRET="test-webhook-secret",
    OPENAI_API_KEY="",
)
