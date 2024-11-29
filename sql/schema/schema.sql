-- Schema for codegate database using SQLite

-- Prompts table
CREATE TABLE prompts (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    timestamp DATETIME NOT NULL,
    provider TEXT,       -- VARCHAR(255)
    system_prompt TEXT,
    user_prompt TEXT NOT NULL,
    type TEXT NOT NULL, -- VARCHAR(50) (e.g. "fim", "chat")
    status TEXT NOT NULL  -- VARCHAR(50)
);

-- Outputs table
CREATE TABLE outputs (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    prompt_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    output TEXT NOT NULL,
    status TEXT NOT NULL, -- VARCHAR(50)
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

-- Alerts table
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    prompt_id TEXT NOT NULL,
    output_id TEXT NOT NULL,
    code_snippet TEXT NOT NULL,  -- VARCHAR(255)
    trigger_string TEXT NOT NULL, -- VARCHAR(255)
    trigger_type TEXT NOT NULL,   -- VARCHAR(50)
    trigger_category TEXT,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (output_id) REFERENCES outputs(id)
);

-- Settings table
CREATE TABLE settings (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    ip TEXT,             -- VARCHAR(45)
    port INTEGER,
    llm_model TEXT,      -- VARCHAR(255)
    system_prompt TEXT,
    other_settings TEXT  -- JSON stored as TEXT
);

-- Create indexes for foreign keys and frequently queried columns
CREATE INDEX idx_outputs_prompt_id ON outputs(prompt_id);
CREATE INDEX idx_alerts_prompt_id ON alerts(prompt_id);
CREATE INDEX idx_alerts_output_id ON alerts(output_id);
CREATE INDEX idx_prompts_timestamp ON prompts(timestamp);
CREATE INDEX idx_outputs_timestamp ON outputs(timestamp);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
