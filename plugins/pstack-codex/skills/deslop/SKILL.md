---
name: deslop
description: Remove AI-generated code clutter from a scoped diff before commit. Use for $deslop, deslop this diff, or cleaning narrating comments, speculative guards, dead compatibility paths, and unrelated edits.
---

# Deslop

Clean a scoped diff without changing its intended behavior.

1. Resolve the scope from the caller. Otherwise use the working-tree and staged
   diff against the current branch base.
2. Read the surrounding code before judging the patch. Do not optimize from an
   isolated hunk.
3. Remove narrating comments, banners, commented-out code, placeholder prose,
   redundant wrappers, speculative guards, dead compatibility branches, and
   unrelated cleanup that the requested change did not need.
4. Preserve legal headers, public API contracts, externally forced protocol
   constraints, and suppressions proven necessary for correctness. Prefer
   encoding an internal constraint in a type, test, lint, or runtime invariant.
5. Keep the smallest coherent implementation. Do not replace one kind of clutter
   with a new abstraction.
6. Run the narrow formatter, lint, typecheck, and tests appropriate to the
   touched files. Inspect the final diff and report removals plus anything kept
   for a concrete reason.

Do not widen scope, rewrite unrelated code, or claim behavior preservation
without running the available proof.
