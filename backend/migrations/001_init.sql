-- FIRE Database Migration 001: Initial Schema
-- Run: psql -U fire_user -d fire_db -f 001_init.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ══════════════════════════════════════════════════════════════
-- Business Units (Offices)
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS business_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default offices
INSERT INTO business_units (name, address, latitude, longitude) VALUES
    ('Астана', 'г. Астана, ул. Кунаева 2', 51.1283, 71.4306),
    ('Алматы', 'г. Алматы, пр. Достык 291', 43.2180, 76.9264)
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- Managers
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS managers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(255) NOT NULL,
    position VARCHAR(100) NOT NULL,  -- Спец, Ведущий спец, Глав спец
    skills TEXT[] DEFAULT '{}',       -- VIP, ENG, KZ
    business_unit_id UUID REFERENCES business_units(id),
    current_workload INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for workload queries
CREATE INDEX IF NOT EXISTS idx_managers_workload ON managers(current_workload);
CREATE INDEX IF NOT EXISTS idx_managers_business_unit ON managers(business_unit_id);

-- ══════════════════════════════════════════════════════════════
-- Tickets (unified table with analysis results)
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Client info
    client_guid VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    gender VARCHAR(20),
    age INTEGER,
    segment VARCHAR(50) DEFAULT 'Mass',  -- Mass, VIP, Priority

    -- Ticket content
    description TEXT,
    attachments VARCHAR(500),

    -- AI Analysis results
    ticket_type VARCHAR(100),  -- Жалоба, Смена данных, etc.
    sentiment VARCHAR(50),     -- Позитивный, Нейтральный, Негативный
    priority INTEGER CHECK (priority >= 1 AND priority <= 10),
    language VARCHAR(10) DEFAULT 'RU',  -- KZ, ENG, RU
    summary TEXT,

    -- Geo data
    city VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    nearest_office VARCHAR(100),

    -- Assignment
    assigned_manager_id UUID REFERENCES managers(id),
    routing_reason VARCHAR(500),

    -- Meta
    status VARCHAR(50) DEFAULT 'new',  -- new, analyzed, distributed
    processing_time_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_segment ON tickets(segment);
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_type ON tickets(ticket_type);
CREATE INDEX IF NOT EXISTS idx_tickets_language ON tickets(language);
CREATE INDEX IF NOT EXISTS idx_tickets_city ON tickets(city);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_manager ON tickets(assigned_manager_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority DESC);

-- ══════════════════════════════════════════════════════════════
-- Sample Managers Data
-- ══════════════════════════════════════════════════════════════
DO $$
DECLARE
    astana_id UUID;
    almaty_id UUID;
BEGIN
    SELECT id INTO astana_id FROM business_units WHERE name = 'Астана' LIMIT 1;
    SELECT id INTO almaty_id FROM business_units WHERE name = 'Алматы' LIMIT 1;

    -- Astana managers
    INSERT INTO managers (full_name, position, skills, business_unit_id, current_workload) VALUES
        ('Айгерим Нурланова', 'Глав спец', ARRAY['VIP', 'KZ', 'ENG'], astana_id, 0),
        ('Бауыржан Касымов', 'Ведущий спец', ARRAY['VIP', 'KZ'], astana_id, 0),
        ('Светлана Петрова', 'Спец', ARRAY['ENG'], astana_id, 0),
        ('Дамир Сулейменов', 'Спец', ARRAY['KZ'], astana_id, 0),
        ('Анна Иванова', 'Ведущий спец', ARRAY['VIP'], astana_id, 0)
    ON CONFLICT DO NOTHING;

    -- Almaty managers
    INSERT INTO managers (full_name, position, skills, business_unit_id, current_workload) VALUES
        ('Марат Жумабаев', 'Глав спец', ARRAY['VIP', 'KZ', 'ENG'], almaty_id, 0),
        ('Динара Алиева', 'Ведущий спец', ARRAY['VIP', 'KZ'], almaty_id, 0),
        ('Александр Ким', 'Спец', ARRAY['ENG'], almaty_id, 0),
        ('Гульнара Омарова', 'Спец', ARRAY['KZ'], almaty_id, 0),
        ('Елена Сидорова', 'Ведущий спец', ARRAY['VIP', 'ENG'], almaty_id, 0)
    ON CONFLICT DO NOTHING;
END $$;

-- ══════════════════════════════════════════════════════════════
-- Views for analytics
-- ══════════════════════════════════════════════════════════════

-- Ticket type distribution
CREATE OR REPLACE VIEW v_ticket_type_stats AS
SELECT
    ticket_type,
    COUNT(*) as count,
    ROUND(AVG(priority)::numeric, 1) as avg_priority
FROM tickets
WHERE ticket_type IS NOT NULL
GROUP BY ticket_type
ORDER BY count DESC;

-- Manager workload view
CREATE OR REPLACE VIEW v_manager_workload AS
SELECT
    m.id,
    m.full_name,
    m.position,
    m.skills,
    b.name as office,
    m.current_workload,
    COUNT(t.id) as total_tickets
FROM managers m
LEFT JOIN business_units b ON m.business_unit_id = b.id
LEFT JOIN tickets t ON t.assigned_manager_id = m.id
GROUP BY m.id, m.full_name, m.position, m.skills, b.name, m.current_workload
ORDER BY m.current_workload DESC;

-- Office distribution view
CREATE OR REPLACE VIEW v_office_stats AS
SELECT
    nearest_office,
    COUNT(*) as ticket_count,
    ROUND(AVG(priority)::numeric, 1) as avg_priority,
    ROUND(AVG(processing_time_ms)::numeric, 0) as avg_processing_ms
FROM tickets
WHERE nearest_office IS NOT NULL
GROUP BY nearest_office;

-- ══════════════════════════════════════════════════════════════
-- Functions
-- ══════════════════════════════════════════════════════════════

-- Function to get manager with lowest workload in an office
CREATE OR REPLACE FUNCTION get_available_manager(
    p_office_id UUID,
    p_required_skills TEXT[] DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    manager_id UUID;
BEGIN
    SELECT m.id INTO manager_id
    FROM managers m
    WHERE m.business_unit_id = p_office_id
      AND (p_required_skills = '{}' OR m.skills @> p_required_skills)
    ORDER BY m.current_workload ASC
    LIMIT 1;

    RETURN manager_id;
END;
$$ LANGUAGE plpgsql;

-- Function to increment manager workload
CREATE OR REPLACE FUNCTION assign_ticket_to_manager(
    p_ticket_id UUID,
    p_manager_id UUID,
    p_reason VARCHAR
) RETURNS VOID AS $$
BEGIN
    UPDATE tickets
    SET assigned_manager_id = p_manager_id,
        routing_reason = p_reason,
        status = 'distributed',
        processed_at = NOW()
    WHERE id = p_ticket_id;

    UPDATE managers
    SET current_workload = current_workload + 1
    WHERE id = p_manager_id;
END;
$$ LANGUAGE plpgsql;
