import type { components } from '../../../shared/api/generated/schema';

export type ProjectStateAggregate = components['schemas']['ProjectStateAggregate'];
export type ProjectStage = components['schemas']['ProjectStageResponse'];
export type Requirement = components['schemas']['RequirementResponse'];
export type ProjectTask = components['schemas']['TaskResponse'];
export type OpenQuestion = components['schemas']['OpenQuestionResponse'];
export type ProjectConflict = components['schemas']['ProjectConflictResponse'];
export type EvidenceOption = components['schemas']['EvidenceOptionResponse'];

export type ProjectStateCollection =
  | 'stages'
  | 'requirements'
  | 'tasks'
  | 'open-questions'
  | 'conflicts';

export type ProjectStatePageByCollection = {
  stages: components['schemas']['ProjectStagePage'];
  requirements: components['schemas']['RequirementPage'];
  tasks: components['schemas']['TaskPage'];
  'open-questions': components['schemas']['OpenQuestionPage'];
  conflicts: components['schemas']['ProjectConflictPage'];
};

export type ProjectStateResponseByCollection = {
  stages: ProjectStage;
  requirements: Requirement;
  tasks: ProjectTask;
  'open-questions': OpenQuestion;
  conflicts: ProjectConflict;
};

export type ProjectStateCreateByCollection = {
  stages: components['schemas']['ProjectStageCreate'];
  requirements: components['schemas']['RequirementCreate'];
  tasks: components['schemas']['TaskCreate'];
  'open-questions': components['schemas']['OpenQuestionCreate'];
  conflicts: components['schemas']['ProjectConflictCreate'];
};

export type ProjectStateRecordKind =
  | 'stage'
  | 'requirement'
  | 'task'
  | 'open-question'
  | 'conflict';

export type ProjectStateCollectionByKind = {
  stage: 'stages';
  requirement: 'requirements';
  task: 'tasks';
  'open-question': 'open-questions';
  conflict: 'conflicts';
};

export type ProjectStateResponseByKind = {
  [K in ProjectStateRecordKind]: ProjectStateResponseByCollection[ProjectStateCollectionByKind[K]];
};

export type ProjectStatePatchByKind = {
  stage: components['schemas']['PatchedProjectStagePatch'];
  requirement: components['schemas']['PatchedRequirementPatch'];
  task: components['schemas']['PatchedTaskPatch'];
  'open-question': components['schemas']['PatchedOpenQuestionPatch'];
  conflict: components['schemas']['PatchedProjectConflictPatch'];
};

export const projectStateQueryKeys = {
  all: ['project-state'] as const,
  project: (projectId: string) => [...projectStateQueryKeys.all, projectId] as const,
  aggregate: (projectId: string) =>
    [...projectStateQueryKeys.project(projectId), 'aggregate'] as const,
  collection: (projectId: string, collection: ProjectStateCollection) =>
    [...projectStateQueryKeys.project(projectId), collection] as const,
  evidenceOptions: (projectId: string) =>
    [...projectStateQueryKeys.project(projectId), 'evidence-options'] as const,
};
