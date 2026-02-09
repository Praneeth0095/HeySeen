# HeySeen Favicon

## Files
- `favicon.svg` - Modern SVG favicon (preferred by modern browsers)
- `favicon.ico` - Legacy ICO format (fallback for older browsers)

## Design
The favicon features the HeySeen eye icon in the brand color scheme:
- Primary color: #FFB800 (Golden Yellow)
- Secondary color: #FF8C00 (Dark Orange)
- Gradient effect for visual depth

## Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge): Use `favicon.svg`
- Older browsers and Windows: Fall back to `favicon.ico`
- iOS devices: Use `apple-touch-icon` referencing the SVG

## Implementation
The favicon links are included in `index.html`:
```html
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="icon" type="image/x-icon" href="favicon.ico">
<link rel="apple-touch-icon" href="favicon.svg">
```

## Updating
To update the favicon:
1. Edit `favicon.svg` with the new design
2. For ICO format, run: `python3 deploy/create_heyseen_favicon.py` (requires Pillow)
3. Clear browser cache to see changes
