// @ts-check

import { emitFile, getNamespaceFullName } from "@typespec/compiler";
import { getId, getJsonSchemaTypes } from "@typespec/json-schema";

const OWNED_NAMESPACE = "Wavenumber.SupplyChainMonkey.V1";

/**
 * Emit root identities from the TypeSpec program. A deterministic post-process
 * joins these roots to schema/OpenAPI paths and digests.
 *
 * @param {import("@typespec/compiler").EmitContext} context
 */
export async function $onEmit(context) {
  const roots = getJsonSchemaTypes(context.program)
    .filter((type) => type.kind !== "Namespace" && isOwned(type))
    .map((type) => ({
      name: qualifiedName(type),
      schema_id: requiredId(context.program, type),
    }))
    .sort((left, right) => left.name.localeCompare(right.name));

  if (roots.length === 0) {
    throw new Error("SCM catalog emitter found no owned @jsonSchema roots.");
  }

  await emitFile(context.program, {
    path: `${context.emitterOutputDir}/wn_contract_roots.a0.json`,
    content: `${JSON.stringify({
      type: "wn.contract_roots",
      version: "a0",
      namespace: OWNED_NAMESPACE,
      roots,
    }, null, 2)}\n`,
  });
}

/** @param {import("@typespec/compiler").Type} type */
function isOwned(type) {
  const namespace = "namespace" in type && type.namespace
    ? getNamespaceFullName(type.namespace)
    : "";
  return namespace === OWNED_NAMESPACE || namespace.startsWith(`${OWNED_NAMESPACE}.`);
}

/** @param {import("@typespec/compiler").Type} type */
function qualifiedName(type) {
  if (!("name" in type) || !type.name) {
    throw new Error(`TypeSpec ${type.kind} lacks a stable declaration name.`);
  }
  const namespace = "namespace" in type && type.namespace
    ? getNamespaceFullName(type.namespace)
    : "";
  return namespace ? `${namespace}.${String(type.name)}` : String(type.name);
}

/**
 * @param {import("@typespec/compiler").Program} program
 * @param {import("@typespec/compiler").Type} type
 */
function requiredId(program, type) {
  const id = getId(program, type);
  if (!id) {
    throw new Error(`Root ${qualifiedName(type)} is missing an explicit @id.`);
  }
  return id;
}
