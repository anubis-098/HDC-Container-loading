const fs = require('node:fs');
const path = require('node:path');
const filename = path.join(__dirname, '..', 'nginx.conf');
const content = fs.readFileSync(filename);
if (content[0] === 0xef && content[1] === 0xbb && content[2] === 0xbf) {
  throw new Error('nginx.conf contains a UTF-8 BOM. Save this file as UTF-8 without BOM before building.');
}
if (content.includes(0)) {
  throw new Error('nginx.conf contains null bytes. Save this file as UTF-8 without BOM, not UTF-16.');
}
console.log('nginx.conf encoding check passed (UTF-8 without BOM).');
