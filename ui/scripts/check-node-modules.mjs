/**
 * Exit 0 if every dependency/devDependency from package.json has node_modules/<name>/package.json.
 * Used by docker-entrypoint-dev.sh when node_modules lives on a named volume.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const pkgPath = path.join(root, "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
const deps = { ...pkg.dependencies, ...pkg.devDependencies };

for (const name of Object.keys(deps)) {
  const installed = path.join(root, "node_modules", ...name.split("/"), "package.json");
  if (!fs.existsSync(installed)) {
    console.error(`[check-node-modules] missing: ${name} (expected ${installed})`);
    process.exit(1);
  }
}
