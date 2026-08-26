import re
import os

PALETTE = {
    "white": "#ffffff",
    "black": "#000000",
    "transparent": "transparent",
    "slate-50": "#f8fafc",
    "slate-100": "#f1f5f9",
    "slate-200": "#e2e8f0",
    "slate-300": "#cbd5e1",
    "slate-400": "#94a3b8",
    "slate-500": "#64748b",
    "slate-600": "#475569",
    "slate-700": "#334155",
    "slate-800": "#1e293b",
    "slate-900": "#0f172a",
    "slate-950": "#020617",
    
    "red-50": "#fef2f2",
    "red-100": "#fee2e2",
    "red-200": "#fecaca",
    "red-300": "#fca5a5",
    "red-400": "#f87171",
    "red-500": "#ef4444",
    "red-600": "#dc2626",
    "red-700": "#b91c1c",
    "red-800": "#991b1b",
    "red-900": "#7f1d1d",
    
    "orange-50": "#fff7ed",
    "orange-100": "#ffedd5",
    "orange-200": "#fed7aa",
    "orange-300": "#fdba74",
    "orange-400": "#fb923c",
    "orange-500": "#ea580c",
    "orange-600": "#ea580c",
    "orange-700": "#c2410c",
    "orange-800": "#9a3412",
    "orange-900": "#7c2d12",
    
    "amber-50": "#fffbeb",
    "amber-100": "#fef3c7",
    "amber-200": "#fde68a",
    "amber-300": "#fcd34d",
    "amber-400": "#fbbf24",
    "amber-500": "#f59e0b",
    "amber-600": "#d97706",
    "amber-700": "#b45309",
    "amber-800": "#92400e",
    "amber-900": "#78350f",
    
    "green-50": "#f0fdf4",
    "green-100": "#dcfce7",
    "green-200": "#bbf7d0",
    "green-300": "#86efac",
    "green-400": "#4ade80",
    "green-500": "#22c55e",
    "green-600": "#16a34a",
    "green-700": "#15803d",
    "green-800": "#166534",
    "green-900": "#14532d",

    "emerald-50": "#ecfdf5",
    "emerald-100": "#d1fae5",
    "emerald-200": "#a7f3d0",
    "emerald-300": "#6ee7b7",
    "emerald-400": "#34d399",
    "emerald-500": "#10b981",
    "emerald-600": "#059669",
    "emerald-700": "#047857",
    "emerald-800": "#065f46",
    "emerald-900": "#064e3b",
    
    "blue-50": "#eff6ff",
    "blue-100": "#dbeafe",
    "blue-200": "#bfdbfe",
    "blue-300": "#93c5fd",
    "blue-400": "#60a5fa",
    "blue-500": "#3b82f6",
    "blue-600": "#2563eb",
    "blue-700": "#1d4ed8",
    "blue-800": "#1e40af",
    "blue-900": "#1e3a8a",

    "indigo-50": "#eef2ff",
    "indigo-100": "#e0e7ff",
    "indigo-200": "#c7d2fe",
    "indigo-300": "#a5b4fc",
    "indigo-400": "#818cf8",
    "indigo-500": "#6366f1",
    "indigo-600": "#4f46e5",
    "indigo-700": "#4338ca",
    "indigo-800": "#3730a3",
    "indigo-900": "#312e81",
    
    "purple-50": "#faf5ff",
    "purple-100": "#f3e8ff",
    "purple-200": "#e9d5ff",
    "purple-300": "#d8b4fe",
    "purple-400": "#c084fc",
    "purple-500": "#a855f7",
    "purple-600": "#9333ea",
    "purple-700": "#7e22ce",
    "purple-800": "#6b21a8",
    "purple-900": "#581c87",

    "fuchsia-50": "#fdf4ff",
    "fuchsia-100": "#fae8ff",
    "fuchsia-200": "#f5d0fe",
    "fuchsia-300": "#f0abfc",
    "fuchsia-400": "#e879f9",
    "fuchsia-500": "#d946ef",
    "fuchsia-600": "#c026d3",
    "fuchsia-700": "#a21caf",
    "fuchsia-800": "#86198f",
    "fuchsia-900": "#701a75",
    
    "pink-50": "#fdf2f8",
    "pink-100": "#fce7f3",
    "pink-200": "#fbcfe8",
    "pink-300": "#f9a8d4",
    "pink-400": "#f472b6",
    "pink-500": "#ec4899",
    "pink-600": "#db2777",
    "pink-700": "#be185d",
    "pink-800": "#9d174d",
    "pink-900": "#831843",
    
    "brand-primary": "#0066ff",
    "brand-primary-light": "#388bfd",
    "brand-primary-dark": "#0052cc",
    "brand-action": "#ff6b00",
}

# Generate root colors
root_css = "  /* Primitive Colors */\n"
for k, v in PALETTE.items():
    root_css += f"  --color-{k}: {v};\n"

def invert_shade(shade_str):
    if shade_str == '50': return '900'
    val = int(shade_str)
    return str(1000 - val) if val <= 900 else shade_str

dark_css = "  /* Inverted Primitive Colors for Dark Mode */\n"
for k, v in PALETTE.items():
    if k in ['white', 'black', 'transparent', 'brand-primary', 'brand-primary-light', 'brand-primary-dark', 'brand-action']:
        continue
    
    parts = k.split('-')
    if len(parts) == 2:
        color_name, shade = parts
        inverted_shade = invert_shade(shade)
        if f"{color_name}-{inverted_shade}" in PALETTE:
            dark_css += f"  --color-{k}: var(--color-{color_name}-{inverted_shade});\n"
        else:
            dark_css += f"  --color-{k}: {v};\n"
            
dark_css += "  --color-white: #000000;\n"
dark_css += "  --color-black: #ffffff;\n"

css_file = 'apps/web/src/app/globals.css'
with open(css_file, 'r') as f:
    content = f.read()

# Insert primitive colors at the end of :root {
content = content.replace("}\n\n/* Tech + Business Dark Mode Overrides */", root_css + "}\n\n/* Tech + Business Dark Mode Overrides */")
# Insert dark css at the end of .theme-dark {
content = content.replace("}\n\n\nhtml {", dark_css + "}\n\n\nhtml {")

with open(css_file, 'w') as f:
    f.write(content)

print("globals.css updated.")
