-- name: CreatePrompt :one
INSERT INTO prompts (
    id,
    timestamp,
    provider,
    system_prompt,
    user_prompt,
    type,
    status
) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *;

-- name: GetPrompt :one
SELECT * FROM prompts WHERE id = ?;

-- name: ListPrompts :many
WITH prompt_counts AS (
    SELECT 
        p.id,
        COUNT(DISTINCT o.id) as output_count,
        COUNT(DISTINCT a.id) as alert_count
    FROM prompts p
    LEFT JOIN outputs o ON p.id = o.prompt_id
    LEFT JOIN alerts a ON p.id = a.prompt_id
    GROUP BY p.id
)
SELECT 
    p.*,
    pc.output_count,
    pc.alert_count
FROM prompts p
JOIN prompt_counts pc ON p.id = pc.id
ORDER BY p.timestamp DESC 
LIMIT ? OFFSET ?;

-- name: GetPromptWithOutputsAndAlerts :many
WITH recent_outputs AS (
    SELECT * FROM outputs 
    WHERE prompt_id = ?
    ORDER BY timestamp DESC
    LIMIT 10
),
recent_alerts AS (
    SELECT * FROM alerts 
    WHERE prompt_id = ?
    ORDER BY timestamp DESC
    LIMIT 10
)
SELECT 
    p.*,
    o.id as output_id,
    o.output,
    o.status as output_status,
    a.id as alert_id,
    a.code_snippet,
    a.trigger_string,
    a.trigger_type,
    a.trigger_category
FROM prompts p
LEFT JOIN recent_outputs o ON p.id = o.prompt_id
LEFT JOIN recent_alerts a ON p.id = a.prompt_id
WHERE p.id = ?
ORDER BY o.timestamp DESC, a.timestamp DESC;

-- name: UpdatePromptStatus :one
UPDATE prompts 
SET status = ? 
WHERE id = ? 
RETURNING *;

-- name: DeletePrompt :exec
DELETE FROM prompts WHERE id = ?;
