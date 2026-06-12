# Content Queue

Place JSON content files here. Each file should contain a single post payload.

## Format

```json
{
    "platform": "linkedin",
    "text": "Your post content here...",
    "created_at": "2026-05-25T00:00:00",
    "status": "pending"
}
```

## Rules

- One file per post
- Files are consumed in creation-date order  
- Status values: `pending`, `posted`, `skipped`, `ghost_drafted`
- The system will update status after processing
