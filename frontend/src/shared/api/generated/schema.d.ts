export interface paths {
    "/api/schema/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * @description OpenApi3 schema for this API. Format can be selected via content negotiation.
         *
         *     - YAML: application/vnd.oai.openapi
         *     - JSON: application/vnd.oai.openapi+json
         */
        get: operations["schema_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/csrf/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_auth_csrf_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/email-verification/confirm/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_email_verification_confirm_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/email-verification/resend/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_email_verification_resend_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_login_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_logout_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_auth_me_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_register_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conflicts/{record_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["project_state_conflict_update"];
        trace?: never;
    };
    "/api/v1/health/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Check backend readiness */
        get: operations["health_check"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/invitations/accept/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["invitation_accept"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/invitations/preview/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["invitation_preview"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/open-questions/{record_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["project_state_open_question_update"];
        trace?: never;
    };
    "/api/v1/projects/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["projects_list"];
        put?: never;
        post: operations["projects_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["projects_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["projects_update_metadata"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/archive/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["projects_archive"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/complete/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["projects_complete"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/conflicts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_conflicts_list"];
        put?: never;
        post: operations["project_state_conflicts_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/evidence-options/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_evidence_options_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/invitations/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_invitations_list"];
        put?: never;
        post: operations["project_invitations_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/invitations/{invitation_id}/revoke/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["project_invitations_revoke"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/members/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["projects_members_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/open-questions/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_open_questions_list"];
        put?: never;
        post: operations["project_state_open_questions_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/passport/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["projects_passport_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["projects_passport_update"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/questionnaire/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["questionnaire_project_read"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/questionnaire/conflicts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["questionnaire_project_conflicts_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/questionnaire/submissions/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["questionnaire_submission_start"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/reopen/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["projects_reopen"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/requirements/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_requirements_list"];
        put?: never;
        post: operations["project_state_requirements_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/restore/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["projects_restore"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/stages/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_stages_list"];
        put?: never;
        post: operations["project_state_stages_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/state/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_aggregate_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/tasks/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["project_state_tasks_list"];
        put?: never;
        post: operations["project_state_tasks_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questionnaire/conflicts/{conflict_id}/resolve/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["questionnaire_conflict_resolve"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questionnaire/submissions/{submission_id}/answers/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["questionnaire_answers_save"];
        trace?: never;
    };
    "/api/v1/questionnaire/submissions/{submission_id}/refresh-passport-version/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["questionnaire_submission_refresh_passport_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questionnaire/submissions/{submission_id}/request-correction/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["questionnaire_submission_request_correction"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questionnaire/submissions/{submission_id}/submit/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["questionnaire_submission_submit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/requirements/{record_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["project_state_requirement_update"];
        trace?: never;
    };
    "/api/v1/stages/{record_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["project_state_stage_update"];
        trace?: never;
    };
    "/api/v1/tasks/{record_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["project_state_task_update"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        ConfirmVerificationRequest: {
            token: string;
        };
        ConfirmVerificationResponse: {
            email_verified: boolean;
            /** Format: date-time */
            email_verified_at: string;
        };
        Credentials: {
            /** Format: email */
            email: string;
            password: string;
        };
        CsrfToken: {
            csrf_token: string;
        };
        /**
         * @description * `keep_passport` - Keep passport value
         *     * `apply_answer` - Apply questionnaire answer
         * @enum {string}
         */
        DecisionEnum: "keep_passport" | "apply_answer";
        ErrorEnvelope: {
            code: string;
            detail: string;
            errors?: unknown;
            /** Format: uuid */
            request_id: string;
        };
        EvidenceOptionPage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["EvidenceOptionResponse"][];
        };
        EvidenceOptionResponse: {
            readonly source_type: string;
            /** Format: uuid */
            source_id: string;
            question_key: string;
            value: unknown;
            schema_key: string;
            schema_version: number;
            /** Format: date-time */
            submitted_at: string;
        };
        EvidenceReference: {
            source_type: components["schemas"]["EvidenceReferenceSourceTypeEnum"];
            /** Format: uuid */
            source_id: string;
        };
        /**
         * @description * `questionnaire_answer` - questionnaire_answer
         * @enum {string}
         */
        EvidenceReferenceSourceTypeEnum: "questionnaire_answer";
        EvidenceResponse: {
            /** Format: uuid */
            readonly id: string;
            readonly source_type: components["schemas"]["EvidenceSourceTypeEnum"];
            /** Format: uuid */
            readonly source_id: string;
            readonly excerpt: string;
            readonly metadata: unknown;
            /** Format: date-time */
            readonly created_at: string;
        };
        /**
         * @description * `questionnaire_answer` - Questionnaire answer
         *     * `message` - Message
         * @enum {string}
         */
        EvidenceSourceTypeEnum: "questionnaire_answer" | "message";
        HealthResponse: {
            status: components["schemas"]["HealthResponseStatusEnum"];
            dependencies: {
                [key: string]: "ok" | "unavailable";
            };
        };
        /**
         * @description * `ok` - ok
         *     * `unavailable` - unavailable
         * @enum {string}
         */
        HealthResponseStatusEnum: "ok" | "unavailable";
        InvitationAcceptanceResponse: {
            /** Format: uuid */
            invitation_id: string;
            /** Format: uuid */
            project_id: string;
            status: components["schemas"]["InvitationAcceptanceResponseStatusEnum"];
        };
        /**
         * @description * `accepted` - accepted
         * @enum {string}
         */
        InvitationAcceptanceResponseStatusEnum: "accepted";
        InvitationCreate: {
            /** Format: email */
            invited_email: string;
        };
        InvitationListResponse: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["InvitationResponse"][];
        };
        InvitationPreviewRequest: {
            token: string;
        };
        InvitationPreviewResponse: {
            project_name: string;
            email_hint: string;
            /** Format: date-time */
            expires_at: string;
            status: components["schemas"]["ProjectInvitationStatusEnum"];
        };
        InvitationResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            /** Format: email */
            readonly invited_email: string;
            readonly status: components["schemas"]["ProjectInvitationStatusEnum"];
            /** Format: date-time */
            readonly expires_at: string;
            /** Format: date-time */
            readonly accepted_at: string | null;
            /** Format: date-time */
            readonly revoked_at: string | null;
            /** Format: date-time */
            readonly created_at: string;
        };
        /** @enum {unknown} */
        NullEnum: null;
        OpenQuestionCreate: {
            question: string;
            /** @default  */
            answer: string;
        };
        OpenQuestionPage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["OpenQuestionResponse"][];
        };
        OpenQuestionResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly question: string;
            readonly answer: string;
            readonly status: components["schemas"]["OpenQuestionStatusEnum"];
            /** Format: uuid */
            readonly created_by_id: string;
            /** Format: date-time */
            readonly resolved_at: string | null;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        /**
         * @description * `open` - Open
         *     * `resolved` - Resolved
         *     * `dismissed` - Dismissed
         * @enum {string}
         */
        OpenQuestionStatusEnum: "open" | "resolved" | "dismissed";
        /**
         * @description * `prefilled` - Prefilled from passport
         *     * `customer` - Provided by customer
         * @enum {string}
         */
        OriginEnum: "prefilled" | "customer";
        PatchedOpenQuestionPatch: {
            question?: string;
            answer?: string;
            status?: components["schemas"]["OpenQuestionStatusEnum"];
        };
        PatchedProjectConflictPatch: {
            status?: components["schemas"]["ProjectConflictStatusEnum"];
            resolution?: string;
        };
        PatchedProjectMetadataUpdate: {
            name?: string;
            project_type?: components["schemas"]["ProjectTypeEnum"];
            description?: string | null;
        };
        PatchedProjectStagePatch: {
            name?: string;
            description?: string;
            position?: number;
            status?: components["schemas"]["ProjectStageStatusEnum"];
            /** Format: date */
            start_date?: string | null;
            /** Format: date */
            due_date?: string | null;
        };
        PatchedRequirementPatch: {
            title?: string;
            description?: string;
            status?: components["schemas"]["RequirementStatusEnum"];
        };
        PatchedSaveQuestionnaireAnswers: {
            answers?: {
                [key: string]: unknown;
            };
        };
        PatchedTaskPatch: {
            title?: string;
            description?: string;
            /** Format: uuid */
            stage_id?: string | null;
            /** Format: uuid */
            assignee_id?: string | null;
            /** Format: date */
            due_date?: string | null;
            status?: components["schemas"]["TaskStatusEnum"];
        };
        ProjectConflictCreate: {
            title: string;
            /** @default  */
            description: string;
            evidence_refs: components["schemas"]["EvidenceReference"][];
        };
        ProjectConflictPage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["ProjectConflictResponse"][];
        };
        ProjectConflictResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly title: string;
            readonly description: string;
            readonly status: components["schemas"]["ProjectConflictStatusEnum"];
            readonly resolution: string;
            /** Format: uuid */
            readonly resolved_by_id: string | null;
            /** Format: date-time */
            readonly resolved_at: string | null;
            readonly evidence: components["schemas"]["EvidenceResponse"][];
            /** Format: uuid */
            readonly created_by_id: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        /**
         * @description * `unresolved` - Unresolved
         *     * `resolved` - Resolved
         *     * `dismissed` - Dismissed
         * @enum {string}
         */
        ProjectConflictStatusEnum: "unresolved" | "resolved" | "dismissed";
        ProjectCreate: {
            name: string;
            project_type: components["schemas"]["ProjectTypeEnum"];
            description?: string | null;
        };
        /**
         * @description * `pending` - Pending
         *     * `accepted` - Accepted
         *     * `revoked` - Revoked
         *     * `expired` - Expired
         * @enum {string}
         */
        ProjectInvitationStatusEnum: "pending" | "accepted" | "revoked" | "expired";
        ProjectListResponse: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["ProjectResponse"][];
        };
        ProjectMemberSummary: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly user_id: string;
            readonly role: components["schemas"]["RoleEnum"];
            /** Format: date-time */
            readonly joined_at: string;
            readonly first_name: string;
            readonly last_name: string;
        };
        /**
         * @description Keep the version required in drf-spectacular's PATCH request schema.
         *
         *     drf-spectacular marks every serializer partial for PATCH operations. The
         *     passport uses optional business fields but requires the optimistic version,
         *     so the schema-only serializer ignores that automatic partial flag.
         */
        ProjectPassportPatchSchema: {
            version: number;
            goal?: string;
            target_audience?: string;
            expected_result?: string;
            functional_scope?: unknown;
            integrations?: unknown;
            constraints?: unknown;
            /** Format: date */
            deadline?: string | null;
            /** Format: decimal */
            budget_min?: string | null;
            /** Format: decimal */
            budget_max?: string | null;
            currency?: string | null;
            additional_data?: unknown;
        };
        ProjectPassportResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly goal: string;
            readonly target_audience: string;
            readonly expected_result: string;
            readonly functional_scope: unknown;
            readonly integrations: unknown;
            readonly constraints: unknown;
            /** Format: date */
            readonly deadline: string | null;
            /** Format: decimal */
            readonly budget_min: string | null;
            /** Format: decimal */
            readonly budget_max: string | null;
            readonly currency: string | null;
            readonly additional_data: unknown;
            readonly version: number;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        ProjectQuestionnaireResponse: {
            schema: components["schemas"]["QuestionnaireSchemaResponse"];
            submission: components["schemas"]["QuestionnaireSubmissionResponse"] | null;
            history: components["schemas"]["QuestionnaireSubmissionResponse"][];
        };
        ProjectResponse: {
            /** Format: uuid */
            readonly id: string;
            readonly name: string;
            readonly description: string | null;
            readonly project_type: components["schemas"]["ProjectTypeEnum"];
            readonly status: components["schemas"]["ProjectStatusEnum"];
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            /** Format: date-time */
            readonly completed_at: string | null;
            /** Format: date-time */
            readonly archived_at: string | null;
        };
        ProjectStageCreate: {
            name: string;
            /** @default  */
            description: string;
            /** @default 0 */
            position: number;
            /** Format: date */
            start_date?: string | null;
            /** Format: date */
            due_date?: string | null;
        };
        ProjectStagePage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["ProjectStageResponse"][];
        };
        ProjectStageResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly name: string;
            readonly description: string;
            readonly position: number;
            readonly status: components["schemas"]["ProjectStageStatusEnum"];
            /** Format: date */
            readonly start_date: string | null;
            /** Format: date */
            readonly due_date: string | null;
            /** Format: uuid */
            readonly created_by_id: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        /**
         * @description * `planned` - Planned
         *     * `active` - Active
         *     * `blocked` - Blocked
         *     * `completed` - Completed
         *     * `cancelled` - Cancelled
         * @enum {string}
         */
        ProjectStageStatusEnum: "planned" | "active" | "blocked" | "completed" | "cancelled";
        ProjectStateAggregate: {
            /** Format: uuid */
            project_id: string;
            counts: components["schemas"]["ProjectStateCounts"];
            collections: components["schemas"]["ProjectStateCollections"];
        };
        ProjectStateCollections: {
            stages: string;
            requirements: string;
            tasks: string;
            open_questions: string;
            conflicts: string;
            evidence_options: string;
        };
        ProjectStateCounts: {
            stages: number;
            requirements: number;
            tasks: number;
            open_questions: number;
            conflicts: number;
        };
        /**
         * @description * `draft` - Draft
         *     * `active` - Active
         *     * `completed` - Completed
         *     * `archived` - Archived
         * @enum {string}
         */
        ProjectStatusEnum: "draft" | "active" | "completed" | "archived";
        /**
         * @description * `website` - Website
         *     * `telegram_bot` - Telegram bot
         *     * `automation` - Automation
         *     * `other` - Other
         * @enum {string}
         */
        ProjectTypeEnum: "website" | "telegram_bot" | "automation" | "other";
        QuestionnaireAnswerResponse: {
            readonly question_key: string;
            readonly value: unknown;
            readonly origin: components["schemas"]["OriginEnum"];
            readonly is_confirmed: boolean;
            /** Format: date-time */
            readonly updated_at: string;
        };
        QuestionnaireConflictResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly submission_id: string;
            readonly question_key: string;
            readonly mapped_field: string;
            readonly passport_value: unknown;
            readonly answer_value: unknown;
            readonly status: components["schemas"]["QuestionnaireConflictStatusEnum"];
            readonly decision: (components["schemas"]["DecisionEnum"] | components["schemas"]["NullEnum"]) | null;
            /** Format: uuid */
            readonly reviewed_by_id: string | null;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly resolved_at: string | null;
        };
        /**
         * @description * `pending` - Pending
         *     * `resolved` - Resolved
         * @enum {string}
         */
        QuestionnaireConflictStatusEnum: "pending" | "resolved";
        QuestionnaireQuestionSchema: {
            key: string;
            label: string;
            type: components["schemas"]["TypeEnum"];
            required: boolean;
            min_length?: number;
            max_length?: number;
            min_items?: number;
            max_items?: number;
            minimum?: string;
            maximum_digits?: number;
            decimal_places?: number;
            required_if_any?: string[];
            visible_if?: unknown;
            mapping?: string | null;
            options?: unknown[];
        };
        QuestionnaireSchemaResponse: {
            schema_key: string;
            project_type: components["schemas"]["ProjectTypeEnum"];
            version: number;
            questions: components["schemas"]["QuestionnaireQuestionSchema"][];
        };
        QuestionnaireSubmissionResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly schema_key: string;
            readonly schema_version: number;
            readonly passport_version: number;
            readonly status: components["schemas"]["QuestionnaireSubmissionStatusEnum"];
            /** Format: uuid */
            readonly started_by_id: string;
            /** Format: date-time */
            readonly started_at: string;
            /** Format: uuid */
            readonly submitted_by_id: string | null;
            /** Format: date-time */
            readonly submitted_at: string | null;
            /** Format: uuid */
            readonly supersedes_id: string | null;
            readonly answers: components["schemas"]["QuestionnaireAnswerResponse"][];
        };
        /**
         * @description * `draft` - Draft
         *     * `submitted` - Submitted
         *     * `correction_requested` - Correction requested
         * @enum {string}
         */
        QuestionnaireSubmissionStatusEnum: "draft" | "submitted" | "correction_requested";
        RequirementCreate: {
            title: string;
            /** @default  */
            description: string;
        };
        RequirementPage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["RequirementResponse"][];
        };
        RequirementResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            readonly title: string;
            readonly description: string;
            readonly status: components["schemas"]["RequirementStatusEnum"];
            /** Format: uuid */
            readonly created_by_id: string;
            /** Format: uuid */
            readonly confirmed_by_id: string | null;
            /** Format: date-time */
            readonly confirmed_at: string | null;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        /**
         * @description * `draft` - Draft
         *     * `confirmed` - Confirmed
         *     * `in_progress` - In progress
         *     * `blocked` - Blocked
         *     * `completed` - Completed
         *     * `rejected` - Rejected
         * @enum {string}
         */
        RequirementStatusEnum: "draft" | "confirmed" | "in_progress" | "blocked" | "completed" | "rejected";
        ResendVerificationRequest: {
            /** Format: email */
            email?: string;
        };
        ResendVerificationResponse: {
            detail: string;
        };
        ResolveQuestionnaireConflict: {
            decision: components["schemas"]["DecisionEnum"];
            expected_passport_version: number;
        };
        /**
         * @description * `executor` - Executor
         *     * `customer` - Customer
         * @enum {string}
         */
        RoleEnum: "executor" | "customer";
        SubmitQuestionnaireSubmission: {
            /** @default false */
            confirm_prefilled: boolean;
        };
        TaskCreate: {
            title: string;
            /** @default  */
            description: string;
            /** Format: uuid */
            stage_id?: string | null;
            /** Format: uuid */
            assignee_id?: string | null;
            /** Format: date */
            due_date?: string | null;
        };
        TaskPage: {
            count: number;
            /** Format: uri */
            next: string | null;
            /** Format: uri */
            previous: string | null;
            results: components["schemas"]["TaskResponse"][];
        };
        TaskResponse: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly project_id: string;
            /** Format: uuid */
            readonly stage_id: string | null;
            readonly title: string;
            readonly description: string;
            readonly status: components["schemas"]["TaskStatusEnum"];
            /** Format: uuid */
            readonly assignee_id: string | null;
            /** Format: date */
            readonly due_date: string | null;
            /** Format: uuid */
            readonly created_by_id: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
        };
        /**
         * @description * `todo` - To do
         *     * `in_progress` - In progress
         *     * `blocked` - Blocked
         *     * `done` - Done
         *     * `cancelled` - Cancelled
         * @enum {string}
         */
        TaskStatusEnum: "todo" | "in_progress" | "blocked" | "done" | "cancelled";
        /**
         * @description * `text` - text
         *     * `textarea` - textarea
         *     * `boolean` - boolean
         *     * `select` - select
         *     * `url` - url
         *     * `date` - date
         *     * `decimal` - decimal
         *     * `currency` - currency
         *     * `string_list` - string_list
         * @enum {string}
         */
        TypeEnum: "text" | "textarea" | "boolean" | "select" | "url" | "date" | "decimal" | "currency" | "string_list";
        UserSummary: {
            /** Format: uuid */
            readonly id: string;
            /**
             * Email address
             * Format: email
             */
            readonly email: string;
            readonly first_name: string;
            readonly last_name: string;
            readonly email_verified: boolean;
            /** Format: date-time */
            readonly email_verified_at: string | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    schema_retrieve: {
        parameters: {
            query?: {
                format?: "json" | "yaml";
                lang?: "af" | "ar" | "ar-dz" | "ast" | "az" | "be" | "bg" | "bn" | "br" | "bs" | "ca" | "ckb" | "cs" | "cy" | "da" | "de" | "dsb" | "el" | "en" | "en-au" | "en-gb" | "eo" | "es" | "es-ar" | "es-co" | "es-mx" | "es-ni" | "es-ve" | "et" | "eu" | "fa" | "fi" | "fr" | "fy" | "ga" | "gd" | "gl" | "he" | "hi" | "hr" | "hsb" | "hu" | "hy" | "ia" | "id" | "ig" | "io" | "is" | "it" | "ja" | "ka" | "kab" | "kk" | "km" | "kn" | "ko" | "ky" | "lb" | "lt" | "lv" | "mk" | "ml" | "mn" | "mr" | "ms" | "my" | "nb" | "ne" | "nl" | "nn" | "os" | "pa" | "pl" | "pt" | "pt-br" | "ro" | "ru" | "sk" | "sl" | "sq" | "sr" | "sr-latn" | "sv" | "sw" | "ta" | "te" | "tg" | "th" | "tk" | "tr" | "tt" | "udm" | "ug" | "uk" | "ur" | "uz" | "vi" | "zh-hans" | "zh-hant";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.oai.openapi": {
                        [key: string]: unknown;
                    };
                    "application/yaml": {
                        [key: string]: unknown;
                    };
                    "application/vnd.oai.openapi+json": {
                        [key: string]: unknown;
                    };
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    v1_auth_csrf_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsrfToken"];
                };
            };
        };
    };
    v1_auth_email_verification_confirm_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConfirmVerificationRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConfirmVerificationResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    v1_auth_email_verification_resend_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ResendVerificationRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ResendVerificationRequest"];
                "multipart/form-data": components["schemas"]["ResendVerificationRequest"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResendVerificationResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    v1_auth_login_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Credentials"];
                "application/x-www-form-urlencoded": components["schemas"]["Credentials"];
                "multipart/form-data": components["schemas"]["Credentials"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    v1_auth_logout_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    v1_auth_me_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    v1_auth_register_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Credentials"];
                "application/x-www-form-urlencoded": components["schemas"]["Credentials"];
                "multipart/form-data": components["schemas"]["Credentials"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_conflict_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                record_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedProjectConflictPatch"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedProjectConflictPatch"];
                "multipart/form-data": components["schemas"]["PatchedProjectConflictPatch"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectConflictResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    health_check: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
            /** @description A required backend dependency is unavailable. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    invitation_accept: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InvitationPreviewRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["InvitationPreviewRequest"];
                "multipart/form-data": components["schemas"]["InvitationPreviewRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitationAcceptanceResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    invitation_preview: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InvitationPreviewRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["InvitationPreviewRequest"];
                "multipart/form-data": components["schemas"]["InvitationPreviewRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitationPreviewResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_open_question_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                record_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedOpenQuestionPatch"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedOpenQuestionPatch"];
                "multipart/form-data": components["schemas"]["PatchedOpenQuestionPatch"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpenQuestionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                status?: "archived";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectListResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["ProjectCreate"];
                "multipart/form-data": components["schemas"]["ProjectCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_update_metadata: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedProjectMetadataUpdate"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedProjectMetadataUpdate"];
                "multipart/form-data": components["schemas"]["PatchedProjectMetadataUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_archive: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_complete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_conflicts_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectConflictPage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_conflicts_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectConflictCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["ProjectConflictCreate"];
                "multipart/form-data": components["schemas"]["ProjectConflictCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectConflictResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_evidence_options_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvidenceOptionPage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_invitations_list: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitationListResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_invitations_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InvitationCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["InvitationCreate"];
                "multipart/form-data": components["schemas"]["InvitationCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitationResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_invitations_revoke: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invitation_id: string;
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["InvitationResponse"];
                "application/x-www-form-urlencoded": components["schemas"]["InvitationResponse"];
                "multipart/form-data": components["schemas"]["InvitationResponse"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitationResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_members_list: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectMemberSummary"][];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_open_questions_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpenQuestionPage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_open_questions_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpenQuestionCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["OpenQuestionCreate"];
                "multipart/form-data": components["schemas"]["OpenQuestionCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpenQuestionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_passport_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectPassportResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_passport_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectPassportPatchSchema"];
                "application/x-www-form-urlencoded": components["schemas"]["ProjectPassportPatchSchema"];
                "multipart/form-data": components["schemas"]["ProjectPassportPatchSchema"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectPassportResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_project_read: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectQuestionnaireResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_project_conflicts_list: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireConflictResponse"][];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_submission_start: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_reopen: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_requirements_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementPage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_requirements_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["RequirementCreate"];
                "multipart/form-data": components["schemas"]["RequirementCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_restore: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_stages_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectStagePage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_stages_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectStageCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["ProjectStageCreate"];
                "multipart/form-data": components["schemas"]["ProjectStageCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectStageResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_aggregate_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectStateAggregate"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_tasks_list: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskPage"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_tasks_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskCreate"];
                "application/x-www-form-urlencoded": components["schemas"]["TaskCreate"];
                "multipart/form-data": components["schemas"]["TaskCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_conflict_resolve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conflict_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResolveQuestionnaireConflict"];
                "application/x-www-form-urlencoded": components["schemas"]["ResolveQuestionnaireConflict"];
                "multipart/form-data": components["schemas"]["ResolveQuestionnaireConflict"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireConflictResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_answers_save: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedSaveQuestionnaireAnswers"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedSaveQuestionnaireAnswers"];
                "multipart/form-data": components["schemas"]["PatchedSaveQuestionnaireAnswers"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_submission_refresh_passport_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_submission_request_correction: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    questionnaire_submission_submit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SubmitQuestionnaireSubmission"];
                "application/x-www-form-urlencoded": components["schemas"]["SubmitQuestionnaireSubmission"];
                "multipart/form-data": components["schemas"]["SubmitQuestionnaireSubmission"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionnaireSubmissionResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_requirement_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                record_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedRequirementPatch"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedRequirementPatch"];
                "multipart/form-data": components["schemas"]["PatchedRequirementPatch"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_stage_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                record_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedProjectStagePatch"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedProjectStagePatch"];
                "multipart/form-data": components["schemas"]["PatchedProjectStagePatch"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectStageResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_state_task_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                record_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedTaskPatch"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedTaskPatch"];
                "multipart/form-data": components["schemas"]["PatchedTaskPatch"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskResponse"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
}
