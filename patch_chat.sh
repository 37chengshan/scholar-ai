#!/bin/bash
sed -i '' 's/"font-medium text-ink bg-transparent border-l-2 border-ink\/20 pl-6 rounded-none shadow-none"/"font-bold text-right bg-transparent rounded-none shadow-none text-foreground text-lg leading-relaxed relative border-b-2 border-transparent"/g' apps/web/src/features/chat/components/ChatLegacy.tsx
sed -i '' 's/"bg-paper text-ink rounded-none shadow-none"/"bg-transparent text-foreground rounded-none shadow-none border-l-[1px] border-black pl-6 magazine-body max-w-prose mx-auto"/g' apps/web/src/features/chat/components/ChatLegacy.tsx
