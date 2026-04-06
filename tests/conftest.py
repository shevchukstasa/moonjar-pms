"""
Shared test fixtures for Moonjar PMS.

Provides two fixture modes:
1. DB-backed fixtures (db, client) — for integration tests that need a real database.
2. Mock fixtures (sample_factory, sample_user, sample_order) — lightweight
   SimpleNamespace objects for unit tests that never touch the DB.
"""
import uuid
import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from types import SimpleNamespace

import jwt as pyjwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from api.database import Base, get_db
from api.config import get_settings
from api.auth import ALGORITHM

settings = get_settings()

# Test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.split("/")[-1], "moonjar_test"
) if settings.DATABASE_URL else "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ═══════════════════════════════════════════════════════════════════════════
#  DB-backed fixtures (integration tests)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def db_engine():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(db_engine):
    """Get test database session with rollback."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """Get test HTTP client with DB override."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
#  Auth fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def auth_headers():
    """Generate valid JWT auth headers for test requests.

    Creates a real JWT token signed with the app's SECRET_KEY, using
    the same algorithm as production (HS256). The token has:
    - sub: a deterministic test user UUID
    - role: owner (full access for tests)
    - type: access
    - jti: unique session id
    - exp: 1 hour from now
    """
    from api.auth import create_access_token

    test_user_id = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
    token = create_access_token(user_id=test_user_id, role="owner")
    return {"Cookie": f"access_token={token}"}


@pytest.fixture
def auth_headers_for_role():
    """Factory fixture: generate auth headers for any role.

    Usage:
        def test_something(auth_headers_for_role):
            headers = auth_headers_for_role("production_manager")
    """
    from api.auth import create_access_token

    def _make(role: str, user_id: str = None):
        uid = user_id or str(uuid.uuid4())
        token = create_access_token(user_id=uid, role=role)
        return {"Cookie": f"access_token={token}"}

    return _make


# ═══════════════════════════════════════════════════════════════════════════
#  Mock object fixtures (unit tests — no DB required)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_factory():
    """Create a mock Factory object (SimpleNamespace, no DB)."""
    factory_id = uuid.uuid4()
    return SimpleNamespace(
        id=factory_id,
        name="Bali Factory",
        location="Bali",
        address="Jl. Raya Ubud No. 1",
        region="Bali",
        settings={},
        timezone="Asia/Makassar",
        masters_group_chat_id=None,
        purchaser_chat_id=None,
        telegram_language="id",
        receiving_approval_mode="all",
        kiln_constants_mode="manual",
        rotation_rules=None,
        served_locations=["Bali", "Lombok"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_user(sample_factory):
    """Create a mock User object (SimpleNamespace, no DB)."""
    user_id = uuid.uuid4()
    return SimpleNamespace(
        id=user_id,
        email="testuser@moonjar.com",
        name="Test User",
        role="production_manager",
        password_hash=None,
        google_id=None,
        telegram_user_id=None,
        language="en",
        is_active=True,
        failed_login_count=0,
        locked_until=None,
        totp_secret_encrypted=None,
        totp_enabled=False,
        last_password_change=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        user_factories=[
            SimpleNamespace(factory_id=sample_factory.id),
        ],
    )


@pytest.fixture
def sample_order(sample_factory):
    """Create a mock ProductionOrder with 2 positions (SimpleNamespace, no DB).

    Includes order items and positions to mirror the real data structure.
    """
    order_id = uuid.uuid4()
    item_1_id = uuid.uuid4()
    item_2_id = uuid.uuid4()

    order = SimpleNamespace(
        id=order_id,
        order_number="MJ-TEST-001",
        client="Test Client Hotel",
        client_location="Bali",
        sales_manager_name="Test Manager",
        sales_manager_contact="test@sales.com",
        factory_id=sample_factory.id,
        document_date=date(2026, 4, 1),
        production_received_date=date(2026, 4, 2),
        final_deadline=date(2026, 5, 15),
        schedule_deadline=date(2026, 5, 10),
        desired_delivery_date=date(2026, 5, 15),
        status="new",
        status_override=False,
        sales_status=None,
        source="manual",
        external_id=None,
        sales_payload_json=None,
        mandatory_qc=False,
        notes=None,
        shipped_at=None,
        cancellation_requested=False,
        cancellation_requested_at=None,
        cancellation_decision=None,
        cancellation_decided_at=None,
        cancellation_decided_by=None,
    )

    # Items (line items from the sales order)
    item_1 = SimpleNamespace(
        id=item_1_id,
        order_id=order_id,
        color="White",
        color_2=None,
        size="10x10",
        application="Authentic",
        finishing=None,
        thickness=Decimal("11.0"),
        quantity_pcs=200,
        quantity_sqm=Decimal("2.000"),
        collection="Classic",
        application_type="SS",
        place_of_application="floor",
        product_type="tile",
        shape="rectangle",
        length_cm=Decimal("10.00"),
        width_cm=Decimal("10.00"),
        depth_cm=None,
        bowl_shape=None,
        shape_dimensions=None,
        edge_profile=None,
    )

    item_2 = SimpleNamespace(
        id=item_2_id,
        order_id=order_id,
        color="Sage",
        color_2=None,
        size="20x20",
        application="Creative",
        finishing=None,
        thickness=Decimal("11.0"),
        quantity_pcs=100,
        quantity_sqm=Decimal("4.000"),
        collection="Modern",
        application_type="BS",
        place_of_application="wall",
        product_type="tile",
        shape="rectangle",
        length_cm=Decimal("20.00"),
        width_cm=Decimal("20.00"),
        depth_cm=None,
        bowl_shape=None,
        shape_dimensions=None,
        edge_profile=None,
    )

    # Positions (individual production units from items)
    pos_1 = SimpleNamespace(
        id=uuid.uuid4(),
        order_id=order_id,
        order_item_id=item_1_id,
        parent_position_id=None,
        factory_id=sample_factory.id,
        status="planned",
        batch_id=None,
        resource_id=None,
        placement_position=None,
        placement_level=None,
        delay_hours=Decimal("0"),
        reservation_at=None,
        materials_written_off_at=None,
        quantity=200,
        quantity_sqm=Decimal("2.000"),
        quantity_with_defect_margin=210,
        color="White",
        color_2=None,
        size="10x10",
        application="Authentic",
        finishing=None,
        collection="Classic",
        application_type="SS",
        place_of_application="floor",
        product_type="tile",
        shape="rectangle",
        length_cm=Decimal("10.00"),
        width_cm=Decimal("10.00"),
        depth_cm=None,
        bowl_shape=None,
        shape_dimensions=None,
    )

    pos_2 = SimpleNamespace(
        id=uuid.uuid4(),
        order_id=order_id,
        order_item_id=item_2_id,
        parent_position_id=None,
        factory_id=sample_factory.id,
        status="planned",
        batch_id=None,
        resource_id=None,
        placement_position=None,
        placement_level=None,
        delay_hours=Decimal("0"),
        reservation_at=None,
        materials_written_off_at=None,
        quantity=100,
        quantity_sqm=Decimal("4.000"),
        quantity_with_defect_margin=105,
        color="Sage",
        color_2=None,
        size="20x20",
        application="Creative",
        finishing=None,
        collection="Modern",
        application_type="BS",
        place_of_application="wall",
        product_type="tile",
        shape="rectangle",
        length_cm=Decimal("20.00"),
        width_cm=Decimal("20.00"),
        depth_cm=None,
        bowl_shape=None,
        shape_dimensions=None,
    )

    order.items = [item_1, item_2]
    order.positions = [pos_1, pos_2]

    return order
