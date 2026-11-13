export {
  getSpecification,
  saveSpecification,
  startSpecificationGeneration,
} from './api/specificationApi';
export { specificationQueryKeys } from './model/types';
export type { Specification, SpecificationGeneration } from './model/types';
export { useSpecification } from './model/queries';
