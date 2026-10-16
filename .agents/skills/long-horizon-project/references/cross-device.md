# Cross-Device Procedure

Use two repositories when project code is public but assistant state is private.

## First Device

1. Finish the current phase and run verification.
2. Ensure the project repository has no unintended changes.
3. Apply the project's documented Git workflow, the user's explicit Git instructions, or the active Git-specific Skill. This Skill does not choose whether `commit` or `push` is automatic.
4. If that workflow requires it, commit and push the project code.
5. Write the exact project branch, commit, and push result to `skilluse/context/current.md`.
6. Commit and push the separate `skilluse` state repository when the applicable Git workflow calls for it.

Do not describe the handoff as synchronized while required code or state changes remain uncommitted or unpushed. If the applicable workflow intentionally leaves them local, record the handoff as local-only. Uncommitted files stay on the current device.

## Next Device

```text
git clone <project-repository> <project-directory>
cd <project-directory>
git clone <private-state-repository> skilluse
```

Install the user-level Skill on the new device, then pull both repositories before starting a new conversation. Confirm that the commit recorded in `skilluse/context/current.md` matches the project repository's current commit. If it does not match, stop and reconcile the repositories before modifying code.

The Skill is user-level and is installed separately on each device. The project state is not the chat transcript; it is the files in the private `skilluse` repository.
