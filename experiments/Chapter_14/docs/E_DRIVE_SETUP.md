# Move Docker storage and project output off C:

There are TWO locations to move:

| Data | Where it lives | What to do |
|---|---|---|
| Project, source, backups, metrics logs, PDFs | Folder where you extract the kit | Extract to E:\NoSQL_Labs\NoSQL_Exercises_14_15_16 |
| Container images, MongoDB/Cassandra/Neo4j named volumes, Linux container files | Docker Desktop Linux disk image | Change Docker Desktop Disk image location |

## Do this first

1. Save any work. In Docker Desktop, stop the old Exercise 13 container group. If its Kubernetes cluster is still running, use its **Stop** control, not **Reset cluster**. Stopping preserves data and reduces memory usage.
2. Make sure E: (or your chosen drive) has enough free space for the existing Docker disk and new images/data. The kit can require several GB; leave roughly 10-15 GB headroom if possible. This is a planning allowance, not a measured image size. Exercise 16 also needs sufficient RAM for two JVM databases; about 6 GB available to Docker is a practical starting allowance.
3. Open **Docker Desktop > Settings > Resources > Advanced**.
4. Find **Disk image location**. Choose a folder on E:, for example `E:\DockerDesktopData`.
5. Apply the change using Docker Desktop's interface. Allow Docker to finish moving/restarting before running builds. Verify the displayed path is on E: afterward.
6. Check that the old Exercise 13 containers/images are still listed. Extract the new combined kit to E: and open PowerShell in the folder containing SETUP.ps1.

If your settings screen differs or has no Disk image location control, send a screenshot of **Settings > Resources**. Do not manually drag a running VHDX file, unregister Docker WSL distributions or factory-reset Docker to solve this.

Moving Docker's disk and moving the project are independent. The new kit uses relative bind mounts for `./backups`, `./logs` and `./results`; these are on E: when the project is on E:. Database volumes remain Linux volumes inside the Docker disk, avoiding direct Windows-folder storage for live database files.

Docker Desktop itself can remain installed on C:. Some small application/configuration files can still be on C:. The migration addresses the large Linux disk storage; it does not promise zero C: usage or immediate shrinking of unrelated WSL disks.

## Read-only space check

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\SPACE_CHECK.ps1
```

Do not run `docker system prune --volumes`, `docker compose down -v`, or delete previous exercise volumes just to start this kit. No supplied script performs those operations.

Official Docker documentation: https://docs.docker.com/desktop/features/wsl/
