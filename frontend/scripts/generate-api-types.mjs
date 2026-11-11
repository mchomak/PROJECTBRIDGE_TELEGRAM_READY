import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import openapiTS, { astToString } from 'openapi-typescript';

const schemaUrl = process.env.API_SCHEMA_URL ?? 'http://localhost:8000/api/schema/';
const outputPath = fileURLToPath(
  new URL('../src/shared/api/generated/schema.d.ts', import.meta.url),
);

try {
  console.log(`Fetching OpenAPI schema from ${schemaUrl}`);
  const response = await fetch(schemaUrl, {
    headers: { Accept: 'application/vnd.oai.openapi+json, application/json' },
  });

  if (!response.ok) {
    throw new Error(`Schema request failed with ${response.status} ${response.statusText}`);
  }

  const schema = await response.json();
  const declaration = await openapiTS(schema);

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, astToString(declaration), 'utf8');
  console.log(`Generated API types at ${outputPath}`);
} catch (error) {
  const detail = error instanceof Error ? error.message : String(error);
  console.error(`Failed to generate API types from ${schemaUrl}: ${detail}`);
  process.exitCode = 1;
}
