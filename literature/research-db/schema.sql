PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fragment_sources;
DROP TABLE IF EXISTS report_fragments;
DROP TABLE IF EXISTS source_recommendations;
DROP TABLE IF EXISTS source_equations;
DROP TABLE IF EXISTS source_concepts;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS equations;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS sources;

CREATE TABLE sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_type TEXT NOT NULL,
  authors TEXT,
  year INTEGER,
  venue TEXT,
  url TEXT,
  local_path TEXT,
  citation_key TEXT,
  summary TEXT,
  relevance_score REAL,
  status TEXT,
  notes TEXT
);

CREATE TABLE concepts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  definition TEXT NOT NULL,
  why_it_matters TEXT NOT NULL,
  wikipedia_url TEXT,
  notes TEXT
);

CREATE TABLE equations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  latex TEXT NOT NULL,
  symbol_legend TEXT NOT NULL,
  conceptual_explanation TEXT NOT NULL,
  report_use TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  recommendation TEXT NOT NULL,
  rationale TEXT NOT NULL,
  priority TEXT NOT NULL,
  applies_to TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE source_concepts (
  source_id INTEGER NOT NULL,
  concept_id INTEGER NOT NULL,
  evidence TEXT,
  PRIMARY KEY (source_id, concept_id),
  FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);

CREATE TABLE source_equations (
  source_id INTEGER NOT NULL,
  equation_id INTEGER NOT NULL,
  location_hint TEXT,
  evidence TEXT,
  PRIMARY KEY (source_id, equation_id),
  FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY (equation_id) REFERENCES equations(id) ON DELETE CASCADE
);

CREATE TABLE source_recommendations (
  source_id INTEGER NOT NULL,
  recommendation_id INTEGER NOT NULL,
  evidence TEXT,
  PRIMARY KEY (source_id, recommendation_id),
  FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE CASCADE
);

CREATE TABLE report_fragments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  target_path TEXT NOT NULL,
  section_title TEXT NOT NULL,
  intent TEXT NOT NULL,
  status TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE fragment_sources (
  fragment_id INTEGER NOT NULL,
  source_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  PRIMARY KEY (fragment_id, source_id, role),
  FOREIGN KEY (fragment_id) REFERENCES report_fragments(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);
