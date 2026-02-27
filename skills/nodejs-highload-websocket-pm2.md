Node.js Express application architecture for 5000+ concurrent users with WebSocket real-time, PM2 cluster deployment, and production optimization — without Redis.

# Node.js High-Load Architecture: Express + WebSocket + PM2

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [PM2 Cluster Mode Setup](#pm2-cluster-mode)
3. [Express Optimizations for High Load](#express-optimizations)
4. [Socket.io Integration with PM2 Cluster](#socketio-pm2-cluster)
5. [WebSocket Without Redis — Sticky Sessions](#websocket-without-redis)
6. [In-Memory Caching Without Redis](#in-memory-caching)
7. [Rate Limiting Without Redis](#rate-limiting-without-redis)
8. [Real-Time Event Broadcasting](#real-time-broadcasting)
9. [Graceful Shutdown and Zero-Downtime Reload](#graceful-shutdown)
10. [Nginx Reverse Proxy for WebSocket + HTTP](#nginx-config)
11. [Health Checks and Monitoring](#health-monitoring)
12. [Error Recovery and Resilience](#error-recovery)
13. [Competition Platform Real-Time Patterns](#competition-realtime)
14. [Production Deployment Checklist](#deployment-checklist)
15. [PM2 ecosystem.config.js Complete Template](#pm2-ecosystem)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │               Nginx                      │
                    │  - SSL termination                       │
                    │  - Static file serving (Vue SPA)         │
                    │  - Reverse proxy to Node.js             │
                    │  - ip_hash for sticky sessions           │
                    │  - Gzip / Brotli compression            │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │            PM2 Cluster                    │
                    │                                          │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
                    │  │ Worker 0 │ │ Worker 1 │ │ Worker 2 │ │
                    │  │ Express  │ │ Express  │ │ Express  │ │
                    │  │ Socket.io│ │ Socket.io│ │ Socket.io│ │
                    │  │ DB Pool  │ │ DB Pool  │ │ DB Pool  │ │
                    │  └──────────┘ └──────────┘ └──────────┘ │
                    │                                          │
                    │  IPC (process.send) for cross-worker     │
                    │  broadcasts (no Redis needed)            │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  PostgreSQL (via PgBouncer or direct)    │
                    │  Connection pool per worker              │
                    └─────────────────────────────────────────┘
```

---

## PM2 Cluster Mode Setup

### ecosystem.config.js — Production Template

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'competition-api',
      script: './dist/server.js',   // compiled JS entry point
      instances: 'max',             // use all CPU cores
      exec_mode: 'cluster',         // cluster mode for load balancing

      // Environment
      env_production: {
        NODE_ENV: 'production',
        PORT: 3000,
      },

      // Memory management
      max_memory_restart: '500M',   // restart worker if exceeds 500MB
      node_args: [
        '--max-old-space-size=512', // V8 heap limit per worker
      ],

      // Logging
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS Z',
      error_file: './logs/pm2-error.log',
      out_file: './logs/pm2-out.log',
      merge_logs: true,             // merge logs from all workers into one file
      log_type: 'json',

      // Auto-restart
      watch: false,                 // NEVER watch in production
      max_restarts: 15,             // max restarts in restart_delay window
      min_uptime: 5000,             // consider started after 5s uptime
      restart_delay: 4000,          // wait 4s between restarts
      autorestart: true,
      exp_backoff_restart_delay: 100, // exponential backoff on repeated crashes

      // Graceful shutdown
      kill_timeout: 10000,          // 10s to finish pending requests
      listen_timeout: 8000,         // 8s for new worker to signal ready
      shutdown_with_message: true,  // send 'shutdown' message before SIGINT
      wait_ready: true,             // wait for process.send('ready') before routing traffic

      // Cluster settings
      instance_var: 'INSTANCE_ID', // env var for worker ID

      // Source maps for error stacks
      source_map_support: true,
    },
  ],
};
```

### PM2 Commands

```bash
# Start in production
pm2 start ecosystem.config.js --env production

# Zero-downtime reload (graceful restart, one worker at a time)
pm2 reload competition-api

# Hard restart (drops connections)
pm2 restart competition-api

# Monitor
pm2 monit
pm2 status
pm2 logs competition-api --lines 100

# Save process list (auto-start on reboot)
pm2 save
pm2 startup

# Scale up/down
pm2 scale competition-api +2   # add 2 more workers
pm2 scale competition-api 4    # set to exactly 4 workers
```

---

## Express Optimizations for High Load

### server.js — Optimized Entry Point

```javascript
// server.js
require('dotenv').config();
const http = require('http');
const app = require('./app');
const { initWebSocket } = require('./websocket');
const { connectDB } = require('./config/database');
const logger = require('./utils/logger');

const PORT = process.env.PORT || 3000;

async function startServer() {
  // Connect database
  await connectDB();

  // Create HTTP server (needed for Socket.io)
  const server = http.createServer(app);

  // Initialize WebSocket
  initWebSocket(server);

  server.listen(PORT, () => {
    logger.info(`Worker ${process.pid} listening on port ${PORT}`);

    // Signal PM2 that this worker is ready
    if (process.send) {
      process.send('ready');
    }
  });

  // Keep-alive tuning for reverse proxy
  server.keepAliveTimeout = 65000;    // must be > Nginx proxy_read_timeout
  server.headersTimeout = 66000;      // must be > keepAliveTimeout
  server.requestTimeout = 30000;      // max time for entire request
  server.timeout = 120000;            // socket timeout (120s for long-polling fallback)

  // Graceful shutdown
  async function gracefulShutdown(signal) {
    logger.info(`${signal} received. Starting graceful shutdown...`);

    // Stop accepting new connections
    server.close(async () => {
      logger.info('HTTP server closed');

      try {
        // Close database connections
        const { sequelize } = require('./models');
        await sequelize.close();
        logger.info('Database connections closed');
      } catch (err) {
        logger.error('Error during shutdown:', err);
      }

      process.exit(0);
    });

    // Force shutdown after 10s
    setTimeout(() => {
      logger.error('Forced shutdown after timeout');
      process.exit(1);
    }, 10000);
  }

  // PM2 sends 'shutdown' message before SIGINT
  process.on('message', (msg) => {
    if (msg === 'shutdown') {
      gracefulShutdown('PM2_SHUTDOWN');
    }
  });

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));
}

// Catch startup errors
process.on('uncaughtException', (err) => {
  logger.error('Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (err) => {
  logger.error('Unhandled Rejection:', err);
  process.exit(1);
});

startServer().catch((err) => {
  logger.error('Failed to start server:', err);
  process.exit(1);
});
```

### app.js — Express Tuning

```javascript
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const hpp = require('hpp');

const app = express();

// Trust proxy (behind Nginx)
app.set('trust proxy', 1);

// Disable ETag for API responses (reduces 304 overhead for dynamic data)
app.set('etag', false);

// Remove X-Powered-By
app.disable('x-powered-by');

// Security
app.use(helmet({
  contentSecurityPolicy: false, // SPA handles its own CSP
}));

// CORS
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:5173'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  maxAge: 86400,
}));

// HPP — prevent HTTP parameter pollution
app.use(hpp());

// Body parsing with strict limits
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: false, limit: '10kb' }));

// Compression (if not handled by Nginx)
app.use(compression({
  level: 6,
  threshold: 1024,
  filter: (req, res) => {
    if (req.headers['x-no-compression']) return false;
    return compression.filter(req, res);
  },
}));

// Routes
app.use('/api/v1', require('./routes'));

// Health check (PM2 + Nginx + monitoring)
app.get('/health', async (req, res) => {
  try {
    const { sequelize } = require('./models');
    await sequelize.query('SELECT 1');
    res.json({
      status: 'ok',
      pid: process.pid,
      uptime: Math.floor(process.uptime()),
      memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    res.status(503).json({ status: 'error', message: 'Database unavailable' });
  }
});

// 404
app.all('*', (req, res) => {
  res.status(404).json({ status: 'error', message: `Route ${req.originalUrl} not found` });
});

// Error handler
app.use(require('./middleware/errorHandler'));

module.exports = app;
```

---

## Socket.io Integration with PM2 Cluster

### The Problem

PM2 cluster mode runs multiple Node.js processes. WebSocket connections are stateful — a client connected to Worker 0 can't receive messages broadcast from Worker 1.

### Solution Without Redis: IPC + Sticky Sessions

Two things are needed:
1. **Sticky sessions** — ensure a client always connects to the same worker
2. **IPC broadcasting** — when one worker needs to broadcast to clients on other workers

### WebSocket Setup

```javascript
// websocket.js
const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');
const logger = require('./utils/logger');

let io;

function initWebSocket(httpServer) {
  io = new Server(httpServer, {
    cors: {
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:5173'],
      credentials: true,
    },

    // Transport configuration
    transports: ['websocket', 'polling'],    // prefer websocket
    allowUpgrades: true,
    pingInterval: 25000,                      // heartbeat every 25s
    pingTimeout: 20000,                       // disconnect after 20s no pong
    maxHttpBufferSize: 1e6,                   // 1MB max message size

    // Path
    path: '/socket.io/',

    // Connection state recovery (Socket.io v4.6+)
    connectionStateRecovery: {
      maxDisconnectionDuration: 2 * 60 * 1000,  // 2 minutes
      skipMiddlewares: true,
    },
  });

  // Authentication middleware
  io.use(async (socket, next) => {
    try {
      const token = socket.handshake.auth?.token || socket.handshake.headers?.authorization?.split(' ')[1];

      if (!token) {
        return next(new Error('Authentication required'));
      }

      const decoded = jwt.verify(token, process.env.JWT_SECRET);

      // Attach user to socket
      socket.userId = decoded.id;
      socket.userRole = decoded.role;

      next();
    } catch (err) {
      next(new Error('Invalid token'));
    }
  });

  // Connection handler
  io.on('connection', (socket) => {
    logger.info(`User ${socket.userId} connected (worker ${process.pid})`);

    // Join user-specific room
    socket.join(`user:${socket.userId}`);

    // Join competition rooms as needed
    socket.on('join:competition', (competitionId) => {
      socket.join(`competition:${competitionId}`);
      logger.debug(`User ${socket.userId} joined competition:${competitionId}`);
    });

    socket.on('leave:competition', (competitionId) => {
      socket.leave(`competition:${competitionId}`);
    });

    // Handle client events
    socket.on('submit:answer', async (data, callback) => {
      try {
        // Process answer submission
        const result = await processAnswer(socket.userId, data);

        // Acknowledge to sender
        callback({ success: true, result });

        // Broadcast to competition room (this worker's clients only!)
        socket.to(`competition:${data.competitionId}`).emit('score:updated', {
          userId: socket.userId,
          score: result.newScore,
        });

        // Broadcast to ALL workers via IPC
        broadcastToAllWorkers('score:updated', {
          room: `competition:${data.competitionId}`,
          event: 'score:updated',
          data: { userId: socket.userId, score: result.newScore },
          excludeSocketId: socket.id,
        });
      } catch (err) {
        callback({ success: false, error: err.message });
      }
    });

    socket.on('disconnect', (reason) => {
      logger.info(`User ${socket.userId} disconnected: ${reason}`);
    });

    socket.on('error', (err) => {
      logger.error(`Socket error for user ${socket.userId}:`, err);
    });
  });

  // Listen for IPC messages from other workers
  if (process.send) {
    process.on('message', (msg) => {
      if (msg.type === 'ws:broadcast') {
        const { room, event, data, excludeSocketId } = msg.payload;
        if (room) {
          io.to(room).except(excludeSocketId || '').emit(event, data);
        } else {
          io.emit(event, data);
        }
      }
    });
  }

  return io;
}

// Broadcast to all PM2 workers via IPC
function broadcastToAllWorkers(event, payload) {
  if (process.send) {
    process.send({
      type: 'ws:broadcast:request',
      payload,
    });
  }
}

// Get Socket.io instance
function getIO() {
  if (!io) throw new Error('Socket.io not initialized');
  return io;
}

// Emit to specific user across all workers
function emitToUser(userId, event, data) {
  if (io) {
    io.to(`user:${userId}`).emit(event, data);
  }
  broadcastToAllWorkers('ws:broadcast', {
    room: `user:${userId}`,
    event,
    data,
  });
}

// Emit to competition room across all workers
function emitToCompetition(competitionId, event, data) {
  if (io) {
    io.to(`competition:${competitionId}`).emit(event, data);
  }
  broadcastToAllWorkers('ws:broadcast', {
    room: `competition:${competitionId}`,
    event,
    data,
  });
}

module.exports = { initWebSocket, getIO, emitToUser, emitToCompetition, broadcastToAllWorkers };
```

### PM2 IPC Relay Script

Create a custom PM2 module or use the built-in `pm2` IPC:

```javascript
// ipc-relay.js — Run as a PM2 module or integrate into ecosystem
// This script relays IPC messages between PM2 workers

const pm2 = require('pm2');

pm2.connect(() => {
  pm2.launchBus((err, bus) => {
    if (err) {
      console.error('PM2 bus error:', err);
      return;
    }

    bus.on('ws:broadcast:request', (packet) => {
      // Relay to all workers
      pm2.list((err, list) => {
        if (err) return;

        list
          .filter((proc) => proc.name === 'competition-api' && proc.pm2_env.status === 'online')
          .forEach((proc) => {
            pm2.sendDataToProcessId(proc.pm_id, {
              type: 'ws:broadcast',
              data: {},
              payload: packet.data.payload,
              topic: 'ws:broadcast',
            }, (err) => {
              if (err) console.error('IPC relay error:', err);
            });
          });
      });
    });
  });
});
```

### Alternative: Simple Worker-to-Worker IPC (No extra process)

```javascript
// In server.js — simpler approach using Node.js cluster IPC
const cluster = require('cluster');

if (cluster.isWorker) {
  // Listen for messages from master
  process.on('message', (msg) => {
    if (msg.type === 'ws:broadcast') {
      const io = require('./websocket').getIO();
      const { room, event, data } = msg.payload;
      if (room) {
        io.to(room).emit(event, data);
      } else {
        io.emit(event, data);
      }
    }
  });
}

// When a worker wants to broadcast to all:
function broadcastToCluster(payload) {
  // Send to master, which relays to all workers
  process.send({
    type: 'ws:broadcast:relay',
    payload,
    fromPid: process.pid,
  });
}

// PM2 automatically handles the master process relaying
// In ecosystem.config.js, PM2 cluster master forwards messages by default
```

---

## WebSocket Without Redis — Sticky Sessions

### Nginx Sticky Sessions Configuration

```nginx
upstream nodejs_cluster {
    # ip_hash ensures the same client IP always goes to the same worker
    ip_hash;

    server 127.0.0.1:3000;
    # PM2 cluster mode — all workers share port 3000
    # Nginx ip_hash ensures sticky connections

    keepalive 64;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_comp_level 5;
    gzip_min_length 256;
    gzip_types
      application/json
      application/javascript
      text/css
      text/plain
      text/xml
      application/xml;

    # API proxy
    location /api/ {
        proxy_pass http://nodejs_cluster;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 60s;

        # Buffer settings for API
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # WebSocket proxy — critical configuration
    location /socket.io/ {
        proxy_pass http://nodejs_cluster;
        proxy_http_version 1.1;

        # WebSocket upgrade headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Long timeouts for WebSocket connections
        proxy_connect_timeout 10s;
        proxy_send_timeout 86400s;    # 24 hours — keep WS alive
        proxy_read_timeout 86400s;    # 24 hours

        # Don't buffer WebSocket messages
        proxy_buffering off;
        proxy_cache off;

        # TCP keepalive for WebSocket
        proxy_socket_keepalive on;
    }

    # Serve Vue SPA static files
    location / {
        root /var/www/competition-app/dist;
        index index.html;
        try_files $uri $uri/ /index.html;

        # Cache static assets aggressively
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2|woff|ttf)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## In-Memory Caching Without Redis

Since there's no Redis, use application-level caching with `node-cache` or a simple Map:

```javascript
// utils/cache.js
const NodeCache = require('node-cache');

// Per-worker cache (each PM2 worker has its own cache)
const cache = new NodeCache({
  stdTTL: 60,              // default TTL: 60 seconds
  checkperiod: 120,        // cleanup check every 2 minutes
  useClones: false,        // don't clone objects (faster, but careful with mutation)
  maxKeys: 10000,          // max entries to prevent memory leak
});

// Typed cache helpers
const cacheService = {
  get(key) {
    return cache.get(key);
  },

  set(key, value, ttl) {
    return cache.set(key, value, ttl);
  },

  del(key) {
    return cache.del(key);
  },

  // Cache-aside pattern
  async getOrSet(key, fetchFn, ttl = 60) {
    const cached = cache.get(key);
    if (cached !== undefined) return cached;

    const value = await fetchFn();
    cache.set(key, value, ttl);
    return value;
  },

  // Invalidate by prefix pattern
  invalidatePrefix(prefix) {
    const keys = cache.keys().filter(k => k.startsWith(prefix));
    cache.del(keys);
  },

  stats() {
    return cache.getStats();
  },

  flush() {
    cache.flushAll();
  },
};

module.exports = cacheService;
```

### Usage in Services

```javascript
const cache = require('../utils/cache');

class CompetitionService {
  // Cache leaderboard for 10 seconds (gets updated frequently)
  async getLeaderboard(competitionId, page = 1, limit = 50) {
    const cacheKey = `leaderboard:${competitionId}:${page}:${limit}`;

    return cache.getOrSet(cacheKey, async () => {
      const scores = await UserScore.findAll({
        where: { competitionId },
        include: [{
          model: User,
          as: 'user',
          attributes: ['id', 'username', 'avatarUrl'],
        }],
        order: [['score', 'DESC']],
        limit,
        offset: (page - 1) * limit,
        raw: true,
        nest: true,
      });

      return scores;
    }, 10); // 10 second TTL
  }

  // Invalidate cache when score changes
  async updateScore(competitionId, userId, scoreChange) {
    await sequelize.transaction(async (t) => {
      await UserScore.increment('score', {
        by: scoreChange,
        where: { competitionId, userId },
        transaction: t,
      });
    });

    // Invalidate all leaderboard pages for this competition
    cache.invalidatePrefix(`leaderboard:${competitionId}`);
  }

  // Cache competition details for 5 minutes (rarely changes)
  async getCompetition(id) {
    return cache.getOrSet(`competition:${id}`, async () => {
      return Competition.findByPk(id, {
        include: [
          { model: User, as: 'creator', attributes: ['id', 'username'] },
        ],
      });
    }, 300); // 5 minute TTL
  }
}
```

---

## Rate Limiting Without Redis

```javascript
// middleware/rateLimiter.js
const rateLimit = require('express-rate-limit');

// In-memory store (per worker — acceptable without Redis for moderate load)
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,   // 15 minutes
  max: 1000,                   // 1000 requests per window per IP
  message: { status: 'error', message: 'Too many requests' },
  standardHeaders: true,
  legacyHeaders: false,
  // No store specified = uses built-in MemoryStore (per worker)
  // With PM2 cluster, each worker tracks independently
  // Effective limit = max × number_of_workers (e.g., 1000 × 4 = 4000)
  // This is acceptable for most cases
});

const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,   // 1 hour
  max: 10,                     // 10 login attempts per hour
  message: { status: 'error', message: 'Too many login attempts' },
  skipSuccessfulRequests: true,
});

const submitLimiter = rateLimit({
  windowMs: 1000,              // 1 second
  max: 5,                      // 5 submissions per second per IP
  message: { status: 'error', message: 'Submitting too fast' },
});

module.exports = { apiLimiter, authLimiter, submitLimiter };
```

---

## Real-Time Event Broadcasting

### Broadcasting from Controllers/Services

```javascript
// controllers/competitionController.js
const { emitToCompetition, emitToUser } = require('../websocket');

const competitionController = {
  // When a match finishes
  async finishMatch(req, res) {
    const { matchId } = req.params;
    const match = await MatchService.finishMatch(matchId);

    // Broadcast to everyone watching this competition
    emitToCompetition(match.competitionId, 'match:finished', {
      matchId: match.id,
      winnerId: match.winnerId,
      score: match.finalScore,
    });

    // Notify specific players
    emitToUser(match.player1Id, 'match:result', {
      matchId: match.id,
      result: match.player1Id === match.winnerId ? 'win' : 'loss',
    });
    emitToUser(match.player2Id, 'match:result', {
      matchId: match.id,
      result: match.player2Id === match.winnerId ? 'win' : 'loss',
    });

    res.json({ status: 'success', data: match });
  },

  // When leaderboard updates
  async submitScore(req, res) {
    const result = await ScoreService.submit(req.user.id, req.body);

    // Broadcast leaderboard update
    emitToCompetition(result.competitionId, 'leaderboard:update', {
      userId: req.user.id,
      username: req.user.username,
      newScore: result.score,
      rank: result.rank,
    });

    res.json({ status: 'success', data: result });
  },

  // Timer/countdown events
  async startCompetition(req, res) {
    const competition = await CompetitionService.start(req.params.id);

    emitToCompetition(competition.id, 'competition:started', {
      competitionId: competition.id,
      startedAt: competition.startedAt,
      endsAt: competition.endsAt,
    });

    // Schedule end event
    const duration = competition.endsAt - competition.startedAt;
    setTimeout(() => {
      emitToCompetition(competition.id, 'competition:ended', {
        competitionId: competition.id,
      });
    }, duration);

    res.json({ status: 'success', data: competition });
  },
};
```

### Client-Side Socket.io (Vue 3)

```javascript
// composables/useSocket.js
import { ref, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client';

const socket = ref(null);
const isConnected = ref(false);
const connectionError = ref(null);

export function useSocket() {
  function connect(token) {
    if (socket.value?.connected) return;

    socket.value = io(import.meta.env.VITE_API_URL || '', {
      path: '/socket.io/',
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
      timeout: 10000,
    });

    socket.value.on('connect', () => {
      isConnected.value = true;
      connectionError.value = null;
      console.log('WebSocket connected');
    });

    socket.value.on('disconnect', (reason) => {
      isConnected.value = false;
      console.log('WebSocket disconnected:', reason);
    });

    socket.value.on('connect_error', (err) => {
      connectionError.value = err.message;
      console.error('WebSocket error:', err.message);
    });
  }

  function disconnect() {
    socket.value?.disconnect();
    socket.value = null;
    isConnected.value = false;
  }

  function emit(event, data, callback) {
    socket.value?.emit(event, data, callback);
  }

  function on(event, handler) {
    socket.value?.on(event, handler);
  }

  function off(event, handler) {
    socket.value?.off(event, handler);
  }

  // Join a competition room
  function joinCompetition(competitionId) {
    emit('join:competition', competitionId);
  }

  function leaveCompetition(competitionId) {
    emit('leave:competition', competitionId);
  }

  return {
    socket,
    isConnected,
    connectionError,
    connect,
    disconnect,
    emit,
    on,
    off,
    joinCompetition,
    leaveCompetition,
  };
}
```

```vue
<!-- CompetitionLive.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useSocket } from '@/composables/useSocket';
import { useAuth } from '@/composables/useAuth';

const props = defineProps({ competitionId: String });

const { on, off, joinCompetition, leaveCompetition, isConnected } = useSocket();
const leaderboard = ref([]);
const liveEvents = ref([]);

onMounted(() => {
  joinCompetition(props.competitionId);

  on('leaderboard:update', (data) => {
    // Update leaderboard entry
    const idx = leaderboard.value.findIndex(e => e.userId === data.userId);
    if (idx >= 0) {
      leaderboard.value[idx] = { ...leaderboard.value[idx], ...data };
    } else {
      leaderboard.value.push(data);
    }
    // Re-sort
    leaderboard.value.sort((a, b) => b.newScore - a.newScore);
  });

  on('match:finished', (data) => {
    liveEvents.value.unshift({
      type: 'match',
      ...data,
      timestamp: Date.now(),
    });
    // Keep only last 50 events
    if (liveEvents.value.length > 50) liveEvents.value.pop();
  });

  on('competition:ended', () => {
    // Show results modal, stop timers, etc.
  });
});

onUnmounted(() => {
  leaveCompetition(props.competitionId);
  off('leaderboard:update');
  off('match:finished');
  off('competition:ended');
});
</script>
```

---

## Health Checks and Monitoring

```javascript
// middleware/requestMetrics.js
const metrics = {
  totalRequests: 0,
  activeRequests: 0,
  errors: 0,
  avgResponseTime: 0,
  _responseTimes: [],
};

function requestMetrics(req, res, next) {
  metrics.totalRequests++;
  metrics.activeRequests++;

  const start = process.hrtime.bigint();

  res.on('finish', () => {
    metrics.activeRequests--;

    const duration = Number(process.hrtime.bigint() - start) / 1e6; // ms

    if (res.statusCode >= 500) metrics.errors++;

    // Rolling average (last 1000 requests)
    metrics._responseTimes.push(duration);
    if (metrics._responseTimes.length > 1000) metrics._responseTimes.shift();
    metrics.avgResponseTime = metrics._responseTimes.reduce((a, b) => a + b, 0) / metrics._responseTimes.length;
  });

  next();
}

function getMetrics() {
  return {
    pid: process.pid,
    uptime: Math.floor(process.uptime()),
    memory: {
      heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
      heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
      rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
    },
    requests: {
      total: metrics.totalRequests,
      active: metrics.activeRequests,
      errors: metrics.errors,
      avgResponseTimeMs: Math.round(metrics.avgResponseTime * 100) / 100,
    },
  };
}

module.exports = { requestMetrics, getMetrics };
```

---

## Production Deployment Checklist

```bash
# 1. Build
npm run build          # TypeScript → JavaScript or Vite build for frontend

# 2. Install production dependencies only
npm ci --production

# 3. Set environment variables
export NODE_ENV=production
export PORT=3000
export DATABASE_URL=postgres://...
export JWT_SECRET=...
export ALLOWED_ORIGINS=https://myapp.com

# 4. Run migrations
npx sequelize-cli db:migrate --env production

# 5. Start with PM2
pm2 start ecosystem.config.js --env production

# 6. Save PM2 process list
pm2 save

# 7. Setup PM2 startup (auto-start on reboot)
pm2 startup

# 8. Verify
pm2 status
pm2 logs
curl http://localhost:3000/health

# 9. Nginx
sudo nginx -t && sudo systemctl reload nginx

# Zero-downtime deploy (CI/CD):
git pull
npm ci --production
npm run build
npx sequelize-cli db:migrate --env production
pm2 reload competition-api   # graceful reload, one worker at a time
```

---

This architecture supports 5000+ concurrent users with:
- **PM2 cluster** utilizing all CPU cores
- **WebSocket** real-time via Socket.io with IPC cross-worker broadcasting
- **Sticky sessions** via Nginx ip_hash (no Redis adapter needed)
- **In-memory caching** per worker with node-cache
- **PostgreSQL** as the single data store with optimized connection pooling
- **Graceful shutdown** for zero-downtime deployments