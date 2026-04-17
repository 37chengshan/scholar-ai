#!/bin/bash
sed -i '' 's/"flex items-center gap-3 bg-card border border-primary\/30 p-1 rounded-full focus-within:border-primary transition-colors shadow-sm group"/"flex items-center gap-3 bg-transparent border-b-[3px] border-black\/20 pb-2 focus-within:border-orange-600 transition-colors group"/g' apps/web/src/features/search/components/SearchToolbar.tsx
