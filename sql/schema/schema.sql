-- Schema for codegate database using SQLite

-- Workspaces table
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    name TEXT,
    folder_tree_json TEXT -- JSON stored as TEXT
);

-- Prompts table
CREATE TABLE prompts (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    workspace_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    provider TEXT,       -- VARCHAR(255)
    request TEXT NOT NULL,  -- Record the full request that arrived to the server
    type TEXT NOT NULL, -- VARCHAR(50) (e.g. "fim", "chat")
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
);

-- Outputs table
CREATE TABLE outputs (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    prompt_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    output TEXT NOT NULL,   -- Record the full response. If it was stream will be a list of objects.
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

-- Alerts table
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    prompt_id TEXT NOT NULL,
    code_snippet TEXT,  -- We check in code that not both code_snippet and trigger_string are NULL
    trigger_string TEXT, -- VARCHAR(255)
    trigger_type TEXT NOT NULL,   -- VARCHAR(50)
    trigger_category TEXT,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
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
CREATE INDEX idx_prompts_workspace_id ON prompts(workspace_id);
CREATE INDEX idx_outputs_prompt_id ON outputs(prompt_id);
CREATE INDEX idx_alerts_prompt_id ON alerts(prompt_id);
CREATE INDEX idx_prompts_timestamp ON prompts(timestamp);
CREATE INDEX idx_outputs_timestamp ON outputs(timestamp);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
