#!/bin/bash

# Update Border Radius to 0 for brutalist magazine style in theme.css
sed -i '' 's/--radius: 0.625rem;/--radius: 0rem;/' apps/web/src/styles/theme.css
sed -i '' 's/--radius-sm: 0.375rem;/--radius-sm: 0rem;/' apps/web/src/styles/theme.css
sed -i '' 's/--radius-md: 0.5rem;/--radius-md: 0rem;/' apps/web/src/styles/theme.css
sed -i '' 's/--radius-lg: 0.625rem;/--radius-lg: 0rem;/' apps/web/src/styles/theme.css
sed -i '' 's/--radius-xl: 1rem;/--radius-xl: 0rem;/' apps/web/src/styles/theme.css

# Update Shadows for brutalist look (offset shadows)
sed -i '' 's/--shadow-paper: 0 1px 3px rgba(36, 28, 22, 0.06), 0 1px 2px rgba(36, 28, 22, 0.04);/--shadow-paper: 4px 4px 0px 0px rgba(9, 9, 11, 1);/' apps/web/src/styles/theme.css
sed -i '' 's/--shadow-paper-hover: 0 6px 18px rgba(36, 28, 22, 0.1), 0 2px 6px rgba(36, 28, 22, 0.06);/--shadow-paper-hover: 6px 6px 0px 0px rgba(9, 9, 11, 1);/' apps/web/src/styles/theme.css
sed -i '' 's/--shadow-paper-active: 0 10px 28px rgba(36, 28, 22, 0.14), 0 4px 10px rgba(36, 28, 22, 0.08);/--shadow-paper-active: 2px 2px 0px 0px rgba(9, 9, 11, 1);/' apps/web/src/styles/theme.css

# In Layout.tsx, make borders much stronger 
sed -i '' 's/border-border\/50/border-foreground border-2/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/border-border\/60/border-foreground border-2/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/border-r border-border\/50/border-r-2 border-foreground/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/border-border\/70/border-foreground border-2/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/border-border\/80/border-foreground border-2/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/bg-paper-1\/88/bg-background/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/bg-paper-2\/96/bg-yellow-50/g' apps/web/src/app/components/Layout.tsx
sed -i '' 's/border-b border-foreground\/20/border-b-2 border-foreground/g' apps/web/src/app/components/Layout.tsx

# Also fix the main area background gradient
sed -i '' 's/bg-\[radial-gradient(circle_at_top,_rgba(194,91,31,0.07),_transparent_42%),linear-gradient(180deg,_rgba(255,253,250,0.94),_rgba(247,242,234,0.86))\]/bg-paper-1/g' apps/web/src/app/components/Layout.tsx
