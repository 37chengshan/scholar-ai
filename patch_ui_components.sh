#!/bin/bash
# Patch Card
sed -i '' 's/"bg-card text-card-foreground flex flex-col gap-6 rounded-xl border"/"bg-card text-card-foreground flex flex-col gap-6 rounded-none border-2 border-r-4 border-b-4 border-foreground shadow-[4px_4px_0_0_#FF3300] hover:shadow-[6px_6px_0_0_#002FA7] transition-all hover:-translate-y-1"/g' apps/web/src/app/components/ui/card.tsx

# Patch Button
sed -i '' 's/"whitespace-nowrap transition-colors outline-ring\/50 focus-visible:ring-ring\/50 disabled:pointer-events-none disabled:opacity-50 inline-flex items-center justify-center gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not(\[class\*=\x27size-\x27\])]:size-4"/"whitespace-nowrap transition-all outline-ring\/50 focus-visible:ring-ring\/50 disabled:pointer-events-none disabled:opacity-50 inline-flex items-center justify-center gap-2 border-2 border-foreground [\&_svg]:pointer-events-none [\&_svg]:shrink-0 [\&_svg:not(\[class\*=size-\])]:size-4 hover:-translate-y-1"/g' apps/web/src/app/components/ui/button.tsx
sed -i '' 's/default: "bg-primary text-primary-foreground hover:bg-primary\/90"/default: "bg-primary text-primary-foreground hover:bg-primary\/90 shadow-[3px_3px_0_0_#09090b]"/g' apps/web/src/app/components/ui/button.tsx
sed -i '' 's/outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground"/outline: "border-2 border-foreground bg-background hover:bg-accent hover:text-accent-foreground shadow-[3px_3px_0_0_#09090b]"/g' apps/web/src/app/components/ui/button.tsx
sed -i '' 's/secondary: "bg-secondary text-secondary-foreground hover:bg-secondary\/80"/secondary: "bg-secondary text-secondary-foreground hover:bg-secondary\/80 shadow-[3px_3px_0_0_#09090b]"/g' apps/web/src/app/components/ui/button.tsx
