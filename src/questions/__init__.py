"""Phase-2 question bank: the canonical schema, validation, scoring, and store.

The question bank is the project's actual deliverable (a static player just renders
it). Everything here is deliberately explicit and auditable — multi-select answers,
point-based scoring, per-question provenance back to a KB unit, and a review gate so
no unreviewed (e.g. LLM-drafted) question can reach a learner.
"""

from .schema import (  # noqa: F401
    Choice, Provenance, Question, ExamConfig,
    KINDS, POLARITIES, REVIEW_STATUSES, DISTRACTOR_STRATEGIES,
    make_question_id, validate, score, grade_exam,
    connect, write_questions, set_meta, export_json, load_questions,
)
