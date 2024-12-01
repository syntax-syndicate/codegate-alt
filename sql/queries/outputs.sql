-- name: CreateOutput :one
INSERT INTO outputs (
    id,
    prompt_id,
    timestamp,
    output,
    status
) VALUES (?, ?, ?, ?, ?) RETURNING *;

-- name: GetOutput :one
SELECT * FROM outputs WHERE id = ?;

-- name: GetOutputsByPromptId :many
SELECT 
    o.*,
    COUNT(a.id) as alert_count
FROM outputs o
LEFT JOIN alerts a ON o.id = a.output_id
WHERE o.prompt_id = ?
GROUP BY o.id
ORDER BY o.timestamp DESC;

-- name: UpdateOutputStatus :one
UPDATE outputs 
SET status = ? 
WHERE id = ? 
RETURNING *;

-- name: GetRecentOutputs :many
SELECT 
    o.*,
    p.type as prompt_type,
    p.status as prompt_status
FROM outputs o
JOIN prompts p ON o.prompt_id = p.id
WHERE o.timestamp >= datetime('now', '-24 hours')
ORDER BY o.timestamp DESC
LIMIT ?;

-- name: DeleteOutput :exec
DELETE FROM outputs WHERE id = ?;

-- name: GetOutputStats :one
SELECT 
    COUNT(*) as total_outputs,
    COUNT(DISTINCT prompt_id) as unique_prompts,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_outputs,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_outputs
FROM outputs
WHERE timestamp >= datetime('now', '-? hours');
