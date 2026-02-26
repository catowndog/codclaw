Comprehensive guide to building secure, performant, and production-ready Node.js Express applications including routing, middleware, CORS, security hardening, error handling, and best practices.

# Node.js Express — Complete Guide

## Table of Contents
1. [Overview & Installation](#overview--installation)
2. [Application Setup & Configuration](#application-setup--configuration)
3. [Routing In-Depth](#routing-in-depth)
4. [Middleware System](#middleware-system)
5. [Request & Response Objects](#request--response-objects)
6. [CORS — Cross-Origin Resource Sharing](#cors--cross-origin-resource-sharing)
7. [Security Hardening](#security-hardening)
8. [Authentication & Authorization](#authentication--authorization)
9. [Error Handling](#error-handling)
10. [Validation & Sanitization](#validation--sanitization)
11. [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
12. [File Uploads](#file-uploads)
13. [Performance Optimization](#performance-optimization)
14. [Logging & Monitoring](#logging--monitoring)
15. [Testing](#testing)
16. [Production Deployment](#production-deployment)
17. [Common Pitfalls & Anti-Patterns](#common-pitfalls--anti-patterns)

---

## Overview & Installation

Express is a minimal, flexible Node.js web application framework that provides a robust set of features for building web and mobile applications, APIs, and microservices.

### Installation

```bash
# Initialize project
mkdir my-app && cd my-app
npm init -y

# Install Express
npm install express

# Common companion packages
npm install helmet cors express-rate-limit compression morgan dotenv
npm install express-validator cookie-parser hpp

# Dev dependencies
npm install -D nodemon typescript @types/express @types/node
```

### Minimal Application

```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ message: 'Hello, World!' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

---

## Application Setup & Configuration

### Production-Ready Application Structure

```
project/
├── src/
│   ├── config/
│   │   ├── index.js          # Central config
│   │   ├── database.js       # DB connection
│   │   └── cors.js           # CORS config
│   ├── controllers/
│   │   └── userController.js
│   ├── middleware/
│   │   ├── auth.js
│   │   ├── errorHandler.js
│   │   ├── validate.js
│   │   └── rateLimiter.js
│   ├── models/
│   │   └── User.js
│   ├── routes/
│   │   ├── index.js
│   │   └── userRoutes.js
│   ├── services/
│   │   └── userService.js
│   ├── utils/
│   │   ├── AppError.js
│   │   └── catchAsync.js
│   └── app.js                # Express app setup
├── tests/
├── .env
├── .env.example
├── package.json
└── server.js                 # Entry point
```

### Comprehensive App Setup (app.js)

```javascript
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const hpp = require('hpp');
const cookieParser = require('cookie-parser');
const path = require('path');

const AppError = require('./utils/AppError');
const globalErrorHandler = require('./middleware/errorHandler');
const routes = require('./routes');

const app = express();

// ======================
// 1. SECURITY MIDDLEWARE
// ======================

// Set security HTTP headers
app.use(helmet());

// CORS
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  exposedHeaders: ['X-Total-Count', 'Content-Range'],
  maxAge: 86400, // 24 hours preflight cache
}));

// Rate limiting
const limiter = rateLimit({
  max: 100,                    // 100 requests
  windowMs: 15 * 60 * 1000,   // per 15 minutes
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api', limiter);

// Prevent HTTP Parameter Pollution
app.use(hpp({
  whitelist: ['sort', 'fields', 'page', 'limit', 'filter']
}));

// ======================
// 2. BODY PARSING
// ======================

// Parse JSON bodies (limit size to prevent large payload attacks)
app.use(express.json({ limit: '10kb' }));

// Parse URL-encoded bodies
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Parse cookies
app.use(cookieParser());

// ======================
// 3. PERFORMANCE
// ======================

// Compress responses
app.use(compression());

// ======================
// 4. LOGGING
// ======================

if (process.env.NODE_ENV === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// ======================
// 5. STATIC FILES
// ======================

app.use(express.static(path.join(__dirname, 'public'), {
  maxAge: '1d',       // Cache static files for 1 day
  etag: true,
  lastModified: true,
}));

// ======================
// 6. TRUST PROXY (for reverse proxies like Nginx)
// ======================

app.set('trust proxy', 1); // Trust first proxy

// ======================
// 7. ROUTES
// ======================

app.use('/api/v1', routes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// ======================
// 8. 404 HANDLER
// ======================

app.all('*', (req, res, next) => {
  next(new AppError(`Cannot find ${req.originalUrl} on this server`, 404));
});

// ======================
// 9. GLOBAL ERROR HANDLER
// ======================

app.use(globalErrorHandler);

module.exports = app;
```

### Server Entry Point (server.js)

```javascript
require('dotenv').config();
const app = require('./src/app');
const { connectDB } = require('./src/config/database');

const PORT = process.env.PORT || 3000;

// Handle uncaught exceptions (synchronous errors)
process.on('uncaughtException', (err) => {
  console.error('UNCAUGHT EXCEPTION! Shutting down...');
  console.error(err.name, err.message, err.stack);
  process.exit(1);
});

const startServer = async () => {
  // Connect to database
  await connectDB();

  const server = app.listen(PORT, () => {
    console.log(`Server running in ${process.env.NODE_ENV} mode on port ${PORT}`);
  });

  // Handle unhandled promise rejections (async errors)
  process.on('unhandledRejection', (err) => {
    console.error('UNHANDLED REJECTION! Shutting down...');
    console.error(err.name, err.message);
    server.close(() => {
      process.exit(1);
    });
  });

  // Graceful shutdown on SIGTERM
  process.on('SIGTERM', () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    server.close(() => {
      console.log('Process terminated.');
    });
  });
};

startServer();
```

### Environment Configuration

```bash
# .env
NODE_ENV=development
PORT=3000

# Database
DATABASE_URL=mongodb://localhost:27017/myapp

# JWT
JWT_SECRET=your-super-secret-key-change-in-production-min-32-chars
JWT_EXPIRES_IN=90d
JWT_COOKIE_EXPIRES_IN=90

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Rate Limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=15
```

---

## Routing In-Depth

### Basic Routing

```javascript
// All HTTP methods
app.get('/users', handler);       // Read
app.post('/users', handler);      // Create
app.put('/users/:id', handler);   // Full update
app.patch('/users/:id', handler); // Partial update
app.delete('/users/:id', handler);// Delete
app.options('/users', handler);   // Preflight
app.head('/users', handler);      // Headers only
app.all('/users', handler);       // All methods
```

### Router Module Pattern

```javascript
// routes/userRoutes.js
const express = require('express');
const router = express.Router();
const userController = require('../controllers/userController');
const { protect, restrictTo } = require('../middleware/auth');
const { validateUser, validateParams } = require('../middleware/validate');

// Public routes
router.post('/register', validateUser('register'), userController.register);
router.post('/login', validateUser('login'), userController.login);
router.post('/forgot-password', userController.forgotPassword);
router.patch('/reset-password/:token', userController.resetPassword);

// All routes after this line require authentication
router.use(protect);

router.get('/me', userController.getMe);
router.patch('/update-me', userController.updateMe);
router.delete('/delete-me', userController.deleteMe);
router.patch('/update-password', userController.updatePassword);

// Admin only routes
router.use(restrictTo('admin'));

router
  .route('/')
  .get(userController.getAllUsers)
  .post(validateUser('create'), userController.createUser);

router
  .route('/:id')
  .get(validateParams, userController.getUser)
  .patch(validateUser('update'), userController.updateUser)
  .delete(userController.deleteUser);

module.exports = router;
```

```javascript
// routes/index.js
const express = require('express');
const router = express.Router();

const userRoutes = require('./userRoutes');
const productRoutes = require('./productRoutes');
const orderRoutes = require('./orderRoutes');

router.use('/users', userRoutes);
router.use('/products', productRoutes);
router.use('/orders', orderRoutes);

module.exports = router;
```

### Route Parameters & Query Strings

```javascript
// Route parameters
router.get('/users/:id', (req, res) => {
  console.log(req.params.id); // e.g., "123"
});

// Optional parameters
router.get('/posts/:year/:month?', (req, res) => {
  console.log(req.params.year);   // required
  console.log(req.params.month);  // optional, undefined if not provided
});

// Regex constraints on params
router.get('/users/:id(\\d+)', (req, res) => {
  // Only matches numeric IDs
});

// Query strings: /api/users?page=2&limit=10&sort=-createdAt
router.get('/users', (req, res) => {
  const { page = 1, limit = 10, sort = '-createdAt', fields, filter } = req.query;
  // Use these for pagination, sorting, field selection
});

// Parameter middleware — runs for any route with :id
router.param('id', (req, res, next, id) => {
  // Validate ID format, preload resource, etc.
  if (!id.match(/^[0-9a-fA-F]{24}$/)) {
    return next(new AppError('Invalid ID format', 400));
  }
  next();
});
```

---

## Middleware System

Middleware functions execute in the order they are defined. Each has access to `req`, `res`, and `next`.

### Types of Middleware

```javascript
// 1. Application-level middleware
app.use((req, res, next) => {
  req.requestTime = new Date().toISOString();
  next();
});

// 2. Router-level middleware
router.use((req, res, next) => {
  console.log('Router-specific middleware');
  next();
});

// 3. Error-handling middleware (4 parameters)
app.use((err, req, res, next) => {
  res.status(err.statusCode || 500).json({ error: err.message });
});

// 4. Built-in middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

// 5. Third-party middleware
app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
```

### Custom Middleware Examples

```javascript
// Request logger
const requestLogger = (req, res, next) => {
  const start = Date.now();
  
  // After response finishes
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.originalUrl} ${res.statusCode} - ${duration}ms`);
  });
  
  next();
};

// Async middleware wrapper
const catchAsync = (fn) => {
  return (req, res, next) => {
    fn(req, res, next).catch(next);
  };
};

// Usage:
router.get('/users', catchAsync(async (req, res, next) => {
  const users = await User.find();
  res.json({ status: 'success', data: users });
}));

// Request ID middleware
const { v4: uuidv4 } = require('uuid');

const addRequestId = (req, res, next) => {
  req.id = req.headers['x-request-id'] || uuidv4();
  res.setHeader('X-Request-Id', req.id);
  next();
};

// Response time header
const responseTime = (req, res, next) => {
  const start = process.hrtime.bigint();
  res.on('finish', () => {
    const end = process.hrtime.bigint();
    const ms = Number(end - start) / 1e6;
    res.setHeader('X-Response-Time', `${ms.toFixed(2)}ms`);
  });
  next();
};

// Conditional middleware
const conditionalMiddleware = (condition, middleware) => {
  return (req, res, next) => {
    if (condition(req)) {
      return middleware(req, res, next);
    }
    next();
  };
};

// Usage:
app.use(conditionalMiddleware(
  (req) => req.path.startsWith('/api'),
  express.json()
));
```

---

## Request & Response Objects

### Request Object (`req`)

```javascript
router.post('/example/:id', (req, res) => {
  // URL & Path
  req.originalUrl;   // '/api/v1/example/123?foo=bar'
  req.baseUrl;       // '/api/v1'
  req.path;          // '/example/123'
  req.url;           // '/example/123?foo=bar'
  req.method;        // 'POST'
  req.protocol;      // 'https'
  req.hostname;      // 'example.com'
  req.ip;            // '::1' or '127.0.0.1'
  req.ips;           // ['client', 'proxy1', 'proxy2'] (when trust proxy)
  req.secure;        // true if HTTPS
  req.xhr;           // true if X-Requested-With: XMLHttpRequest
  req.subdomains;    // ['api'] for api.example.com

  // Parameters
  req.params;        // { id: '123' }
  req.query;         // { foo: 'bar' }
  req.body;          // parsed body (requires body parser)

  // Headers
  req.headers;                    // all headers (lowercase keys)
  req.get('Content-Type');        // specific header
  req.get('Authorization');       // 'Bearer token...'
  req.is('json');                 // check Content-Type

  // Cookies (requires cookie-parser)
  req.cookies;         // unsigned cookies
  req.signedCookies;   // signed cookies

  // Accepts negotiation
  req.accepts('json');            // content negotiation
  req.accepts(['html', 'json']); // returns best match
});
```

### Response Object (`res`)

```javascript
router.get('/example', (req, res) => {
  // Status codes
  res.status(200);
  res.sendStatus(204); // sends status with default message

  // Send responses
  res.json({ key: 'value' });              // JSON
  res.send('text or buffer');               // auto-detect
  res.send(Buffer.from('binary'));          // binary
  res.end();                                // end without data

  // Headers
  res.set('X-Custom-Header', 'value');
  res.set({
    'X-Custom-Header': 'value',
    'X-Another': 'value2'
  });
  res.type('json');                         // sets Content-Type
  res.append('Set-Cookie', 'foo=bar');      // append to existing header

  // Redirects
  res.redirect('/new-url');                 // 302
  res.redirect(301, '/permanent-new-url');  // 301

  // Cookies
  res.cookie('name', 'value', {
    httpOnly: true,     // not accessible via JavaScript
    secure: true,       // HTTPS only
    sameSite: 'strict', // CSRF protection
    maxAge: 86400000,   // 1 day in ms
    signed: true,       // use cookie-parser secret
    path: '/',
    domain: '.example.com',
  });
  res.clearCookie('name');

  // File responses
  res.download('/path/to/file.pdf');
  res.sendFile('/absolute/path/to/file.html');
  res.attachment('filename.pdf'); // sets Content-Disposition

  // Render template
  res.render('template', { title: 'Page' });

  // Chaining
  res.status(201).json({ created: true });
});
```

### Standardized API Response Pattern

```javascript
// utils/apiResponse.js
class ApiResponse {
  static success(res, data, statusCode = 200, meta = {}) {
    const response = {
      status: 'success',
      ...meta,
      data,
    };
    return res.status(statusCode).json(response);
  }

  static created(res, data) {
    return this.success(res, data, 201);
  }

  static noContent(res) {
    return res.status(204).send();
  }

  static paginated(res, data, { page, limit, total }) {
    return this.success(res, data, 200, {
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        pages: Math.ceil(total / limit),
      },
    });
  }

  static error(res, message, statusCode = 500, errors = null) {
    const response = {
      status: 'error',
      message,
    };
    if (errors) response.errors = errors;
    return res.status(statusCode).json(response);
  }
}

module.exports = ApiResponse;
```

---

## CORS — Cross-Origin Resource Sharing

CORS is a browser security mechanism that restricts cross-origin HTTP requests. Express needs explicit CORS configuration to allow requests from different origins.

### How CORS Works

1. **Simple requests** (GET, POST with simple headers): Browser sends request directly with `Origin` header; server responds with `Access-Control-Allow-Origin`.
2. **Preflight requests** (PUT, DELETE, custom headers): Browser sends `OPTIONS` request first; if server allows, then actual request follows.

### Basic CORS Setup

```javascript
const cors = require('cors');

// Allow all origins (NOT recommended for production)
app.use(cors());

// Allow specific origin
app.use(cors({
  origin: 'https://example.com'
}));
```

### Advanced CORS Configuration

```javascript
// config/cors.js
const AppError = require('../utils/AppError');

const allowedOrigins = [
  'https://myapp.com',
  'https://www.myapp.com',
  'https://admin.myapp.com',
  'https://staging.myapp.com',
];

// Add localhost in development
if (process.env.NODE_ENV === 'development') {
  allowedOrigins.push(
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
  );
}

const corsOptions = {
  origin: function (origin, callback) {
    // Allow requests with no origin (mobile apps, curl, server-to-server)
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new AppError(`Origin ${origin} not allowed by CORS`, 403));
    }
  },

  // Allow credentials (cookies, authorization headers)
  credentials: true,

  // Allowed methods
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],

  // Allowed request headers
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'Accept',
    'Origin',
    'X-CSRF-Token',
  ],

  // Headers exposed to the client
  exposedHeaders: [
    'X-Total-Count',
    'Content-Range',
    'X-Request-Id',
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset',
  ],

  // Preflight cache duration (24 hours)
  maxAge: 86400,

  // Pass preflight response to next handler
  preflightContinue: false,

  // Return 204 for OPTIONS (some legacy browsers choke on 200)
  optionsSuccessStatus: 204,
};

module.exports = corsOptions;
```

### Per-Route CORS

```javascript
const cors = require('cors');

// Different CORS for different routes
const publicCors = cors({ origin: '*' });
const privateCors = cors({ origin: 'https://admin.myapp.com', credentials: true });

// Public API — anyone can access
app.use('/api/v1/public', publicCors, publicRoutes);

// Private API — only admin dashboard
app.use('/api/v1/admin', privateCors, adminRoutes);

// Specific route
router.get('/data', cors({ origin: 'https://specific-client.com' }), handler);
```

### Manual CORS Implementation (without cors package)

```javascript
app.use((req, res, next) => {
  const origin = req.headers.origin;
  
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Max-Age', '86400');
  res.setHeader('Access-Control-Expose-Headers', 'X-Total-Count');
  
  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.sendStatus(204);
  }
  
  next();
});
```

### Common CORS Issues & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| `Access-Control-Allow-Origin` missing | CORS not configured | Add `cors()` middleware |
| Credentials not sent | `credentials: true` missing | Set both server + client `credentials` |
| Custom header blocked | Header not in `allowedHeaders` | Add header to `allowedHeaders` |
| Preflight fails | OPTIONS handler missing/failing | Ensure OPTIONS returns 204 with headers |
| Wildcard + credentials | `*` origin cant be used with credentials | Use specific origin string |
| Cookie not set cross-origin | `SameSite` attribute wrong | Use `SameSite: 'none'` + `Secure: true` |

**Important:** When using `credentials: true`, `Access-Control-Allow-Origin` CANNOT be `*`. You must specify the exact origin.

---

## Security Hardening

### Helmet — Security Headers

```javascript
const helmet = require('helmet');

app.use(helmet({
  // Content Security Policy
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:", "https:"],
      scriptSrc: ["'self'"],
      connectSrc: ["'self'", "https://api.example.com"],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"],
    },
  },
  // Prevent clickjacking
  frameguard: { action: 'deny' },
  // Hide X-Powered-By
  hidePoweredBy: true,
  // Strict Transport Security
  hsts: {
    maxAge: 31536000, // 1 year
    includeSubDomains: true,
    preload: true,
  },
  // Prevent MIME type sniffing
  noSniff: true,
  // XSS filter
  xssFilter: true,
  // Referrer Policy
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
  // Permissions Policy
  permittedCrossDomainPolicies: { permittedPolicies: 'none' },
}));

// Disable X-Powered-By (also achievable with helmet)
app.disable('x-powered-by');
```

### Complete Security Headers Table

| Header | Purpose | Helmet Config |
|--------|---------|---------------|
| `Strict-Transport-Security` | Force HTTPS | `hsts` |
| `Content-Security-Policy` | Prevent XSS, injection | `contentSecurityPolicy` |
| `X-Content-Type-Options` | Prevent MIME sniffing | `noSniff` |
| `X-Frame-Options` | Prevent clickjacking | `frameguard` |
| `X-XSS-Protection` | XSS filter | `xssFilter` |
| `Referrer-Policy` | Control referrer info | `referrerPolicy` |
| `Permissions-Policy` | Control browser features | Manual header |
| `X-Powered-By` | Remove (information leak) | `hidePoweredBy` |

### Injection Attack Prevention

```javascript
// 1. NoSQL Injection Prevention
// NEVER trust user input directly in queries

// BAD — vulnerable to NoSQL injection
app.post('/login', async (req, res) => {
  // If body is { "email": {"$gt": ""}, "password": {"$gt": ""} }
  // This will match the first user!
  const user = await User.findOne({
    email: req.body.email,
    password: req.body.password,
  });
});

// GOOD — sanitize input
const mongoSanitize = require('express-mongo-sanitize');
app.use(mongoSanitize()); // Strips $ and . from req.body, req.query, req.params

// Or manual sanitization
const sanitizeInput = (obj) => {
  for (const key in obj) {
    if (typeof obj[key] === 'string') {
      obj[key] = obj[key].replace(/[\$\.]/g, '');
    } else if (typeof obj[key] === 'object') {
      sanitizeInput(obj[key]);
    }
  }
  return obj;
};

// 2. SQL Injection Prevention (if using SQL)
// ALWAYS use parameterized queries
// BAD:
// db.query(`SELECT * FROM users WHERE id = ${req.params.id}`);
// GOOD:
// db.query('SELECT * FROM users WHERE id = $1', [req.params.id]);

// 3. XSS Prevention
const xss = require('xss');

const sanitizeBody = (req, res, next) => {
  if (req.body) {
    for (const key in req.body) {
      if (typeof req.body[key] === 'string') {
        req.body[key] = xss(req.body[key]);
      }
    }
  }
  next();
};
app.use(sanitizeBody);

// 4. Path Traversal Prevention
app.get('/files/:filename', (req, res) => {
  const filename = path.basename(req.params.filename); // strips directory traversal
  const filePath = path.join(__dirname, 'uploads', filename);
  
  // Ensure the resolved path starts with uploads directory
  if (!filePath.startsWith(path.join(__dirname, 'uploads'))) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  
  res.sendFile(filePath);
});
```

### CSRF Protection

```javascript
const csrf = require('csurf');
const cookieParser = require('cookie-parser');

app.use(cookieParser());

// For server-rendered apps (not needed for pure API with JWT)
const csrfProtection = csrf({
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
  }
});

// Apply to routes that need it
app.get('/form', csrfProtection, (req, res) => {
  res.render('form', { csrfToken: req.csrfToken() });
});

app.post('/process', csrfProtection, (req, res) => {
  // Token automatically validated
  res.json({ success: true });
});

// For SPAs: Double Submit Cookie pattern
app.get('/api/csrf-token', (req, res) => {
  const token = crypto.randomBytes(32).toString('hex');
  res.cookie('XSRF-TOKEN', token, {
    httpOnly: false, // Must be readable by JS
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
  });
  res.json({ csrfToken: token });
});

// Verify CSRF middleware for APIs
const verifyCsrf = (req, res, next) => {
  const cookieToken = req.cookies['XSRF-TOKEN'];
  const headerToken = req.headers['x-xsrf-token'];
  
  if (!cookieToken || cookieToken !== headerToken) {
    return next(new AppError('Invalid CSRF token', 403));
  }
  next();
};
```

---

## Authentication & Authorization

### JWT Authentication

```javascript
// middleware/auth.js
const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const User = require('../models/User');
const AppError = require('../utils/AppError');
const catchAsync = require('../utils/catchAsync');

const signToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN,
    issuer: 'myapp',
    audience: 'myapp-users',
  });
};

const createSendToken = (user, statusCode, req, res) => {
  const token = signToken(user._id);

  const cookieOptions = {
    expires: new Date(
      Date.now() + process.env.JWT_COOKIE_EXPIRES_IN * 24 * 60 * 60 * 1000
    ),
    httpOnly: true,         // Cannot be accessed by JS
    secure: req.secure || req.headers['x-forwarded-proto'] === 'https',
    sameSite: 'strict',
    path: '/',
  };

  res.cookie('jwt', token, cookieOptions);

  // Remove password from output
  user.password = undefined;

  res.status(statusCode).json({
    status: 'success',
    token, // Also send in body for non-cookie clients
    data: { user },
  });
};

// Protect routes — verify JWT
const protect = catchAsync(async (req, res, next) => {
  let token;

  // 1. Extract token from header or cookie
  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    token = req.headers.authorization.split(' ')[1];
  } else if (req.cookies.jwt) {
    token = req.cookies.jwt;
  }

  if (!token) {
    return next(new AppError('You are not logged in. Please log in to get access.', 401));
  }

  // 2. Verify token
  let decoded;
  try {
    decoded = await promisify(jwt.verify)(token, process.env.JWT_SECRET);
  } catch (err) {
    if (err.name === 'JsonWebTokenError') {
      return next(new AppError('Invalid token. Please log in again.', 401));
    }
    if (err.name === 'TokenExpiredError') {
      return next(new AppError('Your token has expired. Please log in again.', 401));
    }
    return next(err);
  }

  // 3. Check if user still exists
  const currentUser = await User.findById(decoded.id).select('+password');
  if (!currentUser) {
    return next(new AppError('The user belonging to this token no longer exists.', 401));
  }

  // 4. Check if user changed password after token was issued
  if (currentUser.changedPasswordAfter(decoded.iat)) {
    return next(new AppError('User recently changed password. Please log in again.', 401));
  }

  // 5. Grant access
  req.user = currentUser;
  next();
});

// Authorization — restrict to roles
const restrictTo = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(new AppError('You do not have permission to perform this action', 403));
    }
    next();
  };
};

module.exports = { signToken, createSendToken, protect, restrictTo };
```

### Refresh Token Pattern

```javascript
const createTokenPair = (userId) => {
  const accessToken = jwt.sign({ id: userId }, process.env.JWT_SECRET, {
    expiresIn: '15m', // Short-lived
  });
  
  const refreshToken = jwt.sign({ id: userId }, process.env.JWT_REFRESH_SECRET, {
    expiresIn: '7d', // Long-lived
  });
  
  return { accessToken, refreshToken };
};

router.post('/refresh-token', catchAsync(async (req, res, next) => {
  const { refreshToken } = req.cookies;
  
  if (!refreshToken) {
    return next(new AppError('No refresh token provided', 401));
  }
  
  // Verify refresh token
  const decoded = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET);
  
  // Check if token is in whitelist/not blacklisted
  const storedToken = await RefreshToken.findOne({
    token: refreshToken,
    userId: decoded.id,
    revoked: false,
  });
  
  if (!storedToken) {
    return next(new AppError('Invalid refresh token', 401));
  }
  
  // Rotate refresh token
  storedToken.revoked = true;
  await storedToken.save();
  
  const tokens = createTokenPair(decoded.id);
  
  await RefreshToken.create({
    token: tokens.refreshToken,
    userId: decoded.id,
  });
  
  res.cookie('refreshToken', tokens.refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
  });
  
  res.json({ accessToken: tokens.accessToken });
}));
```

---

## Error Handling

### Custom Error Class

```javascript
// utils/AppError.js
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
    this.isOperational = true; // Mark as operational (vs programming) error

    Error.captureStackTrace(this, this.constructor);
  }
}

module.exports = AppError;
```

### Global Error Handler

```javascript
// middleware/errorHandler.js
const AppError = require('../utils/AppError');

const handleCastErrorDB = (err) => {
  const message = `Invalid ${err.path}: ${err.value}.`;
  return new AppError(message, 400);
};

const handleDuplicateFieldsDB = (err) => {
  const field = Object.keys(err.keyValue)[0];
  const value = err.keyValue[field];
  const message = `Duplicate field value: "${value}" for field "${field}". Please use another value.`;
  return new AppError(message, 400);
};

const handleValidationErrorDB = (err) => {
  const errors = Object.values(err.errors).map((el) => el.message);
  const message = `Invalid input data: ${errors.join('. ')}`;
  return new AppError(message, 400);
};

const handleJWTError = () => new AppError('Invalid token. Please log in again.', 401);
const handleJWTExpiredError = () => new AppError('Token expired. Please log in again.', 401);

const sendErrorDev = (err, req, res) => {
  res.status(err.statusCode).json({
    status: err.status,
    error: err,
    message: err.message,
    stack: err.stack,
  });
};

const sendErrorProd = (err, req, res) => {
  // Operational, trusted error: send message to client
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      status: err.status,
      message: err.message,
    });
  }

  // Programming or unknown error: don't leak details
  console.error('ERROR 💥:', err);
  return res.status(500).json({
    status: 'error',
    message: 'Something went very wrong!',
  });
};

module.exports = (err, req, res, next) => {
  err.statusCode = err.statusCode || 500;
  err.status = err.status || 'error';

  if (process.env.NODE_ENV === 'development') {
    sendErrorDev(err, req, res);
  } else {
    let error = { ...err, message: err.message, name: err.name };

    if (error.name === 'CastError') error = handleCastErrorDB(error);
    if (error.code === 11000) error = handleDuplicateFieldsDB(error);
    if (error.name === 'ValidationError') error = handleValidationErrorDB(error);
    if (error.name === 'JsonWebTokenError') error = handleJWTError();
    if (error.name === 'TokenExpiredError') error = handleJWTExpiredError();

    sendErrorProd(error, req, res);
  }
};
```

### Async Error Wrapper

```javascript
// utils/catchAsync.js
module.exports = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

// Usage in controllers
const catchAsync = require('../utils/catchAsync');
const AppError = require('../utils/AppError');

exports.getUser = catchAsync(async (req, res, next) => {
  const user = await User.findById(req.params.id);

  if (!user) {
    return next(new AppError('No user found with that ID', 404));
  }

  res.status(200).json({
    status: 'success',
    data: { user },
  });
});
```

---

## Validation & Sanitization

### Using express-validator

```javascript
const { body, param, query, validationResult } = require('express-validator');

// Validation rules
const userValidationRules = {
  register: [
    body('name')
      .trim()
      .notEmpty().withMessage('Name is required')
      .isLength({ min: 2, max: 50 }).withMessage('Name must be 2-50 characters')
      .matches(/^[a-zA-Z\s]+$/).withMessage('Name can only contain letters and spaces'),

    body('email')
      .trim()
      .notEmpty().withMessage('Email is required')
      .isEmail().withMessage('Please provide a valid email')
      .normalizeEmail()
      .custom(async (email) => {
        const existingUser = await User.findOne({ email });
        if (existingUser) {
          throw new Error('Email already in use');
        }
      }),

    body('password')
      .notEmpty().withMessage('Password is required')
      .isLength({ min: 8 }).withMessage('Password must be at least 8 characters')
      .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/)
      .withMessage('Password must contain uppercase, lowercase, number, and special character'),

    body('passwordConfirm')
      .notEmpty().withMessage('Please confirm your password')
      .custom((value, { req }) => {
        if (value !== req.body.password) {
          throw new Error('Passwords do not match');
        }
        return true;
      }),

    body('role')
      .optional()
      .isIn(['user', 'moderator']).withMessage('Invalid role'),
  ],

  update: [
    body('name').optional().trim().isLength({ min: 2, max: 50 }),
    body('email').optional().trim().isEmail().normalizeEmail(),
    
    // Prevent updating sensitive fields
    body('password').not().exists().withMessage('Cannot update password here'),
    body('role').not().exists().withMessage('Cannot update role'),
  ],
};

// Validation middleware
const validate = (req, res, next) => {
  const errors = validationResult(req);
  
  if (!errors.isEmpty()) {
    const extractedErrors = errors.array().map((err) => ({
      field: err.path,
      message: err.msg,
      value: err.value,
    }));

    return res.status(422).json({
      status: 'fail',
      message: 'Validation failed',
      errors: extractedErrors,
    });
  }

  next();
};

// ID parameter validation
const validateId = [
  param('id')
    .isMongoId().withMessage('Invalid ID format'),
  validate,
];

// Query parameter validation
const validatePagination = [
  query('page').optional().isInt({ min: 1 }).toInt(),
  query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
  query('sort').optional().matches(/^-?[a-zA-Z]+(,-?[a-zA-Z]+)*$/),
  validate,
];

// Usage in routes
router.post('/users',
  userValidationRules.register,
  validate,
  userController.createUser
);

router.get('/users/:id',
  validateId,
  userController.getUser
);
```

---

## Rate Limiting & DDoS Protection

```javascript
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');
const Redis = require('ioredis');

const redisClient = new Redis(process.env.REDIS_URL);

// General API rate limiter
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100,                   // 100 requests per window
  message: {
    status: 'error',
    message: 'Too many requests, please try again later.',
  },
  standardHeaders: true,      // Return rate limit info in `RateLimit-*` headers
  legacyHeaders: false,       // Disable `X-RateLimit-*` headers
  
  // Redis store for multi-instance deployments
  store: new RedisStore({
    sendCommand: (...args) => redisClient.call(...args),
  }),

  // Skip rate limiting for certain IPs
  skip: (req) => {
    const whitelist = ['127.0.0.1', '::1'];
    return whitelist.includes(req.ip);
  },

  // Custom key generator (default is IP)
  keyGenerator: (req) => {
    return req.user?.id || req.ip;
  },
});

// Strict limiter for authentication routes
const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,   // 1 hour
  max: 5,                      // 5 attempts
  message: {
    status: 'error',
    message: 'Too many login attempts. Please try again after 1 hour.',
  },
  skipSuccessfulRequests: true, // Don't count successful logins
});

// Account creation limiter
const createAccountLimiter = rateLimit({
  windowMs: 24 * 60 * 60 * 1000, // 24 hours
  max: 3,                         // 3 accounts per day per IP
  message: 'Too many accounts created. Please try again tomorrow.',
});

// Apply limiters
app.use('/api/', apiLimiter);
app.use('/api/v1/auth/login', authLimiter);
app.use('/api/v1/auth/register', createAccountLimiter);

// Slowdown middleware — gradually increase delay
const slowDown = require('express-slow-down');

const speedLimiter = slowDown({
  windowMs: 15 * 60 * 1000,
  delayAfter: 50,       // Allow 50 requests per window without delay
  delayMs: (hits) => hits * 100, // Add 100ms * hit count delay after
  maxDelayMs: 5000,      // Max 5 seconds delay
});

app.use('/api/', speedLimiter);
```

---

## File Uploads

```javascript
const multer = require('multer');
const path = require('path');
const crypto = require('crypto');
const AppError = require('../utils/AppError');

// Storage configuration
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    // Generate unique filename
    const uniqueSuffix = crypto.randomBytes(16).toString('hex');
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `${uniqueSuffix}${ext}`);
  },
});

// File filter — only allow specific types
const fileFilter = (req, file, cb) => {
  const allowedTypes = /jpeg|jpg|png|gif|webp/;
  const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
  const mimetype = allowedTypes.test(file.mimetype);

  if (extname && mimetype) {
    cb(null, true);
  } else {
    cb(new AppError('Only image files (jpeg, jpg, png, gif, webp) are allowed', 400), false);
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 5 * 1024 * 1024, // 5MB max
    files: 5,                   // Max 5 files
  },
});

// Usage in routes
router.post('/upload/avatar',
  protect,
  upload.single('avatar'),      // Single file, field name 'avatar'
  catchAsync(async (req, res) => {
    if (!req.file) {
      throw new AppError('Please upload a file', 400);
    }
    
    // Optionally process with sharp
    const sharp = require('sharp');
    await sharp(req.file.path)
      .resize(250, 250)
      .jpeg({ quality: 90 })
      .toFile(`uploads/processed-${req.file.filename}`);
    
    res.json({
      status: 'success',
      data: { filename: req.file.filename },
    });
  })
);

router.post('/upload/gallery',
  protect,
  upload.array('photos', 10),    // Multiple files, max 10
  handler
);

router.post('/upload/mixed',
  protect,
  upload.fields([
    { name: 'avatar', maxCount: 1 },
    { name: 'documents', maxCount: 5 },
  ]),
  handler
);
```

---

## Performance Optimization

```javascript
// 1. Compression
const compression = require('compression');
app.use(compression({
  level: 6,             // Compression level (0-9)
  threshold: 1024,      // Only compress responses > 1KB
  filter: (req, res) => {
    if (req.headers['x-no-compression']) return false;
    return compression.filter(req, res);
  },
}));

// 2. Response caching headers
const cacheControl = (duration) => (req, res, next) => {
  if (req.method === 'GET') {
    res.set('Cache-Control', `public, max-age=${duration}`);
  } else {
    res.set('Cache-Control', 'no-store');
  }
  next();
};

router.get('/static-data', cacheControl(3600), handler); // Cache 1 hour

// 3. ETag support (built-in but configurable)
app.set('etag', 'strong'); // or 'weak' or false

// 4. Database query optimization in controllers
exports.getAllUsers = catchAsync(async (req, res) => {
  const users = await User.find()
    .select('-password -__v')        // Only needed fields
    .lean()                          // Plain objects (faster)
    .limit(Number(req.query.limit))
    .skip((Number(req.query.page) - 1) * Number(req.query.limit));
  
  res.json({ data: users });
});

// 5. Keep-alive connections
const server = app.listen(PORT);
server.keepAliveTimeout = 65000;      // Slightly higher than LB timeout
server.headersTimeout = 66000;        // Must be higher than keepAliveTimeout

// 6. Cluster mode for multi-core
const cluster = require('cluster');
const os = require('os');

if (cluster.isPrimary) {
  const numCPUs = os.cpus().length;
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }
  cluster.on('exit', (worker) => {
    console.log(`Worker ${worker.process.pid} died. Restarting...`);
    cluster.fork();
  });
} else {
  app.listen(PORT);
}

// 7. JSON response optimization
app.set('json spaces', 0);           // No pretty-printing in production
app.set('json replacer', null);      // No custom replacer overhead
```

---

## Logging & Monitoring

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'my-app' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    ),
  }));
}

// Express middleware for request logging
const requestLogger = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    logger.info('HTTP Request', {
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration: `${Date.now() - start}ms`,
      ip: req.ip,
      userAgent: req.get('user-agent'),
      userId: req.user?.id,
      requestId: req.id,
    });
  });

  next();
};

app.use(requestLogger);

module.exports = logger;
```

---

## Testing

```javascript
// tests/user.test.js
const request = require('supertest');
const app = require('../src/app');
const User = require('../src/models/User');

describe('User API', () => {
  let authToken;

  beforeAll(async () => {
    await User.deleteMany({});
  });

  describe('POST /api/v1/users/register', () => {
    it('should register a new user', async () => {
      const res = await request(app)
        .post('/api/v1/users/register')
        .send({
          name: 'Test User',
          email: 'test@example.com',
          password: 'Password123!',
          passwordConfirm: 'Password123!',
        })
        .expect(201);

      expect(res.body.status).toBe('success');
      expect(res.body.token).toBeDefined();
      expect(res.body.data.user.email).toBe('test@example.com');
      expect(res.body.data.user.password).toBeUndefined();
      
      authToken = res.body.token;
    });

    it('should not register with invalid email', async () => {
      const res = await request(app)
        .post('/api/v1/users/register')
        .send({ name: 'Test', email: 'notanemail', password: 'Password123!' })
        .expect(422);

      expect(res.body.errors).toBeDefined();
    });

    it('should not register with duplicate email', async () => {
      const res = await request(app)
        .post('/api/v1/users/register')
        .send({
          name: 'Test2',
          email: 'test@example.com',
          password: 'Password123!',
          passwordConfirm: 'Password123!',
        })
        .expect(422);
    });
  });

  describe('GET /api/v1/users/me', () => {
    it('should return current user when authenticated', async () => {
      const res = await request(app)
        .get('/api/v1/users/me')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(res.body.data.user.email).toBe('test@example.com');
    });

    it('should return 401 without token', async () => {
      await request(app)
        .get('/api/v1/users/me')
        .expect(401);
    });
  });
});
```

---

## Production Deployment

### Nginx Reverse Proxy Configuration

```nginx
upstream nodejs_app {
    server 127.0.0.1:3000;
    keepalive 64;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting at Nginx level
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://nodejs_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files served by Nginx
    location /static/ {
        alias /var/www/app/public/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### PM2 Process Manager

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'my-app',
    script: './server.js',
    instances: 'max',       // Use all CPU cores
    exec_mode: 'cluster',
    max_memory_restart: '500M',
    env_production: {
      NODE_ENV: 'production',
      PORT: 3000,
    },
    // Logging
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    merge_logs: true,
    // Auto-restart
    watch: false,
    max_restarts: 10,
    restart_delay: 4000,
    autorestart: true,
    // Graceful shutdown
    kill_timeout: 5000,
    listen_timeout: 8000,
  }],
};
```

```bash
# Start in production
pm2 start ecosystem.config.js --env production

# Monitor
pm2 monit

# Reload with zero downtime
pm2 reload my-app
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM node:20-alpine AS base
WORKDIR /app
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

FROM base AS dependencies
COPY package*.json ./
RUN npm ci --only=production && cp -R node_modules /prod_node_modules
RUN npm ci

FROM base AS build
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS production
ENV NODE_ENV=production
COPY --from=dependencies /prod_node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package*.json ./
USER nodejs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

---

## Common Pitfalls & Anti-Patterns

### ❌ Anti-Patterns to Avoid

```javascript
// 1. NOT handling async errors
// BAD:
app.get('/users', async (req, res) => {
  const users = await User.find(); // If this throws, Express can't catch it!
  res.json(users);
});
// GOOD: Use catchAsync wrapper or try/catch

// 2. Sending response after headers sent
// BAD:
app.get('/data', (req, res) => {
  res.json({ a: 1 });
  res.json({ b: 2 }); // Error! Headers already sent
});

// 3. Not calling next() in middleware
// BAD:
app.use((req, res, next) => {
  console.log('Request received');
  // Forgot next() — request hangs forever!
});

// 4. Blocking the event loop
// BAD:
app.get('/hash', (req, res) => {
  const hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512'); // BLOCKS!
  res.json({ hash });
});
// GOOD:
app.get('/hash', async (req, res) => {
  const hash = await new Promise((resolve, reject) => {
    crypto.pbkdf2(password, salt, 100000, 64, 'sha512', (err, key) => {
      if (err) reject(err);
      else resolve(key);
    });
  });
  res.json({ hash });
});

// 5. Storing secrets in code
// BAD:
const JWT_SECRET = 'my-secret-key';
// GOOD:
const JWT_SECRET = process.env.JWT_SECRET;

// 6. Not validating/sanitizing input
// BAD:
app.get('/search', (req, res) => {
  db.query(`SELECT * FROM users WHERE name = '${req.query.name}'`); // SQL Injection!
});

// 7. Using app.use(cors()) with no restrictions in production
// BAD:
app.use(cors()); // Allows ALL origins!

// 8. Not setting body size limits
// BAD:
app.use(express.json()); // Default limit is 100kb but be explicit
// GOOD:
app.use(express.json({ limit: '10kb' }));

// 9. Leaking internal errors to client
// BAD:
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack }); // Leaks internal details!
});

// 10. Not handling 404
// Always add a catch-all after all routes
app.all('*', (req, res) => {
  res.status(404).json({ message: 'Route not found' });
});
```

### ✅ Best Practices Checklist

- [ ] Use `helmet()` for security headers
- [ ] Configure CORS with specific origins
- [ ] Set body size limits (`express.json({ limit: '10kb' })`)
- [ ] Implement rate limiting on all API endpoints
- [ ] Stricter rate limits on auth endpoints
- [ ] Use `hpp()` to prevent HTTP Parameter Pollution
- [ ] Sanitize input against NoSQL injection
- [ ] Validate all input with `express-validator` or `joi`
- [ ] Hash passwords with `bcrypt` (cost factor ≥ 12)
- [ ] Use HTTPS in production
- [ ] Set secure cookie flags (`httpOnly`, `secure`, `sameSite`)
- [ ] Implement CSRF protection for cookie-based auth
- [ ] Handle all async errors with try/catch or wrapper
- [ ] Set up global error handler
- [ ] Log errors with structured logging (Winston/Pino)
- [ ] Use environment variables for secrets
- [ ] Set `trust proxy` when behind a reverse proxy
- [ ] Enable compression
- [ ] Implement graceful shutdown
- [ ] Handle `uncaughtException` and `unhandledRejection`
- [ ] Use cluster mode or PM2 for multi-core utilization
- [ ] Set proper `Cache-Control` headers
- [ ] Disable `x-powered-by` header
- [ ] Keep dependencies updated (`npm audit`)
- [ ] Never commit `.env` files
- [ ] Use `--production` flag when installing in production

### Security Vulnerability Quick Reference

| Vulnerability | Protection |
|---|---|
| XSS (Cross-Site Scripting) | Helmet CSP, input sanitization, `httpOnly` cookies |
| CSRF (Cross-Site Request Forgery) | `SameSite` cookies, CSRF tokens, `csurf` package |
| SQL/NoSQL Injection | Parameterized queries, `express-mongo-sanitize` |
| Brute Force | Rate limiting, account lockout, CAPTCHA |
| DDoS | Rate limiting, Nginx limits, CDN (Cloudflare) |
| Clickjacking | `X-Frame-Options: DENY`, Helmet `frameguard` |
| MIME Sniffing | `X-Content-Type-Options: nosniff` |
| Man-in-the-Middle | HTTPS, HSTS header |
| Open Redirect | Validate redirect URLs against whitelist |
| Path Traversal | Use `path.basename()`, validate file paths |
| Information Disclosure | Disable `X-Powered-By`, custom error messages in production |
| Prototype Pollution | Use `Object.create(null)`, validate `__proto__` keys |
| ReDoS (Regular Expression DoS) | Avoid complex regex, use `safe-regex` package |
| Dependency Vulnerabilities | Run `npm audit fix` regularly |

---

This guide covers the complete lifecycle of building, securing, and deploying a production-grade Express.js application. Always keep dependencies updated, audit regularly with `npm audit`, and follow the principle of least privilege in all access control decisions.