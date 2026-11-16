# Additional cloud reference: MongoDB Atlas M0

The assignment screenshots require Lab 13.1, monitoring, and Lab 13.2.
They reference main.tf but do not give a separate Atlas deployment lab.
This directory supplies that configuration. Cloud execution is reported separately,
never treated as completed just because main.tf exists.

Install Terraform >=1.5 and use an Atlas API key with permission to create a project
in your organization. Enter credentials locally; do not send them in screenshots.
An organization may restrict project/cluster creation. M0 region availability and
quotas are controlled by Atlas. Do not change M0 to a paid tier to bypass an error.

PowerShell, in this directory:

```powershell
terraform init
terraform fmt
terraform validate
$env:MONGODB_ATLAS_PUBLIC_KEY = Read-Host 'Atlas public API key'
$secret = Read-Host 'Atlas private API key' -AsSecureString
$env:MONGODB_ATLAS_PRIVATE_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
$env:TF_VAR_atlas_org_id = Read-Host 'Atlas organization ID'
$env:TF_VAR_allowed_ip = Read-Host 'Your public IPv4 address (no /32)'
$secret = Read-Host 'New database-user password' -AsSecureString
$env:TF_VAR_atlas_user_password = [System.Net.NetworkCredential]::new('', $secret).Password
terraform plan
```

If you intend to provision the shown resources, run `terraform apply` and inspect
the plan before answering yes. No cloud resources are created by START.ps1.
Capture `terraform validate`, the non-sensitive plan summary, and the Atlas M0
cluster screen only if you run this extra section. A plan is not deployment evidence.
Use Atlas Connect for the connection URI, with the generated user and your allowed IP.
Never publish .tfvars, state, saved plan files, API keys, or database passwords.
The Docker build excludes these files. Keep .terraform.lock.hcl locally after init
to record the chosen provider version.

Changes from the supplied main.tf: current v2 advanced_cluster syntax, TENANT/AWS
M0 placement, no unsupported serverless flag, no fixed M0 database version or disk
autoscaling, project_ip_access_list resource, a specific allowed IP, scoped database
role, and no malformed credential-bearing URI output.

References:
- https://registry.terraform.io/providers/mongodb/mongodbatlas/latest/docs/resources/advanced_cluster
- https://registry.terraform.io/providers/mongodb/mongodbatlas/latest/docs/resources/project_ip_access_list
- https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/
