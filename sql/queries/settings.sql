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

-- name: UpdateSchemaVersion :exec
INSERT INTO schema_versions (version) VALUES (?);

-- name: GetCurrentSchemaVersion :one
SELECT version, timestamp 
FROM schema_versions 
ORDER BY timestamp DESC 
LIMIT 1;

-- name: GetSchemaHistory :many
SELECT version, timestamp 
FROM schema_versions 
ORDER BY timestamp DESC;

-- name: DeleteSettings :exec
DELETE FROM settings WHERE id = ?;

-- name: GetSettingsHistory :many
WITH settings_history AS (
    SELECT 
        id,
        ip,
        port,
        llm_model,
        system_prompt,
        other_settings,
        LAG(ip) OVER (ORDER BY rowid) as prev_ip,
        LAG(port) OVER (ORDER BY rowid) as prev_port,
        LAG(llm_model) OVER (ORDER BY rowid) as prev_llm_model,
        LAG(system_prompt) OVER (ORDER BY rowid) as prev_system_prompt,
        LAG(other_settings) OVER (ORDER BY rowid) as prev_other_settings
    FROM settings
)
SELECT 
    id,
    ip,
    port,
    llm_model,
    system_prompt,
    other_settings,
    CASE 
        WHEN ip != prev_ip THEN 1 
        WHEN port != prev_port THEN 1
        WHEN llm_model != prev_llm_model THEN 1
        WHEN system_prompt != prev_system_prompt THEN 1
        WHEN other_settings != prev_other_settings THEN 1
        ELSE 0 
    END as has_changes
FROM settings_history
WHERE has_changes = 1
ORDER BY rowid DESC;
