"""Pipeline stages, in the order they run. Each is a module with a run() function."""

ORDER = ["blocks", "crawl", "traces", "tags", "holdings", "programs", "tables", "draw", "publish", "audit"]
