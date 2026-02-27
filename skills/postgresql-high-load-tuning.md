PostgreSQL configuration and optimization for high-load applications with 5000+ concurrent users — connection pooling, memory tuning, query optimization, monitoring, and production hardening without Redis.

# PostgreSQL High-Load Tuning (5000+ Concurrent Users)

## Table of Contents

1. [Overview — Designing for High Concurrency](#overview)
2. [postgresql.conf Tuning for High Load](#postgresqlconf-tuning)
3. [Connection Pooling with PgBouncer](#connection-pooling-pgbouncer)
4. [Connection Pooling Without PgBouncer — Application-Level](#application-level-pooling)
5. [Memory Configuration Deep Dive](#memory-configuration)
6. [WAL and Checkpoint Tuning](#wal-checkpoint-tuning)
7. [Autovacuum Tuning for High Write Load](#autovacuum-tuning)
8. [Query Optimization Patterns](#query-optimization)
9. [Indexing Strategy for High Concurrency](#indexing-strategy)
10. [Partitioning for Large Tables](#partitioning)
11. [Materialized Views for Heavy Reads](#materialized-views)
12. [Lock Management and Deadlock Prevention](#lock-management)
13. [Monitoring and Diagnostics](#monitoring)
14. [Backup Strategy for Production](#backup-strategy)
15. [pg_hba.conf Security for Production](#security)
16. [Common High-Load Pitfalls](#pitfalls)

---

## Overview — Designing for High Concurrency

For 5000+ concurrent users with PostgreSQL as the primary data store (no Redis cache layer), the database must handle:
- **High read throughput**: thousands of SELECT queries/sec
- **Concurrent writes**: INSERT/UPDATE from many simultaneous connections
- **Connection management**: PostgreSQL forks a process per connection — 5000 direct connections would kill the server
- **Memory pressure**: shared_buffers, work_mem, effective_cache_size must be tuned
- **I/O optimization**: WAL writes, checkpoints, autovacuum must not block queries

### Architecture Without Redis

```
┌─────────────────────────┐
│   Vue 3 SPA (Vite)      │
│   5000+ concurrent      │
└────────────┬────────────┘
             │ HTTP / WebSocket
             ▼
┌─────────────────────────┐
│  Node.js Express + WS   │
│  PM2 Cluster (N workers)│
│  Each worker: pool of   │
│  ~20 DB connections      │
└────────────┬────────────┘
             │ Sequelize pool
             ▼
┌─────────────────────────┐
│  PgBouncer (optional)   │
│  Transaction pooling    │
│  Max 200 server conns   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  PostgreSQL 16          │
│  max_connections = 300  │
│  Tuned for high load    │
└─────────────────────────┘
```

---

## postgresql.conf Tuning for High Load

### Server with 16GB RAM, 8 CPU cores, SSD storage

```ini
# ============================================
# CONNECTION SETTINGS
# ============================================
listen_addresses = 'localhost'          # or specific IPs, NOT '*' in production
port = 5432
max_connections = 300                   # with PgBouncer: keep low (200-300)
                                        # without PgBouncer: match total pool across all PM2 workers
superuser_reserved_connections = 5      # reserve for admin/maintenance

# ============================================
# MEMORY SETTINGS (16GB RAM server)
# ============================================
shared_buffers = 4GB                    # 25% of total RAM
                                        # PostgreSQL shared memory cache
                                        # bigger = more data cached in PG process

effective_cache_size = 12GB             # 75% of total RAM
                                        # hint to query planner about OS cache
                                        # NOT actual allocation — just a hint

work_mem = 16MB                         # per-operation memory (sorts, hashes, joins)
                                        # CAREFUL: each query can use multiple work_mem allocations
                                        # 5000 users × complex query = huge memory usage
                                        # Formula: RAM / (max_connections × 2) but cap at 64MB
                                        # With 300 connections: 16GB / 600 ≈ 27MB → use 16MB to be safe

maintenance_work_mem = 512MB            # for VACUUM, CREATE INDEX, ALTER TABLE
                                        # can be high — only a few maintenance ops run at once

huge_pages = try                        # use huge pages if OS supports it (Linux)
                                        # reduces TLB misses for shared_buffers

temp_buffers = 16MB                     # per-session temp table buffer

# ============================================
# WAL (Write-Ahead Log) SETTINGS
# ============================================
wal_level = replica                     # needed for replication, pg_basebackup
                                        # use 'minimal' ONLY if no replication needed

max_wal_size = 2GB                      # max WAL size before checkpoint
min_wal_size = 512MB                    # WAL files kept even after checkpoint

wal_buffers = 64MB                      # WAL write buffer — auto-tuned if set to -1
                                        # for high write load, explicit 64MB is good

wal_compression = on                    # compress WAL — reduces I/O, uses CPU
wal_writer_delay = 200ms                # how often WAL writer flushes (default 200ms)
wal_writer_flush_after = 1MB            # flush WAL after this much data

# Synchronous commit — trade durability for speed
synchronous_commit = on                 # 'on' = safest (wait for WAL flush)
                                        # 'off' = faster writes, risk losing last ~600ms on crash
                                        # For competition platform: keep 'on' for data integrity

# ============================================
# CHECKPOINT SETTINGS
# ============================================
checkpoint_timeout = 15min              # time between automatic checkpoints
                                        # higher = fewer checkpoints = less I/O spikes
                                        # but longer recovery after crash

checkpoint_completion_target = 0.9      # spread checkpoint I/O over 90% of checkpoint interval
                                        # smoother I/O, less spiky

checkpoint_flush_after = 256kB          # limit OS dirty pages — smoother I/O

# ============================================
# QUERY PLANNER SETTINGS
# ============================================
random_page_cost = 1.1                  # SSD: set to 1.1 (default 4.0 is for HDD)
                                        # HDD: leave at 4.0
                                        # This tells planner that random I/O is almost as fast as sequential

seq_page_cost = 1.0                     # sequential page cost (baseline)

effective_io_concurrency = 200          # SSD: 200 (default 1 is for HDD)
                                        # how many concurrent I/O requests the disk can handle

cpu_tuple_cost = 0.01                   # default, usually fine
cpu_index_tuple_cost = 0.005            # default, usually fine
cpu_operator_cost = 0.0025              # default, usually fine

# ============================================
# PARALLEL QUERY SETTINGS
# ============================================
max_worker_processes = 8                # total background workers
max_parallel_workers_per_gather = 4     # max parallel workers per query
max_parallel_workers = 8                # max parallel workers total
max_parallel_maintenance_workers = 4    # parallel VACUUM, CREATE INDEX

parallel_tuple_cost = 0.01             # lower = planner prefers parallel
parallel_setup_cost = 100              # cost of launching parallel workers
min_parallel_table_scan_size = 8MB     # min table size for parallel seq scan
min_parallel_index_scan_size = 512kB   # min index size for parallel index scan

# ============================================
# AUTOVACUUM SETTINGS (critical for high-write)
# ============================================
autovacuum = on                         # NEVER turn off
autovacuum_max_workers = 4              # default 3, increase for many tables
autovacuum_naptime = 30s                # check interval (default 1min, lower for active DBs)
autovacuum_vacuum_threshold = 50        # min dead tuples before vacuum
autovacuum_vacuum_scale_factor = 0.05   # vacuum when 5% of table is dead (default 0.2 = 20%)
autovacuum_analyze_threshold = 50       # min changes before analyze
autovacuum_analyze_scale_factor = 0.025 # analyze when 2.5% changed (default 0.1)
autovacuum_vacuum_cost_delay = 2ms      # throttle vacuum I/O (default 2ms in PG16)
autovacuum_vacuum_cost_limit = 1000     # how much work per cycle (default 200, increase for SSD)

# ============================================
# LOGGING
# ============================================
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 500        # log queries slower than 500ms
log_checkpoints = on                    # log checkpoint activity
log_connections = off                   # too noisy with PgBouncer
log_disconnections = off
log_lock_waits = on                     # log lock waits > deadlock_timeout
log_temp_files = 0                      # log ALL temp file usage
log_autovacuum_min_duration = 250ms     # log slow autovacuums
log_line_prefix = '%m [%p] %q%u@%d '   # timestamp, PID, user, database

# ============================================
# LOCK MANAGEMENT
# ============================================
deadlock_timeout = 1s                   # time before checking for deadlock
max_locks_per_transaction = 256         # increase if complex transactions
lock_timeout = 10s                      # max time waiting for a lock (0 = infinite)
statement_timeout = 30s                 # kill queries running > 30s (protect from runaway)
idle_in_transaction_session_timeout = 60s  # kill idle-in-transaction after 60s

# ============================================
# STATISTICS
# ============================================
track_activities = on
track_counts = on
track_io_timing = on                    # track I/O time per query (small overhead)
track_functions = 'all'
default_statistics_target = 200         # more stats = better planner (default 100)

# ============================================
# EXTENSIONS
# ============================================
shared_preload_libraries = 'pg_stat_statements'  # MUST for query analysis
pg_stat_statements.max = 10000
pg_stat_statements.track = 'all'
```

### After changing postgresql.conf:

```bash
# Some settings need restart, others just reload
sudo systemctl restart postgresql   # for shared_buffers, max_connections, etc.
sudo systemctl reload postgresql    # for most other settings

# Check which need restart:
SELECT name, setting, pending_restart FROM pg_settings WHERE pending_restart = true;
```

---

## Connection Pooling with PgBouncer

### Why PgBouncer is Critical

PostgreSQL forks a new OS process for each connection (~5-10MB each).
- 300 connections = ~3GB RAM just for processes
- 5000 direct connections = impossible (50GB+ RAM, massive context switching)

PgBouncer multiplexes thousands of client connections onto a small pool of real PostgreSQL connections.

### Install and Configure PgBouncer

```bash
sudo apt install pgbouncer
```

```ini
# /etc/pgbouncer/pgbouncer.ini

[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool mode:
# session    = connection held for entire client session (safest, least efficient)
# transaction = connection returned after each transaction (best for web apps)
# statement  = connection returned after each statement (most aggressive, limited)
pool_mode = transaction

# Pool sizing
default_pool_size = 25          # connections per user/database pair
min_pool_size = 5               # keep at least 5 connections warm
max_client_conn = 5000          # accept up to 5000 client connections
max_db_connections = 200        # max real connections to PostgreSQL
reserve_pool_size = 5           # extra connections for emergencies
reserve_pool_timeout = 3        # seconds to wait before using reserve

# Timeouts
server_idle_timeout = 300       # close idle server connections after 5min
client_idle_timeout = 300       # close idle client connections after 5min
query_timeout = 30              # kill queries running > 30s
client_login_timeout = 60

# Logging
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
stats_period = 60               # stats log every 60s

# TCP keepalive
tcp_keepalive = 1
tcp_keepidle = 60
tcp_keepintvl = 10
tcp_keepcnt = 5

# Admin
admin_users = postgres
```

```bash
# /etc/pgbouncer/userlist.txt
"myuser" "md5hashofpassword"
# Generate hash: echo -n "passwordusername" | md5sum
# Result format: "username" "md5<hash>"
```

```bash
sudo systemctl start pgbouncer
sudo systemctl enable pgbouncer
```

### Connect Sequelize to PgBouncer

```javascript
// Connect to PgBouncer port (6432) instead of PostgreSQL port (5432)
const sequelize = new Sequelize('mydb', 'myuser', 'password', {
  host: '127.0.0.1',
  port: 6432,               // PgBouncer port
  dialect: 'postgres',
  pool: {
    max: 20,                 // per PM2 worker
    min: 5,
    acquire: 30000,
    idle: 10000,
  },
  dialectOptions: {
    // IMPORTANT for PgBouncer transaction mode:
    // Disable prepared statements (they don't work in transaction mode)
    preparedStatements: false,
    statement_timeout: 30000,    // 30s query timeout
    idle_in_transaction_session_timeout: 60000,  // 60s idle transaction timeout
  },
  logging: false,
});
```

---

## Application-Level Pooling (Without PgBouncer)

If you choose NOT to use PgBouncer, tune Sequelize pools carefully:

```javascript
// Calculate pool size:
// Total connections = PM2_workers × pool.max
// Example: 4 PM2 workers × 25 pool = 100 PostgreSQL connections
// Keep total under max_connections (300) with room for maintenance

const sequelize = new Sequelize(process.env.DATABASE_URL, {
  dialect: 'postgres',
  pool: {
    max: 25,                 // connections per PM2 worker
    min: 5,                  // keep warm connections
    acquire: 30000,          // max ms to wait for connection
    idle: 10000,             // release idle connection after 10s
    evict: 1000,             // check for idle connections every 1s
  },
  dialectOptions: {
    statement_timeout: 30000,
    idle_in_transaction_session_timeout: 60000,
    // TCP keepalive
    keepAlive: true,
    keepAliveInitialDelayMillis: 10000,
  },
  retry: {
    max: 3,                  // retry failed connections
    match: [
      /SequelizeConnectionError/,
      /SequelizeConnectionRefusedError/,
      /SequelizeHostNotFoundError/,
      /SequelizeHostNotReachableError/,
      /SequelizeInvalidConnectionError/,
      /SequelizeConnectionTimedOutError/,
      /ECONNRESET/,
      /ETIMEDOUT/,
    ],
  },
  logging: process.env.NODE_ENV === 'development' ? console.log : false,
  benchmark: true,          // log query execution time
});
```

### Pool Sizing Formula

```
PM2 workers = number of CPU cores (e.g., 4-8)
Pool per worker = 15-30 connections
Total DB connections = workers × pool_max

Example for 8-core server:
  8 workers × 20 pool = 160 connections
  PostgreSQL max_connections = 200 (leave room for admin)

If total needed > max_connections → use PgBouncer
```

---

## Memory Configuration Deep Dive

### shared_buffers Calculation

```
Rule: 25% of total RAM, max 8GB (diminishing returns above 8GB)

4GB RAM server  → shared_buffers = 1GB
8GB RAM server  → shared_buffers = 2GB
16GB RAM server → shared_buffers = 4GB
32GB RAM server → shared_buffers = 8GB
64GB+ RAM       → shared_buffers = 8GB (cap here)
```

### work_mem — The Dangerous One

```
work_mem is allocated PER OPERATION, not per query.
A single complex query with 3 sorts + 2 hash joins = 5 × work_mem

Formula: (Total RAM - shared_buffers) / (max_connections × 3)
16GB - 4GB = 12GB / (300 × 3) = 13MB → use 16MB (round up)

NEVER set work_mem > 64MB for high-concurrency servers
Monitor with: EXPLAIN (ANALYZE, BUFFERS) to see if queries spill to disk
```

### effective_cache_size

```
Not an allocation — just tells the planner how much cache is available.
Set to ~75% of total RAM (OS file cache + shared_buffers).

16GB RAM → effective_cache_size = 12GB
32GB RAM → effective_cache_size = 24GB
```

---

## WAL and Checkpoint Tuning

```sql
-- Monitor checkpoint activity
SELECT * FROM pg_stat_bgwriter;

-- Key metrics:
-- checkpoints_timed: scheduled checkpoints (good)
-- checkpoints_req: forced checkpoints (bad — means max_wal_size too small)
-- If checkpoints_req > 10% of total, increase max_wal_size

-- Monitor WAL generation rate
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0') / 1024 / 1024 AS wal_mb_total;

-- WAL generation per hour (run twice with 1 hour gap)
SELECT pg_current_wal_lsn();
-- ... 1 hour later ...
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), 'previous_lsn') / 1024 / 1024 AS wal_mb_per_hour;
```

---

## Autovacuum Tuning for High Write Load

### Per-Table Autovacuum for Hot Tables

```sql
-- Competition tables with high write rates need aggressive autovacuum
ALTER TABLE match_results SET (
  autovacuum_vacuum_scale_factor = 0.01,     -- vacuum at 1% dead (instead of 5%)
  autovacuum_vacuum_threshold = 100,
  autovacuum_analyze_scale_factor = 0.005,   -- analyze at 0.5% changed
  autovacuum_analyze_threshold = 100,
  autovacuum_vacuum_cost_delay = 0           -- no throttling for this table
);

ALTER TABLE user_scores SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01
);

-- Check autovacuum status
SELECT
  schemaname, relname,
  n_live_tup, n_dead_tup,
  ROUND(100.0 * n_dead_tup / GREATEST(n_live_tup + n_dead_tup, 1), 1) AS dead_pct,
  last_vacuum, last_autovacuum,
  last_analyze, last_autoanalyze,
  autovacuum_count, autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

---

## Query Optimization Patterns

### Keyset Pagination (NOT OFFSET)

```sql
-- ❌ SLOW for deep pages — scans and discards rows
SELECT * FROM users ORDER BY id LIMIT 20 OFFSET 50000;

-- ✅ FAST keyset pagination — always uses index
SELECT * FROM users WHERE id > :last_seen_id ORDER BY id LIMIT 20;

-- For composite sorting (e.g., by score DESC, then id ASC):
SELECT * FROM leaderboard
WHERE (score < :last_score) OR (score = :last_score AND id > :last_id)
ORDER BY score DESC, id ASC
LIMIT 20;
```

### Sequelize Implementation

```javascript
// Keyset pagination helper
async function paginateKeyset(model, { cursor, limit = 20, where = {}, order = [['id', 'ASC']], include = [] }) {
  const finalWhere = { ...where };

  if (cursor) {
    // Assumes cursor is the last seen `id`
    finalWhere.id = { [Op.gt]: cursor };
  }

  const rows = await model.findAll({
    where: finalWhere,
    order,
    limit: limit + 1, // fetch one extra to determine hasNextPage
    include,
  });

  const hasNextPage = rows.length > limit;
  if (hasNextPage) rows.pop(); // remove the extra row

  return {
    data: rows,
    nextCursor: rows.length > 0 ? rows[rows.length - 1].id : null,
    hasNextPage,
  };
}
```

### Batch Operations

```javascript
// ❌ SLOW — N individual queries
for (const score of scores) {
  await UserScore.create(score);
}

// ✅ FAST — single bulk insert
await UserScore.bulkCreate(scores, {
  validate: true,
  returning: false,          // skip returning data = faster
  ignoreDuplicates: true,    // ON CONFLICT DO NOTHING
});

// ✅ FAST upsert — bulk update-or-insert
await UserScore.bulkCreate(scores, {
  updateOnDuplicate: ['score', 'updated_at'],  // ON CONFLICT DO UPDATE
  validate: true,
});
```

### Counting Optimization

```sql
-- ❌ SLOW on huge tables — full table scan
SELECT COUNT(*) FROM users;

-- ✅ FAST approximate count (good for UI "showing ~50,000 results")
SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname = 'users';

-- ✅ Exact count with index-only scan (if you have a partial index)
SELECT COUNT(*) FROM users WHERE is_active = true;
-- This is fast IF there's an index on (is_active) and the table is vacuumed
```

```javascript
// Sequelize — approximate count for large tables
async function approximateCount(tableName) {
  const [result] = await sequelize.query(
    `SELECT reltuples::BIGINT AS count FROM pg_class WHERE relname = :table`,
    { replacements: { table: tableName }, type: QueryTypes.SELECT }
  );
  return result.count;
}
```

---

## Indexing Strategy for High Concurrency

### Competition Platform Index Examples

```sql
-- Leaderboard queries — ranking by score
CREATE INDEX CONCURRENTLY idx_scores_comp_score
ON user_scores (competition_id, score DESC, user_id);

-- User's competitions
CREATE INDEX CONCURRENTLY idx_scores_user_comp
ON user_scores (user_id, competition_id);

-- Active competitions
CREATE INDEX CONCURRENTLY idx_competitions_active
ON competitions (status, start_date)
WHERE status = 'active';

-- Match results by competition + round
CREATE INDEX CONCURRENTLY idx_matches_comp_round
ON matches (competition_id, round, status);

-- Partial index — only unfinished matches
CREATE INDEX CONCURRENTLY idx_matches_pending
ON matches (competition_id, scheduled_at)
WHERE status IN ('pending', 'in_progress');
```

### Monitor Index Health

```sql
-- Enable pg_stat_statements first
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 20 slowest queries
SELECT
  query,
  calls,
  ROUND(total_exec_time::NUMERIC, 2) AS total_ms,
  ROUND(mean_exec_time::NUMERIC, 2) AS avg_ms,
  rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Index hit ratio (should be > 99%)
SELECT
  'index hit rate' AS metric,
  ROUND(100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit + idx_blks_read), 0), 2) AS ratio
FROM pg_statio_user_indexes
UNION ALL
SELECT
  'table hit rate',
  ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 2)
FROM pg_statio_user_tables;

-- If ratio < 99%, you need more shared_buffers or better indexes

-- Table bloat check
SELECT
  relname,
  pg_size_pretty(pg_total_relation_size(oid)) AS total_size,
  pg_size_pretty(pg_relation_size(oid)) AS table_size,
  pg_size_pretty(pg_indexes_size(oid)) AS index_size,
  n_dead_tup,
  n_live_tup
FROM pg_stat_user_tables
JOIN pg_class ON pg_class.relname = pg_stat_user_tables.relname
ORDER BY pg_total_relation_size(oid) DESC
LIMIT 20;
```

---

## Partitioning for Large Tables

```sql
-- Partition match history by month (grows unbounded)
CREATE TABLE match_history (
  id BIGINT GENERATED ALWAYS AS IDENTITY,
  competition_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  score INTEGER NOT NULL,
  played_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  data JSONB DEFAULT '{}'
) PARTITION BY RANGE (played_at);

-- Create monthly partitions
CREATE TABLE match_history_2024_01 PARTITION OF match_history
  FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE match_history_2024_02 PARTITION OF match_history
  FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... create ahead for next 12 months

CREATE TABLE match_history_default PARTITION OF match_history DEFAULT;

-- Auto-create partitions with pg_partman extension
CREATE EXTENSION IF NOT EXISTS pg_partman;

SELECT partman.create_parent(
  'public.match_history',
  'played_at',
  'native',
  'monthly',
  p_premake := 6  -- create 6 months ahead
);
```

---

## Materialized Views for Heavy Reads

```sql
-- Leaderboard materialized view — refreshed periodically instead of computed live
CREATE MATERIALIZED VIEW mv_leaderboard AS
SELECT
  us.competition_id,
  us.user_id,
  u.username,
  u.avatar_url,
  us.score,
  us.matches_played,
  us.wins,
  RANK() OVER (PARTITION BY us.competition_id ORDER BY us.score DESC) AS rank
FROM user_scores us
JOIN users u ON u.id = us.user_id
WHERE us.score > 0
WITH DATA;

-- Unique index required for CONCURRENTLY refresh
CREATE UNIQUE INDEX idx_mv_leaderboard_pk
ON mv_leaderboard (competition_id, user_id);

CREATE INDEX idx_mv_leaderboard_rank
ON mv_leaderboard (competition_id, rank);

-- Refresh without blocking reads
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_leaderboard;

-- Schedule refresh every 30 seconds via pg_cron or application
-- For real-time: skip materialized view, use indexed table + careful queries
```

```javascript
// Sequelize — refresh materialized view
async function refreshLeaderboard() {
  await sequelize.query('REFRESH MATERIALIZED VIEW CONCURRENTLY mv_leaderboard');
}

// Schedule with setInterval or node-cron
const cron = require('node-cron');
cron.schedule('*/30 * * * * *', refreshLeaderboard); // every 30 seconds
```

---

## Lock Management and Deadlock Prevention

```sql
-- Always acquire locks in consistent order
-- If updating user_scores AND users, always lock users first, then user_scores

-- Use SKIP LOCKED for queue-like patterns
SELECT id, task_data FROM task_queue
WHERE status = 'pending'
ORDER BY created_at
LIMIT 10
FOR UPDATE SKIP LOCKED;

-- Monitor current locks
SELECT
  pg_stat_activity.pid,
  pg_stat_activity.usename,
  pg_stat_activity.query,
  pg_stat_activity.state,
  pg_stat_activity.wait_event_type,
  pg_stat_activity.wait_event,
  pg_locks.locktype,
  pg_locks.mode,
  pg_locks.granted
FROM pg_stat_activity
JOIN pg_locks ON pg_locks.pid = pg_stat_activity.pid
WHERE NOT pg_locks.granted
ORDER BY pg_stat_activity.query_start;

-- Kill long-running queries
SELECT pg_cancel_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND query_start < NOW() - INTERVAL '30 seconds'
AND pid != pg_backend_pid();

-- Kill stuck connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle in transaction' AND state_change < NOW() - INTERVAL '60 seconds';
```

---

## Monitoring and Diagnostics

### Essential Monitoring Queries

```sql
-- Dashboard: connection overview
SELECT
  state,
  COUNT(*) AS count,
  MAX(NOW() - state_change) AS max_duration
FROM pg_stat_activity
WHERE pid != pg_backend_pid()
GROUP BY state
ORDER BY count DESC;

-- Active queries right now
SELECT
  pid,
  usename,
  client_addr,
  state,
  NOW() - query_start AS duration,
  LEFT(query, 100) AS query_snippet
FROM pg_stat_activity
WHERE state = 'active' AND pid != pg_backend_pid()
ORDER BY query_start;

-- Database size
SELECT
  datname,
  pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;

-- Table sizes with indexes
SELECT
  relname AS table_name,
  pg_size_pretty(pg_total_relation_size(oid)) AS total,
  pg_size_pretty(pg_relation_size(oid)) AS data,
  pg_size_pretty(pg_indexes_size(oid)) AS indexes,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows
FROM pg_stat_user_tables
JOIN pg_class USING (relname)
WHERE pg_class.relkind = 'r'
ORDER BY pg_total_relation_size(oid) DESC;

-- Cache hit ratios (should be >99%)
SELECT
  sum(heap_blks_read) AS heap_read,
  sum(heap_blks_hit) AS heap_hit,
  ROUND(sum(heap_blks_hit) * 100.0 / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2) AS hit_ratio
FROM pg_statio_user_tables;

-- Replication lag (if using replicas)
SELECT
  client_addr,
  state,
  pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_lag_bytes,
  replay_lag
FROM pg_stat_replication;
```

### Health Check Endpoint Query

```javascript
// Use this in your /health endpoint
async function checkDatabaseHealth() {
  const [result] = await sequelize.query(`
    SELECT
      (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS active_connections,
      (SELECT count(*) FROM pg_stat_activity) AS total_connections,
      (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
      pg_database_size(current_database()) AS db_size_bytes,
      (SELECT ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 2) FROM pg_statio_user_tables) AS cache_hit_ratio
  `, { type: QueryTypes.SELECT });

  return {
    status: 'ok',
    database: {
      activeConnections: result.active_connections,
      totalConnections: result.total_connections,
      maxConnections: result.max_connections,
      connectionUsagePercent: Math.round(result.total_connections / result.max_connections * 100),
      dbSizeMB: Math.round(result.db_size_bytes / 1024 / 1024),
      cacheHitRatio: result.cache_hit_ratio,
    },
  };
}
```

---

## Backup Strategy for Production

```bash
# Daily compressed backup with pg_dump
pg_dump -U postgres -d mydb -F custom -Z 6 -f /backups/mydb_$(date +%Y%m%d_%H%M%S).dump

# Parallel backup for large databases
pg_dump -U postgres -d mydb -F directory -j 4 -Z 6 -f /backups/mydb_$(date +%Y%m%d)/

# Cron job: daily backup at 3 AM, keep 14 days
# /etc/cron.d/pg-backup
0 3 * * * postgres pg_dump -U postgres -d mydb -F custom -Z 6 -f /backups/mydb_$(date +\%Y\%m\%d).dump && find /backups/ -name "mydb_*.dump" -mtime +14 -delete

# Restore
pg_restore -U postgres -d mydb --clean --if-exists /backups/mydb_20240101.dump

# WAL archiving for point-in-time recovery (PITR)
# In postgresql.conf:
# archive_mode = on
# archive_command = 'cp %p /wal_archive/%f'
```

---

## pg_hba.conf Security for Production

```
# TYPE  DATABASE  USER      ADDRESS         METHOD
# Local connections
local   all       postgres                  peer
local   all       all                       scram-sha-256

# Application server (specific IP)
host    mydb      myuser    10.0.1.0/24     scram-sha-256

# PgBouncer (localhost only)
host    all       all       127.0.0.1/32    scram-sha-256

# Replication (if applicable)
host    replication replicator 10.0.1.0/24  scram-sha-256

# Block everything else
host    all       all       0.0.0.0/0       reject
```

---

## Common High-Load Pitfalls

| Pitfall | Impact | Fix |
|---------|--------|-----|
| Too many direct connections | OOM, process overhead | Use PgBouncer or limit pool size |
| OFFSET pagination on large tables | Full table scan for deep pages | Use keyset pagination |
| Missing indexes on FK columns | Slow JOINs, slow CASCADE deletes | Index ALL foreign keys |
| work_mem too high | OOM under load (5000 × sorts × 256MB) | Keep ≤ 16MB, monitor temp files |
| Autovacuum too slow | Table bloat, degraded perf | Lower scale_factor, increase workers |
| No statement_timeout | Runaway queries eat all connections | Set 30s global limit |
| SELECT * in production | Wastes bandwidth, prevents index-only scans | Select only needed columns |
| COUNT(*) on huge tables | Full table scan | Use approximate count or cache it |
| N+1 queries from ORM | Hundreds of queries per page load | Use eager loading (Sequelize include) |
| No connection retry | One network blip = app crash | Configure retry in Sequelize |
| synchronous_commit = off for important data | Data loss on crash | Keep 'on' for financial/competition data |
| Not monitoring slow queries | Silent performance degradation | Enable pg_stat_statements, log_min_duration_statement |

---

This configuration guide targets a **16GB RAM, 8-core SSD server** supporting **5000+ concurrent users** through Node.js + PM2 + Sequelize + PostgreSQL without Redis caching. Adjust numbers proportionally for different hardware specs.