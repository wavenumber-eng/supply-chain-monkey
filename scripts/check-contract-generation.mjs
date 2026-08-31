import { createHash } from "node:crypto";
import { mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GENERATED_ROOT = resolve(REPO_ROOT, "contracts/scm/v1/generated");
const temporaryRoot = await mkdtemp(join(tmpdir(), "scm-contract-check-"));
const temporaryGenerated = resolve(temporaryRoot, "generated");
try {
  runNode(resolve(REPO_ROOT, "scripts/generate-contracts.mjs"), [
    "--output-root",
    temporaryGenerated,
  ]);
  const current = await snapshot(GENERATED_ROOT);
  const generated = await snapshot(temporaryGenerated);
  if (JSON.stringify(current) !== JSON.stringify(generated)) {
    console.error("Generated SCM contracts are stale, missing, or contain unexpected files.");
    process.exitCode = 1;
  } else {
    console.log("Generated SCM contracts are current.");
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}

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
