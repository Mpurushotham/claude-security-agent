# Conftest/OPA policy: baseline OWASP-aligned IaC guardrails for Terraform plans.
#
# Run against a Terraform plan JSON:
#   terraform show -json plan.tfplan > plan.json
#   conftest test --policy policies/opa plan.json
#
# Intentionally small and high-signal; extend per cloud. Adapted from the rego patterns
# in devsecops-gcp/compliance/opa-policies.
package main

import rego.v1

# A05 Security Misconfiguration / CWE-732: world-open ingress.
deny contains msg if {
	some res in input.resource_changes
	res.type in {"aws_security_group_rule", "aws_security_group"}
	some block in array_or_self(res.change.after.ingress)
	some cidr in block.cidr_blocks
	cidr == "0.0.0.0/0"
	msg := sprintf("%s opens ingress to 0.0.0.0/0 — restrict the CIDR (CWE-732)", [res.address])
}

# A02 Cryptographic Failures / CWE-311: storage without encryption at rest.
deny contains msg if {
	some res in input.resource_changes
	res.type == "aws_s3_bucket"
	not res.change.after.server_side_encryption_configuration
	msg := sprintf("%s has no server-side encryption configured (CWE-311)", [res.address])
}

# A09 Logging Failures / CWE-778: storage without access logging.
warn contains msg if {
	some res in input.resource_changes
	res.type == "aws_s3_bucket"
	not res.change.after.logging
	msg := sprintf("%s has no access logging configured (CWE-778)", [res.address])
}

# Helper: a value may be a single block or a list of blocks.
array_or_self(x) := x if is_array(x)
array_or_self(x) := [x] if not is_array(x)
