import { createHash } from "node:crypto";
import { readdir, readFile, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GENERATED_ROOT = resolve(REPO_ROOT, "contracts/scm/v1/generated");
const SCHEMA_ROOT = resolve(GENERATED_ROOT, "schema");
const ROOTS_PATH = resolve(GENERATED_ROOT, "wn_contract_roots.a0.json");
const OPENAPI_PATH = resolve(GENERATED_ROOT, "openapi.json");
const CATALOG_PATH = resolve(GENERATED_ROOT, "wn_contract_catalog.a0.json");

const rootsDocument = await readJson(ROOTS_PATH);
const openapi = await readJson(OPENAPI_PATH);
const schemaFiles = (await readdir(SCHEMA_ROOT))
  .filter((name) => name.endsWith(".json"))
  .sort();

const schemas = [];
const schemasById = new Map();
for (const name of schemaFiles) {
  const path = resolve(SCHEMA_ROOT, name);
  const bytes = await readFile(path);
  const document = JSON.parse(bytes.toString("utf8"));
  const record = {
    name: name.slice(0, -5),
    schema_id: typeof document.$id === "string" ? document.$id : null,
    path: repoPath(path),
    sha256: digest(bytes),
  };
  schemas.push(record);
  if (record.schema_id) schemasById.set(record.schema_id, record);
}

const roots = rootsDocument.roots.map((root) => {
  const artifact = schemasById.get(root.schema_id);
  if (!artifact) throw new Error(`No generated schema matches ${root.schema_id}.`);
  return { ...root, artifact: artifact.path, sha256: artifact.sha256 };
});

const catalog = {
  type: "wn.contract_catalog",
  version: "a0",
  contract: "scm.v1",
  namespace: rootsDocument.namespace,
  roots,
  endpoints: endpointRecords(openapi),
  artifacts: {
    openapi: {
      path: repoPath(OPENAPI_PATH),
      sha256: digest(await readFile(OPENAPI_PATH)),
    },
    schemas,
  },
};

await writeFile(CATALOG_PATH, `${JSON.stringify(catalog, null, 2)}\n`, "utf8");

function endpointRecords(document) {
  const records = [];
  for (const path of Object.keys(document.paths).sort()) {
    const pathItem = document.paths[path];
    for (const method of Object.keys(pathItem).sort()) {
      if (!new Set(["delete", "get", "head", "options", "patch", "post", "put"]).has(method)) continue;
      const operation = pathItem[method];
      records.push({
        operation_id: operation.operationId,
        method: method.toUpperCase(),
        path,
        security: operation.security ?? document.security ?? [],
        request_roots: sortedRefs(operation.requestBody ?? {}),
        responses: Object.fromEntries(Object.keys(operation.responses).sort().map((status) => [
          status,
          sortedRefs(operation.responses[status]),
        ])),
      });
    }
  }
  return records;
}

function sortedRefs(value) {
  const refs = new Set();
  collectRefs(value, refs);
  return [...refs].sort();
}

function collectRefs(value, refs) {
  if (Array.isArray(value)) {
    for (const item of value) collectRefs(item, refs);
  } else if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (key === "$ref" && typeof item === "string") refs.add(item.split("/").at(-1));
      else collectRefs(item, refs);
    }
  }
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function repoPath(path) {
  return relative(REPO_ROOT, path).replaceAll("\\", "/");
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}
