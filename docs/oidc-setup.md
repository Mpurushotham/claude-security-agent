# OIDC setup (AWS / Azure / GCP)

The deploy gate (`.github/workflows/reusable/oidc-deploy.yml`) authenticates with
**short-lived OIDC tokens only**. Never store long-lived cloud credentials as secrets. Each
cloud needs a one-time trust relationship with GitHub's OIDC provider
(`https://token.actions.githubusercontent.com`).

## AWS

1. Create an OIDC identity provider for `token.actions.githubusercontent.com` (audience
   `sts.amazonaws.com`).
2. Create per-environment roles `dev-cicd-deploy-role`, `prod-cicd-deploy-role` with a trust
   policy scoped to your repo and branch, e.g.:

   ```json
   "Condition": {
     "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
     "StringLike": { "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:ref:refs/heads/main" }
   }
   ```
3. Set repo secret `AWS_ACCOUNT_ID` and (optionally) repo variable `AWS_REGION`.

## Azure

1. Register an app (or use a user-assigned managed identity) and add a **federated
   credential** for GitHub Actions scoped to your repo + branch/environment.
2. Grant the identity the needed RBAC role on the target subscription/resource group.
3. Set repo secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

## GCP

1. Create a **Workload Identity Pool + provider** for GitHub, with an attribute condition
   restricting `assertion.repository` to `<org>/<repo>`.
2. Create a deploy service account and bind it to the pool
   (`roles/iam.workloadIdentityUser`); grant it least-privilege deploy roles.
3. Set repo secrets `GCP_WIF_PROVIDER` (full resource name of the provider) and
   `GCP_DEPLOY_SA` (service account email).

## Enforcing it

The `policies/opa/no_long_lived_cloud_creds.rego` conftest policy fails CI if any workflow
introduces static AWS keys or an Azure client secret, and warns when a cloud-auth job is
missing `permissions.id-token: write`. Run it in CI:

```bash
conftest test --policy policies/opa .github/workflows/*.yml
```
