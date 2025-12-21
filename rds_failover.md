# RDS Failover (Multi-AZ)

This environment uses an RDS PostgreSQL instance configured with Multi-AZ for automatic failover. The primary endpoint stays the same; AWS promotes the standby in another AZ.

For login steps, see `rds_login.md`.

## What to Expect
- Short disconnect window (seconds to a few minutes)
- Same endpoint, new primary AZ
- Clients must retry connections after failover

## Verify Multi-AZ
```bash
aws rds describe-db-instances \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1 \
  --query 'DBInstances[0].[MultiAZ,DBInstanceStatus,AvailabilityZone,SecondaryAvailabilityZone]' \
  --output table
```

## Trigger a Failover (CLI)
```bash
aws rds reboot-db-instance \
  --db-instance-identifier co-intelligence-db \
  --force-failover \
  --region us-east-1
```

## Trigger a Failover (Console)
1) RDS > Databases > co-intelligence-db
2) Actions > Reboot
3) Check "Reboot with failover" and confirm

## Verify Failover
```bash
aws rds describe-db-instances \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1 \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

```bash
aws rds describe-events \
  --source-identifier co-intelligence-db \
  --source-type db-instance \
  --duration 60 \
  --region us-east-1
```

## Optional: App Check
After failover, verify the backend reconnects. A simple approach is to run a quick query from the cluster (use a temporary psql pod) or exercise an API endpoint that touches the database.
