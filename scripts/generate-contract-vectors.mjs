import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const VECTOR_ROOT = resolve(REPO_ROOT, "contracts/scm/v1/vectors");
const MANIFEST_PATH = resolve(VECTOR_ROOT, "manifest.a0.json");
const MAX_PLUS_ONE_PATH = resolve(VECTOR_ROOT, "invalid/spn-batch-max-plus-one.json");
const checkOnly = process.argv.includes("--check");

const request = {
  supplier: "Digikey",
  spns: Array.from({ length: 1001 }, (_, index) => `SPN-${String(index + 1).padStart(4, "0")}`),
  include_raw: false,
};
const maxPlusOne = `${JSON.stringify(request)}\n`;

if (checkOnly) {
  await requireExact(MAX_PLUS_ONE_PATH, maxPlusOne, "maximum-plus-one vector");
} else {
  await mkdir(dirname(MAX_PLUS_ONE_PATH), { recursive: true });
  await writeFile(MAX_PLUS_ONE_PATH, maxPlusOne, "utf8");
}

const manifest = JSON.parse(await readFile(MANIFEST_PATH, "utf8"));
for (const entry of manifest.cases) {
  entry.sha256 = digest(await readFile(resolve(VECTOR_ROOT, entry.path)));
}
const renderedManifest = `${JSON.stringify(manifest, null, 2)}\n`;
if (checkOnly) {
  await requireExact(MANIFEST_PATH, renderedManifest, "vector manifest");
  console.log("SCM contract vectors and digests are current.");
} else {
  await writeFile(MANIFEST_PATH, renderedManifest, "utf8");
  console.log("Generated SCM maximum-plus-one vector and vector digests.");
}

async function requireExact(path, expected, label) {
  let actual;
  try {
    actual = await readFile(path, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") throw new Error(`${label} is missing.`);
    throw error;
  }
  if (actual !== expected) throw new Error(`${label} is stale.`);
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
