# Checkpoint contract for jobs run by GreenCloud AI

Spot instances can be reclaimed with about two minutes of warning. A job survives only if it follows this contract.

1. **Read the settings from environment variables:** `GC_CHECKPOINT_URI` (an S3 prefix for this run) and `GC_RUN_ID`.
2. **On start, resume.** Look for the newest checkpoint under `GC_CHECKPOINT_URI`. If one exists, load it and continue. If not, start from the beginning.
3. **Save regularly,** at least every 10 to 15 minutes, to S3. Never rely on the instance's local disk, because it disappears with the instance.
4. **Report progress.** Write a small `progress.json` next to each checkpoint, such as `{"progress": 0.42}` (a number from 0 to 1). The platform reads it to know how much work remains.
5. **Handle SIGTERM.** On a termination signal, write one last checkpoint and exit cleanly.
6. **Write results to S3** before exiting. Everything left on the instance is lost.
7. **Exit code 0 means success.** Any other exit code is a job error: the platform will not retry it, because retrying a bug wastes money.

Jobs that cannot checkpoint still run, but any interruption restarts them from zero. The scheduler penalizes them in cost estimates, and for tight deadlines you should choose on-demand.
