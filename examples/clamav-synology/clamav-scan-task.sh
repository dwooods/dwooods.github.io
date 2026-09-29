# DSM Task Scheduler > Create > Scheduled Task > User-defined script
# Run as root. Mondays and Fridays at 11:00 (NAS is up 07:00 to 23:00).
# Task Settings: "Send run details by email" ticked, "only when the script
# terminates abnormally" UNticked, so a completion email is sent every run.
#
# Same command as the one-line version in Task Scheduler, split across lines
# here for readability. Replace <username> with a real home folder name.
# The exclude list is specific to my NAS: generate yours from a real
# `find /scandir -maxdepth 1 -type d -iname '@*'` listing, not from mine.

docker exec clamav-scanner clamscan \
  --infected --recursive \
  --max-filesize=2000M --max-scansize=4000M \
  --exclude-dir=^/scandir/@database \
  --exclude-dir=^/scandir/@S2S \
  --exclude-dir=^/scandir/@eaDir \
  --exclude-dir=^/scandir/@SynologyApplicationService \
  --exclude-dir=^/scandir/@synologydrive \
  --exclude-dir=^/scandir/@SynoDrive \
  --exclude-dir=^/scandir/@download \
  --exclude-dir=^/scandir/@cloudsync \
  --exclude-dir=^/scandir/@quarantine \
  --exclude-dir=^/scandir/@AntiVirus \
  --exclude-dir=^/scandir/@sharesnap \
  --exclude-dir=^/scandir/@synocalendar \
  --exclude-dir=^/scandir/@ssbackup \
  --exclude-dir=^/scandir/@SynoFinder-log \
  --exclude-dir=^/scandir/@SynologyDriveShareSync \
  --exclude-dir=^/scandir/@SynoFinder-etc-volume \
  --exclude-dir=^/scandir/@userpreference \
  --exclude-dir=^/scandir/@tmp.del \
  --exclude-dir=^/scandir/@squid \
  --exclude-dir=^/scandir/@synoconfd \
  --exclude-dir=^/scandir/@autoupdate \
  --exclude-dir=^/scandir/@docker \
  --exclude-dir=^/scandir/@tmp \
  --exclude-dir=^/scandir2/@eaDir \
  --exclude-dir=^/scandir2/@C2Share \
  --exclude-dir=^/scandir2/@tmp \
  --exclude-dir=^/scandir/photo \
  --exclude-dir=^/scandir/music \
  --exclude-dir=^/scandir/Plex \
  --exclude-dir=^/scandir/ActiveBackupforBusiness \
  --exclude-dir=^/scandir/backup \
  --exclude-dir=^/scandir/video \
  --exclude-dir=^/scandir2/video2 \
  --exclude-dir=^/scandir2/SystemBackupP2 \
  --exclude-dir=^/scandir/homes/<username>/Photos \
  --exclude-dir=^/scandir/homes/<username>/Drive/Moments \
  /scandir /scandir2 > /volume1/docker/clamav_scan_results.txt 2>&1

# rc=$? must be the very next command after the scan. Keep the scan's exit
# code, print the summary (DSM includes script output in its email), then
# exit with the same code so DSM still sees a failure when clamscan
# reports an infection (exit 1) or an error (exit 2).
rc=$?
grep -E 'FOUND$|Scanned files|Infected files|Time:|End Date' \
  /volume1/docker/clamav_scan_results.txt | head -n 40
exit $rc
