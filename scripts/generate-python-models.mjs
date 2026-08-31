import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cp, mkdir, mkdtemp, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CONTRACT_ROOT = resolve(REPO_ROOT, "contracts/scm/v1/generated");
const PROJECTION_PATH = resolve(CONTRACT_ROOT, "projection/python-models.json");
const TARGET_ROOT = resolve(REPO_ROOT, "src/py/scm/generated/v1");
const checkOnly = process.argv.includes("--check");
const temporaryRoot = await mkdtemp(join(tmpdir(), "scm-python-models-"));

try {
  runGenerator(resolve(temporaryRoot, "models.py"));
  await writeFile(
    resolve(temporaryRoot, "__init__.py"),
    '"""Generated SCM v1 structural models. Do not edit."""\n\nfrom .models import *  # noqa: F403\n',
    "utf8",
  );
  await mkdir(resolve(temporaryRoot, "resources"), { recursive: true });
  await writeFile(
    resolve(temporaryRoot, "resources/__init__.py"),
    '"""Packaged SCM v1 runtime schema and catalog resources."""\n',
    "utf8",
  );
  await cp(resolve(CONTRACT_ROOT, "schema"), resolve(temporaryRoot, "resources/schema"), {
    recursive: true,
  });
  await cp(
    resolve(CONTRACT_ROOT, "contract_catalog.a0.json"),
    resolve(temporaryRoot, "resources/contract_catalog.a0.json"),
  );
  await cp(
    resolve(CONTRACT_ROOT, "contract_roots.a0.json"),
    resolve(temporaryRoot, "resources/contract_roots.a0.json"),
  );

  const generated = await snapshot(temporaryRoot);
  const current = await snapshot(TARGET_ROOT, true);
  if (JSON.stringify(generated) === JSON.stringify(current)) {
    console.log("Generated Python SCM models are current.");
  } else if (checkOnly) {
    console.error("Generated Python SCM models are stale or missing.");
    process.exitCode = 1;
  } else {
    assertGeneratedTarget(TARGET_ROOT);
    await rm(TARGET_ROOT, { recursive: true, force: true });
    await mkdir(dirname(TARGET_ROOT), { recursive: true });
    await rename(temporaryRoot, TARGET_ROOT);
    console.log(`Generated Python SCM models at ${repoPath(TARGET_ROOT)}.`);
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}

function runGenerator(output) {
  const uv = process.platform === "win32" ? "uv.exe" : "uv";
  const command = spawnSync(uv, [
    "run",
    "datamodel-codegen",
    "--input", PROJECTION_PATH,
    "--input-file-type", "jsonschema",
    "--output", output,
    "--output-model-type", "pydantic_v2.BaseModel",
    "--target-python-version", "3.13",
    "--extra-fields", "forbid",
    "--formatters", "builtin",
    "--use-double-quotes",
    "--use-annotated",
    "--field-constraints",
    "--use-union-operator",
    "--use-standard-collections",
    "--disable-timestamp",
  ], { cwd: REPO_ROOT, encoding: "utf8" });
  process.stdout.write(command.stdout ?? "");
  process.stderr.write(command.stderr ?? "");
  if (command.error) throw command.error;
  if (command.status !== 0) process.exit(command.status ?? 1);
}

async function snapshot(root, missingAllowed = false) {
  try {
    const paths = await walk(root);
    const records = [];
    for (const path of paths) {
      const bytes = await readFile(path);
      records.push([relative(root, path).replaceAll("\\", "/"), digest(bytes)]);
    }
    return records;
  } catch (error) {
    if (missingAllowed && error?.code === "ENOENT") return [];
    throw error;
  }
}

async function walk(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const paths = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (entry.name === "__pycache__" || entry.name.endsWith(".pyc")) continue;
    const path = resolve(root, entry.name);
    if (entry.isDirectory()) paths.push(...await walk(path));
    else if (entry.isFile()) paths.push(path);
  }
  return paths;
}

function assertGeneratedTarget(path) {
  const expected = resolve(REPO_ROOT, "src/py/scm/generated/v1");
  if (resolve(path) !== expected) throw new Error(`Refusing to replace unexpected path ${path}.`);
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function repoPath(path) {
  return relative(REPO_ROOT, path).replaceAll("\\", "/");
}
