-- FIRE Database Schema
-- Freedom Intelligent Routing Engine

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Business Units (offices) - load first
CREATE TABLE IF NOT EXISTS business_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

-- Managers - load second
CREATE TABLE IF NOT EXISTS managers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(255) NOT NULL,
    position VARCHAR(50) NOT NULL,  -- "Специалист"|"Ведущий специалист"|"Главный специалист"
    office VARCHAR(100),  -- references business_units.name
    skills TEXT[],  -- ["VIP","ENG","KZ"]
    current_workload INTEGER DEFAULT 0,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL
);

-- Tickets - load third
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_guid VARCHAR(255) NOT NULL,
    gender VARCHAR(10),
    birth_date DATE,
    description TEXT,
    attachment VARCHAR(500),
    segment VARCHAR(20) NOT NULL DEFAULT 'Mass',  -- "Mass"|"VIP"|"Priority"
    country VARCHAR(100),
    region VARCHAR(100),
    city VARCHAR(100),
    street VARCHAR(200),
    house VARCHAR(20),
    -- AI analysis results (populated after NLP processing)
    ticket_type VARCHAR(50),
    sentiment VARCHAR(20),
    priority INTEGER,
    language VARCHAR(5),
    summary TEXT,
    -- Geo results
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    nearest_office VARCHAR(100),
    -- Assignment
    assigned_manager_id UUID REFERENCES managers(id) ON DELETE SET NULL,
    processing_time_ms DOUBLE PRECISION,
    status VARCHAR(50) DEFAULT 'new',  -- "new"|"analyzed"|"distributed"
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Analysis (detailed NLP results)
CREATE TABLE IF NOT EXISTS ai_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID UNIQUE NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    type VARCHAR(50),
    tonality VARCHAR(20),
    priority INTEGER,
    language VARCHAR(5),
    summary TEXT,
    geo_latitude DOUBLE PRECISION,
    geo_longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Distributions (ticket assignments)
CREATE TABLE IF NOT EXISTS distributions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID UNIQUE NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    ai_analysis_id UUID REFERENCES ai_analyses(id) ON DELETE SET NULL,
    manager_id UUID NOT NULL REFERENCES managers(id) ON DELETE CASCADE,
    reason TEXT,
    assigned_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_segment ON tickets(segment);
CREATE INDEX IF NOT EXISTS idx_tickets_city ON tickets(city);
CREATE INDEX IF NOT EXISTS idx_managers_office ON managers(business_unit_id);
CREATE INDEX IF NOT EXISTS idx_managers_skills ON managers USING GIN(skills);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_type ON ai_analyses(type);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_priority ON ai_analyses(priority);
CREATE INDEX IF NOT EXISTS idx_distributions_manager ON distributions(manager_id);
