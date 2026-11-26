import { copyFile } from "node:fs/promises";
const files = ["swagger-ui-bundle.js", "swagger-ui-bundle.js.LICENSE.txt", "swagger-ui.css", "favicon-32x32.png", "LICENSE", "NOTICE"];
for (const file of files) {
  const target = ["LICENSE","NOTICE"].includes(file) ? "swagger-" + file + ".txt" : file;
  await copyFile(new URL("./node_modules/swagger-ui-dist/" + file, import.meta.url),
                 new URL("../src/sentinel/static/" + target, import.meta.url));
}
