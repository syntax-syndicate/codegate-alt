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
SELECT 
    a.*,
    p.type as prompt_type,
    o.status as output_status
FROM alerts a
JOIN prompts p ON a.prompt_id = p.id
JOIN outputs o ON a.output_id = o.id
WHERE a.id = ?;

-- name: ListAlertsByPrompt :many
SELECT 
    a.*,
    o.status as output_status
FROM alerts a
JOIN outputs o ON a.output_id = o.id
WHERE a.prompt_id = ? 
ORDER BY a.timestamp DESC;

-- name: GetAlertsByType :many
SELECT 
    a.*,
    p.type as prompt_type,
    o.status as output_status
FROM alerts a
JOIN prompts p ON a.prompt_id = p.id
JOIN outputs o ON a.output_id = o.id
WHERE a.trigger_type = ?
ORDER BY a.timestamp DESC
LIMIT ?;

-- name: GetAlertStats :one
SELECT 
    COUNT(*) as total_alerts,
    COUNT(DISTINCT prompt_id) as affected_prompts,
    COUNT(DISTINCT trigger_type) as unique_trigger_types,
    COUNT(CASE WHEN trigger_category IS NOT NULL THEN 1 END) as categorized_alerts
FROM alerts
WHERE timestamp >= datetime('now', '-? hours');

-- name: GetAlertsByCategory :many
SELECT 
    trigger_category,
    COUNT(*) as alert_count,
    COUNT(DISTINCT prompt_id) as affected_prompts,
    MIN(timestamp) as first_occurrence,
    MAX(timestamp) as last_occurrence
FROM alerts
WHERE trigger_category IS NOT NULL
GROUP BY trigger_category
ORDER BY alert_count DESC;

-- name: DeleteAlert :exec
DELETE FROM alerts WHERE id = ?;

-- name: DeleteAlertsByPrompt :exec
DELETE FROM alerts WHERE prompt_id = ?;
