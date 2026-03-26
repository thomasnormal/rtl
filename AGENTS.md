# Repo Instructions

- This repo is the trainer-owned control plane around OpenCode agents.
- Hidden oracle validators belong in the task store and orchestration runtime, not in staged agent workspaces.
- Stage generator and verifier episodes into isolated workspaces that contain only public task inputs plus OpenCode prompts and skills.
- Give agents strong local tools, especially bash and the native hardware toolchain, but keep the oracle boundary outside the workspace.
- Prefer cheap discriminative checks first, then escalate to heavier simulation or formal runs.
- Clean up large generated files such as waveforms or large build directories.
