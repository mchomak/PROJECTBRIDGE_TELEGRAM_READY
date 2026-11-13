window.STATE =
{
  "slug": "stages-09-13",
  "dir": "2026-11-13-stages-09-13--wip",
  "title": "ProjectBridge: stages 09-13",
  "mode": "full",
  "depth": "normal",
  "polish": null,
  "tier": "T3",
  "briefFile": "2026-11-13-brief.md",
  "memoryFile": "AGENTS.md",
  "skillDir": "C:/Users/McHomak/.agents/skills/autopilot",
  "startedAt": "2026-11-13T03:00:44+03:00",
  "updatedAt": "2026-11-13T17:38:20+03:00",
  "finishedAt": null,
  "stages": [
    {
      "id": "preflight",
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": "2026-11-13T03:00:44+03:00"
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": "2026-11-13T03:00:44+03:00"
    },
    {
      "id": "briefing",
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": "2026-11-13T03:00:44+03:00"
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": "2026-11-13T03:00:44+03:00"
    },
    {
      "id": "plan",
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": "2026-11-13T03:00:44+03:00"
    },
    {
      "id": "build",
      "status": "active",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": null
    },
    {
      "id": "review",
      "status": "pending",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "finishedAt": null
    },
    {
      "id": "final",
      "status": "pending",
      "startedAt": null,
      "finishedAt": null
    }
  ],
  "requirements": {
    "total": 7,
    "done": 0,
    "inTicket": 7,
    "inSpec": 0,
    "placeholder": 0,
    "deferred": 0,
    "dropped": 0
  },
  "tickets": [
    {
      "id": "09",
      "title": "text-processing-and-rag",
      "requirements": [
        "R01"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [],
      "status": "done",
      "startedAt": "2026-11-13T03:00:44+03:00",
      "repairs": 0,
      "handoffs": 0,
      "tests": {
        "passed": 321,
        "failed": 0
      },
      "concerns": [
        "Live RAG requires Stage 10 router and configured credentials."
      ],
      "finishedAt": "2026-11-13T03:33:26+03:00",
      "commit": "27f42b8"
    },
    {
      "id": "10",
      "title": "ai-provider-routing",
      "requirements": [
        "R01"
      ],
      "blockedBy": [
        "09"
      ],
      "wave": 2,
      "zone": [],
      "status": "done",
      "startedAt": "2026-11-13T03:33:26+03:00",
      "repairs": 0,
      "handoffs": 0,
      "tests": {
        "passed": 369,
        "failed": 0
      },
      "concerns": [
        "Live provider not tested; configured credentials and account access required."
      ],
      "finishedAt": "2026-11-13T05:28:43+03:00",
      "commit": "1d1c2b2"
    },
    {
      "id": "11",
      "title": "ai-analysis-and-proposals",
      "requirements": [
        "R01"
      ],
      "blockedBy": [
        "10"
      ],
      "wave": 3,
      "zone": [],
      "status": "done",
      "startedAt": "2026-11-13T05:28:43+03:00",
      "repairs": 0,
      "handoffs": 0,
      "tests": {
        "passed": 399,
        "failed": 0
      },
      "concerns": [
        "No paid provider calls; production AI privacy disclosures remain a deployment gate."
      ],
      "finishedAt": "2026-11-13T15:50:28+03:00",
      "commit": "0b0b19e"
    },
    {
      "id": "12",
      "title": "specification",
      "requirements": [
        "R01"
      ],
      "blockedBy": [
        "11"
      ],
      "wave": 4,
      "zone": [],
      "status": "review",
      "startedAt": "2026-11-13T15:50:28+03:00",
      "repairs": 0,
      "handoffs": 0,
      "tests": {
        "passed": 423,
        "failed": 0
      },
      "concerns": [
        "No paid provider calls; recovery may fail after five unclaimed dispatches."
      ]
    },
    {
      "id": "13",
      "title": "mvp-integration-and-hardening",
      "requirements": [
        "R01"
      ],
      "blockedBy": [
        "12"
      ],
      "wave": 5,
      "zone": [],
      "status": "pending",
      "startedAt": null,
      "repairs": 0,
      "handoffs": 0
    }
  ],
  "tests": null,
  "debt": {
    "placeholders": [],
    "assumptions": [],
    "emptyEnv": []
  },
  "concerns": [],
  "reviewers": {
    "manifestSpec": "/root/spec_gate",
    "craft": "/root/review09"
  },
  "blind": null,
  "coverage": {
    "found": 2,
    "fixed": 2,
    "deferred": 0
  }
}
