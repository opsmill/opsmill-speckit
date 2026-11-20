# opsmill-jira

Everything in `opsmill-sdd`, for repos that track their work in Jira, plus:

- the `jira-branch` preset: a feature branch needs a Jira or JPD ticket
  reference
- the `taskstoissues-jira` preset: `/speckit.taskstoissues` creates Jira
  issues under an existing Epic
- the `git` extension that ships with Spec Kit, whose `before_specify` hook
  runs the branch command that `jira-branch` replaces

Install and upgrade: see the
[opsmill-speckit README](https://github.com/opsmill/opsmill-speckit#install).
