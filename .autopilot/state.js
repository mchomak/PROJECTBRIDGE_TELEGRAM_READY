window.STATE =
{
  "slug": "stages-00-08-audit",
  "dir": "2026-11-13-stages-00-08-audit--wip",
  "title": "ProjectBridge: stage 00-08 audit",
  "mode": "full",
  "depth": "normal",
  "polish": null,
  "tier": "T3",
  "briefFile": "2026-11-13-brief.md",
  "memoryFile": "AGENTS.md",
  "skillDir": "C:/Users/McHomak/.agents/skills/autopilot",
  "startedAt": "2026-11-13T02:43:09+03:00",
  "updatedAt": "2026-11-13T02:46:50+03:00",
  "finishedAt": "2026-11-13T02:46:50+03:00",
  "stages": [
    {
      "id": "preflight",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:43:09+03:00",
      "note": ""
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:43:09+03:00",
      "note": ""
    },
    {
      "id": "briefing",
      "status": "skipped",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:43:09+03:00",
      "reason": "full mode self-briefing; user facts and external services are not invented",
      "note": "Full mode: self briefing"
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:43:09+03:00",
      "note": ""
    },
    {
      "id": "plan",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "note": "",
      "finishedAt": "2026-11-13T02:43:09+03:00"
    },
    {
      "id": "build",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "note": "",
      "finishedAt": "2026-11-13T02:46:50+03:00"
    },
    {
      "id": "review",
      "status": "done",
      "startedAt": "2026-11-13T02:43:09+03:00",
      "note": "",
      "finishedAt": "2026-11-13T02:46:50+03:00"
    },
    {
      "id": "final",
      "status": "failed",
      "startedAt": "2026-11-13T02:46:50+03:00",
      "finishedAt": "2026-11-13T02:46:50+03:00",
      "note": "Partial acceptance: manual browser flows not verified."
    }
  ],
  "requirements": {
    "total": 102,
    "done": 95,
    "inTicket": 0,
    "inSpec": 0,
    "placeholder": 0,
    "deferred": 7,
    "dropped": 0
  },
  "tickets": [
    {
      "id": "01",
      "title": "Stages 00-03",
      "requirements": [
        "R01",
        "R02",
        "R03"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "handoffs": 0,
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:46:50+03:00"
    },
    {
      "id": "02",
      "title": "Stages 04-06",
      "requirements": [
        "R01",
        "R02",
        "R03"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "handoffs": 0,
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:46:50+03:00"
    },
    {
      "id": "03",
      "title": "Stages 07-08",
      "requirements": [
        "R01",
        "R02",
        "R03"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "handoffs": 0,
      "startedAt": "2026-11-13T02:43:09+03:00",
      "finishedAt": "2026-11-13T02:46:50+03:00"
    },
    {
      "id": "04",
      "title": "Report and integration checks",
      "requirements": [
        "R04",
        "R05"
      ],
      "blockedBy": [
        "01",
        "02",
        "03"
      ],
      "wave": 2,
      "zone": [],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "handoffs": 0,
      "startedAt": null,
      "finishedAt": "2026-11-13T02:46:50+03:00"
    }
  ],
  "singlePass": null,
  "tests": {
    "passed": 381,
    "failed": 0
  },
  "debt": {
    "placeholders": [],
    "assumptions": [
      "Invitation tokens are sent only by email."
    ],
    "emptyEnv": []
  },
  "additions": [],
  "coverage": {
    "found": 0,
    "fixed": 0,
    "deferred": 0
  },
  "concerns": [
    "Two-user browser walkthrough, clean installation and volume persistence not verified."
  ],
  "reviewers": {
    "manifestSpec": "stage04_ms_reviewer",
    "craft": "stage04_craft_reviewer"
  },
  "blind": {
    "verdict": "partial",
    "mismatches": [
      "Two-user browser walkthrough and document lifecycle not verified manually."
    ],
    "commands": [
      "Frontend, backend health and Vite proxy health returned HTTP 200."
    ]
  },
  "triage": {
    "fixed": [
      "T08 missing WebSocket Origin validation; fixed in T11 commit 87c6b74.",
      "T09 document page reset/query invalidation; fixed in T10 commit ab19730."
    ],
    "reported": [
      "Test-coverage gaps retained in concerns.",
      "Malware scanning requires a production scanner decision."
    ],
    "dropped": [
      "Earlier OpenAPI invitation enum-name warning did not recur in final schema validation."
    ]
  }
};
