#!/usr/bin/env node
/**
 * Fail when a TS/TSX file references a CSS-module class that does not exist.
 *
 * TypeScript treats `styles.missingClass` as valid with Next's generated CSS
 * module types. The browser then receives `className="undefined"`, which once
 * made Havi's numbered steps render as `1Bạn muốn đăng gì?` while lint and the
 * production build stayed green. This audit keeps that failure deterministic.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

const ROOT = new URL("../", import.meta.url).pathname;
const SRC = join(ROOT, "apps/web/src");

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else if (/\.tsx?$/.test(name) && !name.includes(".test.")) files.push(path);
  }
  return files;
}

const failures = [];

for (const sourcePath of walk(SRC)) {
  const source = readFileSync(sourcePath, "utf8");
  const imports = source.matchAll(
    /import\s+([A-Za-z_$][\w$]*)\s+from\s+["']([^"']+\.module\.css)["']/g,
  );

  for (const match of imports) {
    const [, binding, cssImport] = match;
    const cssPath = resolve(dirname(sourcePath), cssImport);
    const css = readFileSync(cssPath, "utf8");
    const declared = new Set([...css.matchAll(/\.([A-Za-z_][\w-]*)/g)].map((row) => row[1]));
    const reference = new RegExp(`\\b${binding}\\.([A-Za-z_$][\\w$]*)`, "g");

    for (const used of source.matchAll(reference)) {
      if (!declared.has(used[1])) {
        const line = source.slice(0, used.index).split("\n").length;
        failures.push(`${relative(ROOT, sourcePath)}:${line} -> ${cssImport} thiếu .${used[1]}`);
      }
    }
  }
}

if (failures.length > 0) {
  console.error(`CSS module audit: ${failures.length} class chưa được định nghĩa`);
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}

console.log("CSS module audit: không có class bị thiếu");
