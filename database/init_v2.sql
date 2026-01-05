-- public.dim_dates definition

-- Drop table

-- DROP TABLE public.dim_dates;

CREATE TABLE public.dim_dates (
	date_id serial4 NOT NULL,
	full_date date NOT NULL,
	"year" int4 NULL,
	quarter int4 NULL,
	"month" int4 NULL,
	month_name varchar(20) NULL,
	week int4 NULL,
	day_of_week int4 NULL,
	day_name varchar(20) NULL,
	is_weekend bool NULL,
	CONSTRAINT dim_dates_full_date_key UNIQUE (full_date),
	CONSTRAINT dim_dates_pkey PRIMARY KEY (date_id)
);


-- public.dim_skills definition

-- Drop table

-- DROP TABLE public.dim_skills;

CREATE TABLE public.dim_skills (
	skill_id serial4 NOT NULL,
	skill_name varchar(255) NOT NULL,
	skill_category varchar(100) NULL,
	created_at timestamp DEFAULT now() NULL,
	CONSTRAINT dim_skills_pkey PRIMARY KEY (skill_id),
	CONSTRAINT dim_skills_skill_name_key UNIQUE (skill_name)
);


-- public.dim_sources definition

-- Drop table

-- DROP TABLE public.dim_sources;

CREATE TABLE public.dim_sources (
	source_id serial4 NOT NULL,
	source_name varchar(100) NOT NULL,
	source_type varchar(50) NULL,
	base_url text NULL,
	is_official bool DEFAULT false NULL,
	description text NULL,
	created_at timestamp DEFAULT now() NULL,
	CONSTRAINT dim_sources_pkey PRIMARY KEY (source_id),
	CONSTRAINT dim_sources_source_name_key UNIQUE (source_name)
);


-- public.dim_topics definition

-- Drop table

-- DROP TABLE public.dim_topics;

CREATE TABLE public.dim_topics (
	topic_id int4 NOT NULL,
	topic_label varchar(100) NOT NULL,
	topic_description text NULL,
	keywords _text NULL,
	created_at timestamp DEFAULT now() NULL,
	CONSTRAINT dim_topics_pkey PRIMARY KEY (topic_id)
);
COMMENT ON TABLE public.dim_topics IS 'Référentiel des 8 topics identifiés par LDA';


-- public.ref_communes_france definition

-- Drop table

-- DROP TABLE public.ref_communes_france;

CREATE TABLE public.ref_communes_france (
	commune_id serial4 NOT NULL,
	code_insee varchar(5) NOT NULL,
	code_postal varchar(5) NOT NULL,
	code_departement varchar(3) NOT NULL,
	code_region varchar(2) NOT NULL,
	nom_commune varchar(255) NOT NULL,
	nom_commune_complet varchar(255) NULL,
	nom_departement varchar(100) NOT NULL,
	nom_region varchar(100) NOT NULL,
	latitude numeric(10, 7) NULL,
	longitude numeric(10, 7) NULL,
	population int4 NULL,
	superficie_km2 numeric(10, 2) NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	CONSTRAINT ref_communes_france_code_insee_code_postal_key UNIQUE (code_insee, code_postal),
	CONSTRAINT ref_communes_france_code_insee_key UNIQUE (code_insee),
	CONSTRAINT ref_communes_france_pkey PRIMARY KEY (commune_id)
);
CREATE INDEX idx_commune_code_insee ON public.ref_communes_france USING btree (code_insee);
CREATE INDEX idx_commune_code_postal ON public.ref_communes_france USING btree (code_postal);
CREATE INDEX idx_commune_departement ON public.ref_communes_france USING btree (code_departement);
CREATE INDEX idx_commune_nom ON public.ref_communes_france USING btree (nom_commune);
CREATE INDEX idx_commune_nom_trgm ON public.ref_communes_france USING gin (nom_commune gin_trgm_ops);
CREATE INDEX idx_commune_region ON public.ref_communes_france USING btree (code_region);
COMMENT ON TABLE public.ref_communes_france IS 'Référentiel officiel des communes françaises (source: data.gouv.fr)';


-- public.dim_job_categories definition

-- Drop table

-- DROP TABLE public.dim_job_categories;

CREATE TABLE public.dim_job_categories (
	job_category_id serial4 NOT NULL,
	category_name varchar(255) NOT NULL,
	category_code varchar(50) NULL,
	parent_category_id int4 NULL,
	"level" int4 DEFAULT 1 NULL,
	created_at timestamp DEFAULT now() NULL,
	CONSTRAINT dim_job_categories_category_name_key UNIQUE (category_name),
	CONSTRAINT dim_job_categories_pkey PRIMARY KEY (job_category_id),
	CONSTRAINT dim_job_categories_parent_category_id_fkey FOREIGN KEY (parent_category_id) REFERENCES public.dim_job_categories(job_category_id)
);


-- public.fact_job_offers definition

-- Drop table

-- DROP TABLE public.fact_job_offers;

CREATE TABLE public.fact_job_offers (
	offer_id serial4 NOT NULL,
	source_id int4 NULL,
	date_id int4 NULL,
	commune_id int4 NULL, -- Référence à la commune (FK vers ref_communes_france)
	job_category_id int4 NULL,
	external_id varchar(255) NULL,
	title varchar(500) NOT NULL,
	description text NOT NULL,
	description_cleaned text NULL,
	url text NULL,
	company_name varchar(255) NULL,
	contract_type varchar(100) NULL,
	salary_min numeric(10, 2) NULL,
	salary_max numeric(10, 2) NULL,
	published_date date NULL,
	collected_date timestamp DEFAULT now() NULL,
	experience_years int4 NULL,
	skills_extracted _text NULL,
	processed bool DEFAULT false NULL,
	processing_date timestamp NULL,
	topic_id int4 NULL, -- ID du topic LDA (0-7)
	topic_label varchar(100) NULL, -- Label descriptif du topic
	topic_confidence numeric(3, 2) NULL, -- Confiance du modèle LDA (0-1)
	profile_category varchar(100) NULL,
	profile_score int4 NULL,
	education_level int4 NULL,
	education_type varchar(50) NULL,
	remote_possible bool NULL,
	remote_days int4 NULL,
	remote_percentage int4 NULL,
	CONSTRAINT fact_job_offers_external_id_key UNIQUE (external_id),
	CONSTRAINT fact_job_offers_pkey PRIMARY KEY (offer_id),
	CONSTRAINT fact_job_offers_commune_id_fkey FOREIGN KEY (commune_id) REFERENCES public.ref_communes_france(commune_id),
	CONSTRAINT fact_job_offers_date_id_fkey FOREIGN KEY (date_id) REFERENCES public.dim_dates(date_id),
	CONSTRAINT fact_job_offers_job_category_id_fkey FOREIGN KEY (job_category_id) REFERENCES public.dim_job_categories(job_category_id),
	CONSTRAINT fact_job_offers_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.dim_sources(source_id),
	CONSTRAINT fk_topic FOREIGN KEY (topic_id) REFERENCES public.dim_topics(topic_id)
);
CREATE INDEX idx_fact_offers_category ON public.fact_job_offers USING btree (job_category_id);
CREATE INDEX idx_fact_offers_commune ON public.fact_job_offers USING btree (commune_id);
CREATE INDEX idx_fact_offers_external_id ON public.fact_job_offers USING btree (external_id);
CREATE INDEX idx_fact_offers_published_date ON public.fact_job_offers USING btree (published_date);
CREATE INDEX idx_fact_offers_source ON public.fact_job_offers USING btree (source_id);
CREATE INDEX idx_fact_offers_url ON public.fact_job_offers USING btree (url);
CREATE INDEX idx_offers_topic ON public.fact_job_offers USING btree (topic_id);
CREATE INDEX idx_offers_topic_label ON public.fact_job_offers USING btree (topic_label);
COMMENT ON TABLE public.fact_job_offers IS 'Table de faits des offres d''emploi collectées';

-- Column comments

COMMENT ON COLUMN public.fact_job_offers.commune_id IS 'Référence à la commune (FK vers ref_communes_france)';
COMMENT ON COLUMN public.fact_job_offers.topic_id IS 'ID du topic LDA (0-7)';
COMMENT ON COLUMN public.fact_job_offers.topic_label IS 'Label descriptif du topic';
COMMENT ON COLUMN public.fact_job_offers.topic_confidence IS 'Confiance du modèle LDA (0-1)';


-- public.fact_offer_skills definition

-- Drop table

-- DROP TABLE public.fact_offer_skills;

CREATE TABLE public.fact_offer_skills (
	offer_id int4 NOT NULL,
	skill_id int4 NOT NULL,
	confidence numeric(3, 2) NULL,
	CONSTRAINT fact_offer_skills_pkey PRIMARY KEY (offer_id, skill_id),
	CONSTRAINT fact_offer_skills_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.fact_job_offers(offer_id) ON DELETE CASCADE,
	CONSTRAINT fact_offer_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.dim_skills(skill_id)
);


-- public.job_embeddings definition

-- Drop table

-- DROP TABLE public.job_embeddings;

CREATE TABLE public.job_embeddings (
	embedding_id serial4 NOT NULL,
	offer_id int4 NULL,
	embedding public.vector NULL,
	model_name varchar(100) NULL,
	created_at timestamp DEFAULT now() NULL,
	CONSTRAINT job_embeddings_offer_id_key UNIQUE (offer_id),
	CONSTRAINT job_embeddings_pkey PRIMARY KEY (embedding_id),
	CONSTRAINT job_embeddings_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.fact_job_offers(offer_id) ON DELETE CASCADE
);
CREATE INDEX idx_job_embeddings_vector ON public.job_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');