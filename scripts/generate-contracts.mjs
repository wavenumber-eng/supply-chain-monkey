import { mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputArgument = argumentValue("--output-root");
const generatedRoot = outputArgument
  ? resolve(outputArgument)
  : resolve(repoRoot, "contracts/scm/v1/generated");
const expectedRoot = resolve(repoRoot, "contracts/scm/v1/generated");
const temporaryBase = resolve(tmpdir());
const isTemporary = relative(temporaryBase, generatedRoot).split(/[\\/]/)[0] !== "..";
if (generatedRoot !== expectedRoot && !isTemporary) {
  throw new Error(`Refusing to replace unexpected generated path ${generatedRoot}.`);
}

await rm(generatedRoot, { recursive: true, force: true });
await mkdir(generatedRoot, { recursive: true });
runNode(resolve(repoRoot, "scripts/generate-contract-vectors.mjs"), [
  generatedRoot === expectedRoot ? "--write" : "--check",
]);
runNode(resolve(repoRoot, "node_modules/@typespec/compiler/cmd/tsp.js"), [
  "compile",
  "src/tsp/scm/v1/main.tsp",
  "--config",
  "tspconfig.scm.yaml",
  "--output-dir",
  generatedRoot,
]);
runNode(resolve(repoRoot, "scripts/build-contract-catalog.mjs"), [
  "--generated-root",
  generatedRoot,
]);

function runNode(script, args = []) {
  const command = spawnSync(process.execPath, [script, ...args], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  process.stdout.write(command.stdout ?? "");
  process.stderr.write(command.stderr ?? "");
  if (command.error) throw command.error;
  if (command.status !== 0) process.exit(command.status ?? 1);
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? null : process.argv[index + 1];
}
