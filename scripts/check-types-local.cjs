// Optional offline check: resolves packages from an existing dependency tree.
// This does not replace npm run build in the project with its own dependencies.
const ts = require(process.argv[2] + '/typescript');
const path = require('path');
const root = path.resolve('frontend');
const config = ts.readConfigFile(path.join(root, 'tsconfig.json'), ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, root);
parsed.options.baseUrl = root;
parsed.options.paths = {
  ...parsed.options.paths,
  react: [process.argv[2] + '/@types/react/index.d.ts'],
  'react/*': [process.argv[2] + '/@types/react/*'],
  'react-dom/*': [process.argv[2] + '/@types/react-dom/*'],
  'lucide-react': [process.argv[2] + '/lucide-react/dist/lucide-react.d.ts'],
};
const program = ts.createProgram(parsed.fileNames, parsed.options);
const diagnostics = ts.getPreEmitDiagnostics(program);
for (const d of diagnostics) {
  const location = d.file && d.file.getLineAndCharacterOfPosition(d.start || 0);
  console.log(`${d.file?.fileName || ''}:${location ? location.line+1 : ''} TS${d.code} ${ts.flattenDiagnosticMessageText(d.messageText,' ')}`);
}
console.log(`${diagnostics.length} diagnostics. Missing dependency errors mean this is NOT a complete typecheck.`);
process.exitCode = diagnostics.length ? 1 : 0;
