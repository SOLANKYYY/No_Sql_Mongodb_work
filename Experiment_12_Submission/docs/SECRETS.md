# Secret handling

SETUP generates random local passwords in .secrets/credentials.json and .secrets/root.env. TLS private material is held in the experiment12_tls-material Docker volume. Docker images, completed ZIPs and reports exclude all those secrets. Only public certificate fingerprints/subjects/expiry are reported.

Preserve .secrets and the database/TLS volumes together. Deleting only one can make the existing deployment inaccessible. No reset/delete command is included. If credentials are missing but volumes exist, stop and recover the original files or deliberately rebuild this isolated lab after preserving evidence.

The CA signs server and client certificates. Client certificates provide TLS peer verification; database identities use random SCRAM credentials and explicit roles. Never enable allowInvalidCertificates or allowInvalidHostnames to bypass an error.
