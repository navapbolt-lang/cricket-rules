# Widget Integration Guide

## For Partners

### One-line embed

```html
<script src="https://api.cricketrules.ai/widget.js"
        data-partner="your-partner-id"
        data-brand-color="#FF5722"
        data-position="right"
        defer></script>
```

### Parameters

| Attribute | Required | Description |
|---|---|---|
| `data-partner` | Yes | Your partner ID (provided during onboarding) |
| `data-brand-color` | No | Primary color for the widget (hex) |
| `data-logo` | No | URL to your logo (shows in widget header) |
| `data-position` | No | `right` (default) or `left` |
| `data-mode` | No | `auto` (default), `light`, `dark` |

### Testing locally

```html
<script src="http://localhost:8000/widget.js"
        data-partner="demo"
        data-brand-color="#4CAF50"
        defer></script>
```

### No conflicts

The widget uses Shadow DOM — zero CSS conflicts with your site.

### Analytics

Partners get access to `https://api.cricketrules.ai/partner/dashboard`
