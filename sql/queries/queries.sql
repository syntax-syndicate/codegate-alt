-- name: CreatePrompt :one
INSERT INTO prompts (
    id,
    timestamp,
    provider,
    system_prompt,
    user_prompt,
    type
) VALUES (?, ?, ?, ?, ?, ?) RETURNING *;

-- name: GetPrompt :one
SELECT * FROM prompts WHERE id = ?;

-- name: ListPrompts :many
SELECT * FROM prompts 
ORDER BY timestamp DESC 
LIMIT ? OFFSET ?;

-- name: CreateOutput :one
INSERT INTO outputs (
    id,
    prompt_id,
    timestamp,
    output
) VALUES (?, ?, ?, ?) RETURNING *;

-- name: GetOutput :one
SELECT * FROM outputs WHERE id = ?;

-- name: GetOutputsByPromptId :many
SELECT * FROM outputs 
WHERE prompt_id = ? 
ORDER BY timestamp DESC;

-- name: CreateAlert :one
INSERT INTO alerts (
    id,
    prompt_id,
    output_id,
    code_snippet,
    trigger_string,
    trigger_type,
    trigger_category,
    timestamp
) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *;

-- name: GetAlert :one
SELECT * FROM alerts WHERE id = ?;

-- name: ListAlertsByPrompt :many
SELECT * FROM alerts 
WHERE prompt_id = ? 
ORDER BY timestamp DESC;

-- name: GetSettings :one
SELECT * FROM settings ORDER BY id LIMIT 1;

-- name: UpsertSettings :one
INSERT INTO settings (
    id,
    ip,
    port,
    llm_model,
    system_prompt,
    other_settings
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    ip = excluded.ip,
    port = excluded.port,
    llm_model = excluded.llm_model,
    system_prompt = excluded.system_prompt,
    other_settings = excluded.other_settings
RETURNING *;

-- name: GetPromptWithOutputsAndAlerts :many
SELECT 
    p.*,
    o.id as output_id,
    o.output,
    a.id as alert_id,
    a.code_snippet,
    a.trigger_string,
    a.trigger_type,
    a.trigger_category
FROM prompts p
LEFT JOIN outputs o ON p.id = o.prompt_id
LEFT JOIN alerts a ON p.id = a.prompt_id
WHERE p.id = ?
ORDER BY o.timestamp DESC, a.timestamp DESC;
