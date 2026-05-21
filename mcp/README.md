# MCP Servers

Model Context Protocol (MCP) servers expose project-specific tools to Claude
agents over a uniform interface. These are stubs in v0.1.0; the working
servers arrive in a later pipeline part.

| Server          | File                  | Tools exposed                                                                 |
|-----------------|-----------------------|-------------------------------------------------------------------------------|
| library-server  | `library-server.md`   | `verify_doi`, `lookup_by_title`, `list_library`, `propose_candidate`          |
| contract-server | `contract-server.md`  | `read_contract`, `read_rubric`, `run_audit_deterministic`, `record_amendment` |
| youtube-server  | `youtube-server.md`   | `upload`, `set_metadata`, `set_thumbnail`, `fetch_analytics`                  |
