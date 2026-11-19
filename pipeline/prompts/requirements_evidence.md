You check requirements against grounded web research. Report only requirements that the research shows
are factually wrong (`wrong`) or rest on a claim the research does not support (`unsupported_claim`).

## Intent
{{intent}}

## Audience / ICP
{{audience}}

## Requirements
{{requirements}}

## Research notes
{{research}}

## Sources you may cite (cite ONLY these URLs, with a short quote from the research notes)
{{sources}}

## Rules
- Judge the requirements AS STATED for the intent and ICP. Never invent requirements.
- Every finding needs at least one `evidence` item whose `url` is in the source list above.
- If nothing is contradicted by the research, return an empty `findings` list.
- `message` is one plain sentence. Use "" for `question` / `suggested_text` when not applicable.
