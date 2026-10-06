# Conversation retention checks

The systemd timer runs daily at 03:40–03:50 Asia/Shanghai and catches up after downtime. It previews conversations older than 90 days using the existing profile lease and symlink protections. It never passes `--apply` and never deletes conversation data. Failures leave the previous successful report intact; check service status and the report modification time together.

Install on the Docker production host after checking the repository path in the service:

```sh
install -m 0644 deploy/mirror-retention.service deploy/mirror-retention.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mirror-retention.timer
systemctl start mirror-retention.service
systemctl status mirror-retention.service mirror-retention.timer
```

The current report is `/var/lib/mirror-retention/latest.json`, readable by root only. It contains relative conversation paths, not conversation contents. The service journal records success/failure without listing user paths. Optional `/etc/default/mirror-retention` configures `CONVERSATION_RETENTION_DAYS`; deletion is deliberately unavailable through this timer. If changing `RETENTION_REPORT_DIR`, also adjust the systemd writable directory policy.

Review the report before authorizing deletion; back up conversations first, then invoke `scripts/prune_conversations.py --apply` explicitly. Disable scheduling with `systemctl disable --now mirror-retention.timer`.

# Validation and release

`validate.yml` runs tests and dependency audits for master pushes and pull requests. `build-image.yml` is manual-only (`workflow_dispatch`): it calls the same validation workflow, builds the release image, runs the complete image suite, scans every vulnerability severity, and only then publishes if registry credentials are configured. With no registry configured it validates without publishing. Neither workflow changes the running production service. Manual release requires a fresh scan; past zero-finding results are historical evidence, not a current guarantee.
