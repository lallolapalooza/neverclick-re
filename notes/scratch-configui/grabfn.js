// grabfn.js <src.js> <outdir> <name:marker> ...
const fs = require("fs");
const d = fs.readFileSync(process.argv[2], "utf8");
const out = process.argv[3];
for (const spec of process.argv.slice(4)) {
  const [name, marker] = spec.split("::");
  const i = d.indexOf(marker);
  if (i < 0) { console.log(name, "NOT FOUND"); continue; }
  // find start of body: first "){" or "{return" after marker
  let b = d.indexOf("){", i);
  if (b < 0 || b - i > 400) b = d.indexOf("{", i + marker.length);
  else b = b + 1;
  let depth = 0, k = b;
  while (k < d.length) {
    const c = d[k];
    if (c === "{") depth++;
    else if (c === "}") { depth--; if (depth === 0) break; }
    k++;
  }
  fs.writeFileSync(out + "/" + name + ".txt", d.slice(i, k + 1));
  console.log(name, k + 1 - i);
}
