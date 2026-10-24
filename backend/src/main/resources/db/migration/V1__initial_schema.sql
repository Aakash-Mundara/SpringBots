CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(100) NOT NULL, display_name VARCHAR(160) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE user_roles (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(40) NOT NULL, PRIMARY KEY(user_id, role)
);
CREATE TABLE applications (
  application_id VARCHAR(8) PRIMARY KEY, owner_user_id BIGINT REFERENCES users(id),
  application_date DATE NOT NULL, full_name VARCHAR(200) NOT NULL, dob DATE NOT NULL,
  gender VARCHAR(30), pan_number VARCHAR(10) NOT NULL, aadhaar_last4 CHAR(4) NOT NULL,
  mobile VARCHAR(10) NOT NULL, email VARCHAR(254) NOT NULL, address TEXT NOT NULL,
  city VARCHAR(100) NOT NULL, state VARCHAR(100) NOT NULL, pincode VARCHAR(6) NOT NULL,
  occupation_code VARCHAR(40) NOT NULL, annual_income NUMERIC(14,2) NOT NULL,
  consent BOOLEAN NOT NULL DEFAULT FALSE, status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
  submitted_at TIMESTAMPTZ, resubmission_requested_at TIMESTAMPTZ, decided_at TIMESTAMPTZ,
  version BIGINT NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_applications_status_submitted ON applications(status, submitted_at);
CREATE TABLE documents (
  doc_id VARCHAR(80) PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  file_name VARCHAR(255) NOT NULL, declared_doc_type VARCHAR(40) NOT NULL, size_bytes BIGINT NOT NULL,
  sha256 CHAR(64) NOT NULL, s3_key VARCHAR(500) NOT NULL, uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(application_id, sha256)
);
CREATE TABLE extractions (
  id BIGSERIAL PRIMARY KEY, doc_id VARCHAR(80) NOT NULL REFERENCES documents(doc_id),
  doc_type VARCHAR(40) NOT NULL, doc_type_confidence NUMERIC(3,2) NOT NULL,
  provider VARCHAR(30) NOT NULL, extractor_version VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE extracted_fields (
  id BIGSERIAL PRIMARY KEY, extraction_id BIGINT NOT NULL REFERENCES extractions(id),
  doc_id VARCHAR(80) NOT NULL REFERENCES documents(doc_id), field_name VARCHAR(80) NOT NULL,
  value TEXT, confidence NUMERIC(3,2) NOT NULL, source VARCHAR(20) NOT NULL
);
CREATE TABLE field_corrections (
  id BIGSERIAL PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  doc_id VARCHAR(80) NOT NULL REFERENCES documents(doc_id), field_name VARCHAR(80) NOT NULL,
  old_value TEXT, new_value TEXT NOT NULL, reason TEXT NOT NULL, officer_id BIGINT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE decisions (
  id BIGSERIAL PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  decision VARCHAR(20) NOT NULL, reason_codes TEXT[] NOT NULL DEFAULT '{}', name_match_score NUMERIC(5,4),
  risk_category VARCHAR(10), rekyc_due_date DATE, rule_details JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_current BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_decisions_current ON decisions(application_id, is_current);
CREATE TABLE recommendations (
  id BIGSERIAL PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  officer_id BIGINT NOT NULL REFERENCES users(id), recommendation VARCHAR(30) NOT NULL,
  comment TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE checker_decisions (
  id BIGSERIAL PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  checker_id BIGINT NOT NULL REFERENCES users(id), decision VARCHAR(20) NOT NULL,
  comment TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE accounts (
  application_id VARCHAR(8) PRIMARY KEY REFERENCES applications(application_id), customer_id VARCHAR(40) NOT NULL UNIQUE,
  account_number VARCHAR(40) NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE processing_jobs (
  job_id UUID PRIMARY KEY, application_id VARCHAR(8) NOT NULL REFERENCES applications(application_id),
  status VARCHAR(20) NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE llm_cache (
  text_sha256 CHAR(64) PRIMARY KEY, provider VARCHAR(30) NOT NULL,
  response_json JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE rules_config (
  key VARCHAR(120) PRIMARY KEY, value JSONB NOT NULL, updated_by BIGINT REFERENCES users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE occupations (
  occupation_code VARCHAR(40) PRIMARY KEY, description TEXT NOT NULL, risk_level VARCHAR(10) NOT NULL
);
CREATE TABLE sanctions_entries (
  list_id VARCHAR(40) PRIMARY KEY, name VARCHAR(200) NOT NULL, alias VARCHAR(200), dob DATE,
  nationality VARCHAR(20), program VARCHAR(100)
);
CREATE TABLE pep_entries (
  pep_id VARCHAR(40) PRIMARY KEY, name VARCHAR(200) NOT NULL, alias VARCHAR(200), dob DATE,
  position TEXT, category VARCHAR(30)
);
CREATE TABLE existing_customers (
  customer_id VARCHAR(40) PRIMARY KEY, full_name VARCHAR(200) NOT NULL, pan_number VARCHAR(10) NOT NULL, dob DATE
);
CREATE INDEX idx_existing_pan ON existing_customers(pan_number);
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, application_id VARCHAR(8), doc_id VARCHAR(80), actor_user_id BIGINT,
  actor_role VARCHAR(40), action VARCHAR(60) NOT NULL, details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_application_created ON audit_log(application_id, created_at);
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$;
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
