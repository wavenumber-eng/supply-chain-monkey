import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const expectedNode = packageJson.engines.node;
const expectedNpm = packageJson.engines.npm;
const actualNode = process.version.replace(/^v/, "");
const npmUserAgent = process.env.npm_config_user_agent ?? "";
const actualNpm = npmUserAgent.match(/(?:^|\s)npm\/([^\s]+)/)?.[1] ?? "unknown";

const failures = [];
if (actualNode !== expectedNode) failures.push(`Node ${actualNode}; expected ${expectedNode}`);
if (actualNpm !== expectedNpm) failures.push(`npm ${actualNpm}; expected ${expectedNpm}`);
if (packageJson.packageManager !== `npm@${expectedNpm}`) {
  failures.push(`packageManager ${packageJson.packageManager}; expected npm@${expectedNpm}`);
}
if (failures.length) {
  console.error(`SCM contract toolchain mismatch: ${failures.join("; ")}`);
  process.exit(1);
}
console.log(`SCM contract toolchain: Node ${actualNode}, npm ${actualNpm}.`);
