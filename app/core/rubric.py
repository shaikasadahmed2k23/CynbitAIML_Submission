"""BitElevate roadmap + rubric context shared by prompts and mock reviewer."""

TRACKS = [
    "Full Stack SaaS", "Python Backend", "AI & Vector Intelligence",
    "Frontend Ops Dashboard", "QA & Test Automation", "UI/UX",
]

WEEKS = {
    "Weeks 1-2: Setup & git hygiene": "Clean repo setup, small focused commits, conventional commit messages, README, .gitignore, no secrets.",
    "Weeks 3-4: Bug hunting & testing": "Reproduce bugs, write failing tests first, fix root causes, add regression tests.",
    "Weeks 5-6: Core architecture (auth, DB, APIs)": "Sound auth, parameterized DB access, input validation, clear API contracts, no secrets in code.",
    "Weeks 7-8: Caching & concurrency": "Correct caching/invalidation, thread/async safety, no N+1 queries, no race conditions.",
    "Weeks 9-10: Docker & CI/CD capstone": "Reproducible Dockerfile, CI running tests/lint, env-based config, deploy docs.",
}

RUBRIC = {
    "correctness": "Does the code do what it claims; edge cases; logic bugs; race conditions.",
    "code_quality": "Readability, naming, structure, duplication, N+1 or wasteful patterns, leftover debug code.",
    "security": "Injection, leaked secrets, unsafe input handling, authz gaps.",
    "testing": "Tests added/updated for changed behaviour; meaningful assertions.",
    "roadmap_alignment": "Fit with the stated track and roadmap-week learning goals.",
}
