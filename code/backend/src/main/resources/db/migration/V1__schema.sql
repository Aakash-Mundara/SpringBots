-- OnboardIQ core schema (Section 3 of the build prompt).
-- Every mutable business table carries "version BIGINT" for JPA optimistic locking.

-- ---------------------------------------------------------------- auth
CREATE TABLE users (
    id              UUID PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(100) NOT NULL,
    display_name    VARCHAR(128) NOT NULL,
    enabled         BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    version         BIGINT       NOT NULL DEFAULT 0
);

CREATE TABLE user_roles (
    user_id  UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role     VARCHAR(32) NOT NULL CHECK (role IN ('APPLICANT','KYC_OFFICER','COMPLIANCE_OFFICER')),
    PRIMARY KEY (user_id, role)
);

-- ---------------------------------------------------------------- reference data
CREATE TABLE occupations (
    occupation_code  VARCHAR(64)  PRIMARY KEY,
    description      VARCHAR(255) NOT NULL,
    risk_level       VARCHAR(8)   NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH'))
);

CREATE TABLE sanctions_entries (
    list_id      VARCHAR(16)  PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    alias        VARCHAR(255),
    dob          DATE,
    nationality  VARCHAR(8),
    program      VARCHAR(128)
);

CREATE TABLE pep_entries (
    pep_id    VARCHAR(16)  PRIMARY KEY,
    name      VARCHAR(255) NOT NULL,
    dob       DATE,
    position  VARCHAR(255),
    category  VARCHAR(16)
);

CREATE TABLE existing_customers (
    customer_id  VARCHAR(16)  PRIMARY KEY,
    full_name    VARCHAR(255) NOT NULL,
    pan_number   CHAR(10)     NOT NULL,
    dob          DATE
);
CREATE INDEX ix_existing_customers_pan ON existing_customers(pan_number);

CREATE TABLE rules_config (
    key         VARCHAR(128) PRIMARY KEY,
    value       JSONB        NOT NULL,
    updated_by  VARCHAR(64)  NOT NULL DEFAULT 'system',
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    version     BIGINT       NOT NULL DEFAULT 0
);

-- History of every config version (written on seed and on every PUT /admin/rules-config)
CREATE TABLE rules_config_history (
    id              BIGSERIAL    PRIMARY KEY,
    config_version  VARCHAR(32)  NOT NULL,
    snapshot        JSONB        NOT NULL,
    changed_by      VARCHAR(64)  NOT NULL,
    changed_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- applications
CREATE SEQUENCE application_id_seq START WITH 2200001;   -- live IDs never collide with A2000xxx / A2100xxx
CREATE SEQUENCE document_id_seq    START WITH 3100001;   -- live IDs never collide with D3000xxx

CREATE TABLE applications (
    application_id             VARCHAR(16)  PRIMARY KEY,
    owner_user_id              UUID         NOT NULL REFERENCES users(id),
    application_date           DATE         NOT NULL,
    full_name                  VARCHAR(255) NOT NULL,
    dob                        DATE         NOT NULL,
    gender                     VARCHAR(8),
    pan_number                 CHAR(10)     NOT NULL,
    aadhaar_last4              CHAR(4)      NOT NULL CHECK (aadhaar_last4 ~ '^[0-9]{4}$'),
    mobile                     VARCHAR(10)  NOT NULL,
    email                      VARCHAR(255) NOT NULL,
    address                    VARCHAR(512) NOT NULL,
    city                       VARCHAR(128) NOT NULL,
    state                      VARCHAR(128) NOT NULL,
    pincode                    CHAR(6)      NOT NULL,
    occupation_code            VARCHAR(64)  NOT NULL REFERENCES occupations(occupation_code),
    annual_income              BIGINT       NOT NULL CHECK (annual_income >= 0),
    consent                    BOOLEAN      NOT NULL,
    status                     VARCHAR(32)  NOT NULL CHECK (status IN (
                                   'DRAFT','SUBMITTED','EXTRACTING','AUTO_APPROVED','PENDING_CHECKER',
                                   'IN_REVIEW','AUTO_REJECTED','RESUBMISSION_REQUESTED','APPROVED',
                                   'REJECTED','CLOSED_EXPIRED')),
    resubmission_requested_at  TIMESTAMPTZ,
    submitted_at               TIMESTAMPTZ,
    decided_at                 TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ  NOT NULL DEFAULT now(),
    version                    BIGINT       NOT NULL DEFAULT 0
);
CREATE INDEX ix_applications_owner  ON applications(owner_user_id);
CREATE INDEX ix_applications_status ON applications(status);
CREATE INDEX ix_applications_pan    ON applications(pan_number);
CREATE INDEX ix_applications_date   ON applications(application_date);

CREATE TABLE documents (
    doc_id             VARCHAR(16)  PRIMARY KEY,
    application_id     VARCHAR(16)  NOT NULL REFERENCES applications(application_id),
    file_name          VARCHAR(255) NOT NULL,
    declared_doc_type  VARCHAR(32)  NOT NULL CHECK (declared_doc_type IN (
                           'PAN_CARD','AADHAAR_CARD','ELECTRICITY_BILL','BANK_STATEMENT','DRIVING_LICENCE')),
    content_type       VARCHAR(64)  NOT NULL,
    size_bytes         BIGINT       NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 1048576),
    sha256             CHAR(64)     NOT NULL,
    s3_key             VARCHAR(255) NOT NULL UNIQUE,
    uploaded_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    superseded         BOOLEAN      NOT NULL DEFAULT FALSE,
    version            BIGINT       NOT NULL DEFAULT 0,
    CONSTRAINT uq_documents_app_hash UNIQUE (application_id, sha256)
);
CREATE INDEX ix_documents_app ON documents(application_id);

-- ---------------------------------------------------------------- extraction
CREATE TABLE extractions (
    id                   UUID         PRIMARY KEY,
    doc_id               VARCHAR(16)  NOT NULL REFERENCES documents(doc_id),
    doc_type             VARCHAR(32)  NOT NULL,
    doc_type_confidence  NUMERIC(3,2) NOT NULL CHECK (doc_type_confidence BETWEEN 0 AND 1),
    provider             VARCHAR(16)  NOT NULL CHECK (provider IN ('MOCK','AI','OFFICER')),
    extractor_version    VARCHAR(128) NOT NULL,
    status               VARCHAR(16)  NOT NULL CHECK (status IN ('OK','FAILED','TIMEOUT')),
    raw_text             TEXT,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_extractions_doc ON extractions(doc_id, created_at DESC);

CREATE TABLE extracted_fields (
    id             UUID         PRIMARY KEY,
    extraction_id  UUID         NOT NULL REFERENCES extractions(id),
    doc_id         VARCHAR(16)  NOT NULL REFERENCES documents(doc_id),
    field_name     VARCHAR(64)  NOT NULL,
    value          TEXT,
    confidence     NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source         VARCHAR(16)  NOT NULL CHECK (source IN ('MOCK','AI','OFFICER')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_extracted_fields_doc ON extracted_fields(doc_id, field_name, created_at DESC);

CREATE TABLE field_corrections (
    id              UUID         PRIMARY KEY,
    application_id  VARCHAR(16)  NOT NULL REFERENCES applications(application_id),
    doc_id          VARCHAR(16)  NOT NULL REFERENCES documents(doc_id),
    field_name      VARCHAR(64)  NOT NULL,
    old_value       TEXT,
    new_value       TEXT         NOT NULL,
    reason          VARCHAR(1000) NOT NULL,
    officer_id      UUID         NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- decisions & workflow
CREATE TABLE decisions (
    id                UUID          PRIMARY KEY,
    application_id    VARCHAR(16)   NOT NULL REFERENCES applications(application_id),
    decision          VARCHAR(8)    NOT NULL CHECK (decision IN ('APPROVE','REVIEW','REJECT')),
    reason_codes      VARCHAR(1000) NOT NULL DEFAULT '',
    name_match_score  NUMERIC(6,4),
    risk_category     VARCHAR(8)    CHECK (risk_category IN ('LOW','MEDIUM','HIGH')),
    rekyc_due_date    DATE,
    rule_details      JSONB         NOT NULL DEFAULT '{}'::jsonb,
    config_version    VARCHAR(32)   NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    is_current        BOOLEAN       NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_decisions_app ON decisions(application_id, created_at DESC);
CREATE UNIQUE INDEX uq_decisions_current ON decisions(application_id) WHERE is_current;

CREATE TABLE recommendations (
    id              UUID          PRIMARY KEY,
    application_id  VARCHAR(16)   NOT NULL REFERENCES applications(application_id),
    officer_id      UUID          NOT NULL REFERENCES users(id),
    recommendation  VARCHAR(32)   NOT NULL CHECK (recommendation IN ('APPROVE','REJECT','REQUEST_RESUBMISSION')),
    comment         VARCHAR(2000) NOT NULL CHECK (char_length(comment) >= 10),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_recommendations_app ON recommendations(application_id, created_at DESC);

CREATE TABLE checker_decisions (
    id              UUID          PRIMARY KEY,
    application_id  VARCHAR(16)   NOT NULL REFERENCES applications(application_id),
    checker_id      UUID          NOT NULL REFERENCES users(id),
    decision        VARCHAR(16)   NOT NULL CHECK (decision IN ('APPROVE','REJECT','SEND_BACK')),
    comment         VARCHAR(2000) NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    application_id  VARCHAR(16)  PRIMARY KEY REFERENCES applications(application_id),
    customer_id     VARCHAR(16)  NOT NULL UNIQUE CHECK (customer_id ~ '^C[0-9]{8}$'),
    account_number  CHAR(12)     NOT NULL UNIQUE CHECK (account_number ~ '^[0-9]{12}$'),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE processing_jobs (
    job_id          UUID          PRIMARY KEY,
    application_id  VARCHAR(16)   NOT NULL REFERENCES applications(application_id),
    status          VARCHAR(16)   NOT NULL CHECK (status IN ('QUEUED','RUNNING','DONE','FAILED','DLQ')),
    attempts        INT           NOT NULL DEFAULT 0,
    last_error      VARCHAR(2000),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    version         BIGINT        NOT NULL DEFAULT 0
);
CREATE INDEX ix_jobs_app ON processing_jobs(application_id);
CREATE INDEX ix_jobs_status ON processing_jobs(status, updated_at);

-- ---------------------------------------------------------------- audit (append-only, see V2)
CREATE TABLE audit_log (
    id              BIGSERIAL    PRIMARY KEY,
    application_id  VARCHAR(16),
    doc_id          VARCHAR(16),
    actor_user_id   UUID,
    actor_role      VARCHAR(32),
    action          VARCHAR(32)  NOT NULL CHECK (action IN (
                        'APPLICATION_CREATED','DOCUMENT_UPLOADED','DOCUMENT_VIEWED','STATUS_CHANGED',
                        'EXTRACTION_COMPLETED','RULES_EVALUATED','WATCHLIST_HIT','FIELD_CORRECTED',
                        'RECOMMENDATION_MADE','CHECKER_DECISION','ACCOUNT_OPENED','CONFIG_CHANGED',
                        'WATCHLIST_UPDATED')),
    details         JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_app ON audit_log(application_id, id);
