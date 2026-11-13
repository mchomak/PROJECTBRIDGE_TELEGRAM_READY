import type { components } from '../../../shared/api/generated/schema';

export type Specification = components['schemas']['Specification'];
export type SpecificationGeneration = components['schemas']['SpecificationGenerationRequest'];

export const specificationQueryKeys = {
  detail: (projectId: string) => ['specification', projectId] as const,
};
