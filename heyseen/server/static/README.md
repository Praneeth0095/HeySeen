# HeySeen Static Assets

## CSS Architecture

HeySeen sử dụng **CSS thuần không phụ thuộc framework** với **Gan Jing World color scheme** (yellow-gold-orange) để tạo giao diện ấm áp, sáng và dễ đọc.

### File Structure

```
static/
├── index.html          # Main UI 
├── heyseen.css         # All styles (28KB) - Standalone CSS
├── db.js               # IndexedDB manager
├── app.js              # Application logic
└── README.md           # This file
```

### CSS Organization (heyseen.css)

File này chứa **100% styles** cho HeySeen, được tổ chức thành các sections:

1. **Reset & Base Styles** - Normalize, body defaults
2. **Typography** - Text sizes, weights, colors
3. **Layout & Spacing** - Padding, margin, width/height utilities
4. **Colors & Backgrounds** - Color palette
5. **Borders & Shadows** - Border styles, shadow utilities
6. **Flexbox Utilities** - Flex layout helpers
7. **Component Utilities** - Display, position, cursor, etc.
8. **Base Layout** - Header, content, footer structure
9. **Avatar & Header** - User avatar, dropdown menu
10. **Dropdown Menu** - User menu with gradient header
11. **Modals** - Modal system với animations
12. **Buttons** - Primary, secondary buttons
13. **Forms & Inputs** - Input fields, checkboxes, file upload
14. **Cards & Status** - Upload card, status cards, progress bar
15. **Role Badges** - User role badges (Guest → Experts)
16. **Tabs** - Tab navigation in admin panel
17. **Status Badges** - Project status indicators
18. **Table** - Admin table styling
19. **Scrollbar** - Custom scrollbar cho modals
20. **Footer & Links** - Footer với hover effects
21. **Animations** - fadeIn, slideIn, fadeInDown
22. **Responsive** - Mobile-friendly breakpoints

### Why No Tailwind?

**Lý do chuyển sang CSS thuần:**

1. ❌ **Tailwind CDN warning**: "should not be used in production"
2. ✅ **No dependency**: Không phụ thuộc external CDN
3. ✅ **Human-readable**: Code dễ đọc với comments đầy đủ
4. ✅ **Smaller**: 28KB CSS vs loading entire Tailwind (~3MB)
5. ✅ **Fast**: Không cần parse Tailwind classes runtime
6. ✅ **Simple UI**: HeySeen UI đơn giản, không cần utility framework

### Gan Jing World Color Scheme 🎨

HeySeen áp dụng color palette từ [Gan Jing World](https://www.ganjingworld.com) - warm, friendly, family-oriented:

| Color Name | Hex | Usage |
|------------|-----|-------|
| **Gan Jing Gold** | `#FFB800` | Primary buttons, links, icons |
| **Dark Orange** | `#FF8C00` | Hover states, secondary accents |
| **Orange** | `#FFA500` | Alternative gradients |
| **Red-Orange** | `#FF6B35` | Accent colors |
| **Golden Yellow** | `#FFD700` | Avatar, header gradients |

**Gradients:**
- Avatar & Profile: `#FFD700` → `#FF8C00`
- Projects: `#FFA500` → `#FF6B35`
- Admin Panel: `#FFB800` → `#FF8C00`

**Why Gan Jing World colors?**
- ☀️ Warm, optimistic, family-friendly
- 🌟 Clean aesthetic matching "Gan Jing" (Clean World) philosophy
- 🎯 Distinctive branding aligned with developer's platform

### How to Customize

#### Change Colors

File dùng Gan Jing World color palette. Để thay đổi:

```css
/* Typography Colors (Section 2) */
.text-blue-600 { color: #FFB800; }  /* Primary gold - change this */

/* Backgrounds (Section 4) */
.bg-blue-600 { background-color: #FFB800; }

/* Gradients (Section 9) */
.avatar {
    background: linear-gradient(135deg, #FFD700 0%, #FF8C00 100%);
}
```

#### Change Spacing

```css
/* Section 3 - Layout & Spacing */
.mb-4 { margin-bottom: 1rem; }  /* Adjust this */
.p-8 { padding: 2rem; }
```

#### Add New Components

Thêm vào cuối file trước section Responsive:

```css
/* My Custom Component */
.my-component {
    /* Your styles here */
}
```

### Browser Support

- ✅ Chrome/Edge (Chromium)
- ✅ Safari (MacOS, iOS)
- ✅ Firefox
- ⚠️ IE11 not supported (uses CSS Grid, Flexbox)

### Performance

| Metric | Value |
|--------|-------|
| CSS Size | 28KB |
| Load Time | ~50ms (local) |
| Parse Time | <10ms |
| No Bundle | No build step needed |

### Development Workflow

1. Edit [heyseen.css](heyseen.css) - Well-organized với comments
2. Refresh browser (hard refresh: `Cmd+Shift+R`)
3. Test trên nhiều screen sizes

**No build tools required!** Just edit CSS và reload.

### Notes

- Tất cả animations được define trong CSS (không dùng JavaScript)
- Gradient backgrounds dùng inline styles trong HTML cho flexibility
- Modal system sử dụng fixed positioning với backdrop blur
- Responsive breakpoints: 640px (mobile), 1024px (desktop)

---

**Design Inspiration**: [Gan Jing World](https://www.ganjingworld.com/about)  
**Maintained by**: HeySeen Team  
**Last Updated**: February 9, 2026 - Gan Jing World Color Scheme
