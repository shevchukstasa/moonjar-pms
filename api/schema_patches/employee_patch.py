"""Schema patch — employees and attendance tables for HR module."""

EMPLOYEE_SQL = [
    # employees table
    """CREATE TABLE IF NOT EXISTS employees (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        full_name VARCHAR(200) NOT NULL,
        position VARCHAR(100) NOT NULL,
        phone VARCHAR(50),
        hire_date DATE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        employment_type VARCHAR(50) NOT NULL DEFAULT 'full_time',
        department VARCHAR(50) NOT NULL DEFAULT 'production',
        work_schedule VARCHAR(20) NOT NULL DEFAULT 'six_day',
        bpjs_mode VARCHAR(20) NOT NULL DEFAULT 'company_pays',
        base_salary NUMERIC(12,2) NOT NULL DEFAULT 0,
        allowance_bike NUMERIC(10,2) NOT NULL DEFAULT 0,
        allowance_housing NUMERIC(10,2) NOT NULL DEFAULT 0,
        allowance_food NUMERIC(10,2) NOT NULL DEFAULT 0,
        allowance_bpjs NUMERIC(10,2) NOT NULL DEFAULT 0,
        allowance_other NUMERIC(10,2) NOT NULL DEFAULT 0,
        allowance_other_note VARCHAR(200),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",

    # attendance table
    """CREATE TABLE IF NOT EXISTS attendance (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        employee_id UUID NOT NULL REFERENCES employees(id),
        date DATE NOT NULL,
        status VARCHAR(20) NOT NULL,
        overtime_hours NUMERIC(4,1) NOT NULL DEFAULT 0,
        notes TEXT,
        recorded_by UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_attendance_employee_date UNIQUE (employee_id, date)
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_employees_factory ON employees(factory_id)",
    "CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(factory_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)",
    "CREATE INDEX IF NOT EXISTS idx_attendance_employee ON attendance(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(employee_id, date)",

    # Add new columns if not exist (safe for existing tables)
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS department VARCHAR(50) NOT NULL DEFAULT 'production'",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_schedule VARCHAR(20) NOT NULL DEFAULT 'six_day'",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS bpjs_mode VARCHAR(20) NOT NULL DEFAULT 'company_pays'",
]


def apply_patch(db_connection):
    """Apply employee/attendance schema patch. Safe to run multiple times (IF NOT EXISTS)."""
    import sqlalchemy as sa
    for sql in EMPLOYEE_SQL:
        try:
            db_connection.execute(sa.text(sql))
        except Exception:
            pass  # table/index already exists — ignore
