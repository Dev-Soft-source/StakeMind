"""Automation services (policy, queue, worker)."""

from app.services.automation.worker import process_next_job

__all__ = ["process_next_job"]
