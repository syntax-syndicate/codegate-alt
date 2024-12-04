-- name: GetPromptWithOutputs :many
SELECT 
    p.*,
    o.id as output_id,
    o.output,
    o.timestamp as output_timestamp
FROM prompts p
LEFT JOIN outputs o ON p.id = o.prompt_id
ORDER BY o.timestamp DESC;

-- name: GetAlertsWithPromptAndOutput :many
SELECT 
    a.*,
    p.timestamp as prompt_timestamp,
    p.provider,
    p.request,
    p.type,
    o.id as output_id,
    o.output,
    o.timestamp as output_timestamp
FROM alerts a
LEFT JOIN prompts p ON p.id = a.prompt_id
LEFT JOIN outputs o ON p.id = o.prompt_id
ORDER BY a.timestamp DESC;
