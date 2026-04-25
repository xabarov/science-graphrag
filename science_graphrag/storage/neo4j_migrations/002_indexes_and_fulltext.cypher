// Wave Q — Neo4j 5 range + composite + fulltext indexes (idempotent).
// Applied automatically via Neo4jGraphStore.ensure_schema(); this file is for ops / review.

CREATE INDEX work_year IF NOT EXISTS FOR (w:Work) ON (w.publication_year);
CREATE INDEX work_fingerprint IF NOT EXISTS FOR (w:Work) ON (w.fingerprint);
CREATE INDEX work_normalized_title IF NOT EXISTS FOR (w:Work) ON (w.normalized_title);
CREATE INDEX work_doi IF NOT EXISTS FOR (w:Work) ON (w.doi);
CREATE INDEX work_arxiv_id IF NOT EXISTS FOR (w:Work) ON (w.arxiv_id);
CREATE INDEX author_normalized_name IF NOT EXISTS FOR (a:Author) ON (a.normalized_name);
CREATE INDEX institution_normalized_name IF NOT EXISTS FOR (i:Institution) ON (i.normalized_name);
CREATE INDEX institution_ror_id IF NOT EXISTS FOR (i:Institution) ON (i.ror_id);
CREATE INDEX venue_issn IF NOT EXISTS FOR (v:Venue) ON (v.issn);
CREATE INDEX method_normalized IF NOT EXISTS FOR (m:Method) ON (m.normalized_name);
CREATE INDEX dataset_normalized IF NOT EXISTS FOR (d:Dataset) ON (d.normalized_name);
CREATE INDEX work_year_type IF NOT EXISTS FOR (w:Work) ON (w.publication_year, w.work_type);

CREATE FULLTEXT INDEX works_title_abstract IF NOT EXISTS FOR (n:Work) ON EACH [n.title, n.abstract];
CREATE FULLTEXT INDEX methods_text IF NOT EXISTS FOR (n:Method) ON EACH [n.name];
CREATE FULLTEXT INDEX datasets_text IF NOT EXISTS FOR (n:Dataset) ON EACH [n.name];
CREATE FULLTEXT INDEX authors_text IF NOT EXISTS FOR (n:Author) ON EACH [n.full_name, n.normalized_name];
CREATE FULLTEXT INDEX institutions_text IF NOT EXISTS FOR (n:Institution) ON EACH [n.name, n.normalized_name];

// Optional (Wave Q2): requires Neo4j vector-index support (5.13+)
CREATE VECTOR INDEX work_title_emb IF NOT EXISTS
FOR (w:Work) ON (w.title_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
