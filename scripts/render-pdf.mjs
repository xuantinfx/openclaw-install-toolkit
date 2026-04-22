#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mdToPdf } from 'md-to-pdf';

const { values } = parseArgs({
  options: {
    template: { type: 'string' },
    out:      { type: 'string' },
    client:   { type: 'string' },
    date:     { type: 'string' },
    build:    { type: 'string' },
  },
  strict: true,
});

const required = ['template', 'out', 'client', 'date', 'build'];
const missing = required.filter((k) => !values[k]);
if (missing.length) {
  console.error(`render-pdf: missing required arg(s): ${missing.map((k) => '--' + k).join(', ')}`);
  console.error('usage: render-pdf.mjs --template <md> --out <pdf> --client <name> --date <YYYY-MM-DD> --build <id>');
  process.exit(2);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const headerPath = path.join(here, 'legal-header.md.tmpl');
const stylePath  = path.join(here, 'pdf-style.css');

let header, body;
try {
  header = await readFile(headerPath, 'utf8');
} catch (err) {
  console.error(`render-pdf: cannot read legal header ${headerPath}: ${err.message}`);
  process.exit(1);
}
try {
  body = await readFile(values.template, 'utf8');
} catch (err) {
  console.error(`render-pdf: cannot read template ${values.template}: ${err.message}`);
  process.exit(1);
}

const substitute = (s) => s
  .replaceAll('{{client_name}}',   values.client)
  .replaceAll('{{delivery_date}}', values.date)
  .replaceAll('{{build_id}}',      values.build);

const md = substitute(header) + '\n\n' + substitute(body);

const pdf = await mdToPdf(
  { content: md },
  {
    dest: values.out,
    stylesheet: [stylePath],
    stylesheet_encoding: 'utf-8',
  },
);

if (!pdf) {
  console.error('render-pdf: md-to-pdf returned no result');
  process.exit(1);
}

console.log(`wrote ${values.out}`);
