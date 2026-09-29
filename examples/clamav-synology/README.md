# ClamAV on a Synology NAS: example files

Companion files for the blog post "The Scan That Wouldn't Die: ClamAV on a NAS That Only Stays Awake 16 Hours a Day".

- `clamav-scan-task.sh`: the DSM Task Scheduler script (a `docker exec clamav-scanner clamscan ...` command plus a small wrapper that keeps the exit code and prints a summary).
- `clamav-scanner-compose.yml`: a Compose definition equivalent to the container I run. I actually created the container through Portainer's Containers > Add container form, so this file is a reconstruction from the running container, not the file I deployed.

Things to know before you copy anything:

- Both whole volumes are mounted read-only (`/volume1` at `/scandir`, `/volume2` at `/scandir2`). What gets scanned is decided by the paths and `--exclude-dir` list in the script, not by the container.
- The exclude list is specific to my NAS. Generate yours from a real `find` listing of your own folders.
- There is no volume at `/var/lib/clamav`, so virus signatures live in the container's writable layer. Recreating the container or re-pulling `latest` means a full signature re-download.
- The container clock is UTC (`TZ=Etc/UTC`), so timestamps in the scan output are UTC.
- I use the `latest` image tag. That updates signatures on its own but does not update the ClamAV software.
- Replace `<username>` in the script with your own home folder name. Nothing here contains credentials.
