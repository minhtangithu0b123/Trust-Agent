import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "next/server") {
    return nextResolve("next/server.js", context);
  }
  if (specifier.startsWith("./") || specifier.startsWith("../")) {
    const parentURL = context.parentURL;
    if (parentURL && parentURL.startsWith("file:")) {
      const parentDir = path.dirname(fileURLToPath(parentURL));
      const targetPath = path.resolve(parentDir, specifier);
      if (fs.existsSync(targetPath + ".ts")) {
        return {
          shortCircuit: true,
          url: pathToFileURL(targetPath + ".ts").href,
          format: "module",
        };
      }
      if (fs.existsSync(targetPath + ".js")) {
        return {
          shortCircuit: true,
          url: pathToFileURL(targetPath + ".js").href,
          format: "module",
        };
      }
    }
  }
  return nextResolve(specifier, context);
}
