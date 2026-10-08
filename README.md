# ChatGPT Public Storage 📁🌍

Persistent storage for **publicly shareable** project files created or managed with ChatGPT. **Everything committed here is visible to the public.**

## What belongs here
- Public project sources, documentation, images, audio, archives, and other assets.
- Work the user has approved for public access, or material that is clearly safe for anyone to see.

**Do not upload** confidential drafts, private conversations, credentials, access tokens, personal information, or other sensitive material. Review files before publishing. Deleting a file later does not necessarily remove it from Git history.

## Organization
Give each project its own **top-level folder**; keep all related assets, documentation, and archives under it. Only add a root-level file for repository-wide administration or something unrelated to any project.

Example layout (illustrative, not pre-created):

```text
project-name/
  README.md          # project summary and provenance
  docs/
  assets/
  archives/
another-project/
  ...
```

Use descriptive names and create project folders only when needed. Each project's README should explain what the files are.

## Finding and saving files
1. Prefer an existing verified local copy; otherwise retrieve the relevant project folder from storage.
2. Reuse a project's existing folder rather than scattering files across the repository.
3. Public materials can also be mirrored into private companion storage when useful. **Never copy private content into this public repository** to achieve symmetry.
4. The public and private repositories do not need identical contents.

## Existing folders

| Folder | Description |
| --- | --- |
| [`storage-check/`](storage-check/) | Harmless connectivity test proving GitHub read/write access. |

Update this small index when new project folders are introduced.

## Boundaries
- This repository is **for storage, not deployment**; GitHub Pages and other deployment are not set up here. Use a separate repository for deployable projects.
- Pull requests and issues are optional.
- A `.gitignore` is only a local convenience: **it cannot prevent secrets from being uploaded manually or through an API**.
- GitHub file-size and repository limits may apply to large binary files.
