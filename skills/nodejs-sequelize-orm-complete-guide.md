Comprehensive guide to using Sequelize ORM in Node.js with PostgreSQL, MySQL, and SQLite3 — including setup, models, migrations, associations, queries, transactions, hooks, scopes, indexing strategies, and production best practices.

---

# Node.js Sequelize ORM — Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation & Database Drivers](#installation--database-drivers)
3. [Connection & Configuration](#connection--configuration)
4. [Model Definition](#model-definition)
5. [Data Types Reference](#data-types-reference)
6. [CRUD Operations](#crud-operations)
7. [Advanced Querying](#advanced-querying)
8. [Associations (Relations)](#associations-relations)
9. [Eager & Lazy Loading](#eager--lazy-loading)
10. [Migrations & Seeders](#migrations--seeders)
11. [Transactions](#transactions)
12. [Hooks (Lifecycle Events)](#hooks-lifecycle-events)
13. [Scopes](#scopes)
14. [Validation & Constraints](#validation--constraints)
15. [Indexing Strategies](#indexing-strategies)
16. [Raw Queries](#raw-queries)
17. [Connection Pooling & Performance](#connection-pooling--performance)
18. [Database-Specific Notes](#database-specific-notes)
19. [Why NOT MongoDB](#why-not-mongodb)
20. [Project Structure Best Practices](#project-structure-best-practices)
21. [Common Pitfalls & Troubleshooting](#common-pitfalls--troubleshooting)
22. [Security Considerations](#security-considerations)
23. [Real-World Scenarios](#real-world-scenarios)

---

## Overview

**Sequelize** is a promise-based Node.js ORM (Object-Relational Mapping) for relational databases. It supports:

| Database    | Driver Package | Supported |
|-------------|---------------|-----------|
| PostgreSQL  | `pg` + `pg-hstore` | ✅ Yes |
| MySQL       | `mysql2`      | ✅ Yes |
| MariaDB     | `mariadb`     | ✅ Yes |
| SQLite3     | `sqlite3`     | ✅ Yes |
| MS SQL Server | `tedious`   | ✅ Yes |
| MongoDB     | —             | ❌ **No** |

> **Important:** Sequelize is designed exclusively for **SQL/relational** databases. MongoDB is a document (NoSQL) database and is **not supported**. For MongoDB, use **Mongoose** instead.

---

## Installation & Database Drivers

### Base Installation

```bash
npm install sequelize
```

### Database-Specific Drivers

```bash
# PostgreSQL
npm install pg pg-hstore

# MySQL
npm install mysql2

# SQLite3
npm install sqlite3

# MariaDB
npm install mariadb

# Microsoft SQL Server
npm install tedious
```

### CLI Tool (for migrations & seeders)

```bash
npm install -D sequelize-cli
npx sequelize-cli init
```

This creates the following directory structure:

```
├── config/
│   └── config.json
├── models/
│   └── index.js
├── migrations/
└── seeders/
```

---

## Connection & Configuration

### PostgreSQL Connection

```javascript
const { Sequelize } = require('sequelize');

// Option 1: Connection URI
const sequelize = new Sequelize('postgres://user:password@localhost:5432/mydb', {
  dialect: 'postgres',
  logging: false,
  pool: {
    max: 20,
    min: 5,
    acquire: 30000,
    idle: 10000,
  },
});

// Option 2: Separate parameters
const sequelize = new Sequelize('mydb', 'user', 'password', {
  host: 'localhost',
  port: 5432,
  dialect: 'postgres',
  dialectOptions: {
    ssl: {
      require: true,
      rejectUnauthorized: false, // for self-signed certs
    },
  },
  logging: (msg) => console.log(`[SQL] ${msg}`),
});
```

### MySQL Connection

```javascript
const sequelize = new Sequelize('mydb', 'root', 'password', {
  host: 'localhost',
  port: 3306,
  dialect: 'mysql',
  dialectOptions: {
    charset: 'utf8mb4',
    connectTimeout: 60000,
  },
  timezone: '+00:00', // UTC
  pool: {
    max: 10,
    min: 0,
    acquire: 30000,
    idle: 10000,
  },
});
```

### SQLite3 Connection

```javascript
const path = require('path');

const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: path.join(__dirname, 'database.sqlite'), // file path
  logging: false,
});

// In-memory SQLite (great for testing)
const sequelizeMemory = new Sequelize('sqlite::memory:', {
  logging: false,
});
```

### Testing the Connection

```javascript
async function testConnection() {
  try {
    await sequelize.authenticate();
    console.log('✅ Database connection established successfully.');
  } catch (error) {
    console.error('❌ Unable to connect to the database:', error.message);
    process.exit(1);
  }
}

testConnection();
```

### Environment-Based Configuration (`config/config.js`)

```javascript
require('dotenv').config();

module.exports = {
  development: {
    username: process.env.DB_USER || 'root',
    password: process.env.DB_PASS || null,
    database: process.env.DB_NAME || 'app_dev',
    host: process.env.DB_HOST || '127.0.0.1',
    port: parseInt(process.env.DB_PORT) || 5432,
    dialect: process.env.DB_DIALECT || 'postgres',
    logging: console.log,
  },
  test: {
    dialect: 'sqlite',
    storage: ':memory:',
    logging: false,
  },
  production: {
    use_env_variable: 'DATABASE_URL',
    dialect: 'postgres',
    dialectOptions: {
      ssl: {
        require: true,
        rejectUnauthorized: false,
      },
    },
    pool: {
      max: 25,
      min: 5,
      acquire: 60000,
      idle: 10000,
    },
    logging: false,
  },
};
```

> **Tip:** Use `.sequelizerc` to point CLI at a `.js` config instead of `.json`:

```javascript
// .sequelizerc
const path = require('path');

module.exports = {
  config: path.resolve('config', 'config.js'),
  'models-path': path.resolve('src', 'models'),
  'seeders-path': path.resolve('src', 'seeders'),
  'migrations-path': path.resolve('src', 'migrations'),
};
```

---

## Model Definition

### Basic Model

```javascript
const { DataTypes, Model } = require('sequelize');

class User extends Model {
  // Instance methods
  getFullName() {
    return `${this.firstName} ${this.lastName}`;
  }

  // Class methods
  static async findByEmail(email) {
    return this.findOne({ where: { email } });
  }
}

User.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    firstName: {
      type: DataTypes.STRING(100),
      allowNull: false,
      validate: {
        notEmpty: { msg: 'First name cannot be empty' },
        len: {
          args: [2, 100],
          msg: 'First name must be between 2 and 100 characters',
        },
      },
    },
    lastName: {
      type: DataTypes.STRING(100),
      allowNull: false,
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: false,
      unique: true,
      validate: {
        isEmail: { msg: 'Must be a valid email address' },
      },
      set(value) {
        this.setDataValue('email', value.toLowerCase().trim());
      },
    },
    password: {
      type: DataTypes.STRING,
      allowNull: false,
      validate: {
        len: [8, 128],
      },
    },
    role: {
      type: DataTypes.ENUM('user', 'admin', 'moderator'),
      defaultValue: 'user',
      allowNull: false,
    },
    age: {
      type: DataTypes.INTEGER,
      validate: {
        min: 0,
        max: 150,
        isInt: true,
      },
    },
    isActive: {
      type: DataTypes.BOOLEAN,
      defaultValue: true,
    },
    lastLoginAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    metadata: {
      type: DataTypes.JSONB, // PostgreSQL only; use JSON for MySQL
      defaultValue: {},
    },
  },
  {
    sequelize,
    modelName: 'User',
    tableName: 'users',
    timestamps: true,       // adds createdAt & updatedAt
    paranoid: true,          // adds deletedAt (soft delete)
    underscored: true,       // snake_case column names
    freezeTableName: true,   // don't pluralize table name
    indexes: [
      { unique: true, fields: ['email'] },
      { fields: ['role'] },
      { fields: ['is_active', 'role'] },       // composite: filters by active+role
      { fields: ['last_login_at'] },
      { fields: ['created_at'] },              // for ORDER BY createdAt
      { fields: ['is_active', 'created_at'] }, // for scoped + sorted queries
      { fields: ['deleted_at'] },              // paranoid soft-delete lookups
    ],
  }
);

module.exports = User;
```

### Using `sequelize.define()` (alternative syntax)

```javascript
const Post = sequelize.define(
  'Post',
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    title: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    slug: {
      type: DataTypes.STRING(255),
      unique: true,
    },
    content: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('draft', 'published', 'archived'),
      defaultValue: 'draft',
    },
    viewCount: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
    publishedAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
  },
  {
    tableName: 'posts',
    timestamps: true,
    paranoid: true,
    underscored: true,
    indexes: [
      { unique: true, fields: ['slug'] },
      { fields: ['status'] },
      { fields: ['user_id'] },                       // FK: belongsTo User
      { fields: ['status', 'published_at'] },         // published posts sorted by date
      { fields: ['user_id', 'status'] },              // user's posts filtered by status
      { fields: ['created_at'] },                     // ORDER BY
      { fields: ['view_count'] },                     // sorting by popularity
      { fields: ['user_id', 'created_at'] },          // user's posts sorted by date
      { fields: ['deleted_at'] },                     // paranoid lookups
    ],
  }
);

module.exports = Post;
```

### Virtual Fields & Getters/Setters

```javascript
{
  firstName: DataTypes.STRING,
  lastName: DataTypes.STRING,
  fullName: {
    type: DataTypes.VIRTUAL,
    get() {
      return `${this.firstName} ${this.lastName}`;
    },
    set(value) {
      throw new Error('Do not try to set the `fullName` value!');
    },
  },
  password: {
    type: DataTypes.STRING,
    set(value) {
      // Hashing on set
      const bcrypt = require('bcryptjs');
      this.setDataValue('password', bcrypt.hashSync(value, 12));
    },
  },
}
```

---

## Data Types Reference

| Sequelize Type | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| `DataTypes.STRING` | VARCHAR(255) | VARCHAR(255) | TEXT |
| `DataTypes.STRING(1234)` | VARCHAR(1234) | VARCHAR(1234) | TEXT |
| `DataTypes.TEXT` | TEXT | TEXT | TEXT |
| `DataTypes.TEXT('tiny')` | TEXT | TINYTEXT | TEXT |
| `DataTypes.TEXT('long')` | TEXT | LONGTEXT | TEXT |
| `DataTypes.BOOLEAN` | BOOLEAN | TINYINT(1) | INTEGER |
| `DataTypes.INTEGER` | INTEGER | INTEGER | INTEGER |
| `DataTypes.BIGINT` | BIGINT | BIGINT | INTEGER |
| `DataTypes.FLOAT` | FLOAT | FLOAT | REAL |
| `DataTypes.DOUBLE` | DOUBLE PRECISION | DOUBLE | REAL |
| `DataTypes.DECIMAL(10, 2)` | DECIMAL(10,2) | DECIMAL(10,2) | NUMERIC |
| `DataTypes.DATE` | TIMESTAMP WITH TZ | DATETIME | TEXT |
| `DataTypes.DATEONLY` | DATE | DATE | TEXT |
| `DataTypes.UUID` | UUID | CHAR(36) | TEXT |
| `DataTypes.UUIDV4` | — (default) | — (default) | — (default) |
| `DataTypes.JSON` | JSON | JSON | TEXT |
| `DataTypes.JSONB` | JSONB | ❌ N/A | ❌ N/A |
| `DataTypes.BLOB` | BYTEA | BLOB | BLOB |
| `DataTypes.ENUM(...)` | ENUM type | ENUM | TEXT |
| `DataTypes.ARRAY(...)` | ARRAY | ❌ N/A | ❌ N/A |
| `DataTypes.RANGE(...)` | RANGE | ❌ N/A | ❌ N/A |
| `DataTypes.CITEXT` | CITEXT | ❌ N/A | ❌ N/A |

> **PostgreSQL-only types:** `JSONB`, `ARRAY`, `RANGE`, `CITEXT`, `HSTORE`, `TSVECTOR`, `GEOMETRY`

---

## CRUD Operations

### Create

```javascript
// Single record
const user = await User.create({
  firstName: 'John',
  lastName: 'Doe',
  email: 'john@example.com',
  password: 'securePassword123',
});

console.log(user.id);          // auto-generated UUID
console.log(user.toJSON());    // plain object

// Bulk create
const users = await User.bulkCreate(
  [
    { firstName: 'Alice', lastName: 'Smith', email: 'alice@example.com', password: 'pass1234' },
    { firstName: 'Bob', lastName: 'Jones', email: 'bob@example.com', password: 'pass5678' },
  ],
  {
    validate: true,           // validate each row
    ignoreDuplicates: true,   // skip duplicates (PostgreSQL/MySQL)
    updateOnDuplicate: ['firstName', 'lastName'], // upsert behavior
  }
);

// Build (don't save yet) then save
const unsavedUser = User.build({ firstName: 'Jane', lastName: 'Doe', email: 'jane@example.com', password: 'test1234' });
console.log(unsavedUser.isNewRecord); // true
await unsavedUser.save();
console.log(unsavedUser.isNewRecord); // false

// findOrCreate
const [userRecord, created] = await User.findOrCreate({
  where: { email: 'john@example.com' },
  defaults: {
    firstName: 'John',
    lastName: 'Doe',
    password: 'fallbackPassword',
  },
});
console.log(created); // true if newly created, false if found
```

### Read

```javascript
// Find by primary key
const user = await User.findByPk('some-uuid-here');

// Find one
const admin = await User.findOne({
  where: { role: 'admin', isActive: true },
});

// Find all
const users = await User.findAll({
  where: { isActive: true },
  attributes: ['id', 'firstName', 'lastName', 'email'],
  order: [['createdAt', 'DESC']],
  limit: 20,
  offset: 0,
});

// Find and count (for pagination)
const { count, rows } = await User.findAndCountAll({
  where: { role: 'user' },
  limit: 10,
  offset: 0,
  distinct: true, // important when using includes
});
console.log(`Total: ${count}, Page results: ${rows.length}`);

// Count
const activeUsers = await User.count({ where: { isActive: true } });

// Aggregate functions
const avgAge = await User.findAll({
  attributes: [
    [sequelize.fn('AVG', sequelize.col('age')), 'averageAge'],
    [sequelize.fn('COUNT', sequelize.col('id')), 'totalUsers'],
    [sequelize.fn('MAX', sequelize.col('age')), 'maxAge'],
  ],
  raw: true,
});
```

### Update

```javascript
// Instance update
const user = await User.findByPk(id);
user.firstName = 'UpdatedName';
await user.save();

// Or:
await user.update({ firstName: 'UpdatedName', lastName: 'UpdatedLast' });

// Bulk update
const [affectedCount] = await User.update(
  { isActive: false },
  {
    where: {
      lastLoginAt: {
        [Op.lt]: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000), // 90 days ago
      },
    },
  }
);
console.log(`Deactivated ${affectedCount} users`);

// Increment / Decrement
await Post.increment('viewCount', { by: 1, where: { id: postId } });
await Product.decrement('stock', { by: quantity, where: { id: productId } });
```

### Delete

```javascript
// Instance delete
const user = await User.findByPk(id);
await user.destroy();

// With paranoid: true, this performs a soft delete (sets deletedAt)
// Force hard delete:
await user.destroy({ force: true });

// Bulk delete
const deletedCount = await User.destroy({
  where: { isActive: false },
});

// Restore soft-deleted records
await user.restore();
await User.restore({ where: { id: someId } });
```

---

## Advanced Querying

### Operators

```javascript
const { Op } = require('sequelize');

const results = await User.findAll({
  where: {
    // AND (implicit)
    role: 'user',
    isActive: true,

    // Comparison operators
    age: {
      [Op.gt]: 18,          // >
      [Op.gte]: 18,         // >=
      [Op.lt]: 65,          // <
      [Op.lte]: 65,         // <=
      [Op.ne]: 30,          // !=
      [Op.between]: [18, 65],     // BETWEEN 18 AND 65
      [Op.notBetween]: [0, 5],
    },

    // String operators
    firstName: {
      [Op.like]: '%john%',      // LIKE (case-sensitive in PG)
      [Op.iLike]: '%john%',     // ILIKE (PostgreSQL only, case-insensitive)
      [Op.startsWith]: 'Jo',
      [Op.endsWith]: 'hn',
      [Op.substring]: 'oh',
    },

    // IN
    role: {
      [Op.in]: ['admin', 'moderator'],
      [Op.notIn]: ['banned'],
    },

    // NULL checks
    lastLoginAt: {
      [Op.is]: null,         // IS NULL
      [Op.not]: null,        // IS NOT NULL
    },

    // OR
    [Op.or]: [
      { role: 'admin' },
      { age: { [Op.gte]: 21 } },
    ],

    // AND (explicit)
    [Op.and]: [
      { isActive: true },
      { role: 'user' },
    ],
  },
});
```

### PostgreSQL JSONB Queries

```javascript
// Query inside JSONB column
const users = await User.findAll({
  where: {
    metadata: {
      preferences: {
        theme: 'dark',
      },
    },
    // Or using specific path:
    'metadata.preferences.notifications': true,
  },
});

// Using raw JSON path queries
const users = await User.findAll({
  where: sequelize.where(
    sequelize.fn('jsonb_extract_path_text', sequelize.col('metadata'), 'level'),
    'premium'
  ),
});
```

### PostgreSQL ARRAY Queries

```javascript
// Model with ARRAY field
tags: {
  type: DataTypes.ARRAY(DataTypes.STRING),
  defaultValue: [],
}

// Query array contains
const posts = await Post.findAll({
  where: {
    tags: {
      [Op.contains]: ['javascript', 'nodejs'],    // @> (contains all)
      [Op.overlap]: ['python', 'javascript'],      // && (overlap / any)
    },
  },
});
```

### Grouping & Aggregation

```javascript
const stats = await Post.findAll({
  attributes: [
    'status',
    [sequelize.fn('COUNT', sequelize.col('id')), 'count'],
    [sequelize.fn('AVG', sequelize.col('view_count')), 'avgViews'],
  ],
  group: ['status'],
  having: sequelize.where(
    sequelize.fn('COUNT', sequelize.col('id')),
    { [Op.gt]: 5 }
  ),
  raw: true,
});
// [{ status: 'published', count: 42, avgViews: 1205.3 }, ...]
```

### Subqueries

```javascript
const usersWithMostPosts = await User.findAll({
  where: {
    id: {
      [Op.in]: sequelize.literal(
        '(SELECT user_id FROM posts GROUP BY user_id HAVING COUNT(*) > 10)'
      ),
    },
  },
});
```

---

## Associations (Relations)

### One-to-One

```javascript
// A User has one Profile
User.hasOne(Profile, {
  foreignKey: 'userId',
  as: 'profile',
  onDelete: 'CASCADE',
  onUpdate: 'CASCADE',
});

Profile.belongsTo(User, {
  foreignKey: 'userId',
  as: 'user',
});
```

### One-to-Many

```javascript
// A User has many Posts
User.hasMany(Post, {
  foreignKey: 'userId',
  as: 'posts',
  onDelete: 'CASCADE',
});

Post.belongsTo(User, {
  foreignKey: 'userId',
  as: 'author',
});
```

### Many-to-Many

```javascript
// Posts have many Tags through PostTags junction table
Post.belongsToMany(Tag, {
  through: 'PostTags',     // junction table name (string) or model
  foreignKey: 'postId',
  otherKey: 'tagId',
  as: 'tags',
  timestamps: true,
});

Tag.belongsToMany(Post, {
  through: 'PostTags',
  foreignKey: 'tagId',
  otherKey: 'postId',
  as: 'posts',
});

// With a custom junction model (when you need extra columns)
class PostTag extends Model {}
PostTag.init(
  {
    postId: {
      type: DataTypes.INTEGER,
      references: { model: Post, key: 'id' },
    },
    tagId: {
      type: DataTypes.INTEGER,
      references: { model: Tag, key: 'id' },
    },
    assignedBy: {
      type: DataTypes.UUID,
    },
    order: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
  },
  { sequelize, modelName: 'PostTag', tableName: 'post_tags', timestamps: true }
);

Post.belongsToMany(Tag, { through: PostTag, foreignKey: 'postId', otherKey: 'tagId', as: 'tags' });
Tag.belongsToMany(Post, { through: PostTag, foreignKey: 'tagId', otherKey: 'postId', as: 'posts' });
```

### Self-Referencing Associations

```javascript
// Hierarchical categories
Category.hasMany(Category, { foreignKey: 'parentId', as: 'children' });
Category.belongsTo(Category, { foreignKey: 'parentId', as: 'parent' });

// User followers (many-to-many self)
User.belongsToMany(User, {
  through: 'UserFollowers',
  as: 'followers',
  foreignKey: 'followingId',
  otherKey: 'followerId',
});

User.belongsToMany(User, {
  through: 'UserFollowers',
  as: 'following',
  foreignKey: 'followerId',
  otherKey: 'followingId',
});
```

### Polymorphic Associations

```javascript
// Comments on Posts and Videos
class Comment extends Model {}
Comment.init({
  id: { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
  body: DataTypes.TEXT,
  commentableId: DataTypes.INTEGER,
  commentableType: DataTypes.STRING, // 'Post' or 'Video'
}, { sequelize, modelName: 'Comment' });

Post.hasMany(Comment, {
  foreignKey: 'commentableId',
  constraints: false,
  scope: { commentableType: 'Post' },
  as: 'comments',
});

Comment.belongsTo(Post, {
  foreignKey: 'commentableId',
  constraints: false,
  as: 'post',
});
```

### Registering All Associations (models/index.js)

```javascript
const fs = require('fs');
const path = require('path');
const { Sequelize } = require('sequelize');
const config = require('../config/config');

const env = process.env.NODE_ENV || 'development';
const dbConfig = config[env];

let sequelize;
if (dbConfig.use_env_variable) {
  sequelize = new Sequelize(process.env[dbConfig.use_env_variable], dbConfig);
} else {
  sequelize = new Sequelize(dbConfig.database, dbConfig.username, dbConfig.password, dbConfig);
}

const db = {};

// Auto-load all model files
fs.readdirSync(__dirname)
  .filter((file) => file !== 'index.js' && file.endsWith('.js'))
  .forEach((file) => {
    const model = require(path.join(__dirname, file))(sequelize, Sequelize.DataTypes);
    db[model.name] = model;
  });

// Run associate methods
Object.keys(db).forEach((modelName) => {
  if (db[modelName].associate) {
    db[modelName].associate(db);
  }
});

db.sequelize = sequelize;
db.Sequelize = Sequelize;

module.exports = db;
```

Model file format for auto-loading:

```javascript
// models/user.js
module.exports = (sequelize, DataTypes) => {
  const User = sequelize.define('User', {
    firstName: DataTypes.STRING,
    lastName: DataTypes.STRING,
    email: DataTypes.STRING,
  }, {
    tableName: 'users',
    underscored: true,
    paranoid: true,
  });

  User.associate = (models) => {
    User.hasMany(models.Post, { foreignKey: 'userId', as: 'posts' });
    User.hasOne(models.Profile, { foreignKey: 'userId', as: 'profile' });
  };

  return User;
};
```

---

## Eager & Lazy Loading

### Eager Loading (include)

```javascript
// Load user with all posts
const user = await User.findByPk(userId, {
  include: [
    {
      model: Post,
      as: 'posts',
      where: { status: 'published' }, // optional filter
      required: false,                 // LEFT JOIN (default for hasMany)
      attributes: ['id', 'title', 'publishedAt'],
      limit: 10,
      order: [['publishedAt', 'DESC']],
      include: [
        {
          model: Tag,
          as: 'tags',
          attributes: ['id', 'name'],
          through: { attributes: [] }, // hide junction table fields
        },
        {
          model: Comment,
          as: 'comments',
          attributes: ['id', 'body', 'createdAt'],
          separate: true, // subquery instead of join (prevents duplicate rows)
          limit: 5,
        },
      ],
    },
    {
      model: Profile,
      as: 'profile',
      required: false,
    },
  ],
});
```

### Lazy Loading

```javascript
const user = await User.findByPk(userId);
const posts = await user.getPosts({ where: { status: 'published' } });
const postCount = await user.countPosts();

// Association methods auto-generated:
// hasMany: get, count, has, set, add, remove, create
// belongsTo: get, set, create
// belongsToMany: get, count, has, set, add, remove, create

await user.createPost({ title: 'New Post', content: 'Hello!' });
await post.setAuthor(user);
await post.addTag(tag);
await post.addTags([tag1, tag2]);
await post.removeTag(tag);
await post.setTags([tag1, tag2, tag3]); // replaces all
const hasTech = await post.hasTag(techTag);
```

---

## Migrations & Seeders

### Creating a Migration

```bash
npx sequelize-cli migration:generate --name create-users-table
```

```javascript
// migrations/20240101000000-create-users-table.js
'use strict';

module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('users', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.UUIDV4,
        primaryKey: true,
        allowNull: false,
      },
      first_name: {
        type: Sequelize.STRING(100),
        allowNull: false,
      },
      last_name: {
        type: Sequelize.STRING(100),
        allowNull: false,
      },
      email: {
        type: Sequelize.STRING(255),
        allowNull: false,
        unique: true,
      },
      password: {
        type: Sequelize.STRING,
        allowNull: false,
      },
      role: {
        type: Sequelize.ENUM('user', 'admin', 'moderator'),
        defaultValue: 'user',
        allowNull: false,
      },
      is_active: {
        type: Sequelize.BOOLEAN,
        defaultValue: true,
      },
      metadata: {
        type: Sequelize.JSONB,
        defaultValue: {},
      },
      created_at: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.literal('NOW()'),
      },
      updated_at: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.literal('NOW()'),
      },
      deleted_at: {
        type: Sequelize.DATE,
        allowNull: true,
      },
    });

    // Add indexes — cover every WHERE, JOIN, and ORDER BY pattern
    await queryInterface.addIndex('users', ['email'], { unique: true });
    await queryInterface.addIndex('users', ['role']);
    await queryInterface.addIndex('users', ['is_active']);
    await queryInterface.addIndex('users', ['is_active', 'role']);
    await queryInterface.addIndex('users', ['last_login_at']);
    await queryInterface.addIndex('users', ['created_at']);
    await queryInterface.addIndex('users', ['deleted_at']);
    await queryInterface.addIndex('users', ['is_active', 'created_at']);
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.dropTable('users');
  },
};
```

### Column Alteration Migration

```javascript
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.addColumn('users', 'phone', {
      type: Sequelize.STRING(20),
      allowNull: true,
      after: 'email', // MySQL only
    });

    await queryInterface.changeColumn('users', 'first_name', {
      type: Sequelize.STRING(200),
      allowNull: false,
    });

    await queryInterface.renameColumn('users', 'phone', 'phone_number');
    
    await queryInterface.addIndex('users', ['phone_number']);
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.removeIndex('users', ['phone_number']);
    await queryInterface.renameColumn('users', 'phone_number', 'phone');
    await queryInterface.removeColumn('users', 'phone');
  },
};
```

### Running Migrations

```bash
npx sequelize-cli db:migrate                  # run pending
npx sequelize-cli db:migrate:undo             # undo last
npx sequelize-cli db:migrate:undo:all         # undo all
npx sequelize-cli db:migrate:status           # check status
```

### Seeders

```bash
npx sequelize-cli seed:generate --name demo-users
```

```javascript
// seeders/20240101000000-demo-users.js
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');

module.exports = {
  async up(queryInterface, Sequelize) {
    const hashedPassword = await bcrypt.hash('password123', 12);
    
    await queryInterface.bulkInsert('users', [
      {
        id: uuidv4(),
        first_name: 'Admin',
        last_name: 'User',
        email: 'admin@example.com',
        password: hashedPassword,
        role: 'admin',
        is_active: true,
        metadata: JSON.stringify({ level: 'premium' }),
        created_at: new Date(),
        updated_at: new Date(),
      },
      // ... more users
    ]);
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.bulkDelete('users', null, {});
  },
};
```

```bash
npx sequelize-cli db:seed:all
npx sequelize-cli db:seed:undo:all
```

---

## Transactions

### Managed Transactions (Recommended)

```javascript
const result = await sequelize.transaction(async (t) => {
  const user = await User.create(
    { firstName: 'John', lastName: 'Doe', email: 'john@example.com', password: 'pass1234' },
    { transaction: t }
  );

  const profile = await Profile.create(
    { userId: user.id, bio: 'Hello world' },
    { transaction: t }
  );

  await user.update({ isActive: true }, { transaction: t });

  return { user, profile };
});
// If any operation throws, everything is rolled back automatically
```

### Unmanaged Transactions

```javascript
const t = await sequelize.transaction();

try {
  const user = await User.create(
    { firstName: 'Jane', lastName: 'Doe', email: 'jane@example.com', password: 'pass5678' },
    { transaction: t }
  );

  await Post.create(
    { title: 'First Post', content: 'Hello!', userId: user.id },
    { transaction: t }
  );

  await t.commit();
} catch (error) {
  await t.rollback();
  throw error;
}
```

### Isolation Levels

```javascript
const { Transaction } = require('sequelize');

await sequelize.transaction(
  {
    isolationLevel: Transaction.ISOLATION_LEVELS.SERIALIZABLE,
    // Options: READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE
  },
  async (t) => {
    // ...
  }
);
```

### Pessimistic Locking

```javascript
await sequelize.transaction(async (t) => {
  const product = await Product.findByPk(productId, {
    lock: t.LOCK.UPDATE,      // SELECT ... FOR UPDATE
    transaction: t,
  });

  if (product.stock < quantity) {
    throw new Error('Insufficient stock');
  }

  await product.decrement('stock', { by: quantity, transaction: t });
  await Order.create({ productId, quantity, userId }, { transaction: t });
});
```

---

## Hooks (Lifecycle Events)

```javascript
User.init({ /* fields */ }, {
  sequelize,
  modelName: 'User',
  hooks: {
    beforeValidate: (user, options) => {
      if (user.email) {
        user.email = user.email.toLowerCase().trim();
      }
    },

    beforeCreate: async (user, options) => {
      const bcrypt = require('bcryptjs');
      if (user.changed('password')) {
        user.password = await bcrypt.hash(user.password, 12);
      }
    },

    beforeUpdate: async (user, options) => {
      if (user.changed('password')) {
        const bcrypt = require('bcryptjs');
        user.password = await bcrypt.hash(user.password, 12);
      }
    },

    afterCreate: async (user, options) => {
      await AuditLog.create({
        action: 'USER_CREATED',
        entityId: user.id,
        entityType: 'User',
      }, { transaction: options.transaction });
    },

    beforeDestroy: async (user, options) => {
      const postCount = await user.countPosts();
      if (postCount > 0) {
        throw new Error('Cannot delete user with existing posts');
      }
    },

    afterDestroy: (user, options) => {
      console.log(`User ${user.id} was deleted`);
    },
  },
});
```

### Available Hooks

| Hook | Description |
|---|---|
| `beforeValidate` / `afterValidate` | Before/after model validation |
| `beforeCreate` / `afterCreate` | Before/after INSERT |
| `beforeUpdate` / `afterUpdate` | Before/after UPDATE |
| `beforeSave` / `afterSave` | Before/after INSERT or UPDATE |
| `beforeDestroy` / `afterDestroy` | Before/after DELETE |
| `beforeBulkCreate` / `afterBulkCreate` | Before/after bulk INSERT |
| `beforeBulkUpdate` / `afterBulkUpdate` | Before/after bulk UPDATE |
| `beforeBulkDestroy` / `afterBulkDestroy` | Before/after bulk DELETE |
| `beforeFind` / `afterFind` | Before/after SELECT |
| `beforeSync` / `afterSync` | Before/after model sync |

> **Important:** `bulkCreate`, `update`, and `destroy` do NOT trigger individual hooks by default. Pass `{ individualHooks: true }` to enable them (at a performance cost).

---

## Scopes

```javascript
User.init({ /* fields */ }, {
  sequelize,
  modelName: 'User',
  defaultScope: {
    where: { isActive: true },
    attributes: { exclude: ['password', 'deletedAt'] },
  },
  scopes: {
    active: {
      where: { isActive: true },
    },
    admins: {
      where: { role: 'admin' },
    },
    withPosts: {
      include: [{ model: Post, as: 'posts' }],
    },
    recentlyActive: {
      where: {
        lastLoginAt: {
          [Op.gte]: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        },
      },
    },
    byRole(role) {
      return {
        where: { role },
      };
    },
    limitedTo(limit) {
      return {
        limit,
      };
    },
  },
});

// Usage
const admins = await User.scope('admins').findAll();
const activeAdmins = await User.scope(['active', 'admins']).findAll();
const mods = await User.scope({ method: ['byRole', 'moderator'] }).findAll();
const top10 = await User.scope('active', { method: ['limitedTo', 10] }).findAll();

// Remove default scope
const allUsers = await User.unscoped().findAll();
```

---

## Validation & Constraints

### Built-in Validators

```javascript
{
  email: {
    type: DataTypes.STRING,
    validate: {
      isEmail: true,
      notEmpty: true,
      len: [5, 255],
    },
  },
  age: {
    type: DataTypes.INTEGER,
    validate: {
      isInt: true,
      min: 0,
      max: 150,
    },
  },
  website: {
    type: DataTypes.STRING,
    validate: {
      isUrl: true,
    },
  },
  creditCard: {
    type: DataTypes.STRING,
    validate: {
      isCreditCard: true,
    },
  },
  ip: {
    type: DataTypes.STRING,
    validate: {
      isIP: true,        // IPv4 or IPv6
      isIPv4: true,      // only IPv4
    },
  },
  // Custom validator
  username: {
    type: DataTypes.STRING,
    validate: {
      isAlphanumeric: true,
      len: [3, 30],
      notContainsBadWords(value) {
        const badWords = ['admin', 'root', 'system'];
        if (badWords.includes(value.toLowerCase())) {
          throw new Error('Username contains reserved word');
        }
      },
    },
  },
}
```

### Model-Level Validation

```javascript
User.init({ /* fields */ }, {
  sequelize,
  modelName: 'User',
  validate: {
    // Model-level validation — checks across multiple fields
    bothNamesOrNone() {
      if ((this.firstName === null) !== (this.lastName === null)) {
        throw new Error('Provide either both first and last name, or neither');
      }
    },
    async emailDomainCheck() {
      if (this.role === 'admin' && !this.email.endsWith('@company.com')) {
        throw new Error('Admins must use company email');
      }
    },
  },
});
```

### Handling Validation Errors

```javascript
try {
  await User.create({ email: 'invalid', age: -5 });
} catch (error) {
  if (error instanceof Sequelize.ValidationError) {
    const messages = error.errors.map((e) => ({
      field: e.path,
      message: e.message,
      type: e.type, // e.g., 'Validation error'
      value: e.value,
    }));
    console.log('Validation errors:', messages);
  } else if (error instanceof Sequelize.UniqueConstraintError) {
    console.log('Duplicate entry:', error.fields);
  } else if (error instanceof Sequelize.ForeignKeyConstraintError) {
    console.log('Foreign key violation');
  } else if (error instanceof Sequelize.DatabaseError) {
    console.log('Database error:', error.message);
  }
}
```

---

## Indexing Strategies

> **Core principle:** Every `WHERE` clause, `JOIN` condition, and `ORDER BY` column in your application queries should be backed by a database index. Create indexes proactively when defining models and migrations — not reactively after performance degrades.

### Index Types Overview

| Index Type | Syntax | Use Case |
|---|---|---|
| Single column | `{ fields: ['email'] }` | Exact match, range filters on one column |
| Composite | `{ fields: ['status', 'created_at'] }` | Multi-column WHERE + ORDER BY |
| Unique | `{ unique: true, fields: ['email'] }` | Enforce uniqueness + fast lookups |
| Partial (PostgreSQL) | `{ where: { is_active: true } }` | Index only matching rows |
| GIN (PostgreSQL) | `{ using: 'gin', fields: ['tags'] }` | JSONB, ARRAY, full-text search |
| GiST (PostgreSQL) | `{ using: 'gist' }` | Geometry, ranges, full-text |
| Expression-based | Via raw migration | Functions, computed values |
| FULLTEXT (MySQL) | `{ type: 'FULLTEXT' }` | Natural language text search |

### Systematic Indexing by Query Pattern

Use this checklist for every model — map all application query patterns to indexes:

```javascript
// === MODEL: User ===
// Query patterns and their required indexes:
//
// 1. Login:         WHERE email = ?                    → UNIQUE(email)
// 2. List active:   WHERE is_active = true             → INDEX(is_active)
// 3. List by role:  WHERE role = ?                     → INDEX(role)
// 4. Admin panel:   WHERE is_active = ? AND role = ?   → COMPOSITE(is_active, role)
// 5. Sort by date:  ORDER BY created_at DESC           → INDEX(created_at)
// 6. Inactive purge:WHERE last_login_at < ?            → INDEX(last_login_at)
// 7. Scoped sort:   WHERE is_active = ? ORDER BY created_at → COMPOSITE(is_active, created_at)
// 8. Soft delete:   WHERE deleted_at IS NULL           → INDEX(deleted_at)
// 9. Find by name:  WHERE first_name ILIKE ?           → trigram GIN (see below)

User.init({ /* ... */ }, {
  sequelize,
  modelName: 'User',
  tableName: 'users',
  underscored: true,
  paranoid: true,
  indexes: [
    // Pattern 1: login/lookup by email
    { unique: true, fields: ['email'] },

    // Pattern 2: filter by active status
    { fields: ['is_active'] },

    // Pattern 3: filter by role
    { fields: ['role'] },

    // Pattern 4: admin panel filtering (composite — leftmost prefix serves single-column too)
    { fields: ['is_active', 'role'] },

    // Pattern 5: pagination sorted by creation date
    { fields: ['created_at'] },

    // Pattern 6: stale user cleanup
    { fields: ['last_login_at'] },

    // Pattern 7: active users sorted (covers WHERE + ORDER BY in one scan)
    { fields: ['is_active', 'created_at'] },

    // Pattern 8: paranoid model — soft delete lookups
    { fields: ['deleted_at'] },
  ],
});
```

```javascript
// === MODEL: Post ===
// Query patterns and their required indexes:
//
// 1. Slug lookup:     WHERE slug = ?                           → UNIQUE(slug)
// 2. By author:       WHERE user_id = ?                        → INDEX(user_id)
// 3. Feed:            WHERE status = 'published' ORDER BY published_at → COMPOSITE(status, published_at)
// 4. Author filter:   WHERE user_id = ? AND status = ?         → COMPOSITE(user_id, status)
// 5. Author timeline: WHERE user_id = ? ORDER BY created_at    → COMPOSITE(user_id, created_at)
// 6. Popular posts:   ORDER BY view_count DESC                 → INDEX(view_count)
// 7. Date range:      WHERE published_at BETWEEN ? AND ?       → INDEX(published_at)
// 8. Search title:    WHERE title ILIKE '%keyword%'           → GIN trigram (see below)
// 9. Soft delete:     WHERE deleted_at IS NULL                 → INDEX(deleted_at)

Post.init({ /* ... */ }, {
  sequelize,
  modelName: 'Post',
  tableName: 'posts',
  underscored: true,
  paranoid: true,
  indexes: [
    { unique: true, fields: ['slug'] },
    { fields: ['user_id'] },
    { fields: ['status', 'published_at'] },
    { fields: ['user_id', 'status'] },
    { fields: ['user_id', 'created_at'] },
    { fields: ['view_count'] },
    { fields: ['published_at'] },
    { fields: ['created_at'] },
    { fields: ['deleted_at'] },
  ],
});
```

```javascript
// === MODEL: Comment ===
// Query patterns:
// 1. Comments for a post:  WHERE post_id = ? ORDER BY created_at
// 2. Comments by user:     WHERE user_id = ?
// 3. Polymorphic:          WHERE commentable_id = ? AND commentable_type = ?

Comment.init({ /* ... */ }, {
  sequelize,
  modelName: 'Comment',
  tableName: 'comments',
  underscored: true,
  indexes: [
    { fields: ['post_id', 'created_at'] },                    // comments for post, sorted
    { fields: ['user_id'] },                                   // comments by user
    { fields: ['commentable_type', 'commentable_id'] },        // polymorphic lookup
    { fields: ['created_at'] },
  ],
});
```

```javascript
// === JUNCTION TABLE: PostTags ===
// Query patterns:
// 1. Tags for post:   WHERE post_id = ?
// 2. Posts for tag:   WHERE tag_id = ?
// 3. Unique pair:     (post_id, tag_id) must be unique

PostTag.init({ /* ... */ }, {
  sequelize,
  modelName: 'PostTag',
  tableName: 'post_tags',
  indexes: [
    { unique: true, fields: ['post_id', 'tag_id'] },  // prevents duplicates + covers pattern 1
    { fields: ['tag_id'] },                             // pattern 2 (reverse lookup)
  ],
});
```

### Composite Index Column Order Rules

```javascript
// === THE LEFT-PREFIX RULE ===
// A composite index on (A, B, C) serves queries on:
//   ✅ WHERE A = ?
//   ✅ WHERE A = ? AND B = ?
//   ✅ WHERE A = ? AND B = ? AND C = ?
//   ✅ WHERE A = ? ORDER BY B
//   ❌ WHERE B = ?           (A is not used — index skipped)
//   ❌ WHERE C = ?           (A, B not used — index skipped)
//   ❌ WHERE B = ? AND C = ? (A not used — index skipped)

// === COLUMN ORDER STRATEGY ===
// 1. Equality filters first  (WHERE status = 'active')
// 2. Range filters next      (WHERE created_at > ?)
// 3. ORDER BY columns last   (ORDER BY created_at DESC)

// Example: "published posts sorted by date, paginated"
// Query: WHERE status = 'published' AND deleted_at IS NULL ORDER BY published_at DESC LIMIT 20
// Index: (status, published_at) — equality col first, sort col second
{ fields: ['status', 'published_at'] }

// Example: "user's posts of a specific status, sorted by date"
// Query: WHERE user_id = ? AND status = ? ORDER BY created_at DESC
// Index: (user_id, status, created_at)
{ fields: ['user_id', 'status', 'created_at'] }
```

### Partial Indexes (PostgreSQL)

```javascript
// Index only the rows you actually query — smaller, faster, less storage
{
  indexes: [
    // Only index published posts (draft/archived won't bloat the index)
    {
      fields: ['published_at'],
      where: { status: 'published' },
      name: 'idx_posts_published_date',
    },

    // Only index active users
    {
      fields: ['role', 'created_at'],
      where: { is_active: true },
      name: 'idx_users_active_role_created',
    },

    // Only non-deleted rows (paranoid models — skip soft-deleted)
    {
      fields: ['email'],
      unique: true,
      where: { deleted_at: null },
      name: 'idx_users_email_alive',
    },
  ],
}
```

### GIN Indexes for JSONB, ARRAY & Full-Text (PostgreSQL)

```javascript
// In model definition
{
  indexes: [
    // GIN index on JSONB — supports @>, ?, ?|, ?& operators
    {
      fields: ['metadata'],
      using: 'gin',
      name: 'idx_users_metadata_gin',
    },

    // GIN index on ARRAY column
    {
      fields: ['tags'],
      using: 'gin',
      name: 'idx_posts_tags_gin',
    },
  ],
}

// In migration — for trigram search (ILIKE '%keyword%')
module.exports = {
  async up(queryInterface, Sequelize) {
    // Enable pg_trgm extension (once per database)
    await queryInterface.sequelize.query('CREATE EXTENSION IF NOT EXISTS pg_trgm;');

    // GIN trigram index for ILIKE / LIKE '%keyword%' search
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_title_trgm
      ON posts USING gin (title gin_trgm_ops);
    `);

    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_content_trgm
      ON posts USING gin (content gin_trgm_ops);
    `);

    // GIN index for full-text search with tsvector
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_fts
      ON posts USING gin (to_tsvector('english', title || ' ' || content));
    `);
  },

  async down(queryInterface) {
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_posts_title_trgm;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_posts_content_trgm;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_posts_fts;');
  },
};
```

### FULLTEXT Indexes (MySQL)

```javascript
// In migration
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.addIndex('posts', ['title', 'content'], {
      type: 'FULLTEXT',
      name: 'idx_posts_fulltext',
    });
  },
  async down(queryInterface) {
    await queryInterface.removeIndex('posts', 'idx_posts_fulltext');
  },
};

// Query using MySQL FULLTEXT
const results = await sequelize.query(
  "SELECT * FROM posts WHERE MATCH(title, content) AGAINST(:query IN BOOLEAN MODE)",
  { replacements: { query: 'nodejs sequelize' }, type: QueryTypes.SELECT, model: Post, mapToModel: true }
);
```

### Expression & Functional Indexes (via Migrations)

```javascript
module.exports = {
  async up(queryInterface) {
    // Index on lowercased email (PostgreSQL)
    await queryInterface.sequelize.query(`
      CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower
      ON users (LOWER(email));
    `);

    // Index on date part of timestamp
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_date
      ON orders (DATE(created_at));
    `);

    // Index on JSONB path
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_metadata_level
      ON users ((metadata->>'level'));
    `);

    // Index on computed column (year + month)
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_year_month
      ON posts (EXTRACT(YEAR FROM published_at), EXTRACT(MONTH FROM published_at));
    `);
  },

  async down(queryInterface) {
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_users_email_lower;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_orders_created_date;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_users_metadata_level;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_posts_year_month;');
  },
};
```

### Covering Indexes (PostgreSQL INCLUDE)

```javascript
// Include extra columns in the index so the query is answered entirely from the index
// (index-only scan — no table heap access)
module.exports = {
  async up(queryInterface) {
    // Query: SELECT id, first_name, email FROM users WHERE role = 'admin' AND is_active = true
    // The included columns are returned directly from the index
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_active_covering
      ON users (role, is_active)
      INCLUDE (id, first_name, email);
    `);

    // Query: SELECT id, title FROM posts WHERE user_id = ? AND status = 'published' ORDER BY published_at
    await queryInterface.sequelize.query(`
      CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_status_covering
      ON posts (user_id, status, published_at)
      INCLUDE (id, title);
    `);
  },

  async down(queryInterface) {
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_users_role_active_covering;');
    await queryInterface.sequelize.query('DROP INDEX IF EXISTS idx_posts_user_status_covering;');
  },
};
```

### Foreign Key Indexes

```javascript
// ⚠️ Sequelize associations create foreign keys but NOT indexes automatically (except PostgreSQL unique constraints)
// ALWAYS add explicit indexes on all foreign key columns

// In model
{
  indexes: [
    { fields: ['user_id'] },       // belongsTo User
    { fields: ['category_id'] },   // belongsTo Category
    { fields: ['parent_id'] },     // self-referencing
  ],
}

// In migration — do it right next to the FK creation
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('posts', {
      id: { type: Sequelize.INTEGER, autoIncrement: true, primaryKey: true },
      user_id: {
        type: Sequelize.UUID,
        allowNull: false,
        references: { model: 'users', key: 'id' },
        onDelete: 'CASCADE',
        onUpdate: 'CASCADE',
      },
      category_id: {
        type: Sequelize.INTEGER,
        allowNull: true,
        references: { model: 'categories', key: 'id' },
        onDelete: 'SET NULL',
      },
      // ... other columns
    });

    // Index EVERY foreign key — critical for JOIN performance and cascading deletes
    await queryInterface.addIndex('posts', ['user_id']);
    await queryInterface.addIndex('posts', ['category_id']);
  },

  async down(queryInterface) {
    await queryInterface.dropTable('posts');
  },
};
```

### Comprehensive Indexing Audit Migration

Use this template to audit and add all missing indexes to an existing database:

```javascript
// migrations/20240601000000-add-comprehensive-indexes.js
module.exports = {
  async up(queryInterface, Sequelize) {
    // === USERS TABLE ===
    // Lookup patterns: email, role, active status, login recency, creation date, soft delete
    await queryInterface.addIndex('users', ['email'], { unique: true, name: 'idx_users_email_unique' });
    await queryInterface.addIndex('users', ['role'], { name: 'idx_users_role' });
    await queryInterface.addIndex('users', ['is_active'], { name: 'idx_users_active' });
    await queryInterface.addIndex('users', ['is_active', 'role'], { name: 'idx_users_active_role' });
    await queryInterface.addIndex('users', ['is_active', 'created_at'], { name: 'idx_users_active_created' });
    await queryInterface.addIndex('users', ['last_login_at'], { name: 'idx_users_last_login' });
    await queryInterface.addIndex('users', ['created_at'], { name: 'idx_users_created' });
    await queryInterface.addIndex('users', ['deleted_at'], { name: 'idx_users_deleted' });

    // === POSTS TABLE ===
    // Lookup patterns: slug, author, status, published date, popularity, search, soft delete
    await queryInterface.addIndex('posts', ['slug'], { unique: true, name: 'idx_posts_slug_unique' });
    await queryInterface.addIndex('posts', ['user_id'], { name: 'idx_posts_user' });
    await queryInterface.addIndex('posts', ['status'], { name: 'idx_posts_status' });
    await queryInterface.addIndex('posts', ['status', 'published_at'], { name: 'idx_posts_status_published' });
    await queryInterface.addIndex('posts', ['user_id', 'status'], { name: 'idx_posts_user_status' });
    await queryInterface.addIndex('posts', ['user_id', 'created_at'], { name: 'idx_posts_user_created' });
    await queryInterface.addIndex('posts', ['view_count'], { name: 'idx_posts_views' });
    await queryInterface.addIndex('posts', ['published_at'], { name: 'idx_posts_published' });
    await queryInterface.addIndex('posts', ['created_at'], { name: 'idx_posts_created' });
    await queryInterface.addIndex('posts', ['deleted_at'], { name: 'idx_posts_deleted' });

    // === COMMENTS TABLE ===
    await queryInterface.addIndex('comments', ['post_id', 'created_at'], { name: 'idx_comments_post_created' });
    await queryInterface.addIndex('comments', ['user_id'], { name: 'idx_comments_user' });
    await queryInterface.addIndex('comments', ['created_at'], { name: 'idx_comments_created' });

    // === JUNCTION: POST_TAGS ===
    await queryInterface.addIndex('post_tags', ['post_id', 'tag_id'], { unique: true, name: 'idx_post_tags_unique' });
    await queryInterface.addIndex('post_tags', ['tag_id'], { name: 'idx_post_tags_tag' });

    // === PROFILES TABLE ===
    await queryInterface.addIndex('profiles', ['user_id'], { unique: true, name: 'idx_profiles_user_unique' });

    // === ORDERS TABLE ===
    await queryInterface.addIndex('orders', ['user_id'], { name: 'idx_orders_user' });
    await queryInterface.addIndex('orders', ['status'], { name: 'idx_orders_status' });
    await queryInterface.addIndex('orders', ['user_id', 'status'], { name: 'idx_orders_user_status' });
    await queryInterface.addIndex('orders', ['user_id', 'created_at'], { name: 'idx_orders_user_created' });
    await queryInterface.addIndex('orders', ['created_at'], { name: 'idx_orders_created' });

    // === ORDER_ITEMS TABLE ===
    await queryInterface.addIndex('order_items', ['order_id'], { name: 'idx_order_items_order' });
    await queryInterface.addIndex('order_items', ['product_id'], { name: 'idx_order_items_product' });

    // === PRODUCTS TABLE ===
    await queryInterface.addIndex('products', ['category_id'], { name: 'idx_products_category' });
    await queryInterface.addIndex('products', ['price'], { name: 'idx_products_price' });
    await queryInterface.addIndex('products', ['stock'], { name: 'idx_products_stock' });
    await queryInterface.addIndex('products', ['is_active', 'category_id'], { name: 'idx_products_active_category' });
  },

  async down(queryInterface) {
    // Remove all indexes (list in reverse order or by name)
    const indexes = [
      ['users', 'idx_users_email_unique'], ['users', 'idx_users_role'],
      ['users', 'idx_users_active'], ['users', 'idx_users_active_role'],
      ['users', 'idx_users_active_created'], ['users', 'idx_users_last_login'],
      ['users', 'idx_users_created'], ['users', 'idx_users_deleted'],
      ['posts', 'idx_posts_slug_unique'], ['posts', 'idx_posts_user'],
      ['posts', 'idx_posts_status'], ['posts', 'idx_posts_status_published'],
      ['posts', 'idx_posts_user_status'], ['posts', 'idx_posts_user_created'],
      ['posts', 'idx_posts_views'], ['posts', 'idx_posts_published'],
      ['posts', 'idx_posts_created'], ['posts', 'idx_posts_deleted'],
      ['comments', 'idx_comments_post_created'], ['comments', 'idx_comments_user'],
      ['comments', 'idx_comments_created'],
      ['post_tags', 'idx_post_tags_unique'], ['post_tags', 'idx_post_tags_tag'],
      ['profiles', 'idx_profiles_user_unique'],
      ['orders', 'idx_orders_user'], ['orders', 'idx_orders_status'],
      ['orders', 'idx_orders_user_status'], ['orders', 'idx_orders_user_created'],
      ['orders', 'idx_orders_created'],
      ['order_items', 'idx_order_items_order'], ['order_items', 'idx_order_items_product'],
      ['products', 'idx_products_category'], ['products', 'idx_products_price'],
      ['products', 'idx_products_stock'], ['products', 'idx_products_active_category'],
    ];

    for (const [table, name] of indexes) {
      await queryInterface.removeIndex(table, name).catch(() => {});
    }
  },
};
```

### Monitoring & Analyzing Index Usage

```javascript
// === EXPLAIN ANALYZE — verify queries use your indexes ===

// In development, wrap queries in EXPLAIN to see the execution plan
const [plan] = await sequelize.query(
  'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT * FROM users WHERE role = $1 AND is_active = $2 ORDER BY created_at DESC LIMIT 20',
  { bind: ['admin', true] }
);
console.log(JSON.stringify(plan, null, 2));
// Look for: "Index Scan" or "Index Only Scan" — good
// Watch for: "Seq Scan" on large tables — needs an index

// === Find missing indexes (PostgreSQL) ===
const missingIndexes = await sequelize.query(`
  SELECT
    schemaname, relname AS table,
    seq_scan, seq_tup_read,
    idx_scan, idx_tup_fetch,
    n_tup_ins, n_tup_upd, n_tup_del,
    pg_size_pretty(pg_relation_size(relid)) AS table_size
  FROM pg_stat_user_tables
  WHERE seq_scan > idx_scan        -- more seq scans than index scans
    AND n_live_tup > 10000         -- only tables with substantial rows
  ORDER BY seq_scan - idx_scan DESC;
`, { type: QueryTypes.SELECT });

// === Find unused indexes (bloat candidates) ===
const unusedIndexes = await sequelize.query(`
  SELECT
    indexrelid::regclass AS index,
    relid::regclass AS table,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS times_used
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0
    AND indexrelid NOT IN (SELECT conindid FROM pg_constraint WHERE contype IN ('p', 'u'))
  ORDER BY pg_relation_size(indexrelid) DESC;
`, { type: QueryTypes.SELECT });

// === Find duplicate/redundant indexes ===
const duplicateIndexes = await sequelize.query(`
  SELECT
    a.indexrelid::regclass AS index_a,
    b.indexrelid::regclass AS index_b,
    a.indrelid::regclass AS table,
    pg_size_pretty(pg_relation_size(a.indexrelid)) AS size_a,
    pg_size_pretty(pg_relation_size(b.indexrelid)) AS size_b
  FROM pg_index a
  JOIN pg_index b ON a.indrelid = b.indrelid
    AND a.indexrelid != b.indexrelid
    AND a.indkey::text = LEFT(b.indkey::text, LENGTH(a.indkey::text))
  WHERE a.indisunique = false;
`, { type: QueryTypes.SELECT });

// === Sequelize-level query logging with timing ===
const sequelize = new Sequelize(uri, {
  logging: (sql, timing) => {
    console.log(`[${timing}ms] ${sql}`);
  },
  benchmark: true, // enables timing parameter in logging
});

// === MySQL: Check index usage ===
// EXPLAIN SELECT * FROM users WHERE role = 'admin';
// SHOW INDEX FROM users;
```

### Indexing Decision Checklist

```
For EVERY model/table, answer these questions:

✅ Which columns appear in WHERE clauses?          → Single or composite index
✅ Which columns appear in JOIN / FK conditions?    → Index on FK columns
✅ Which columns appear in ORDER BY?                → Index (or composite with WHERE cols)
✅ Which columns appear in GROUP BY?                → Index on grouped columns
✅ Which unique constraints exist?                  → Unique index
✅ Is the model paranoid (soft delete)?             → Index on deleted_at
✅ Are there LIKE/ILIKE '%keyword%' searches?       → GIN trigram index (PG) / FULLTEXT (MySQL)
✅ Are there JSONB queries?                         → GIN index on JSONB column
✅ Are there ARRAY contains/overlap queries?        → GIN index on ARRAY column
✅ Is this a junction table?                        → Unique composite + reverse FK index
✅ Do queries combine WHERE + ORDER BY?             → Composite (equality cols, then sort col)
✅ Are there date range filters?                    → Index on date column
✅ Are there aggregate queries on specific groups?  → Composite on group + aggregate columns

AVOID over-indexing:
❌ Don't index columns only used in SELECT (not WHERE/JOIN/ORDER)
❌ Don't index tiny tables (< 1000 rows — seq scan is faster)
❌ Don't create duplicate indexes (composite (A,B) already covers WHERE A = ?)
❌ Monitor unused indexes and drop them — each index slows writes
```

---

## Raw Queries

```javascript
const { QueryTypes } = require('sequelize');

// SELECT
const users = await sequelize.query(
  'SELECT id, first_name, email FROM users WHERE role = :role AND is_active = :active',
  {
    replacements: { role: 'admin', active: true },
    type: QueryTypes.SELECT,
  }
);

// With bind parameters (positional)
const users = await sequelize.query(
  'SELECT * FROM users WHERE age > $1 AND role = $2',
  {
    bind: [18, 'user'],
    type: QueryTypes.SELECT,
  }
);

// Map to model
const users = await sequelize.query('SELECT * FROM users WHERE role = ?', {
  replacements: ['admin'],
  type: QueryTypes.SELECT,
  model: User,
  mapToModel: true,
});

// INSERT/UPDATE/DELETE
await sequelize.query(
  'UPDATE users SET is_active = false WHERE last_login_at < :date',
  {
    replacements: { date: '2023-01-01' },
    type: QueryTypes.UPDATE,
  }
);
```

---

## Connection Pooling & Performance

### Pool Configuration

```javascript
const sequelize = new Sequelize(/* ... */, {
  pool: {
    max: 20,        // Maximum number of connections
    min: 5,         // Minimum number of connections
    acquire: 30000, // Max time (ms) to get a connection before error
    idle: 10000,    // Max time (ms) a connection can be idle before release
    evict: 1000,    // Time interval (ms) for eviction checks
  },
  retry: {
    max: 3,         // Retry on connection failure
  },
});
```

### Performance Tips

```javascript
// 1. Always select only needed columns
const users = await User.findAll({
  attributes: ['id', 'email', 'firstName'],
});

// 2. Use raw: true for read-only queries
const stats = await User.findAll({
  attributes: [[sequelize.fn('COUNT', sequelize.col('id')), 'count']],
  group: ['role'],
  raw: true,
});

// 3. Use separate: true for nested has-many includes
const users = await User.findAll({
  include: [{
    model: Post,
    as: 'posts',
    separate: true,  // avoids cartesian product
    limit: 10,
  }],
});

// 4. Use indexes appropriately (see Indexing Strategies section)

// 5. Batch operations
await User.bulkCreate(largeArray, {
  validate: true,
  ignoreDuplicates: true,
  returning: false,      // don't need returned data
});

// 6. Stream large result sets
// Sequelize doesn't natively stream, but you can paginate:
async function* paginateUsers(batchSize = 1000) {
  let offset = 0;
  while (true) {
    const users = await User.findAll({ limit: batchSize, offset, raw: true });
    if (users.length === 0) break;
    yield users;
    offset += batchSize;
  }
}

for await (const batch of paginateUsers(500)) {
  // process batch
}

// 7. Closing connection on app shutdown
process.on('SIGTERM', async () => {
  await sequelize.close();
  process.exit(0);
});
```

---

## Database-Specific Notes

### PostgreSQL

- Supports `JSONB`, `ARRAY`, `RANGE`, `HSTORE`, `CITEXT`, `TSVECTOR`
- Best support for advanced features
- Use `JSONB` over `JSON` for indexing and queries
- `ILIKE` operator available for case-insensitive search
- `UPSERT` supported via `ON CONFLICT`
- Supports `RETURNING` clause natively
- `ENUM` creates a real PostgreSQL type (may require migration to alter)
- Supports partial indexes, expression indexes, GIN, GiST, BRIN index types, and covering indexes (`INCLUDE`)
- Use `CONCURRENTLY` when creating indexes on production tables to avoid locking

```javascript
// Full-text search (PostgreSQL)
const results = await Post.findAll({
  where: sequelize.where(
    sequelize.fn('to_tsvector', 'english', sequelize.col('content')),
    '@@',
    sequelize.fn('to_tsquery', 'english', 'nodejs & sequelize')
  ),
});
```

### MySQL

- Use `mysql2` driver (not `mysql`, which is slower and less maintained)
- `JSON` type supported (MySQL 5.7+), but no `JSONB`
- No `ARRAY` type
- `ENUM` is a column property (easier to alter than PostgreSQL)
- Set `charset: 'utf8mb4'` for full emoji/unicode support
- Timezone handling needs `timezone: '+00:00'`
- Supports `FULLTEXT` indexes for text search
- No partial indexes — use generated columns as workaround
- Composite index max key length: 3072 bytes (InnoDB with utf8mb4)

```javascript
const sequelize = new Sequelize('db', 'user', 'pass', {
  dialect: 'mysql',
  dialectOptions: {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    supportBigNumbers: true,
    bigNumberStrings: true,
  },
  timezone: '+00:00',
});
```

### SQLite3

- File-based or in-memory; no server process
- Great for development, testing, embedded apps
- Limited concurrent write support (uses file locking)
- No native `BOOLEAN`, `DATE`, `ENUM`, `UUID` types — Sequelize handles mapping
- No `ALTER COLUMN` — Sequelize recreates table under the hood
- No `ARRAY` or `JSONB` support
- Limited `ALTER TABLE` (no DROP COLUMN in older SQLite)
- Indexes work but no partial indexes, no expression indexes, no GIN/GiST
- Single-column and composite B-tree indexes only

```javascript
// In-memory for tests
const testSequelize = new Sequelize('sqlite::memory:', {
  logging: false,
});

// Before each test
beforeEach(async () => {
  await testSequelize.sync({ force: true });
});
```

---

## Why NOT MongoDB

**Sequelize does NOT support MongoDB.** Here's why and what to use instead:

| Aspect | Sequelize | MongoDB |
|---|---|---|
| Database type | Relational (SQL) | Document (NoSQL) |
| Schema | Fixed schema, tables, rows | Flexible schema, collections, documents |
| Query Language | SQL | MQL (MongoDB Query Language) |
| ORM/ODM | Sequelize (ORM) | **Mongoose** (ODM) |
| Joins | Native JOIN support | `$lookup` or denormalization |
| Transactions | ACID native | ACID (since v4.0, multi-document) |

**Use Mongoose for MongoDB:**

```bash
npm install mongoose
```

```javascript
const mongoose = require('mongoose');
await mongoose.connect('mongodb://localhost:27017/mydb');

const userSchema = new mongoose.Schema({
  name: String,
  email: { type: String, unique: true },
});

const User = mongoose.model('User', userSchema);
```

---

## Project Structure Best Practices

```
src/
├── config/
│   ├── config.js              # DB configuration per environment
│   └── database.js            # Sequelize instance
├── models/
│   ├── index.js               # Auto-loader + associations
│   ├── user.js
│   ├── post.js
│   ├── profile.js
│   ├── tag.js
│   └── comment.js
├── migrations/
│   ├── 20240101000000-create-users.js
│   ├── 20240101000001-create-posts.js
│   └── ...
├── seeders/
│   ├── 20240101000000-demo-users.js
│   └── ...
├── repositories/              # Data access layer (optional)
│   ├── userRepository.js
│   └── postRepository.js
├── services/                  # Business logic
│   ├── userService.js
│   └── postService.js
├── controllers/
│   ├── userController.js
│   └── postController.js
├── middleware/
│   └── errorHandler.js
├── routes/
│   ├── userRoutes.js
│   └── postRoutes.js
└── app.js
```

### Repository Pattern Example

```javascript
// repositories/userRepository.js
class UserRepository {
  constructor(model) {
    this.model = model;
  }

  async findById(id, options = {}) {
    return this.model.findByPk(id, options);
  }

  async findByEmail(email) {
    return this.model.findOne({ where: { email } });
  }

  async findAll({ page = 1, limit = 20, where = {}, include = [], order = [['createdAt', 'DESC']] } = {}) {
    const offset = (page - 1) * limit;
    return this.model.findAndCountAll({
      where,
      include,
      order,
      limit,
      offset,
      distinct: true,
    });
  }

  async create(data, options = {}) {
    return this.model.create(data, options);
  }

  async updateById(id, data, options = {}) {
    const record = await this.findById(id);
    if (!record) throw new Error('Record not found');
    return record.update(data, options);
  }

  async deleteById(id, options = {}) {
    const record = await this.findById(id);
    if (!record) throw new Error('Record not found');
    return record.destroy(options);
  }
}

module.exports = UserRepository;
```

---

## Common Pitfalls & Troubleshooting

### 1. N+1 Query Problem

```javascript
// ❌ BAD: N+1 queries
const users = await User.findAll();
for (const user of users) {
  const posts = await user.getPosts(); // 1 query per user!
}

// ✅ GOOD: Eager loading
const users = await User.findAll({
  include: [{ model: Post, as: 'posts' }],
});
```

### 2. Circular Dependencies in Models

```javascript
// ❌ BAD: Direct imports cause circular dependency
// user.js imports post.js, post.js imports user.js

// ✅ GOOD: Define associations in models/index.js or use associate() pattern
```

### 3. Forgetting `{ transaction: t }`

```javascript
// ❌ BAD: Operations outside the transaction
await sequelize.transaction(async (t) => {
  const user = await User.create(data, { transaction: t });
  await Profile.create({ userId: user.id }); // NOT in transaction!
});

// ✅ GOOD: Pass transaction to ALL operations
await sequelize.transaction(async (t) => {
  const user = await User.create(data, { transaction: t });
  await Profile.create({ userId: user.id }, { transaction: t });
});
```

### 4. `sync({ force: true })` in Production

```javascript
// ❌ NEVER DO THIS IN PRODUCTION — drops and recreates all tables!
await sequelize.sync({ force: true });

// ✅ Use migrations for schema changes
// sync() is acceptable only for development/testing
if (process.env.NODE_ENV === 'development') {
  await sequelize.sync({ alter: true });
}
```

### 5. `.toJSON()` Gotcha

```javascript
// ❌ Instance properties !== plain object
const user = await User.findByPk(1);
console.log(user.password); // includes password

// ✅ Use toJSON or exclude in attributes
const plainUser = user.toJSON();
delete plainUser.password;

// Or better: use defaultScope to exclude
defaultScope: {
  attributes: { exclude: ['password'] },
}
```

### 6. `findAndCountAll` with Includes

```javascript
// ❌ Count is inflated due to JOINs
const { count } = await User.findAndCountAll({
  include: [{ model: Post, as: 'posts' }],
});

// ✅ Use distinct
const { count } = await User.findAndCountAll({
  include: [{ model: Post, as: 'posts' }],
  distinct: true, // counts distinct primary keys
});
```

### 7. Updating ENUM Values (PostgreSQL)

```javascript
// PostgreSQL ENUM types need a migration to add values:
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.sequelize.query(
      "ALTER TYPE \"enum_users_role\" ADD VALUE 'superadmin';"
    );
  },
  async down(queryInterface, Sequelize) {
    // Cannot remove ENUM values in PostgreSQL without recreating the type
    // This requires creating a new type, migrating data, dropping old type
  },
};
```

### 8. Decimal Precision

```javascript
// ❌ FLOAT loses precision for money
price: { type: DataTypes.FLOAT }

// ✅ Use DECIMAL for financial data
price: { type: DataTypes.DECIMAL(10, 2) }
// Note: Sequelize returns DECIMAL values as strings — convert with parseFloat
```

### 9. Missing Indexes on Foreign Keys

```javascript
// ❌ BAD: Association without index — slow JOINs and cascading deletes
Post.belongsTo(User, { foreignKey: 'userId' });
// The FK constraint is created, but no index!

// ✅ GOOD: Always index FK columns
Post.init({ /* ... */ }, {
  sequelize,
  indexes: [
    { fields: ['user_id'] }, // explicit index on FK
  ],
});

// Or in migration:
await queryInterface.addIndex('posts', ['user_id']);
```

### 10. Queries Not Using Indexes

```javascript
// ❌ BAD: Function on indexed column prevents index usage
const users = await User.findAll({
  where: sequelize.where(
    sequelize.fn('LOWER', sequelize.col('email')),
    'john@example.com'
  ),
});
// If index is on `email`, LOWER(email) won't use it!

// ✅ GOOD: Normalize data on write + use plain index
// (use beforeValidate hook to lowercase email)
const users = await User.findAll({
  where: { email: 'john@example.com' }, // uses index directly
});

// ✅ Or: Create expression index (PostgreSQL)
// CREATE INDEX idx_users_email_lower ON users (LOWER(email));
```

---

## Security Considerations

### 1. SQL Injection Prevention

```javascript
// ✅ Sequelize parametrizes queries automatically
await User.findAll({ where: { email: userInput } }); // Safe

// ✅ Raw queries with replacements
await sequelize.query('SELECT * FROM users WHERE email = :email', {
  replacements: { email: userInput }, // Safe — parametrized
  type: QueryTypes.SELECT,
});

// ❌ NEVER concatenate user input into raw queries
await sequelize.query(`SELECT * FROM users WHERE email = '${userInput}'`); // VULNERABLE!
```

### 2. Mass Assignment Protection

```javascript
// ❌ Allows setting ANY field
await User.create(req.body);

// ✅ Whitelist allowed fields
await User.create({
  firstName: req.body.firstName,
  lastName: req.body.lastName,
  email: req.body.email,
  password: req.body.password,
});

// ✅ Or use fields option
await User.create(req.body, {
  fields: ['firstName', 'lastName', 'email', 'password'],
});
```

### 3. Password Handling

```javascript
// Always hash passwords in hooks
User.addHook('beforeSave', async (user) => {
  if (user.changed('password')) {
    const bcrypt = require('bcryptjs');
    user.password = await bcrypt.hash(user.password, 12);
  }
});

// Exclude password from default queries
defaultScope: {
  attributes: { exclude: ['password'] },
},
scopes: {
  withPassword: {
    attributes: { include: ['password'] },
  },
}

// Usage
const userForAuth = await User.scope('withPassword').findOne({ where: { email } });
const isValid = await bcrypt.compare(inputPassword, userForAuth.password);
```

### 4. Rate Limiting Queries

```javascript
// Always paginate — never return unbounded results
const MAX_LIMIT = 100;
const limit = Math.min(parseInt(req.query.limit) || 20, MAX_LIMIT);
const page = Math.max(parseInt(req.query.page) || 1, 1);

const { count, rows } = await User.findAndCountAll({
  limit,
  offset: (page - 1) * limit,
});
```

---

## Real-World Scenarios

### Full Pagination Helper

```javascript
async function paginate(model, { page = 1, limit = 20, where = {}, include = [], order = [], attributes } = {}) {
  const offset = (page - 1) * limit;
  
  const { count, rows } = await model.findAndCountAll({
    where,
    include,
    order,
    limit,
    offset,
    attributes,
    distinct: true,
  });

  const totalPages = Math.ceil(count / limit);

  return {
    data: rows,
    meta: {
      total: count,
      page,
      limit,
      totalPages,
      hasNextPage: page < totalPages,
      hasPrevPage: page > 1,
    },
  };
}

// Usage in Express
app.get('/api/users', async (req, res) => {
  const result = await paginate(User, {
    page: parseInt(req.query.page) || 1,
    limit: parseInt(req.query.limit) || 20,
    where: { isActive: true },
    include: [{ model: Profile, as: 'profile' }],
    order: [['createdAt', 'DESC']],
  });

  res.json(result);
});
```

### Search with Multiple Filters

```javascript
app.get('/api/posts/search', async (req, res) => {
  const { q, status, authorId, tags, from, to, sortBy = 'createdAt', sortDir = 'DESC' } = req.query;

  const where = {};
  const include = [];

  if (q) {
    where[Op.or] = [
      { title: { [Op.iLike]: `%${q}%` } },       // uses GIN trigram index
      { content: { [Op.iLike]: `%${q}%` } },      // uses GIN trigram index
    ];
  }

  if (status) where.status = status;               // uses idx_posts_status
  if (authorId) where.userId = authorId;            // uses idx_posts_user

  if (from || to) {
    where.publishedAt = {};
    if (from) where.publishedAt[Op.gte] = new Date(from);   // uses idx_posts_published
    if (to) where.publishedAt[Op.lte] = new Date(to);
  }

  if (tags) {
    include.push({
      model: Tag,
      as: 'tags',
      where: { name: { [Op.in]: tags.split(',') } },  // uses index on tags.name
      through: { attributes: [] },
    });
  }

  include.push({
    model: User,
    as: 'author',
    attributes: ['id', 'firstName', 'lastName'],
    required: false,
  });

  const result = await paginate(Post, {
    page: parseInt(req.query.page) || 1,
    limit: parseInt(req.query.limit) || 20,
    where,
    include,
    order: [[sortBy, sortDir.toUpperCase() === 'ASC' ? 'ASC' : 'DESC']],
  });

  res.json(result);
});
```

### E-Commerce Order Creation with Transaction

```javascript
async function createOrder(userId, items) {
  return sequelize.transaction(async (t) => {
    // 1. Create order
    const order = await Order.create(
      { userId, status: 'pending', totalAmount: 0 },
      { transaction: t }
    );

    let totalAmount = 0;

    // 2. Process each item
    for (const item of items) {
      // Lock product row for update (uses PK index)
      const product = await Product.findByPk(item.productId, {
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!product) {
        throw new Error(`Product ${item.productId} not found`);
      }

      if (product.stock < item.quantity) {
        throw new Error(`Insufficient stock for ${product.name}`);
      }

      // Decrement stock
      await product.decrement('stock', {
        by: item.quantity,
        transaction: t,
      });

      // Create order item
      const lineTotal = parseFloat(product.price) * item.quantity;
      await OrderItem.create(
        {
          orderId: order.id,
          productId: product.id,
          quantity: item.quantity,
          unitPrice: product.price,
          lineTotal,
        },
        { transaction: t }
      );

      totalAmount += lineTotal;
    }

    // 3. Update order total
    await order.update({ totalAmount }, { transaction: t });

    // 4. Return order with items
    return Order.findByPk(order.id, {
      include: [
        {
          model: OrderItem,
          as: 'items',
          include: [{ model: Product, as: 'product', attributes: ['id', 'name'] }],
        },
      ],
      transaction: t,
    });
  });
}
```

### Multi-Dialect Support Factory

```javascript
// config/database.js — supports switching dialects via env var
const { Sequelize } = require('sequelize');

function createSequelize() {
  const dialect = process.env.DB_DIALECT || 'postgres';

  const commonOptions = {
    logging: process.env.NODE_ENV === 'development' ? console.log : false,
    define: {
      underscored: true,
      timestamps: true,
      paranoid: true,
    },
  };

  switch (dialect) {
    case 'postgres':
      return new Sequelize(process.env.DATABASE_URL || 'postgres://user:pass@localhost:5432/app', {
        ...commonOptions,
        dialect: 'postgres',
        dialectOptions: {
          ssl: process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : false,
        },
        pool: { max: 20, min: 5 },
      });

    case 'mysql':
      return new Sequelize(process.env.DB_NAME, process.env.DB_USER, process.env.DB_PASS, {
        ...commonOptions,
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT) || 3306,
        dialect: 'mysql',
        dialectOptions: { charset: 'utf8mb4' },
        timezone: '+00:00',
      });

    case 'sqlite':
      return new Sequelize({
        ...commonOptions,
        dialect: 'sqlite',
        storage: process.env.DB_STORAGE || './database.sqlite',
      });

    default:
      throw new Error(`Unsupported dialect: ${dialect}`);
  }
}

module.exports = createSequelize();
```

---

## Quick Reference — Cheat Sheet

```javascript
// === SETUP ===
const { Sequelize, DataTypes, Model, Op } = require('sequelize');
const sequelize = new Sequelize(uri, options);
await sequelize.authenticate();

// === MODEL ===
class User extends Model {}
User.init({ /* fields */ }, { sequelize, modelName: 'User' });

// === SYNC (dev only) ===
await sequelize.sync();                // create if not exists
await sequelize.sync({ force: true }); // drop & recreate
await sequelize.sync({ alter: true }); // alter to match model

// === CRUD ===
await Model.create(data);
await Model.bulkCreate([...]);
await Model.findByPk(id);
await Model.findOne({ where });
await Model.findAll({ where, attributes, order, limit, offset });
await Model.findAndCountAll({ where, limit, offset, distinct: true });
await Model.findOrCreate({ where, defaults });
await instance.update(data);
await Model.update(data, { where });
await instance.destroy();
await Model.destroy({ where });

// === OPERATORS ===
Op.eq, Op.ne, Op.gt, Op.gte, Op.lt, Op.lte
Op.between, Op.notBetween
Op.in, Op.notIn
Op.like, Op.iLike, Op.startsWith, Op.endsWith
Op.and, Op.or, Op.not
Op.is, Op.contains, Op.overlap

// === ASSOCIATIONS ===
A.hasOne(B);
A.hasMany(B);
A.belongsTo(B);
A.belongsToMany(B, { through: 'AB' });

// === TRANSACTIONS ===
await sequelize.transaction(async (t) => {
  await Model.create(data, { transaction: t });
});

// === INDEXES (in model) ===
{ indexes: [
  { unique: true, fields: ['email'] },          // unique lookup
  { fields: ['user_id'] },                       // FK
  { fields: ['status', 'created_at'] },           // composite: WHERE + ORDER BY
  { fields: ['tags'], using: 'gin' },            // GIN for ARRAY/JSONB (PG)
  { fields: ['email'], where: { deleted_at: null } }, // partial (PG)
] }

// === CLOSE ===
await sequelize.close();
```

---

This guide covers the vast majority of Sequelize ORM usage patterns. For the most up-to-date API details, always refer to the [official Sequelize documentation](https://sequelize.org/docs/v6/).