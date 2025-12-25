-- =========================================================
-- ATLAS - Schéma de base de données optimisé
-- Version 2.0 - Architecture avec référentiel géographique
-- =========================================================

-- =========================================================
-- EXTENSIONS
-- =========================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Pour recherche floue sur noms de villes

-- =========================================================
-- TABLE DE RÉFÉRENCE GÉOGRAPHIQUE (statique)
-- =========================================================

-- Toutes les communes françaises (source: data.gouv.fr)
CREATE TABLE ref_communes_france (
    commune_id SERIAL PRIMARY KEY,
    
    -- Codes officiels
    code_insee VARCHAR(5) UNIQUE NOT NULL,
    code_postal VARCHAR(5) NOT NULL,
    code_departement VARCHAR(3) NOT NULL,
    code_region VARCHAR(2) NOT NULL,
    
    -- Noms
    nom_commune VARCHAR(255) NOT NULL,
    nom_commune_complet VARCHAR(255),  -- Avec article (Le Havre, La Rochelle)
    nom_departement VARCHAR(100) NOT NULL,
    nom_region VARCHAR(100) NOT NULL,
    
    -- Géolocalisation
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    
    -- Métadonnées
    population INTEGER,
    superficie_km2 DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Contraintes
    UNIQUE(code_insee, code_postal)
);

-- Index pour recherche ultra-rapide
CREATE INDEX idx_commune_nom ON ref_communes_france(nom_commune);
CREATE INDEX idx_commune_nom_trgm ON ref_communes_france USING gin(nom_commune gin_trgm_ops);
CREATE INDEX idx_commune_code_postal ON ref_communes_france(code_postal);
CREATE INDEX idx_commune_code_insee ON ref_communes_france(code_insee);
CREATE INDEX idx_commune_departement ON ref_communes_france(code_departement);
CREATE INDEX idx_commune_region ON ref_communes_france(code_region);

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

    -- Dimensions (avec référence à ref_communes_france)
    source_id INTEGER REFERENCES dim_sources(source_id),
    date_id INTEGER REFERENCES dim_dates(date_id),
    commune_id INTEGER REFERENCES ref_communes_france(commune_id),
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
-- INDEX PERFORMANCE
-- =========================================================

CREATE INDEX idx_job_embeddings_vector
ON job_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_fact_offers_external_id ON fact_job_offers(external_id);
CREATE INDEX idx_fact_offers_published_date ON fact_job_offers(published_date);
CREATE INDEX idx_fact_offers_commune ON fact_job_offers(commune_id);
CREATE INDEX idx_fact_offers_source ON fact_job_offers(source_id);
CREATE INDEX idx_fact_offers_category ON fact_job_offers(job_category_id);
CREATE INDEX idx_fact_offers_url ON fact_job_offers(url);

-- =========================================================
-- DONNÉES INITIALES
-- =========================================================

INSERT INTO dim_sources (source_name, source_type, is_official, description) VALUES
('france_travail', 'api', TRUE, 'API officielle France Travail'),
('pole_emploi', 'api', TRUE, 'API historique Pôle Emploi'),
('welcome_to_the_jungle', 'scraping', FALSE, 'Welcome to the Jungle'),
('linkedin', 'scraping', FALSE, 'LinkedIn Jobs'),
('indeed', 'scraping', FALSE, 'Indeed France'),
('apec', 'scraping', FALSE, 'APEC - Cadres'),
('scraping', 'scraping', FALSE, 'Collecte par scraping générique'),
('manual', 'manual', FALSE, 'Saisie manuelle');

-- =========================================================
-- FONCTIONS UTILITAIRES
-- =========================================================

-- Fonction pour rechercher une commune (avec fuzzy matching)
CREATE OR REPLACE FUNCTION find_commune(
    p_nom_commune VARCHAR,
    p_code_postal VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_commune_id INTEGER;
BEGIN
    -- Recherche exacte avec code postal si fourni
    IF p_code_postal IS NOT NULL THEN
        SELECT commune_id INTO v_commune_id
        FROM ref_communes_france
        WHERE LOWER(nom_commune) = LOWER(p_nom_commune)
          AND code_postal = p_code_postal
        LIMIT 1;
        
        IF v_commune_id IS NOT NULL THEN
            RETURN v_commune_id;
        END IF;
    END IF;
    
    -- Recherche par nom seul (similitude)
    SELECT commune_id INTO v_commune_id
    FROM ref_communes_france
    WHERE LOWER(nom_commune) = LOWER(p_nom_commune)
    ORDER BY population DESC NULLS LAST
    LIMIT 1;
    
    IF v_commune_id IS NOT NULL THEN
        RETURN v_commune_id;
    END IF;
    
    -- Recherche floue si pas de résultat exact
    SELECT commune_id INTO v_commune_id
    FROM ref_communes_france
    WHERE similarity(nom_commune, p_nom_commune) > 0.6
    ORDER BY similarity(nom_commune, p_nom_commune) DESC, population DESC NULLS LAST
    LIMIT 1;
    
    RETURN v_commune_id;
END;
$$ LANGUAGE plpgsql;

-- Vue pour analytics
CREATE VIEW v_offers_by_region AS
SELECT 
    r.nom_region,
    r.code_region,
    COUNT(DISTINCT f.offer_id) as nb_offres,
    COUNT(DISTINCT f.company_name) as nb_entreprises,
    AVG(f.salary_max) as salaire_moyen_max
FROM fact_job_offers f
JOIN ref_communes_france r ON f.commune_id = r.commune_id
GROUP BY r.nom_region, r.code_region;

CREATE VIEW v_offers_by_departement AS
SELECT 
    r.nom_departement,
    r.code_departement,
    COUNT(DISTINCT f.offer_id) as nb_offres,
    COUNT(DISTINCT f.company_name) as nb_entreprises,
    AVG(f.salary_max) as salaire_moyen_max
FROM fact_job_offers f
JOIN ref_communes_france r ON f.commune_id = r.commune_id
GROUP BY r.nom_departement, r.code_departement;

-- =========================================================
-- COMMENTAIRES
-- =========================================================

COMMENT ON TABLE ref_communes_france IS 'Référentiel officiel des communes françaises (source: data.gouv.fr)';
COMMENT ON TABLE fact_job_offers IS 'Table de faits des offres d''emploi collectées';
COMMENT ON COLUMN fact_job_offers.commune_id IS 'Référence à la commune (FK vers ref_communes_france)';
COMMENT ON FUNCTION find_commune IS 'Recherche une commune par nom (avec fuzzy matching) et/ou code postal';
