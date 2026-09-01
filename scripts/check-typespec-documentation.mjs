import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { NodeHost, compile, getDoc, getSummary } from "@typespec/compiler";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const entry = resolve(repoRoot, "src/tsp/scm/v1/main.tsp");
const openapiPath = resolve(repoRoot, "contracts/scm/v1/generated/openapi.json");
const program = await compile(NodeHost, entry, { noEmit: true });
if (program.hasError()) {
  throw new Error("TypeSpec compilation failed before documentation coverage could be checked.");
}

let namespace = program.getGlobalNamespaceType();
for (const segment of ["Wavenumber", "SupplyChainMonkey", "V1"]) {
  namespace = namespace.namespaces.get(segment);
  if (!namespace) throw new Error(`Missing TypeSpec namespace segment ${segment}.`);
}

const missing = [];
for (const [kind, declarations] of [
  ["model", namespace.models],
  ["scalar", namespace.scalars],
  ["enum", namespace.enums],
  ["union", namespace.unions],
  ["interface", namespace.interfaces],
]) {
  for (const [name, declaration] of declarations) {
    requireText(getDoc(program, declaration), `${kind} ${name}`);
    const members = declaration.properties
      ?? declaration.members
      ?? declaration.variants
      ?? declaration.operations
      ?? new Map();
    for (const [memberName, member] of members) {
      requireText(getDoc(program, member), `${kind} member ${name}.${memberName}`);
      if (kind === "interface") {
        requireText(getSummary(program, member), `operation summary ${name}.${memberName}`);
        for (const [parameterName, parameter] of member.parameters.properties) {
          requireText(
            getDoc(program, parameter),
            `operation parameter ${name}.${memberName}.${parameterName}`,
          );
        }
      }
    }
  }
}

const openapi = JSON.parse(await readFile(openapiPath, "utf8"));
requireText(openapi.info?.description, "OpenAPI service description");
requireText(openapi.info?.version, "OpenAPI service version");
if (openapi.info.version === "0.0.0") missing.push("OpenAPI service version is still 0.0.0");

for (const [path, pathItem] of Object.entries(openapi.paths ?? {})) {
  for (const method of ["get", "post", "put", "patch", "delete"]) {
    const operation = pathItem[method];
    if (!operation) continue;
    requireText(operation.summary, `OpenAPI summary ${method.toUpperCase()} ${path}`);
    requireText(operation.description, `OpenAPI description ${method.toUpperCase()} ${path}`);
  }
}

for (const [name, schema] of Object.entries(openapi.components?.schemas ?? {})) {
  requireText(schema.description, `OpenAPI schema ${name}`);
  for (const [propertyName, property] of Object.entries(schema.properties ?? {})) {
    requireText(property.description, `OpenAPI property ${name}.${propertyName}`);
  }
}

const legacy = openapi.paths?.["/v1/search/stream"]?.get;
const warning = "Never place a real service token";
if (legacy?.deprecated !== true) missing.push("legacy stream is not marked deprecated in OpenAPI");
if (!legacy?.description?.includes(warning)) missing.push("legacy stream description lacks token warning");
const legacyScheme = openapi.components?.securitySchemes?.LegacyQueryTokenAuth;
if (!legacyScheme?.description?.includes(warning)) {
  missing.push("legacy query-token security scheme lacks token warning");
}

if (missing.length > 0) {
  throw new Error(`TypeSpec/OpenAPI documentation coverage failed:\n- ${missing.join("\n- ")}`);
}
console.log("TypeSpec and generated OpenAPI documentation coverage is complete.");

function requireText(value, label) {
  if (typeof value !== "string" || value.trim().length === 0) missing.push(label);
}
