import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, lstatSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.join(root, "website", "dist");
const output = path.join(root, "out");
if (!existsSync(path.join(source, "index.html"))) throw new Error("Website source is incomplete");
if (path.dirname(output) !== root || path.basename(output) !== "out") throw new Error("Unsafe output path");
function validateTree(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const filename = path.join(dir, entry.name);
    if (lstatSync(filename).isSymbolicLink()) throw new Error("Website source cannot contain symlinks");
    if (entry.isDirectory()) validateTree(filename);
    else if (!entry.isFile()) throw new Error("Unexpected website source entry");
  }
}
validateTree(source);
rmSync(output, { recursive: true, force: true });
mkdirSync(output);
cpSync(source, output, {
  recursive: true,
  filter: (filename) => !path.basename(filename).includes(".bak-") && !path.basename(filename).startsWith("."),
});
console.log("Website built: out/");
