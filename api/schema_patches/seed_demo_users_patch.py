"""Seed demo users for all 8 roles.

Idempotent — skips existing users by email.
Links all demo users to the first active factory.
"""
import logging
import uuid
from sqlalchemy import text

logger = logging.getLogger(__name__)

DEMO_USERS = [
    # (email, name, role, password)
    ("ceo@moonjar.com", "CEO Demo", "ceo", "MoonjarCEO2024!"),
    ("admin@moonjar.com", "Admin Demo", "administrator", "MoonjarAdmin2024!"),
    ("qm@moonjar.com", "Quality Manager Demo", "quality_manager", "MoonjarQM2024!"),
    ("warehouse@moonjar.com", "Warehouse Demo", "warehouse", "MoonjarWH2024!"),
    ("sorter@moonjar.com", "Sorter Packer Demo", "sorter_packer", "MoonjarSP2024!"),
    ("purchaser@moonjar.com", "Purchaser Demo", "purchaser", "MoonjarPurch2024!"),
]


def run(engine):
    from api.auth import hash_password

    with engine.connect() as conn:
        # Get first factory ID for linking
        row = conn.execute(text(
            "SELECT id FROM factories WHERE is_active = true ORDER BY created_at LIMIT 1"
        )).fetchone()
        factory_id = row[0] if row else None

        created = 0
        for email, name, role, password in DEMO_USERS:
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()
            if existing:
                logger.info("Demo user %s already exists, skipping", email)
                continue

            user_id = uuid.uuid4()
            conn.execute(
                text("""
                    INSERT INTO users (id, email, name, role, password_hash, is_active, language)
                    VALUES (:id, :email, :name, :role, :password_hash, true, 'en')
                """),
                {
                    "id": str(user_id),
                    "email": email,
                    "name": name,
                    "role": role,
                    "password_hash": hash_password(password),
                },
            )

            # Link to factory
            if factory_id:
                conn.execute(
                    text("""
                        INSERT INTO user_factories (user_id, factory_id)
                        VALUES (:user_id, :factory_id)
                        ON CONFLICT DO NOTHING
                    """),
                    {"user_id": str(user_id), "factory_id": str(factory_id)},
                )

            created += 1
            logger.info("Created demo user: %s (%s)", email, role)

        conn.commit()
        logger.info("seed_demo_users: created %d, skipped %d", created, len(DEMO_USERS) - created)
