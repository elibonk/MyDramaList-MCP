# Verification record

Verified on October 5, 2026 with Python 3.14.6 on macOS.

| Check | Result |
| --- | --- |
| Automated tests | 38 passed (2.28 seconds) |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Wheel build and ordinary pip installation | Passed |
| Real MCP subprocess over stdio | Initialization, tool discovery and status passed |
| Real HTTP subprocess with bearer authentication | Initialization, tool discovery and status passed |
| Host/Origin checks and missing/wrong bearer credentials | Rejected as expected |
| Live MCP `mdl_titles_get_genres` over stdio | Succeeded; returned 35 genres |
| Live SDK title 686 and title 13239 | HTTP 400 Bad Request |
| Live SDK title search for Signal | HTTP 400 Bad Request |
| Live SDK trending and title credits | HTTP 400 Bad Request |
| Login and authenticated account reads | Not tested: no user credentials supplied |
| Real account/content writes | Not tested: no user credentials supplied |
| Docker image/Compose execution | Not tested: Docker was unavailable |

The automated suite uses the real MyDramaList client and a mocked HTTP upstream for CRUD
payloads and error handling. Passing these tests does not prove that MyDramaList accepts
those requests today. The live genre check does prove one complete path from an MCP client,
through this server and the SDK, to the production API.

Title/search requests also failed using small diagnostic variations (no expand parameter,
a title slug, and a search JSON body). The server retains the package's published request
contract; it does not add speculative endpoint/header rewrites. The cause of the HTTP 400
responses has not been established. No authenticated check has been performed, so this
record does not claim whether credentials will change that outcome.

The test suite emits one Starlette deprecation warning about its test-only httpx adapter.
It does not affect the passing HTTP protocol tests or the production transport.

Run `mydramalist-mcp doctor` after installation and after upstream updates. It performs
genre/title/search reads, adds an account-profile check when a token is present, and exits
nonzero if any check fails. The current live report is saved in `examples/doctor-result.json`.

