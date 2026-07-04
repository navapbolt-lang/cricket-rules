# Embed Guide — Partner Integration

## Quick Start

Add this single line to your site's `<head>` or just before `</body>`:

```html
<script src="https://api.cricketrules.ai/widget.js"
        data-partner="your-partner-id"
        data-brand-color="#FF5722"
        data-logo="https://yoursite.com/logo.svg"
        data-position="right"
        defer></script>
```

That's it. The widget will appear as a floating button on your site.

---

## Configuration Options

| Attribute | Type | Default | Description |
|---|---|---|---|
| `data-partner` | string | required | Your partner ID (provided during onboarding) |
| `data-brand-color` | hex | `#1a1a2e` | Primary color for the widget |
| `data-logo` | URL | none | Your logo (appears in widget header) |
| `data-position` | string | `right` | "right" or "left" |
| `data-mode` | string | `auto` | "auto", "light", "dark" |
| `data-context` | string | `general` | "match", "article", "general" |

---

## Context Detection

The widget auto-detects what page the user is on:

- **match.html** or URL contains `/match/` → context: "match"
- **article.html** or URL contains `/article/` or `/news/` → context: "article"
- Everything else → context: "general"

The context affects which suggested questions are shown first.

---

## Styling

The widget uses Shadow DOM — it will NOT conflict with your site's CSS.

To customize beyond `data-brand-color`, include a style override:

```html
<script>
  window.CricketRulesWidget = {
    styles: {
      buttonSize: '56px',
      borderRadius: '16px',
      fontFamily: 'Arial, sans-serif',
      headerHeight: '60px'
    }
  };
</script>
<script src="..." defer></script>
```

---

## API Key

Your partner API key is bundled into the script URL:

```html
<script src="https://api.cricketrules.ai/widget.js?key=sk_live_xxxxx" ...>
```

The key is used for server-side authentication. It's never exposed client-side.

---

## Testing

```html
<!-- Test with staging environment -->
<script src="https://staging.cricketrules.ai/widget.js"
       data-partner="demo"
       data-brand-color="#4CAF50"
       defer></script>
```

---

## What Users See

1. A small floating button (bottom-right or bottom-left)
2. Click → expands into a chat sidebar
3. Suggested questions appear based on page context
4. Type a question → answer appears with law citations
5. Click citations → expand law text
6. 👍/👎 buttons for feedback

---

## Analytics Dashboard

Partners get access to:
- `https://api.cricketrules.ai/partner/dashboard`
- Queries per day/week/month
- Most asked questions
- User satisfaction rate (thumbs up/down)
- Common topics

---

## Browser Support

- Chrome 80+
- Firefox 80+
- Safari 14+
- Edge 80+

IE11 is NOT supported.
