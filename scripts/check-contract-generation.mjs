import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GENERATED_ROOT = resolve(REPO_ROOT, "contracts/scm/v1/generated");
const before = await snapshot(GENERATED_ROOT);
runNode(resolve(REPO_ROOT, "node_modules/@typespec/compiler/cmd/tsp.js"), [
  "compile",
  "src/tsp/scm/v1/main.tsp",
  "--config",
  "tspconfig.scm.yaml",
]);
runNode(resolve(REPO_ROOT, "scripts/build-contract-catalog.mjs"));

const after = await snapshot(GENERATED_ROOT);
if (JSON.stringify(before) !== JSON.stringify(after)) {
  console.error("Generated SCM contracts were stale; regenerated output differs.");
  process.exit(1);
}
console.log("Generated SCM contracts are current.");

function runNode(script, args = []) {
  const command = spawnSync(process.execPath, [script, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  process.stdout.write(command.stdout ?? "");
  process.stderr.write(command.stderr ?? "");
  if (command.error) throw command.error;
  if (command.status !== 0) process.exit(command.status ?? 1);
}

async function snapshot(root) {
  const paths = await walk(root);
  const entries = [];
  for (const path of paths) {
    const bytes = await readFile(path);
    entries.push([
      relative(root, path).replaceAll("\\", "/"),
      createHash("sha256").update(bytes).digest("hex"),
    ]);
  }
  return entries;
}

async function walk(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const paths = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const path = resolve(root, entry.name);
    if (entry.isDirectory()) paths.push(...await walk(path));
    else if (entry.isFile()) paths.push(path);
  }
  return paths;
}
