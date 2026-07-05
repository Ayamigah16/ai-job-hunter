"""Extension point for future AI-generated CV/cover-letter drafting.

Deliberately unimplemented — see docs/adr/0001-stack-and-datastore.md and the
README roadmap. Do not add generation logic here until that phase is scoped.
"""

from __future__ import annotations

from typing import Protocol

from ai_job_hunter.models import JobPosting


class ContentGenerator(Protocol):
    def generate_cover_letter(self, job: JobPosting) -> str: ...

    def generate_tailored_cv(self, job: JobPosting) -> str: ...
