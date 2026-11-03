"""In-memory validation-job registry for the hosted MCP server. A job tracks one `validate_idea` run:
its state (pending -> running -> done/error) and the per-stage verdicts as they land, so `get_status`
can stream progress without blocking. All mutators are no-ops for an unknown id (safe under races).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Job:
    id: str
    session_id: str
    slug: str
    state: str = "pending"
    stages: list = field(default_factory=list)
    error: str = ""
    created: float = field(default_factory=time.time)


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, session_id: str, slug: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], session_id=session_id, slug=slug)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def for_session(self, session_id: str) -> list:
        return [j for j in self._jobs.values() if j.session_id == session_id]

    def start(self, job_id: str) -> None:
        self._set_state(job_id, "running")

    def record_stage(self, job_id: str, stage: str, verdict: str, score: float) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.stages.append({"stage": stage, "verdict": verdict, "score": score})

    def finish(self, job_id: str) -> None:
        self._set_state(job_id, "done")

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.state, job.error = "error", error

    def _set_state(self, job_id: str, state: str) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.state = state
