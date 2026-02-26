A comprehensive guide to PostgreSQL fundamentals covering installation, data types, SQL operations, indexing, transactions, performance tuning, security, and administration.

## Overview

PostgreSQL (often called "Postgres") is a powerful, open-source object-relational database management system (ORDBMS) with over 35 years of active development. It is known for its reliability, feature robustness, extensibility, and standards compliance. PostgreSQL runs on all major operating systems and supports ACID transactions, foreign keys, subqueries, triggers, user-defined types, and functions.

---

## 1. Installation and Setup

### 1.1 Installing PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Docker (recommended for development):**
```bash
docker run --name my-postgres \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  -d postgres:16
```

### 1.2 Initial Configuration

After installation, PostgreSQL creates a system user called `postgres`. To access the database:

```bash
# Switch to postgres user
sudo -u postgres psql

# Or connect directly
psql -U postgres -h localhost -p 5432
```

### 1.3 Key Configuration Files

| File | Location (typical) | Purpose |
|------|-------------------|---------|
| `postgresql.conf` | `/etc/postgresql/16/main/` | Main server configuration |
| `pg_hba.conf` | `/etc/postgresql/16/main/` | Client authentication rules |
| `pg_ident.conf` | `/etc/postgresql/16/main/` | OS-to-Postgres user name mapping |

**Important `postgresql.conf` settings:**
```ini
# Connection settings
listen_addresses = 'localhost'      # or '*' for all interfaces
port = 5432
max_connections = 100

# Memory settings
shared_buffers = 256MB              # 25% of total RAM recommended
effective_cache_size = 1GB          # 50-75% of total RAM
work_mem = 4MB                      # per-operation memory
maintenance_work_mem = 64MB         # for VACUUM, CREATE INDEX

# WAL settings
wal_level = replica
max_wal_size = 1GB

# Logging
logging_collector = on
log_directory = 'log'
log_statement = 'all'               # none, ddl, mod, all
log_min_duration_statement = 1000   # log queries > 1s
```

**`pg_hba.conf` example:**
```
# TYPE  DATABASE  USER      ADDRESS        METHOD
local   all       postgres                 peer
local   all       all                      md5
host    all       all       127.0.0.1/32   md5
host    all       all       ::1/128        md5
host    all       all       0.0.0.0/0      scram-sha-256
```

After modifying configuration files:
```bash
sudo systemctl reload postgresql
# or from inside psql:
SELECT pg_reload_conf();
```

---

## 2. Database and User Management

### 2.1 Creating and Managing Databases

```sql
-- Create a database
CREATE DATABASE myapp;

-- Create with specific options
CREATE DATABASE myapp
  OWNER = myuser
  ENCODING = 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8'
  TEMPLATE = template0
  CONNECTION LIMIT = 50;

-- List all databases
\l
-- or
SELECT datname, datowner, encoding, datcollate FROM pg_database;

-- Connect to a database
\c myapp

-- Rename a database
ALTER DATABASE myapp RENAME TO myapp_v2;

-- Drop a database (CAUTION!)
DROP DATABASE IF EXISTS myapp;

-- Drop with force (terminates active connections, PG 13+)
DROP DATABASE myapp WITH (FORCE);
```

### 2.2 Creating and Managing Roles/Users

In PostgreSQL, users and groups are both "roles":

```sql
-- Create a user (role with LOGIN)
CREATE USER myuser WITH PASSWORD 'secure_password_123';

-- Create a role with specific privileges
CREATE ROLE app_admin WITH
  LOGIN
  CREATEDB
  CREATEROLE
  PASSWORD 'admin_pass'
  VALID UNTIL '2025-12-31'
  CONNECTION LIMIT 10;

-- Create a group role (no LOGIN)
CREATE ROLE readonly_group;

-- Grant group membership
GRANT readonly_group TO myuser;

-- Alter a role
ALTER ROLE myuser WITH SUPERUSER;
ALTER ROLE myuser SET search_path TO myschema, public;

-- List all roles
\du
SELECT rolname, rolsuper, rolcreatedb, rolcanlogin FROM pg_roles;

-- Drop a role
DROP ROLE IF EXISTS myuser;
```

### 2.3 Privileges and Permissions

```sql
-- Grant database-level privileges
GRANT CONNECT ON DATABASE myapp TO myuser;
GRANT CREATE ON DATABASE myapp TO myuser;

-- Grant schema-level privileges
GRANT USAGE ON SCHEMA public TO myuser;
GRANT CREATE ON SCHEMA public TO myuser;

-- Grant table-level privileges
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_group;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users TO myuser;

-- Grant column-level privileges
GRANT SELECT (id, username, email) ON TABLE users TO limited_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO readonly_group;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO myuser;

-- Revoke privileges
REVOKE ALL ON TABLE users FROM myuser;
REVOKE CONNECT ON DATABASE myapp FROM PUBLIC;
```

---

## 3. Schemas

Schemas are namespaces within a database that organize database objects:

```sql
-- Create a schema
CREATE SCHEMA sales;
CREATE SCHEMA IF NOT EXISTS hr AUTHORIZATION myuser;

-- Set search path
SET search_path TO sales, public;
-- Permanently for a role:
ALTER ROLE myuser SET search_path TO sales, public;

-- Create objects in a schema
CREATE TABLE sales.orders (
  id SERIAL PRIMARY KEY,
  amount NUMERIC(10,2)
);

-- Access objects with qualified names
SELECT * FROM sales.orders;

-- List schemas
\dn
SELECT schema_name FROM information_schema.schemata;

-- Drop a schema
DROP SCHEMA sales CASCADE; -- drops all objects inside
```

---

## 4. Data Types

### 4.1 Complete Data Types Reference

| Category | Type | Description | Example |
|----------|------|-------------|---------|
| **Numeric** | `SMALLINT` | 2 bytes, -32768 to 32767 | `42` |
| | `INTEGER` / `INT` | 4 bytes, ±2 billion | `100000` |
| | `BIGINT` | 8 bytes, ±9.2 quintillion | `9999999999` |
| | `NUMERIC(p,s)` / `DECIMAL` | Exact precision | `99999.99` |
| | `REAL` | 4 bytes, 6 decimal digits | `3.14` |
| | `DOUBLE PRECISION` | 8 bytes, 15 decimal digits | `3.141592653589` |
| | `SERIAL` | Auto-incrementing INT | auto |
| | `BIGSERIAL` | Auto-incrementing BIGINT | auto |
| **Text** | `CHAR(n)` | Fixed-length, padded | `'AB  '` |
| | `VARCHAR(n)` | Variable-length with limit | `'hello'` |
| | `TEXT` | Unlimited variable-length | `'any length...'` |
| **Boolean** | `BOOLEAN` | true/false/null | `TRUE` |
| **Date/Time** | `DATE` | Date only | `'2024-01-15'` |
| | `TIME` | Time only | `'14:30:00'` |
| | `TIMESTAMP` | Date + time (no TZ) | `'2024-01-15 14:30:00'` |
| | `TIMESTAMPTZ` | Date + time with TZ | `'2024-01-15 14:30:00+03'` |
| | `INTERVAL` | Time span | `'2 hours 30 minutes'` |
| **Binary** | `BYTEA` | Binary data | `'\xDEADBEEF'` |
| **JSON** | `JSON` | Text JSON | `'{"key": "val"}'` |
| | `JSONB` | Binary JSON (preferred) | `'{"key": "val"}'` |
| **UUID** | `UUID` | 128-bit identifier | `gen_random_uuid()` |
| **Array** | `type[]` | Array of any type | `'{1,2,3}'` |
| **Network** | `INET` | IPv4/IPv6 address | `'192.168.1.1/24'` |
| | `CIDR` | IPv4/IPv6 network | `'192.168.1.0/24'` |
| | `MACADDR` | MAC address | `'08:00:2b:01:02:03'` |
| **Enum** | `CREATE TYPE` | Custom enumeration | see below |
| **Range** | `INT4RANGE`, `TSRANGE`, etc. | Range of values | `'[1,10)'` |
| **Geometric** | `POINT`, `LINE`, `CIRCLE` | Geometric shapes | `'(1,2)'` |

### 4.2 Custom Types

```sql
-- Enum type
CREATE TYPE mood AS ENUM ('sad', 'ok', 'happy');

CREATE TABLE person (
  name TEXT,
  current_mood mood
);

INSERT INTO person VALUES ('Alice', 'happy');

-- Composite type
CREATE TYPE address AS (
  street TEXT,
  city TEXT,
  zip_code VARCHAR(10)
);

-- Domain (type with constraints)
CREATE DOMAIN email AS TEXT
  CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE TABLE contacts (
  id SERIAL PRIMARY KEY,
  contact_email email NOT NULL
);
```

---

## 5. Table Operations (DDL)

### 5.1 Creating Tables

```sql
CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  username      VARCHAR(50) NOT NULL UNIQUE,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name     VARCHAR(100),
  age           INTEGER CHECK (age >= 0 AND age <= 150),
  balance       NUMERIC(12,2) DEFAULT 0.00,
  is_active     BOOLEAN DEFAULT TRUE,
  role          VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),
  metadata      JSONB DEFAULT '{}',
  tags          TEXT[] DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  deleted_at    TIMESTAMPTZ
);

-- Table with foreign key
CREATE TABLE orders (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  total       NUMERIC(12,2) NOT NULL CHECK (total > 0),
  status      VARCHAR(20) DEFAULT 'pending',
  items       JSONB NOT NULL DEFAULT '[]',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Table with composite primary key
CREATE TABLE order_items (
  order_id    BIGINT REFERENCES orders(id) ON DELETE CASCADE,
  product_id  BIGINT NOT NULL,
  quantity    INTEGER NOT NULL CHECK (quantity > 0),
  unit_price  NUMERIC(10,2) NOT NULL,
  PRIMARY KEY (order_id, product_id)
);

-- Unlogged table (faster writes, no WAL, lost on crash)
CREATE UNLOGGED TABLE session_data (
  session_id TEXT PRIMARY KEY,
  data JSONB,
  expires_at TIMESTAMPTZ
);

-- Temporary table (exists only for current session)
CREATE TEMP TABLE temp_results (
  id INT,
  value TEXT
);
```

### 5.2 Altering Tables

```sql
-- Add column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Drop column
ALTER TABLE users DROP COLUMN phone;

-- Rename column
ALTER TABLE users RENAME COLUMN full_name TO display_name;

-- Change data type
ALTER TABLE users ALTER COLUMN age TYPE SMALLINT;

-- Set/drop default
ALTER TABLE users ALTER COLUMN is_active SET DEFAULT TRUE;
ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT;

-- Set/drop NOT NULL
ALTER TABLE users ALTER COLUMN email SET NOT NULL;
ALTER TABLE users ALTER COLUMN full_name DROP NOT NULL;

-- Add constraint
ALTER TABLE users ADD CONSTRAINT chk_username_length CHECK (LENGTH(username) >= 3);
ALTER TABLE users ADD CONSTRAINT uq_email UNIQUE (email);

-- Drop constraint
ALTER TABLE users DROP CONSTRAINT chk_username_length;

-- Rename table
ALTER TABLE users RENAME TO app_users;
```

### 5.3 Table Introspection

```sql
-- Describe table
\d users
\d+ users  -- with additional info

-- List all tables
\dt
\dt+ public.*

-- Get table info from catalog
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

---

## 6. CRUD Operations (DML)

### 6.1 INSERT

```sql
-- Single row
INSERT INTO users (username, email, password_hash)
VALUES ('alice', 'alice@example.com', 'hash123');

-- Multiple rows
INSERT INTO users (username, email, password_hash)
VALUES
  ('bob', 'bob@example.com', 'hash456'),
  ('charlie', 'charlie@example.com', 'hash789');

-- Returning inserted data
INSERT INTO users (username, email, password_hash)
VALUES ('diana', 'diana@example.com', 'hash000')
RETURNING id, username, created_at;

-- Insert from SELECT
INSERT INTO archived_users (id, username, email)
SELECT id, username, email FROM users WHERE deleted_at IS NOT NULL;

-- Upsert (INSERT ON CONFLICT)
INSERT INTO users (username, email, password_hash)
VALUES ('alice', 'alice_new@example.com', 'newhash')
ON CONFLICT (username) DO UPDATE
SET email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    updated_at = NOW();

-- Upsert: do nothing on conflict
INSERT INTO users (username, email, password_hash)
VALUES ('alice', 'alice@example.com', 'hash123')
ON CONFLICT (username) DO NOTHING;
```

### 6.2 SELECT

```sql
-- Basic select
SELECT * FROM users;
SELECT id, username, email FROM users;

-- Filtering
SELECT * FROM users WHERE is_active = TRUE AND age > 18;
SELECT * FROM users WHERE email LIKE '%@gmail.com';
SELECT * FROM users WHERE email ILIKE '%@gmail.com';  -- case-insensitive
SELECT * FROM users WHERE role IN ('admin', 'moderator');
SELECT * FROM users WHERE age BETWEEN 18 AND 65;
SELECT * FROM users WHERE deleted_at IS NULL;
SELECT * FROM users WHERE tags @> ARRAY['vip'];  -- array contains

-- Sorting
SELECT * FROM users ORDER BY created_at DESC;
SELECT * FROM users ORDER BY role ASC, username ASC;
SELECT * FROM users ORDER BY created_at DESC NULLS LAST;

-- Pagination
SELECT * FROM users ORDER BY id LIMIT 20 OFFSET 40;
-- Better: keyset pagination
SELECT * FROM users WHERE id > 100 ORDER BY id LIMIT 20;

-- Distinct
SELECT DISTINCT role FROM users;
SELECT DISTINCT ON (role) id, role, username FROM users ORDER BY role, created_at;

-- Aliases
SELECT
  u.username AS name,
  u.email AS contact,
  EXTRACT(YEAR FROM AGE(NOW(), u.created_at)) AS years_active
FROM users u;

-- CASE expressions
SELECT
  username,
  CASE
    WHEN age < 18 THEN 'minor'
    WHEN age BETWEEN 18 AND 65 THEN 'adult'
    ELSE 'senior'
  END AS age_group
FROM users;

-- COALESCE and NULLIF
SELECT
  COALESCE(full_name, username) AS display_name,
  NULLIF(phone, '') AS phone  -- returns NULL if empty string
FROM users;
```

### 6.3 Aggregate Functions and GROUP BY

```sql
-- Basic aggregation
SELECT
  COUNT(*) AS total_users,
  COUNT(DISTINCT role) AS role_count,
  AVG(age) AS avg_age,
  MIN(age) AS min_age,
  MAX(age) AS max_age,
  SUM(balance) AS total_balance
FROM users
WHERE is_active = TRUE;

-- GROUP BY
SELECT
  role,
  COUNT(*) AS user_count,
  ROUND(AVG(age), 1) AS avg_age,
  SUM(balance) AS total_balance
FROM users
GROUP BY role
ORDER BY user_count DESC;

-- HAVING (filter groups)
SELECT role, COUNT(*) AS cnt
FROM users
GROUP BY role
HAVING COUNT(*) > 10;

-- Grouping sets
SELECT
  role,
  is_active,
  COUNT(*)
FROM users
GROUP BY GROUPING SETS ((role), (is_active), (role, is_active), ());

-- FILTER clause
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE is_active) AS active,
  COUNT(*) FILTER (WHERE NOT is_active) AS inactive,
  AVG(age) FILTER (WHERE role = 'admin') AS avg_admin_age
FROM users;
```

### 6.4 Joins

```sql
-- INNER JOIN (only matching rows)
SELECT u.username, o.id AS order_id, o.total
FROM users u
INNER JOIN orders o ON o.user_id = u.id;

-- LEFT JOIN (all left rows, NULLs for non-matching right)
SELECT u.username, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id, u.username;

-- RIGHT JOIN
SELECT o.*, u.username
FROM orders o
RIGHT JOIN users u ON o.user_id = u.id;

-- FULL OUTER JOIN
SELECT u.username, o.id
FROM users u
FULL OUTER JOIN orders o ON o.user_id = u.id;

-- CROSS JOIN (cartesian product)
SELECT u.username, r.role_name
FROM users u
CROSS JOIN roles r;

-- Self join
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;

-- Multiple joins
SELECT
  u.username,
  o.id AS order_id,
  p.name AS product_name,
  oi.quantity,
  oi.unit_price
FROM users u
JOIN orders o ON o.user_id = u.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.status = 'completed';

-- LATERAL JOIN (subquery can reference earlier tables)
SELECT u.username, recent.total
FROM users u
LEFT JOIN LATERAL (
  SELECT total
  FROM orders
  WHERE user_id = u.id
  ORDER BY created_at DESC
  LIMIT 3
) recent ON TRUE;
```

### 6.5 UPDATE

```sql
-- Basic update
UPDATE users SET is_active = FALSE WHERE last_login < NOW() - INTERVAL '1 year';

-- Update multiple columns
UPDATE users
SET
  role = 'admin',
  updated_at = NOW()
WHERE username = 'alice';

-- Update with RETURNING
UPDATE users
SET balance = balance + 100
WHERE id = 1
RETURNING id, username, balance;

-- Update with subquery
UPDATE orders
SET status = 'cancelled'
WHERE user_id IN (SELECT id FROM users WHERE is_active = FALSE);

-- Update with FROM (join-based update)
UPDATE orders o
SET status = 'flagged'
FROM users u
WHERE o.user_id = u.id
  AND u.role = 'suspended';
```

### 6.6 DELETE

```sql
-- Basic delete
DELETE FROM users WHERE id = 42;

-- Delete with condition
DELETE FROM users WHERE is_active = FALSE AND created_at < '2020-01-01';

-- Delete with RETURNING
DELETE FROM users WHERE deleted_at IS NOT NULL
RETURNING id, username;

-- Delete with subquery
DELETE FROM orders
WHERE user_id NOT IN (SELECT id FROM users);

-- TRUNCATE (fast delete all rows)
TRUNCATE TABLE orders;
TRUNCATE TABLE orders RESTART IDENTITY CASCADE;
```

---

## 7. Subqueries and CTEs

### 7.1 Subqueries

```sql
-- Scalar subquery
SELECT username, (SELECT COUNT(*) FROM orders WHERE user_id = users.id) AS order_count
FROM users;

-- IN subquery
SELECT * FROM users
WHERE id IN (SELECT DISTINCT user_id FROM orders WHERE total > 1000);

-- EXISTS subquery (often more efficient than IN)
SELECT * FROM users u
WHERE EXISTS (
  SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 1000
);

-- NOT EXISTS (anti-join)
SELECT * FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM orders o WHERE o.user_id = u.id
);

-- ANY / ALL
SELECT * FROM products WHERE price > ALL (SELECT AVG(price) FROM products GROUP BY category);
SELECT * FROM products WHERE category = ANY (ARRAY['electronics', 'books']);
```

### 7.2 Common Table Expressions (CTEs)

```sql
-- Basic CTE
WITH active_users AS (
  SELECT id, username, email
  FROM users
  WHERE is_active = TRUE
)
SELECT au.username, COUNT(o.id) AS orders
FROM active_users au
LEFT JOIN orders o ON o.user_id = au.id
GROUP BY au.username;

-- Multiple CTEs
WITH
  user_orders AS (
    SELECT user_id, COUNT(*) AS order_count, SUM(total) AS total_spent
    FROM orders
    GROUP BY user_id
  ),
  user_categories AS (
    SELECT
      user_id,
      CASE
        WHEN total_spent > 10000 THEN 'platinum'
        WHEN total_spent > 5000 THEN 'gold'
        WHEN total_spent > 1000 THEN 'silver'
        ELSE 'bronze'
      END AS category
    FROM user_orders
  )
SELECT u.username, uc.category, uo.order_count, uo.total_spent
FROM users u
JOIN user_orders uo ON uo.user_id = u.id
JOIN user_categories uc ON uc.user_id = u.id
ORDER BY uo.total_spent DESC;

-- Recursive CTE (hierarchical data)
WITH RECURSIVE org_tree AS (
  -- Base case: top-level (no manager)
  SELECT id, name, manager_id, 1 AS depth, name::TEXT AS path
  FROM employees
  WHERE manager_id IS NULL

  UNION ALL

  -- Recursive case
  SELECT e.id, e.name, e.manager_id, t.depth + 1, t.path || ' > ' || e.name
  FROM employees e
  JOIN org_tree t ON e.manager_id = t.id
)
SELECT * FROM org_tree ORDER BY path;

-- Writable CTE
WITH deleted AS (
  DELETE FROM users WHERE is_active = FALSE
  RETURNING *
)
INSERT INTO archived_users SELECT * FROM deleted;
```

---

## 8. Window Functions

```sql
-- ROW_NUMBER: unique sequential number
SELECT
  username,
  balance,
  ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank
FROM users;

-- RANK and DENSE_RANK
SELECT
  username,
  role,
  balance,
  RANK() OVER (PARTITION BY role ORDER BY balance DESC) AS rank,
  DENSE_RANK() OVER (PARTITION BY role ORDER BY balance DESC) AS dense_rank
FROM users;

-- Running totals
SELECT
  id,
  created_at::DATE AS day,
  total,
  SUM(total) OVER (ORDER BY created_at) AS running_total
FROM orders;

-- Moving average
SELECT
  created_at::DATE,
  total,
  AVG(total) OVER (
    ORDER BY created_at
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS moving_avg_7day
FROM orders;

-- LAG and LEAD (previous/next row values)
SELECT
  created_at::DATE AS day,
  total,
  LAG(total) OVER (ORDER BY created_at) AS prev_total,
  LEAD(total) OVER (ORDER BY created_at) AS next_total,
  total - LAG(total) OVER (ORDER BY created_at) AS change
FROM orders;

-- FIRST_VALUE, LAST_VALUE, NTH_VALUE
SELECT
  username,
  role,
  balance,
  FIRST_VALUE(username) OVER (PARTITION BY role ORDER BY balance DESC) AS top_earner
FROM users;

-- NTILE: divide into buckets
SELECT
  username,
  balance,
  NTILE(4) OVER (ORDER BY balance DESC) AS quartile
FROM users;

-- Named window
SELECT
  username,
  balance,
  ROW_NUMBER() OVER w AS row_num,
  SUM(balance) OVER w AS running_sum
FROM users
WINDOW w AS (ORDER BY balance DESC);
```

---

## 9. Indexes

### 9.1 Index Types and Creation

```sql
-- B-Tree (default, most common)
CREATE INDEX idx_users_email ON users (email);
CREATE UNIQUE INDEX idx_users_username ON users (username);

-- Composite index
CREATE INDEX idx_orders_user_status ON orders (user_id, status);

-- Partial index (index subset of rows)
CREATE INDEX idx_active_users ON users (email) WHERE is_active = TRUE;
CREATE INDEX idx_pending_orders ON orders (created_at) WHERE status = 'pending';

-- Expression index
CREATE INDEX idx_users_lower_email ON users (LOWER(email));
CREATE INDEX idx_users_year ON users (EXTRACT(YEAR FROM created_at));

-- GIN index (for JSONB, arrays, full-text search)
CREATE INDEX idx_users_metadata ON users USING GIN (metadata);
CREATE INDEX idx_users_tags ON users USING GIN (tags);
CREATE INDEX idx_products_search ON products USING GIN (to_tsvector('english', name || ' ' || description));

-- GiST index (geometric, range, full-text)
CREATE INDEX idx_locations_point ON locations USING GIST (coordinates);
CREATE INDEX idx_events_during ON events USING GIST (duration);

-- BRIN index (for large, naturally ordered tables)
CREATE INDEX idx_logs_created ON logs USING BRIN (created_at);

-- Hash index (equality only, PG 10+)
CREATE INDEX idx_sessions_token ON sessions USING HASH (token);

-- Covering index (INCLUDE - PG 11+)
CREATE INDEX idx_orders_user ON orders (user_id) INCLUDE (total, status);

-- Concurrent index creation (no lock)
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- Drop
DROP INDEX idx_users_email;
DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
```

### 9.2 Index Usage Analysis

```sql
-- Check if index is used
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'alice@example.com';

-- Check index usage statistics
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;

-- Find unused indexes
SELECT
  indexrelid::regclass AS index_name,
  relid::regclass AS table_name,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Table and index sizes
SELECT
  relname,
  pg_size_pretty(pg_total_relation_size(oid)) AS total,
  pg_size_pretty(pg_relation_size(oid)) AS table_only,
  pg_size_pretty(pg_indexes_size(oid)) AS indexes
FROM pg_class
WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(oid) DESC;
```

---

## 10. Transactions and Concurrency

### 10.1 Transaction Basics

```sql
-- Explicit transaction
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- Rollback
BEGIN;
  DELETE FROM users WHERE id = 999;
ROLLBACK;  -- undoes the delete

-- Savepoints
BEGIN;
  INSERT INTO orders (user_id, total) VALUES (1, 100);
  SAVEPOINT sp1;
  INSERT INTO orders (user_id, total) VALUES (1, -50);  -- might fail
  ROLLBACK TO SAVEPOINT sp1;  -- undo only the second insert
  INSERT INTO orders (user_id, total) VALUES (1, 50);   -- try again
COMMIT;
```

### 10.2 Isolation Levels

```sql
-- Read Committed (default)
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- Repeatable Read
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- Serializable (strictest)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- Set default for session
SET default_transaction_isolation = 'serializable';
```

| Isolation Level | Dirty Read | Non-repeatable Read | Phantom Read | Serialization Anomaly |
|----------------|------------|--------------------|--------------|-----------------------|
| Read Committed | ✗ | Possible | Possible | Possible |
| Repeatable Read | ✗ | ✗ | ✗ (in PG) | Possible |
| Serializable | ✗ | ✗ | ✗ | ✗ |

### 10.3 Locking

```sql
-- Row-level lock
SELECT * FROM accounts WHERE id = 1 FOR UPDATE;          -- exclusive
SELECT * FROM accounts WHERE id = 1 FOR SHARE;           -- shared
SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT;   -- fail immediately if locked
SELECT * FROM accounts WHERE id = 1 FOR UPDATE SKIP LOCKED;  -- skip locked rows

-- Advisory locks (application-level)
SELECT pg_advisory_lock(12345);        -- session-level lock
SELECT pg_advisory_unlock(12345);
SELECT pg_try_advisory_lock(12345);    -- non-blocking

-- View current locks
SELECT pid, locktype, relation::regclass, mode, granted
FROM pg_locks
WHERE NOT granted;
```

---

## 11. Views and Materialized Views

```sql
-- Regular view
CREATE OR REPLACE VIEW active_user_orders AS
SELECT
  u.id AS user_id,
  u.username,
  u.email,
  COUNT(o.id) AS orders_count,
  COALESCE(SUM(o.total), 0) AS total_spent
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.is_active = TRUE
GROUP BY u.id, u.username, u.email;

-- Use it like a table
SELECT * FROM active_user_orders WHERE total_spent > 1000;

-- Materialized view (stores data physically)
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
  created_at::DATE AS sale_date,
  COUNT(*) AS order_count,
  SUM(total) AS revenue
FROM orders
WHERE status = 'completed'
GROUP BY created_at::DATE
ORDER BY sale_date;

-- Create index on materialized view
CREATE INDEX idx_mv_daily_sales_date ON mv_daily_sales (sale_date);

-- Refresh materialized view
REFRESH MATERIALIZED VIEW mv_daily_sales;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;  -- requires unique index

-- Drop
DROP VIEW active_user_orders;
DROP MATERIALIZED VIEW mv_daily_sales;
```

---

## 12. Functions and Procedures

### 12.1 Functions

```sql
-- Simple SQL function
CREATE OR REPLACE FUNCTION get_user_order_count(p_user_id BIGINT)
RETURNS INTEGER AS $$
  SELECT COUNT(*)::INTEGER FROM orders WHERE user_id = p_user_id;
$$ LANGUAGE sql STABLE;

-- PL/pgSQL function
CREATE OR REPLACE FUNCTION transfer_funds(
  p_from_id BIGINT,
  p_to_id BIGINT,
  p_amount NUMERIC
)
RETURNS VOID AS $$
DECLARE
  v_balance NUMERIC;
BEGIN
  -- Check balance
  SELECT balance INTO v_balance FROM accounts WHERE id = p_from_id FOR UPDATE;

  IF v_balance IS NULL THEN
    RAISE EXCEPTION 'Account % not found', p_from_id;
  END IF;

  IF v_balance < p_amount THEN
    RAISE EXCEPTION 'Insufficient funds. Balance: %, Required: %', v_balance, p_amount;
  END IF;

  -- Perform transfer
  UPDATE accounts SET balance = balance - p_amount WHERE id = p_from_id;
  UPDATE accounts SET balance = balance + p_amount WHERE id = p_to_id;

  RAISE NOTICE 'Transferred % from account % to account %', p_amount, p_from_id, p_to_id;
END;
$$ LANGUAGE plpgsql;

-- Call functions
SELECT get_user_order_count(1);
SELECT transfer_funds(1, 2, 500.00);

-- Function returning a table
CREATE OR REPLACE FUNCTION search_users(p_query TEXT)
RETURNS TABLE (id BIGINT, username VARCHAR, email VARCHAR) AS $$
BEGIN
  RETURN QUERY
  SELECT u.id, u.username, u.email
  FROM users u
  WHERE u.username ILIKE '%' || p_query || '%'
     OR u.email ILIKE '%' || p_query || '%';
END;
$$ LANGUAGE plpgsql STABLE;

SELECT * FROM search_users('alice');
```

### 12.2 Procedures (PG 11+)

```sql
-- Procedures can manage transactions
CREATE OR REPLACE PROCEDURE batch_deactivate_users(p_days INTEGER)
LANGUAGE plpgsql AS $$
DECLARE
  v_count INTEGER := 0;
  v_batch INTEGER := 1000;
BEGIN
  LOOP
    UPDATE users
    SET is_active = FALSE, updated_at = NOW()
    WHERE id IN (
      SELECT id FROM users
      WHERE is_active = TRUE
        AND last_login < NOW() - (p_days || ' days')::INTERVAL
      LIMIT v_batch
    );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    EXIT WHEN v_count = 0;

    COMMIT;  -- commit each batch
    RAISE NOTICE 'Deactivated % users', v_count;
  END LOOP;
END;
$$;

-- Call procedure
CALL batch_deactivate_users(365);
```

---

## 13. Triggers

```sql
-- Trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Audit trigger
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  operation TEXT NOT NULL,
  old_data JSONB,
  new_data JSONB,
  changed_by TEXT DEFAULT current_user,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    INSERT INTO audit_log (table_name, operation, old_data)
    VALUES (TG_TABLE_NAME, TG_OP, to_jsonb(OLD));
    RETURN OLD;
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_log (table_name, operation, old_data, new_data)
    VALUES (TG_TABLE_NAME, TG_OP, to_jsonb(OLD), to_jsonb(NEW));
    RETURN NEW;
  ELSIF TG_OP = 'INSERT' THEN
    INSERT INTO audit_log (table_name, operation, new_data)
    VALUES (TG_TABLE_NAME, TG_OP, to_jsonb(NEW));
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_audit
  AFTER INSERT OR UPDATE OR DELETE ON users
  FOR EACH ROW
  EXECUTE FUNCTION audit_trigger_func();

-- List triggers
SELECT trigger_name, event_manipulation, action_timing
FROM information_schema.triggers
WHERE trigger_schema = 'public';

-- Drop trigger
DROP TRIGGER trg_users_audit ON users;
```

---

## 14. JSON/JSONB Operations

```sql
-- Create and insert JSON
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  data JSONB NOT NULL
);

INSERT INTO events (data) VALUES
  ('{"type": "click", "page": "/home", "user": {"id": 1, "name": "Alice"}, "tags": ["web", "mobile"]}'),
  ('{"type": "view", "page": "/products", "user": {"id": 2, "name": "Bob"}, "duration": 45}');

-- Access JSON fields
SELECT
  data->>'type' AS event_type,           -- text value
  data->'user'->>'name' AS user_name,    -- nested text
  data->'user'->'id' AS user_id,         -- json value
  data#>>'{user,name}' AS user_name2     -- path extraction
FROM events;

-- Filter by JSON
SELECT * FROM events WHERE data->>'type' = 'click';
SELECT * FROM events WHERE (data->'user'->>'id')::INT = 1;
SELECT * FROM events WHERE data @> '{"type": "click"}';       -- contains
SELECT * FROM events WHERE data ? 'duration';                  -- key exists
SELECT * FROM events WHERE data ?| ARRAY['duration', 'tags'];  -- any key exists
SELECT * FROM events WHERE data ?& ARRAY['type', 'page'];      -- all keys exist

-- JSON array operations
SELECT * FROM events WHERE data->'tags' ? 'web';       -- array contains
SELECT jsonb_array_elements_text(data->'tags') AS tag FROM events;

-- Modify JSONB
UPDATE events SET data = data || '{"processed": true}' WHERE id = 1;       -- merge
UPDATE events SET data = data - 'duration' WHERE id = 2;                     -- remove key
UPDATE events SET data = jsonb_set(data, '{user,email}', '"a@b.com"') WHERE id = 1;  -- set nested

-- Aggregation with JSON
SELECT
  data->>'type' AS event_type,
  COUNT(*),
  jsonb_agg(data->'user'->>'name') AS users
FROM events
GROUP BY data->>'type';
```

---

## 15. Full-Text Search

```sql
-- Basic full-text search
SELECT * FROM products
WHERE to_tsvector('english', name || ' ' || description)
      @@ to_tsquery('english', 'wireless & keyboard');

-- Add tsvector column for performance
ALTER TABLE products ADD COLUMN search_vector tsvector;

UPDATE products SET search_vector =
  to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, ''));

CREATE INDEX idx_products_fts ON products USING GIN (search_vector);

-- Trigger to keep it updated
CREATE TRIGGER trg_products_search
  BEFORE INSERT OR UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION
  tsvector_update_trigger(search_vector, 'pg_catalog.english', name, description);

-- Search with ranking
SELECT
  name,
  ts_rank(search_vector, query) AS rank,
  ts_headline('english', description, query, 'StartSel=<b>, StopSel=</b>') AS headline
FROM products,
  to_tsquery('english', 'wireless & (keyboard | mouse)') AS query
WHERE search_vector @@ query
ORDER BY rank DESC;

-- Phrase search (PG 9.6+)
SELECT * FROM products
WHERE search_vector @@ phraseto_tsquery('english', 'wireless keyboard');
```

---

## 16. Performance and Query Analysis

### 16.1 EXPLAIN

```sql
-- Basic explain
EXPLAIN SELECT * FROM users WHERE email = 'alice@example.com';

-- Explain with actual execution
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.username, COUNT(o.id)
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id;

-- JSON format for programmatic parsing
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM users WHERE id = 1;
```

**Reading EXPLAIN output:**
```
Seq Scan on users  (cost=0.00..1.04 rows=1 width=556) (actual time=0.012..0.013 rows=1 loops=1)
  Filter: (email = 'alice@example.com'::text)
  Rows Removed by Filter: 3
Planning Time: 0.065 ms
Execution Time: 0.031 ms
```

- `cost=startup..total` — estimated cost units
- `rows` — estimated (plan) vs actual row count
- `width` — average row size in bytes
- `Seq Scan` — full table scan (may need index)
- `Index Scan` — index used (good)
- `Bitmap Index Scan` — index + bitmap (good for many rows)

### 16.2 Common Performance Tips

```sql
-- 1. ANALYZE tables for up-to-date statistics
ANALYZE users;
ANALYZE;  -- all tables

-- 2. VACUUM (reclaim dead tuple space)
VACUUM users;
VACUUM FULL users;  -- rewrites table, locks it
VACUUM ANALYZE users;  -- both

-- 3. Check slow queries
SELECT
  query,
  calls,
  ROUND(total_exec_time::NUMERIC, 2) AS total_ms,
  ROUND(mean_exec_time::NUMERIC, 2) AS avg_ms,
  rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Enable pg_stat_statements (in postgresql.conf)
-- shared_preload_libraries = 'pg_stat_statements'
-- Then: CREATE EXTENSION pg_stat_statements;

-- 4. Check table bloat
SELECT
  relname,
  n_live_tup,
  n_dead_tup,
  ROUND(100.0 * n_dead_tup / GREATEST(n_live_tup + n_dead_tup, 1), 1) AS dead_pct,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 5. Connection monitoring
SELECT
  pid,
  usename,
  application_name,
  client_addr,
  state,
  query,
  query_start
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;

-- Cancel a query
SELECT pg_cancel_backend(12345);

-- Terminate a connection
SELECT pg_terminate_backend(12345);
```

---

## 17. Backup and Restore

```bash
# Logical backup (single database)
pg_dump -U postgres -h localhost -d myapp -F custom -f myapp.dump
pg_dump -U postgres -d myapp -F plain -f myapp.sql    # SQL format

# Backup specific tables
pg_dump -U postgres -d myapp -t users -t orders -F custom -f tables.dump

# Schema only
pg_dump -U postgres -d myapp --schema-only -f schema.sql

# Data only
pg_dump -U postgres -d myapp --data-only -f data.sql

# All databases
pg_dumpall -U postgres -f all_databases.sql

# Restore from custom format
pg_restore -U postgres -d myapp -F custom myapp.dump
pg_restore -U postgres -d myapp --clean --if-exists myapp.dump

# Restore from SQL
psql -U postgres -d myapp -f myapp.sql

# Parallel backup/restore (faster for large DBs)
pg_dump -U postgres -d myapp -F directory -j 4 -f backup_dir/
pg_restore -U postgres -d myapp -j 4 backup_dir/
```

---

## 18. Partitioning (PG 10+)

```sql
-- Range partitioning
CREATE TABLE measurements (
  id BIGSERIAL,
  sensor_id INTEGER NOT NULL,
  value NUMERIC NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (recorded_at);

-- Create partitions
CREATE TABLE measurements_2024_q1 PARTITION OF measurements
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
CREATE TABLE measurements_2024_q2 PARTITION OF measurements
  FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
CREATE TABLE measurements_2024_q3 PARTITION OF measurements
  FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');
CREATE TABLE measurements_2024_q4 PARTITION OF measurements
  FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

-- Default partition (catches everything else)
CREATE TABLE measurements_default PARTITION OF measurements DEFAULT;

-- Create indexes (automatically applies to all partitions)
CREATE INDEX idx_measurements_time ON measurements (recorded_at);

-- List partitioning
CREATE TABLE orders_by_region (
  id BIGSERIAL,
  region TEXT NOT NULL,
  total NUMERIC
) PARTITION BY LIST (region);

CREATE TABLE orders_us PARTITION OF orders_by_region FOR VALUES IN ('US');
CREATE TABLE orders_eu PARTITION OF orders_by_region FOR VALUES IN ('EU', 'UK');
CREATE TABLE orders_asia PARTITION OF orders_by_region FOR VALUES IN ('JP', 'CN', 'KR');

-- Hash partitioning
CREATE TABLE sessions (
  id UUID NOT NULL,
  user_id BIGINT,
  data JSONB
) PARTITION BY HASH (id);

CREATE TABLE sessions_0 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE sessions_1 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE sessions_2 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE sessions_3 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- Detach/attach partitions
ALTER TABLE measurements DETACH PARTITION measurements_2024_q1;
ALTER TABLE measurements ATTACH PARTITION measurements_2024_q1
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

---

## 19. Useful psql Commands

| Command | Description |
|---------|-------------|
| `\l` | List databases |
| `\c dbname` | Connect to database |
| `\dt` | List tables |
| `\dt+` | List tables with sizes |
| `\d tablename` | Describe table |
| `\d+ tablename` | Detailed table info |
| `\di` | List indexes |
| `\dv` | List views |
| `\dm` | List materialized views |
| `\df` | List functions |
| `\dn` | List schemas |
| `\du` | List roles |
| `\dp` | List access privileges |
| `\ds` | List sequences |
| `\x` | Toggle expanded display |
| `\timing` | Toggle query timing |
| `\i file.sql` | Execute SQL file |
| `\o output.txt` | Send output to file |
| `\copy` | Copy data to/from CSV |
| `\! command` | Execute shell command |
| `\q` | Quit psql |
| `\?` | Help on psql commands |
| `\h SQL_COMMAND` | Help on SQL syntax |

### Useful data import/export:
```sql
-- Copy table to CSV
\copy users TO '/tmp/users.csv' WITH CSV HEADER;

-- Copy CSV to table
\copy users (username, email) FROM '/tmp/new_users.csv' WITH CSV HEADER;

-- COPY with SQL (server-side)
COPY users TO '/tmp/users.csv' WITH CSV HEADER;
COPY users FROM '/tmp/users.csv' WITH CSV HEADER;
```

---

## 20. Common Pitfalls and Best Practices

### Pitfalls to Avoid

1. **Using `SELECT *` in production** — always specify columns
2. **Not using parameterized queries** — SQL injection risk
3. **Missing indexes on foreign keys** — slow joins and deletes
4. **Using `OFFSET` for pagination on large tables** — use keyset pagination instead
5. **Not setting `statement_timeout`** — runaway queries
6. **Ignoring `VACUUM`/`ANALYZE`** — table bloat, bad query plans
7. **Using `SERIAL` in new projects** — prefer `GENERATED ALWAYS AS IDENTITY`
8. **Storing timestamps without timezone** — always use `TIMESTAMPTZ`

### Best Practices

```sql
-- Use identity columns instead of SERIAL (PG 10+)
CREATE TABLE products (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL
);

-- Always use TIMESTAMPTZ
CREATE TABLE events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Set statement timeout
SET statement_timeout = '30s';

-- Use connection pooling (PgBouncer, pgpool-II)
-- Never connect directly from application with 100+ connections

-- Index foreign keys
CREATE INDEX idx_orders_user_id ON orders (user_id);

-- Keyset pagination
SELECT * FROM products
WHERE id > :last_seen_id
ORDER BY id
LIMIT 20;
```

---

## 21. Essential Extensions

```sql
-- List installed extensions
SELECT * FROM pg_available_extensions WHERE installed_version IS NOT NULL;

-- Popular extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- Query statistics
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- Trigram similarity (fuzzy search)
CREATE EXTENSION IF NOT EXISTS "btree_gist";    -- GiST index for scalar types
CREATE EXTENSION IF NOT EXISTS "hstore";        -- Key-value pairs
CREATE EXTENSION IF NOT EXISTS "citext";        -- Case-insensitive text
CREATE EXTENSION IF NOT EXISTS "tablefunc";     -- Crosstab/pivot
CREATE EXTENSION IF NOT EXISTS "postgis";       -- Geospatial (separate install)

-- Example: fuzzy search with pg_trgm
CREATE INDEX idx_users_name_trgm ON users USING GIN (username gin_trgm_ops);
SELECT username, similarity(username, 'alce') AS sim
FROM users
WHERE username % 'alce'  -- similarity threshold
ORDER BY sim DESC;
```

---

This guide covers the foundational knowledge needed to work effectively with PostgreSQL. For deeper exploration, refer to the official PostgreSQL documentation at https://www.postgresql.org/docs/current/ which remains the most authoritative and comprehensive resource.