import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const generatedRootArgument = argumentValue("--generated-root");
const GENERATED_ROOT = generatedRootArgument
  ? resolve(generatedRootArgument)
  : resolve(REPO_ROOT, "contracts/scm/v1/generated");
const SCHEMA_ROOT = resolve(GENERATED_ROOT, "schema");
const ROOTS_PATH = resolve(GENERATED_ROOT, "contract_roots.a0.json");
const OPENAPI_PATH = resolve(GENERATED_ROOT, "openapi.json");
const CATALOG_PATH = resolve(GENERATED_ROOT, "contract_catalog.a0.json");
const PYTHON_PROJECTION_PATH = resolve(GENERATED_ROOT, "projection/python-models.json");
const VECTOR_MANIFEST_PATH = resolve(REPO_ROOT, "contracts/scm/v1/vectors/manifest.a0.json");

const rootsDocument = await readJson(ROOTS_PATH);
const openapi = await readJson(OPENAPI_PATH);
const schemaFiles = (await readdir(SCHEMA_ROOT))
  .filter((name) => name.endsWith(".json"))
  .sort();

const schemaIdentities = new Map();
for (const name of schemaFiles) {
  const document = await readJson(resolve(SCHEMA_ROOT, name));
  const emittedId = typeof document.$id === "string" ? document.$id : name;
  const canonicalId = emittedId.includes(":")
    ? emittedId
    : `urn:supply-chain-monkey:schema:v1.declaration.${name.slice(0, -5)}`;
  schemaIdentities.set(name, canonicalId);
  schemaIdentities.set(emittedId, canonicalId);
}
for (const name of schemaFiles) {
  const path = resolve(SCHEMA_ROOT, name);
  const document = await readJson(path);
  document.$id = schemaIdentities.get(name);
  rewriteExternalSchemaRefs(document, schemaIdentities);
  await writeFile(path, `${JSON.stringify(document, null, 4)}\n`, "utf8");
}

const schemas = [];
const schemasById = new Map();
const schemasByName = new Map();
for (const name of schemaFiles) {
  const path = resolve(SCHEMA_ROOT, name);
  const bytes = await readFile(path);
  const document = JSON.parse(bytes.toString("utf8"));
  const record = {
    name: name.slice(0, -5),
    schema_id: typeof document.$id === "string" ? document.$id : null,
    path: artifactPath(path),
    sha256: digest(bytes),
  };
  schemas.push(record);
  schemasByName.set(record.name, document);
  if (record.schema_id) schemasById.set(record.schema_id, record);
}

const roots = rootsDocument.roots.map((root) => {
  const artifact = schemasById.get(root.schema_id);
  if (!artifact) throw new Error(`No generated schema matches ${root.schema_id}.`);
  return { ...root, artifact: artifact.path, sha256: artifact.sha256 };
});

const pythonProjection = projectionBundle(schemasByName, schemasById, roots);
await mkdir(dirname(PYTHON_PROJECTION_PATH), { recursive: true });
await writeFile(PYTHON_PROJECTION_PATH, `${JSON.stringify(pythonProjection, null, 2)}\n`, "utf8");

const catalog = {
  type: "wn.contract_catalog",
  version: "a0",
  contract: "scm.v1",
  namespace: rootsDocument.namespace,
  roots,
  endpoints: endpointRecords(openapi),
  artifacts: {
    openapi: {
      path: artifactPath(OPENAPI_PATH),
      sha256: digest(await readFile(OPENAPI_PATH)),
    },
    python_projection: {
      path: artifactPath(PYTHON_PROJECTION_PATH),
      sha256: digest(await readFile(PYTHON_PROJECTION_PATH)),
      authority: false,
      purpose: "datamodel-code-generator input with local $defs references",
    },
    vectors: {
      path: "contracts/scm/v1/vectors/manifest.a0.json",
      sha256: digest(await readFile(VECTOR_MANIFEST_PATH)),
    },
    schemas,
  },
};

await writeFile(CATALOG_PATH, `${JSON.stringify(catalog, null, 2)}\n`, "utf8");

function projectionBundle(documents, recordsById, roots) {
  const idToName = new Map([...recordsById].map(([id, record]) => [id, record.name]));
  const definitions = {};
  for (const name of [...documents.keys()].sort()) {
    const { $schema: _schema, $id: _id, ...document } = documents.get(name);
    const rewritten = rewriteRefs(document, idToName);
    if (name === "JsonValue") {
      const numberIndex = rewritten.anyOf.findIndex((value) => value.type === "number");
      if (numberIndex === -1) throw new Error("JsonValue projection requires a number branch.");
      rewritten.anyOf.splice(numberIndex, 0, { type: "integer" });
    }
    definitions[name] = { title: name, ...rewritten };
  }
  return {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: "urn:supply-chain-monkey:projection:python-models:v1",
    $comment: "Generation projection only. Runtime validation uses unmodified root schemas.",
    anyOf: roots.map((root) => ({
      $ref: `#/$defs/${root.name.split(".").at(-1)}`,
    })),
    $defs: definitions,
  };
}

function rewriteRefs(value, idToName) {
  if (Array.isArray(value)) return value.map((item) => rewriteRefs(item, idToName));
  if (!value || typeof value !== "object") return value;
  const rewritten = Object.fromEntries(Object.entries(value).map(([key, item]) => {
    if (key !== "$ref" || typeof item !== "string") {
      return [key, rewriteRefs(item, idToName)];
    }
    const [target, fragment = ""] = item.split("#", 2);
    const name = idToName.get(target) ?? basename(target, ".json");
    const suffix = fragment ? `/${fragment.replace(/^\//, "")}` : "";
    return [key, `#/$defs/${name}${suffix}`];
  }));
  if (
    rewritten.type === "object" &&
    Object.keys(rewritten.properties ?? {}).length === 0 &&
    rewritten.unevaluatedProperties?.$ref
  ) {
    rewritten.additionalProperties = rewritten.unevaluatedProperties;
    delete rewritten.unevaluatedProperties;
  }
  return rewritten;
}

function rewriteExternalSchemaRefs(value, identities) {
  if (Array.isArray(value)) {
    value.forEach((item) => rewriteExternalSchemaRefs(item, identities));
    return;
  }
  if (!value || typeof value !== "object") return;
  if (typeof value.$ref === "string" && !value.$ref.startsWith("#")) {
    const [target, fragment = ""] = value.$ref.split("#", 2);
    const identity = identities.get(target);
    if (!identity) throw new Error(`Unresolved generated schema reference ${value.$ref}.`);
    value.$ref = fragment ? `${identity}#${fragment}` : identity;
  }
  Object.values(value).forEach((item) => rewriteExternalSchemaRefs(item, identities));
}

function endpointRecords(document) {
  const records = [];
  for (const path of Object.keys(document.paths).sort()) {
    const pathItem = document.paths[path];
    for (const method of Object.keys(pathItem).sort()) {
      if (!new Set(["delete", "get", "head", "options", "patch", "post", "put"]).has(method)) continue;
      const operation = pathItem[method];
      const eventRoots = [...new Set(operation["x-scm-event-roots"] ?? [])].sort();
      records.push({
        operation_id: operation.operationId,
        method: method.toUpperCase(),
        path,
        security: operation.security ?? document.security ?? [],
        request_roots: sortedRefs(operation.requestBody ?? {}),
        responses: Object.fromEntries(Object.keys(operation.responses).sort().map((status) => [
          status,
          [...new Set([
            ...sortedRefs(operation.responses[status]),
            ...(status === "200" ? eventRoots : []),
          ])].sort(),
        ])),
        event_roots: eventRoots,
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

function artifactPath(path) {
  const suffix = relative(GENERATED_ROOT, path).replaceAll("\\", "/");
  return `contracts/scm/v1/generated/${suffix}`;
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? null : process.argv[index + 1];
}
