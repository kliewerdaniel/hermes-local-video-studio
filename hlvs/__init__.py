"""hermes-local-video-studio — a reproducible local video production capability.

The design rule that governs every module here: an operation is not "done"
because a command returned 0. It is done when something measured the result.
`StepResult` carries `requested` and `verified` separately so a report can never
confuse the two.
"""

__version__ = "0.1.0"
