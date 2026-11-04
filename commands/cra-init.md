---
description: Scaffold the research blackboard into a project directory
argument-hint: <project-dir>
---

If the `cra` CLI is installed, run `cra init $ARGUMENTS` (it does exactly the following). Otherwise copy every file in templates/blackboard/ of the crypto-research-agents repo into $ARGUMENTS (create it if needed; never overwrite existing files), create subdirs results/ paper/ baselines/ lean/ falsify/, copy templates/paper/ into paper/ if paper/ is empty, then ask the user for the one-sentence thesis, target venue and deadline and fill STATE.md (phase P0).
