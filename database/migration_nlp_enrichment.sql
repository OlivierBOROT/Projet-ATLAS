-- ============================================================================
-- MIGRATION NLP ENRICHMENT
-- ============================================================================
-- Ajout des colonnes issues du traitement NLP des offres
-- Date: 2025-12-31
-- ============================================================================

-- 1. AJOUT DES COLONNES NLP à fact_job_offers
ALTER TABLE public.fact_job_offers
    -- Profil identifié
    ADD COLUMN IF NOT EXISTS profile_category VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS profile_confidence INT NULL,  -- Confiance en % (0-100)
    
    -- Niveau d'études
    ADD COLUMN IF NOT EXISTS education_level INT NULL,  -- Bac+X (3, 5, etc.)
    ADD COLUMN IF NOT EXISTS education_type VARCHAR(100) NULL,  -- Master, Ingénieur, etc.
    
    -- Télétravail
    ADD COLUMN IF NOT EXISTS remote_possible BOOLEAN DEFAULT false NULL,
    ADD COLUMN IF NOT EXISTS remote_days INT NULL,  -- Nombre de jours/semaine
    ADD COLUMN IF NOT EXISTS remote_percentage INT NULL;  -- Pourcentage (0-100)

-- 2. COMMENTAIRES sur les nouvelles colonnes
COMMENT ON COLUMN public.fact_job_offers.profile_category IS 'Catégorie de profil identifiée par NLP (Data Science, Backend Developer, etc.)';
COMMENT ON COLUMN public.fact_job_offers.profile_confidence IS 'Confiance de la catégorisation en % (0-100)';
COMMENT ON COLUMN public.fact_job_offers.education_level IS 'Niveau de formation requis (Bac+X)';
COMMENT ON COLUMN public.fact_job_offers.education_type IS 'Type de diplôme (Master, Ingénieur, Doctorat, etc.)';
COMMENT ON COLUMN public.fact_job_offers.remote_possible IS 'Possibilité de télétravail';
COMMENT ON COLUMN public.fact_job_offers.remote_days IS 'Nombre de jours de télétravail par semaine';
COMMENT ON COLUMN public.fact_job_offers.remote_percentage IS 'Pourcentage de télétravail (0-100%)';

-- 3. CRÉATION D'INDEX pour optimiser les requêtes
CREATE INDEX IF NOT EXISTS idx_offers_profile_category ON public.fact_job_offers(profile_category);
CREATE INDEX IF NOT EXISTS idx_offers_remote_possible ON public.fact_job_offers(remote_possible);
CREATE INDEX IF NOT EXISTS idx_offers_education_level ON public.fact_job_offers(education_level);

-- 4. VÉRIFICATION des colonnes ajoutées
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'fact_job_offers'
  AND column_name IN (
      'profile_category', 
      'profile_confidence', 
      'education_level', 
      'education_type',
      'remote_possible',
      'remote_days',
      'remote_percentage'
  )
ORDER BY ordinal_position;

-- ============================================================================
-- FIN DE LA MIGRATION
-- ============================================================================
