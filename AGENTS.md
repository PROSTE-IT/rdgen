# PROSTE IT RustDesk project

Before changing this project, read `docs/PROSTE_IT_RUSTDESK.md` in full.

This workspace contains three independent Git repositories. Never commit the
contents of `rustdesk/` or `rdbk/` to the `rdgen` repository. Work and commit in
the repository that owns the changed files, run its tests, and keep the active
feature branches documented in the project file.

Do not add credentials, API tokens, customer data, production `.env` files, or
the address-book spreadsheet to Git.
