# AgriGuard Design Guidelines

## Design Approach
**Reference-Based Approach**: Drawing inspiration from John Deere Operations Center and Climate FieldView platforms, combined with Apple's clean design philosophy. This approach balances professional agricultural data visualization with minimalist, user-friendly interfaces.

## Color Palette

### Primary Colors (Dark & Light Mode)
- **Primary Green**: #2E7D32 (agricultural/brand color)
- **Data Blue**: #1565C0 (secondary, for data visualization)
- **Warning Amber**: #FF8F00 (accent, for alerts)

### Semantic Colors
- **Background**: #F8F9FA (light grey base)
- **Success/Healthy**: #4CAF50 (healthy vegetation)
- **Warning/Moderate**: #FF9800 (moderate stress)
- **Error/Severe**: #D32F2F (severe stress)

### Map Stress Zones
- Mild: Light yellow/green tint
- Moderate: Orange (#FF9800)
- Severe: Red (#D32F2F)

## Typography
- **Primary Font**: SF Pro Display (headings, key metrics)
- **Secondary Font**: Inter (body text, data labels)
- **Sizes**: Large metrics (32-48px), Section headers (24-28px), Body (16px), Labels (14px)
- **Weights**: Bold (600) for metrics, Medium (500) for headers, Regular (400) for body

## Layout System

### Spacing Units (Tailwind)
- Primary spacing set: **4, 6, 8, 12, 16, 24** (p-4, m-6, gap-8, py-12, px-16, space-y-24)
- Card padding: 24px (p-6)
- Section spacing: 48-96px vertical (py-12 to py-24)
- Grid gaps: 16-24px (gap-4 to gap-6)

### Grid Structure
- Dashboard: 12-column responsive grid
- Metrics cards: 3-column on desktop (lg:grid-cols-3), stacked on mobile
- Time series: Full-width with side filters
- Map integration: 8-column main + 4-column sidebar layout option

## Component Library

### Core UI Elements

**Metric Cards**
- White background with subtle shadow (shadow-sm)
- Rounded corners (rounded-lg)
- Large numeric display with unit label
- Trend indicator (up/down arrow with percentage)
- Icon representing metric type (leaf for NDVI, droplet for ET, thermometer for LST)

**Stress Detection Map**
- Leaflet.js integration with satellite/terrain basemap
- Color-coded overlay zones with opacity for visibility
- Field boundary outlines in primary green
- Interactive tooltips on hover showing stress details
- Legend panel showing zone definitions

**Charts (Time Series)**
- Line charts for trend analysis using Recharts
- Color coding: NDVI (green), ET (blue), LST (orange)
- Grid background with subtle lines
- Date range selector at bottom
- Responsive tooltips with precise values

**Stress Drivers Panel**
- Three-column indicator cards
- Icon + label + severity badge layout
- Progress bars showing threshold levels
- Color-coded by severity (green → orange → red)

### Navigation
- Top navigation bar with logo left, menu items center, user profile right
- Active state: Bottom border in primary green (border-b-2)
- Clean, minimal design following Apple HIG patterns

### Forms & Filters
- Dropdown selects with custom styling (county, field selection)
- Date range picker with calendar UI
- Filter chips showing active selections
- Apply/Reset buttons in primary green

### AgriBot Chatbot
- Slide-in side panel (right-aligned)
- Chat bubble interface with user/bot distinction
- Input field at bottom with send button
- Placeholder state with welcome message
- Toggle button (floating action button) in bottom-right

### Data Overlays
- Modal windows for detailed yield forecasts
- Toast notifications for data updates
- Loading skeletons matching card layouts

## Visual Hierarchy

1. **Primary Focus**: Key metric cards at top (NDVI, ET, LST) with large numbers
2. **Secondary**: Interactive stress map taking center stage
3. **Tertiary**: Time series charts and stress drivers
4. **Supporting**: Filters, navigation, chatbot toggle

## Animations
Use sparingly:
- Smooth transitions on hover (200ms ease)
- Map zoom animations (300ms)
- Panel slide-ins (250ms ease-out)
- No distracting auto-play animations

## Accessibility
- Maintain consistent dark mode capability (not required by default, but infrastructure ready)
- Color contrast ratios meet WCAG AA standards
- Stress zones use patterns in addition to color for colorblind users
- Keyboard navigation for all interactive elements

## Images & Icons
- Use Heroicons or Lucide for UI icons
- Satellite imagery via map tiles (Leaflet providers)
- No large hero image (data dashboard prioritizes immediate utility)
- Field photos in reports section (future enhancement area)

## Professional Agricultural Aesthetic
- Clean, data-first design inspired by precision agriculture tools
- Professional color palette grounded in agricultural green
- Apple-inspired minimalism with focus on data clarity
- Modern card-based layouts with ample whitespace
- Confidence-inspiring design suitable for farm business decisions