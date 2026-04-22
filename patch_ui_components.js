const fs = require('fs');

function patchFile(filePath, replacements) {
    let content = fs.readFileSync(filePath, 'utf8');
    for (const [search, replace] of replacements) {
        content = content.replace(search, replace);
    }
    fs.writeFileSync(filePath, content);
}

// Card
patchFile('apps/web/src/app/components/ui/card.tsx', [
    ['"bg-card text-card-foreground flex flex-col gap-6 rounded-xl border"', '"bg-card text-card-foreground flex flex-col gap-6 rounded-none border-2 border-foreground hover:shadow-[4px_4px_0_0_#FF3300] shadow-[3px_3px_0_0_#09090b] transition-all hover:-translate-y-1 hover:-translate-x-1"']
]);

// Button
patchFile('apps/web/src/app/components/ui/button.tsx', [
    [/default: "bg-primary text-primary-foreground hover:bg-primary\/90"/g, 'default: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-[3px_3px_0_0_#09090b] outline-2 outline-foreground outline"'],
    [/outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground"/g, 'outline: "border-2 border-foreground bg-background hover:bg-accent hover:text-accent-foreground shadow-[3px_3px_0_0_#09090b]"'],
    [/secondary: "bg-secondary text-secondary-foreground hover:bg-secondary\/80"/g, 'secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-[3px_3px_0_0_#09090b] border-2 border-foreground"']
]);


patchFile('apps/web/src/app/components/ui/input.tsx', [
    [/rounded-md border/g, 'rounded-none border-2 border-foreground shadow-[3px_3px_0_0_#09090b] transition-all focus:shadow-[4px_4px_0_0_#FF3300] focus:-translate-y-px focus:-translate-x-px']
]);

patchFile('apps/web/src/app/components/ui/textarea.tsx', [
    [/rounded-md border/g, 'rounded-none border-2 border-foreground shadow-[3px_3px_0_0_#09090b] transition-all focus:shadow-[4px_4px_0_0_#FF3300] focus:-translate-y-px focus:-translate-x-px']
]);

