# Conftest/OPA policy: forbid long-lived cloud credentials in GitHub Actions workflows.
#
# Enforces the org rule "OIDC short-lived credentials only" (mirrors the agent prompt and
# docs/oidc-setup.md). Run with:
#   conftest test --policy policies/opa .github/workflows/*.yml
#
# Maps to: OWASP A07 (Identification & Authentication Failures), CWE-798 (Hard-coded creds).
package main

import rego.v1

# AWS static keys must never appear in a workflow.
deny contains msg if {
	some job_name, job in input.jobs
	some step in job.steps
	with_uses := step.uses
	contains(with_uses, "aws-actions/configure-aws-credentials")
	step["with"]["aws-access-key-id"]
	msg := sprintf("job '%s' uses a static AWS access key — use OIDC role-to-assume instead (CWE-798)", [job_name])
}

# Azure login must use OIDC (client-id + tenant-id), never a client secret.
deny contains msg if {
	some job_name, job in input.jobs
	some step in job.steps
	contains(step.uses, "azure/login")
	step["with"]["client-secret"]
	msg := sprintf("job '%s' uses an Azure client-secret — use OIDC (client-id/tenant-id) instead (CWE-798)", [job_name])
}

# Any job that authenticates to a cloud must request id-token: write at job or workflow level.
warn contains msg if {
	some job_name, job in input.jobs
	some step in job.steps
	is_cloud_auth(step.uses)
	not has_id_token_write(job)
	not has_id_token_write(input)
	msg := sprintf("job '%s' authenticates to a cloud but does not set permissions.id-token: write (OIDC)", [job_name])
}

is_cloud_auth(uses) if contains(uses, "aws-actions/configure-aws-credentials")
is_cloud_auth(uses) if contains(uses, "azure/login")
is_cloud_auth(uses) if contains(uses, "google-github-actions/auth")

has_id_token_write(obj) if obj.permissions["id-token"] == "write"
