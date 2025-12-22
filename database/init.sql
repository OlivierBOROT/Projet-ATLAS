-- =========================================================
-- EXTENSIONS
-- =========================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =========================================================
-- TABLES DE DIMENSIONS
-- =========================================================

CREATE TABLE dim_sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50),             -- api, scraping, manual
    base_url TEXT,
    is_official BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_dates (
    date_id SERIAL PRIMARY KEY,
    full_date DATE UNIQUE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN
);

CREATE TABLE dim_locations (
    location_id SERIAL PRIMARY KEY,
    city VARCHAR(255),
    postal_code VARCHAR(10),
    department VARCHAR(100),
    department_code VARCHAR(3),
    region VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_job_categories (
    job_category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) UNIQUE NOT NULL,
    category_code VARCHAR(50),
    parent_category_id INTEGER REFERENCES dim_job_categories(job_category_id),
    level INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_skills (
    skill_id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) UNIQUE NOT NULL,
    skill_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================
-- TABLES DE FAITS
-- =========================================================

CREATE TABLE fact_job_offers (
    offer_id SERIAL PRIMARY KEY,

    -- Dimensions
    source_id INTEGER REFERENCES dim_sources(source_id),
    date_id INTEGER REFERENCES dim_dates(date_id),
    location_id INTEGER REFERENCES dim_locations(location_id),
    job_category_id INTEGER REFERENCES dim_job_categories(job_category_id),

    -- Métadonnées offre
    external_id VARCHAR(255) UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    description_cleaned TEXT,
    url TEXT,

    company_name VARCHAR(255),
    contract_type VARCHAR(100),

    salary_min DECIMAL(10,2),
    salary_max DECIMAL(10,2),

    published_date DATE,
    collected_date TIMESTAMP DEFAULT NOW(),

    -- NLP
    experience_years INTEGER,
    skills_extracted TEXT[],

    processed BOOLEAN DEFAULT FALSE,
    processing_date TIMESTAMP
);

CREATE TABLE fact_offer_skills (
    offer_id INTEGER REFERENCES fact_job_offers(offer_id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES dim_skills(skill_id),
    confidence DECIMAL(3,2),
    PRIMARY KEY (offer_id, skill_id)
);

CREATE TABLE job_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    offer_id INTEGER UNIQUE
        REFERENCES fact_job_offers(offer_id) ON DELETE CASCADE,

    embedding vector(384),
    model_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================
-- INDEX
-- =========================================================

CREATE INDEX idx_job_embeddings_vector
ON job_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_fact_offers_external_id ON fact_job_offers(external_id);
CREATE INDEX idx_fact_offers_published_date ON fact_job_offers(published_date);
CREATE INDEX idx_fact_offers_location ON fact_job_offers(location_id);
CREATE INDEX idx_fact_offers_source ON fact_job_offers(source_id);
CREATE INDEX idx_fact_offers_category ON fact_job_offers(job_category_id);
CREATE INDEX idx_fact_offers_url ON fact_job_offers(url);

-- =========================================================
-- DONNÉES INITIALES
-- =========================================================

INSERT INTO dim_sources (source_name, source_type, is_official, description) VALUES
('france_travail', 'api', TRUE, 'API officielle France Travail'),
('pole_emploi', 'api', TRUE, 'API historique Pôle Emploi'),
('scraping', 'scraping', FALSE, 'Collecte par scraping'),
('manual', 'manual', FALSE, 'Saisie manuelle');