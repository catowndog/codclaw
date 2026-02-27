Complete architecture for a competition/tournament platform API built with Node.js Express, Sequelize ORM, PostgreSQL, Vue 3, and Socket.io real-time — covering data models, API endpoints, scoring, leaderboards, brackets, and real-time updates.

# Competition Platform API Architecture

## Table of Contents

1. [Data Models and Schema Design](#data-models)
2. [Database Migrations](#migrations)
3. [API Endpoint Design](#api-endpoints)
4. [Authentication and Authorization](#auth)
5. [Competition Lifecycle](#competition-lifecycle)
6. [Scoring System](#scoring-system)
7. [Leaderboard Implementation](#leaderboard)
8. [Match/Round System](#match-system)
9. [Bracket/Tournament System](#bracket-system)
10. [Real-Time Events Architecture](#realtime-events)
11. [Service Layer Patterns](#service-layer)
12. [Controller Patterns](#controller-patterns)
13. [Validation Middleware](#validation)
14. [Error Handling](#error-handling)
15. [API Response Standards](#api-response)
16. [Project Structure](#project-structure)
17. [Performance Patterns for 5K+ Users](#performance)
18. [Vue 3 Frontend Integration](#frontend-integration)

---

## Data Models and Schema Design

### ER Diagram (Core Entities)

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│    users      │────<│ competition_users  │>────│  competitions    │
│              │     │ (participants)     │     │                  │
│ id (UUID)    │     │ user_id           │     │ id (UUID)        │
│ username     │     │ competition_id    │     │ title            │
│ email        │     │ role (participant/│     │ description      │
│ password     │     │   judge/admin)    │     │ type (solo/team/ │
│ avatar_url   │     │ status (registered│     │   bracket/score) │
│ rating       │     │   /confirmed/     │     │ status (draft/   │
│ role         │     │   disqualified)   │     │   open/active/   │
│ is_active    │     │ seed_number       │     │   scoring/       │
│ created_at   │     │ registered_at     │     │   finished)      │
│ updated_at   │     └───────────────────┘     │ max_participants │
└──────────────┘                                │ start_date       │
       │                                        │ end_date         │
       │     ┌──────────────────┐               │ rules (JSONB)    │
       │     │  user_scores     │               │ settings (JSONB) │
       │────<│                  │>──────────────│ creator_id (FK)  │
       │     │ user_id          │               │ created_at       │
       │     │ competition_id   │               └──────────────────┘
       │     │ score            │                        │
       │     │ matches_played   │               ┌────────┴─────────┐
       │     │ wins             │               │                  │
       │     │ losses           │        ┌──────▼──────┐    ┌──────▼──────┐
       │     │ draws            │        │   rounds     │    │  prizes     │
       │     │ rank             │        │              │    │             │
       │     │ metadata (JSONB) │        │ id           │    │ id          │
       │     └──────────────────┘        │ competition_id│   │ competition_id│
       │                                 │ round_number │    │ place       │
       │     ┌──────────────────┐        │ status       │    │ title       │
       │────<│  matches         │>───────│ started_at   │    │ description │
              │                 │        │ ended_at     │    │ value       │
              │ id              │        └──────────────┘    └─────────────┘
              │ competition_id  │
              │ round_id        │
              │ player1_id (FK) │
              │ player2_id (FK) │
              │ winner_id (FK)  │
              │ player1_score   │
              │ player2_score   │
              │ status          │
              │ scheduled_at    │
              │ started_at      │
              │ finished_at     │
              │ metadata (JSONB)│
              └─────────────────┘
```

### Sequelize Models

```javascript
// models/User.js
module.exports = (sequelize, DataTypes) => {
  const User = sequelize.define('User', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    username: {
      type: DataTypes.STRING(50),
      allowNull: false,
      unique: true,
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: false,
      unique: true,
      set(value) { this.setDataValue('email', value.toLowerCase().trim()); },
    },
    password: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    avatarUrl: {
      type: DataTypes.STRING(500),
      allowNull: true,
    },
    rating: {
      type: DataTypes.INTEGER,
      defaultValue: 1000,  // ELO-like starting rating
    },
    role: {
      type: DataTypes.ENUM('user', 'moderator', 'admin'),
      defaultValue: 'user',
    },
    isActive: {
      type: DataTypes.BOOLEAN,
      defaultValue: true,
    },
    lastLoginAt: DataTypes.DATE,
    metadata: {
      type: DataTypes.JSONB,
      defaultValue: {},
    },
  }, {
    tableName: 'users',
    timestamps: true,
    paranoid: true,
    underscored: true,
    defaultScope: {
      attributes: { exclude: ['password', 'deletedAt'] },
    },
    scopes: {
      withPassword: { attributes: {} },
    },
    indexes: [
      { unique: true, fields: ['email'] },
      { unique: true, fields: ['username'] },
      { fields: ['rating'] },
      { fields: ['is_active'] },
      { fields: ['role'] },
      { fields: ['created_at'] },
      { fields: ['deleted_at'] },
    ],
  });

  User.associate = (models) => {
    User.hasMany(models.Competition, { foreignKey: 'creatorId', as: 'createdCompetitions' });
    User.hasMany(models.CompetitionUser, { foreignKey: 'userId', as: 'participations' });
    User.hasMany(models.UserScore, { foreignKey: 'userId', as: 'scores' });
  };

  return User;
};
```

```javascript
// models/Competition.js
module.exports = (sequelize, DataTypes) => {
  const Competition = sequelize.define('Competition', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    title: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    slug: {
      type: DataTypes.STRING(255),
      allowNull: false,
      unique: true,
    },
    description: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    type: {
      type: DataTypes.ENUM('solo_score', 'head_to_head', 'bracket', 'team', 'round_robin'),
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('draft', 'open', 'active', 'scoring', 'finished', 'cancelled'),
      defaultValue: 'draft',
    },
    maxParticipants: {
      type: DataTypes.INTEGER,
      allowNull: true,  // null = unlimited
    },
    minParticipants: {
      type: DataTypes.INTEGER,
      defaultValue: 2,
    },
    startDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    endDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    registrationDeadline: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    rules: {
      type: DataTypes.JSONB,
      defaultValue: {},
      // { scoringType: 'points'|'time'|'accuracy', maxScore: 100, ... }
    },
    settings: {
      type: DataTypes.JSONB,
      defaultValue: {},
      // { isPublic: true, allowLateJoin: false, autoStart: true, ... }
    },
    creatorId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    imageUrl: DataTypes.STRING(500),
    participantCount: {
      type: DataTypes.INTEGER,
      defaultValue: 0,  // denormalized for performance
    },
  }, {
    tableName: 'competitions',
    timestamps: true,
    paranoid: true,
    underscored: true,
    indexes: [
      { unique: true, fields: ['slug'] },
      { fields: ['status'] },
      { fields: ['type'] },
      { fields: ['creator_id'] },
      { fields: ['status', 'start_date'] },
      { fields: ['status', 'created_at'] },
      { fields: ['start_date'] },
      { fields: ['registration_deadline'] },
      { fields: ['created_at'] },
      { fields: ['deleted_at'] },
    ],
  });

  Competition.associate = (models) => {
    Competition.belongsTo(models.User, { foreignKey: 'creatorId', as: 'creator' });
    Competition.hasMany(models.CompetitionUser, { foreignKey: 'competitionId', as: 'participants' });
    Competition.hasMany(models.UserScore, { foreignKey: 'competitionId', as: 'scores' });
    Competition.hasMany(models.Round, { foreignKey: 'competitionId', as: 'rounds' });
    Competition.hasMany(models.Match, { foreignKey: 'competitionId', as: 'matches' });
  };

  return Competition;
};
```

```javascript
// models/CompetitionUser.js (junction table with extra data)
module.exports = (sequelize, DataTypes) => {
  const CompetitionUser = sequelize.define('CompetitionUser', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    userId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    competitionId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    role: {
      type: DataTypes.ENUM('participant', 'judge', 'organizer'),
      defaultValue: 'participant',
    },
    status: {
      type: DataTypes.ENUM('registered', 'confirmed', 'checked_in', 'active', 'eliminated', 'disqualified', 'withdrawn'),
      defaultValue: 'registered',
    },
    seedNumber: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    registeredAt: {
      type: DataTypes.DATE,
      defaultValue: DataTypes.NOW,
    },
  }, {
    tableName: 'competition_users',
    timestamps: true,
    underscored: true,
    indexes: [
      { unique: true, fields: ['user_id', 'competition_id'] },   // one registration per user per competition
      { fields: ['competition_id', 'status'] },
      { fields: ['competition_id', 'role'] },
      { fields: ['user_id'] },
      { fields: ['status'] },
    ],
  });

  CompetitionUser.associate = (models) => {
    CompetitionUser.belongsTo(models.User, { foreignKey: 'userId', as: 'user' });
    CompetitionUser.belongsTo(models.Competition, { foreignKey: 'competitionId', as: 'competition' });
  };

  return CompetitionUser;
};
```

```javascript
// models/UserScore.js
module.exports = (sequelize, DataTypes) => {
  const UserScore = sequelize.define('UserScore', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    userId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    competitionId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    score: {
      type: DataTypes.DECIMAL(12, 2),
      defaultValue: 0,
    },
    matchesPlayed: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
    wins: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
    losses: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
    draws: {
      type: DataTypes.INTEGER,
      defaultValue: 0,
    },
    rank: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    metadata: {
      type: DataTypes.JSONB,
      defaultValue: {},
      // { bestTime: 12.5, accuracy: 95.2, streakCurrent: 5, streakBest: 8 }
    },
  }, {
    tableName: 'user_scores',
    timestamps: true,
    underscored: true,
    indexes: [
      { unique: true, fields: ['user_id', 'competition_id'] },
      { fields: ['competition_id', 'score'] },                  // leaderboard sort
      { fields: ['competition_id', 'rank'] },                   // rank lookup
      { fields: ['user_id'] },
      { fields: ['score'] },
    ],
  });

  UserScore.associate = (models) => {
    UserScore.belongsTo(models.User, { foreignKey: 'userId', as: 'user' });
    UserScore.belongsTo(models.Competition, { foreignKey: 'competitionId', as: 'competition' });
  };

  return UserScore;
};
```

```javascript
// models/Match.js
module.exports = (sequelize, DataTypes) => {
  const Match = sequelize.define('Match', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    competitionId: { type: DataTypes.UUID, allowNull: false },
    roundId: { type: DataTypes.UUID, allowNull: true },
    player1Id: { type: DataTypes.UUID, allowNull: false },
    player2Id: { type: DataTypes.UUID, allowNull: true },  // null for bye
    winnerId: { type: DataTypes.UUID, allowNull: true },
    player1Score: { type: DataTypes.DECIMAL(10, 2), defaultValue: 0 },
    player2Score: { type: DataTypes.DECIMAL(10, 2), defaultValue: 0 },
    status: {
      type: DataTypes.ENUM('scheduled', 'in_progress', 'finished', 'cancelled', 'walkover'),
      defaultValue: 'scheduled',
    },
    bracketPosition: { type: DataTypes.INTEGER, allowNull: true },   // for bracket tournaments
    scheduledAt: { type: DataTypes.DATE, allowNull: true },
    startedAt: { type: DataTypes.DATE, allowNull: true },
    finishedAt: { type: DataTypes.DATE, allowNull: true },
    metadata: {
      type: DataTypes.JSONB,
      defaultValue: {},
    },
  }, {
    tableName: 'matches',
    timestamps: true,
    underscored: true,
    indexes: [
      { fields: ['competition_id', 'round_id'] },
      { fields: ['competition_id', 'status'] },
      { fields: ['player1_id'] },
      { fields: ['player2_id'] },
      { fields: ['winner_id'] },
      { fields: ['status', 'scheduled_at'] },
      { fields: ['competition_id', 'bracket_position'] },
      { fields: ['round_id', 'bracket_position'] },
      { fields: ['created_at'] },
    ],
  });

  Match.associate = (models) => {
    Match.belongsTo(models.Competition, { foreignKey: 'competitionId', as: 'competition' });
    Match.belongsTo(models.Round, { foreignKey: 'roundId', as: 'round' });
    Match.belongsTo(models.User, { foreignKey: 'player1Id', as: 'player1' });
    Match.belongsTo(models.User, { foreignKey: 'player2Id', as: 'player2' });
    Match.belongsTo(models.User, { foreignKey: 'winnerId', as: 'winner' });
  };

  return Match;
};
```

```javascript
// models/Round.js
module.exports = (sequelize, DataTypes) => {
  const Round = sequelize.define('Round', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    competitionId: { type: DataTypes.UUID, allowNull: false },
    roundNumber: { type: DataTypes.INTEGER, allowNull: false },
    name: { type: DataTypes.STRING(100), allowNull: true },  // "Quarter Finals", "Round 1"
    status: {
      type: DataTypes.ENUM('pending', 'active', 'finished'),
      defaultValue: 'pending',
    },
    startedAt: DataTypes.DATE,
    endedAt: DataTypes.DATE,
  }, {
    tableName: 'rounds',
    timestamps: true,
    underscored: true,
    indexes: [
      { unique: true, fields: ['competition_id', 'round_number'] },
      { fields: ['competition_id', 'status'] },
    ],
  });

  Round.associate = (models) => {
    Round.belongsTo(models.Competition, { foreignKey: 'competitionId', as: 'competition' });
    Round.hasMany(models.Match, { foreignKey: 'roundId', as: 'matches' });
  };

  return Round;
};
```

---

## API Endpoint Design

### RESTful API Routes

```javascript
// routes/index.js
const router = require('express').Router();

router.use('/auth', require('./auth'));
router.use('/users', require('./users'));
router.use('/competitions', require('./competitions'));
router.use('/matches', require('./matches'));
router.use('/leaderboard', require('./leaderboard'));

module.exports = router;
```

```javascript
// routes/competitions.js
const router = require('express').Router();
const ctrl = require('../controllers/competitionController');
const { protect, restrictTo } = require('../middleware/auth');
const { validate } = require('../middleware/validate');
const { competitionRules } = require('../validators/competition');

// Public
router.get('/', ctrl.getAll);                                    // GET /api/v1/competitions
router.get('/featured', ctrl.getFeatured);                       // GET /api/v1/competitions/featured
router.get('/:idOrSlug', ctrl.getOne);                           // GET /api/v1/competitions/:idOrSlug

// Authenticated
router.use(protect);
router.post('/', validate(competitionRules.create), ctrl.create);               // POST /api/v1/competitions
router.patch('/:id', validate(competitionRules.update), ctrl.update);           // PATCH /api/v1/competitions/:id
router.delete('/:id', ctrl.delete);                                              // DELETE /api/v1/competitions/:id

// Participation
router.post('/:id/join', ctrl.join);                             // POST /api/v1/competitions/:id/join
router.post('/:id/leave', ctrl.leave);                           // POST /api/v1/competitions/:id/leave
router.get('/:id/participants', ctrl.getParticipants);           // GET /api/v1/competitions/:id/participants

// Lifecycle
router.post('/:id/start', ctrl.start);                           // POST /api/v1/competitions/:id/start
router.post('/:id/finish', ctrl.finish);                         // POST /api/v1/competitions/:id/finish

// Scoring
router.post('/:id/score', validate(competitionRules.submitScore), ctrl.submitScore);  // POST /api/v1/competitions/:id/score
router.get('/:id/leaderboard', ctrl.getLeaderboard);             // GET /api/v1/competitions/:id/leaderboard

// Matches
router.get('/:id/matches', ctrl.getMatches);                     // GET /api/v1/competitions/:id/matches
router.get('/:id/bracket', ctrl.getBracket);                     // GET /api/v1/competitions/:id/bracket

// Admin
router.post('/:id/generate-bracket', restrictTo('admin', 'moderator'), ctrl.generateBracket);
router.post('/:id/generate-rounds', restrictTo('admin', 'moderator'), ctrl.generateRounds);

module.exports = router;
```

```javascript
// routes/matches.js
const router = require('express').Router();
const ctrl = require('../controllers/matchController');
const { protect } = require('../middleware/auth');

router.use(protect);

router.get('/:id', ctrl.getMatch);                               // GET /api/v1/matches/:id
router.post('/:id/start', ctrl.startMatch);                      // POST /api/v1/matches/:id/start
router.post('/:id/finish', ctrl.finishMatch);                    // POST /api/v1/matches/:id/finish
router.post('/:id/score', ctrl.updateMatchScore);                // POST /api/v1/matches/:id/score

module.exports = router;
```

---

## Competition Lifecycle

### State Machine

```
draft → open → active → scoring → finished
  │       │       │                    │
  │       │       └── cancelled        │
  │       └── cancelled                │
  └── deleted                          └── (archived)

State transitions:
- draft → open:      Creator publishes, registration opens
- open → active:     Start date reached OR manual start, registration closes
- active → scoring:  Competition play period ends, final scoring
- scoring → finished: Scores finalized, rankings locked
- any → cancelled:   Admin/creator cancels
```

```javascript
// services/CompetitionService.js
const { Competition, CompetitionUser, UserScore, Match, Round, User, sequelize } = require('../models');
const { Op } = require('sequelize');
const { emitToCompetition } = require('../websocket');
const AppError = require('../utils/AppError');

class CompetitionService {
  // State transition validation
  static VALID_TRANSITIONS = {
    draft: ['open', 'cancelled'],
    open: ['active', 'cancelled'],
    active: ['scoring', 'finished', 'cancelled'],
    scoring: ['finished'],
    finished: [],
    cancelled: [],
  };

  static canTransition(currentStatus, newStatus) {
    return this.VALID_TRANSITIONS[currentStatus]?.includes(newStatus) || false;
  }

  // Create competition
  async create(userId, data) {
    const slug = this.generateSlug(data.title);

    return sequelize.transaction(async (t) => {
      const competition = await Competition.create({
        ...data,
        slug,
        creatorId: userId,
        status: 'draft',
      }, { transaction: t });

      // Auto-register creator as organizer
      await CompetitionUser.create({
        userId,
        competitionId: competition.id,
        role: 'organizer',
        status: 'confirmed',
      }, { transaction: t });

      return competition;
    });
  }

  // Join competition
  async join(competitionId, userId) {
    return sequelize.transaction(async (t) => {
      const competition = await Competition.findByPk(competitionId, {
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!competition) throw new AppError('Competition not found', 404);
      if (competition.status !== 'open') throw new AppError('Registration is closed', 400);

      if (competition.maxParticipants && competition.participantCount >= competition.maxParticipants) {
        throw new AppError('Competition is full', 400);
      }

      if (competition.registrationDeadline && new Date() > competition.registrationDeadline) {
        throw new AppError('Registration deadline passed', 400);
      }

      // Check if already registered
      const existing = await CompetitionUser.findOne({
        where: { userId, competitionId },
        transaction: t,
      });
      if (existing) throw new AppError('Already registered', 409);

      // Register
      const registration = await CompetitionUser.create({
        userId,
        competitionId,
        role: 'participant',
        status: 'registered',
      }, { transaction: t });

      // Initialize score record
      await UserScore.create({
        userId,
        competitionId,
        score: 0,
      }, { transaction: t });

      // Update participant count
      await competition.increment('participantCount', { transaction: t });

      // Real-time notification
      emitToCompetition(competitionId, 'participant:joined', {
        userId,
        participantCount: competition.participantCount + 1,
      });

      return registration;
    });
  }

  // Start competition
  async start(competitionId, userId) {
    return sequelize.transaction(async (t) => {
      const competition = await Competition.findByPk(competitionId, {
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!competition) throw new AppError('Competition not found', 404);
      if (competition.creatorId !== userId) throw new AppError('Only creator can start', 403);
      if (!CompetitionService.canTransition(competition.status, 'active')) {
        throw new AppError(`Cannot start from status: ${competition.status}`, 400);
      }

      const participantCount = await CompetitionUser.count({
        where: { competitionId, role: 'participant', status: { [Op.in]: ['registered', 'confirmed'] } },
        transaction: t,
      });

      if (participantCount < competition.minParticipants) {
        throw new AppError(`Need at least ${competition.minParticipants} participants`, 400);
      }

      // Activate all registered participants
      await CompetitionUser.update(
        { status: 'active' },
        { where: { competitionId, role: 'participant', status: { [Op.in]: ['registered', 'confirmed'] } }, transaction: t }
      );

      // Update competition status
      await competition.update({
        status: 'active',
        startDate: new Date(),
      }, { transaction: t });

      // For bracket tournaments, generate bracket
      if (competition.type === 'bracket') {
        await this.generateBracket(competition, t);
      }

      // Real-time notification
      emitToCompetition(competitionId, 'competition:started', {
        competitionId,
        startedAt: new Date().toISOString(),
      });

      return competition.reload({ transaction: t });
    });
  }

  // Generate bracket for elimination tournament
  async generateBracket(competition, transaction) {
    const participants = await CompetitionUser.findAll({
      where: { competitionId: competition.id, role: 'participant', status: 'active' },
      include: [{ model: User, as: 'user', attributes: ['id', 'rating'] }],
      order: [[{ model: User, as: 'user' }, 'rating', 'DESC']],
      transaction,
    });

    // Pad to next power of 2 for clean bracket
    const bracketSize = Math.pow(2, Math.ceil(Math.log2(participants.length)));
    const totalRounds = Math.log2(bracketSize);
    const roundNames = this.getRoundNames(totalRounds);

    // Create rounds
    const rounds = [];
    for (let i = 1; i <= totalRounds; i++) {
      const round = await Round.create({
        competitionId: competition.id,
        roundNumber: i,
        name: roundNames[i - 1],
        status: i === 1 ? 'active' : 'pending',
      }, { transaction });
      rounds.push(round);
    }

    // Seed participants (1 vs last, 2 vs second-to-last, etc.)
    const seeded = this.seedParticipants(participants, bracketSize);

    // Create first round matches
    for (let i = 0; i < seeded.length; i += 2) {
      const player1 = seeded[i];
      const player2 = seeded[i + 1]; // may be null (bye)

      const match = await Match.create({
        competitionId: competition.id,
        roundId: rounds[0].id,
        player1Id: player1.userId,
        player2Id: player2?.userId || null,
        bracketPosition: Math.floor(i / 2) + 1,
        status: player2 ? 'scheduled' : 'walkover',
        winnerId: player2 ? null : player1.userId,  // auto-win for byes
      }, { transaction });
    }

    return rounds;
  }

  seedParticipants(participants, bracketSize) {
    // Standard seeding: 1 vs N, 2 vs N-1, etc.
    const seeded = new Array(bracketSize).fill(null);
    participants.forEach((p, i) => {
      if (i < bracketSize) seeded[i] = p;
    });

    // Apply standard bracket seeding order
    return this.bracketOrder(seeded);
  }

  bracketOrder(players) {
    if (players.length <= 2) return players;
    const half = players.length / 2;
    const result = [];
    for (let i = 0; i < half; i++) {
      result.push(players[i], players[players.length - 1 - i]);
    }
    return result;
  }

  getRoundNames(totalRounds) {
    const names = [];
    for (let i = 1; i <= totalRounds; i++) {
      const remaining = totalRounds - i;
      if (remaining === 0) names.push('Final');
      else if (remaining === 1) names.push('Semi-Finals');
      else if (remaining === 2) names.push('Quarter-Finals');
      else names.push(`Round ${i}`);
    }
    return names;
  }

  generateSlug(title) {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      + '-' + Date.now().toString(36);
  }
}

module.exports = new CompetitionService();
```

---

## Leaderboard Implementation

```javascript
// services/LeaderboardService.js
class LeaderboardService {
  // Get leaderboard with rank computation
  async getLeaderboard(competitionId, { page = 1, limit = 50, search } = {}) {
    const where = { competitionId };

    // Build query
    const include = [{
      model: User,
      as: 'user',
      attributes: ['id', 'username', 'avatarUrl', 'rating'],
      where: search ? {
        username: { [Op.iLike]: `%${search}%` },
      } : undefined,
    }];

    const { count, rows } = await UserScore.findAndCountAll({
      where,
      include,
      order: [
        ['score', 'DESC'],
        ['wins', 'DESC'],
        ['matches_played', 'ASC'],  // tiebreaker: fewer matches = more efficient
      ],
      limit,
      offset: (page - 1) * limit,
      distinct: true,
    });

    // Compute rank based on offset
    const startRank = (page - 1) * limit + 1;
    const leaderboard = rows.map((row, index) => ({
      rank: startRank + index,
      userId: row.userId,
      username: row.user.username,
      avatarUrl: row.user.avatarUrl,
      score: parseFloat(row.score),
      matchesPlayed: row.matchesPlayed,
      wins: row.wins,
      losses: row.losses,
      draws: row.draws,
      winRate: row.matchesPlayed > 0
        ? Math.round((row.wins / row.matchesPlayed) * 100)
        : 0,
      metadata: row.metadata,
    }));

    return {
      data: leaderboard,
      meta: {
        total: count,
        page,
        limit,
        totalPages: Math.ceil(count / limit),
      },
    };
  }

  // Get specific user's rank in a competition
  async getUserRank(competitionId, userId) {
    const userScore = await UserScore.findOne({
      where: { competitionId, userId },
    });

    if (!userScore) return null;

    // Count how many users have higher score
    const rank = await UserScore.count({
      where: {
        competitionId,
        score: { [Op.gt]: userScore.score },
      },
    }) + 1;

    return { rank, score: parseFloat(userScore.score) };
  }

  // Update score and broadcast
  async updateScore(competitionId, userId, scoreChange, matchResult = {}) {
    return sequelize.transaction(async (t) => {
      const [userScore] = await UserScore.findOrCreate({
        where: { userId, competitionId },
        defaults: { score: 0 },
        transaction: t,
      });

      const updates = {
        score: sequelize.literal(`score + ${parseFloat(scoreChange)}`),
        matchesPlayed: sequelize.literal('matches_played + 1'),
      };

      if (matchResult.won) updates.wins = sequelize.literal('wins + 1');
      else if (matchResult.lost) updates.losses = sequelize.literal('losses + 1');
      else if (matchResult.draw) updates.draws = sequelize.literal('draws + 1');

      await UserScore.update(updates, {
        where: { userId, competitionId },
        transaction: t,
      });

      // Reload to get new values
      await userScore.reload({ transaction: t });

      // Get new rank
      const rank = await UserScore.count({
        where: {
          competitionId,
          score: { [Op.gt]: userScore.score },
        },
        transaction: t,
      }) + 1;

      // Broadcast leaderboard change
      emitToCompetition(competitionId, 'leaderboard:update', {
        userId,
        score: parseFloat(userScore.score),
        rank,
        matchesPlayed: userScore.matchesPlayed,
        wins: userScore.wins,
      });

      return { score: parseFloat(userScore.score), rank };
    });
  }
}

module.exports = new LeaderboardService();
```

---

## Real-Time Events Architecture

### Event Catalog

| Event | Direction | Room | Payload |
|-------|-----------|------|---------|
| `competition:started` | Server → Client | `competition:{id}` | `{ competitionId, startedAt }` |
| `competition:ended` | Server → Client | `competition:{id}` | `{ competitionId, results }` |
| `participant:joined` | Server → Client | `competition:{id}` | `{ userId, username, participantCount }` |
| `participant:left` | Server → Client | `competition:{id}` | `{ userId, participantCount }` |
| `leaderboard:update` | Server → Client | `competition:{id}` | `{ userId, score, rank }` |
| `match:started` | Server → Client | `competition:{id}` | `{ matchId, player1, player2 }` |
| `match:score_update` | Server → Client | `competition:{id}` | `{ matchId, player1Score, player2Score }` |
| `match:finished` | Server → Client | `competition:{id}` | `{ matchId, winnerId, finalScore }` |
| `round:started` | Server → Client | `competition:{id}` | `{ roundId, roundNumber, name }` |
| `round:finished` | Server → Client | `competition:{id}` | `{ roundId, nextRoundId }` |
| `notification` | Server → Client | `user:{id}` | `{ type, message, data }` |
| `join:competition` | Client → Server | — | `competitionId` |
| `leave:competition` | Client → Server | — | `competitionId` |
| `submit:answer` | Client → Server | — | `{ competitionId, answer, ... }` |

---

## API Response Standards

```javascript
// utils/ApiResponse.js
class ApiResponse {
  static success(res, data, statusCode = 200) {
    return res.status(statusCode).json({
      status: 'success',
      data,
    });
  }

  static created(res, data) {
    return this.success(res, data, 201);
  }

  static paginated(res, data, meta) {
    return res.status(200).json({
      status: 'success',
      data,
      meta: {
        total: meta.total,
        page: meta.page,
        limit: meta.limit,
        totalPages: meta.totalPages,
        hasNextPage: meta.page < meta.totalPages,
        hasPrevPage: meta.page > 1,
      },
    });
  }

  static noContent(res) {
    return res.status(204).send();
  }
}

module.exports = ApiResponse;
```

---

## Project Structure

```
backend/
├── src/
│   ├── config/
│   │   ├── config.js              # DB config (dev/test/prod)
│   │   └── database.js            # Sequelize instance
│   ├── controllers/
│   │   ├── authController.js
│   │   ├── competitionController.js
│   │   ├── matchController.js
│   │   ├── leaderboardController.js
│   │   └── userController.js
│   ├── middleware/
│   │   ├── auth.js                # JWT protect + restrictTo
│   │   ├── errorHandler.js        # Global error handler
│   │   ├── rateLimiter.js         # Rate limiting
│   │   └── validate.js            # express-validator middleware
│   ├── models/
│   │   ├── index.js               # Auto-loader + associations
│   │   ├── User.js
│   │   ├── Competition.js
│   │   ├── CompetitionUser.js
│   │   ├── UserScore.js
│   │   ├── Match.js
│   │   └── Round.js
│   ├── migrations/
│   │   ├── 001-create-users.js
│   │   ├── 002-create-competitions.js
│   │   ├── 003-create-competition-users.js
│   │   ├── 004-create-user-scores.js
│   │   ├── 005-create-rounds.js
│   │   ├── 006-create-matches.js
│   │   └── 007-add-indexes.js
│   ├── seeders/
│   ├── routes/
│   │   ├── index.js
│   │   ├── auth.js
│   │   ├── competitions.js
│   │   ├── matches.js
│   │   ├── leaderboard.js
│   │   └── users.js
│   ├── services/
│   │   ├── AuthService.js
│   │   ├── CompetitionService.js
│   │   ├── LeaderboardService.js
│   │   ├── MatchService.js
│   │   └── UserService.js
│   ├── validators/
│   │   ├── auth.js
│   │   ├── competition.js
│   │   └── match.js
│   ├── utils/
│   │   ├── AppError.js
│   │   ├── ApiResponse.js
│   │   ├── catchAsync.js
│   │   ├── cache.js
│   │   └── logger.js
│   ├── websocket.js               # Socket.io setup
│   ├── app.js                     # Express app
│   └── server.js                  # Entry point
├── ecosystem.config.js            # PM2 config
├── .sequelizerc
├── .env
├── .env.production
└── package.json

frontend/
├── src/
│   ├── api/                       # API client (axios)
│   ├── assets/
│   ├── components/
│   │   ├── ui/                    # Reusable UI components
│   │   ├── competition/           # Competition-specific components
│   │   └── layout/                # Layout components
│   ├── composables/
│   │   ├── useAuth.js
│   │   ├── useSocket.js
│   │   ├── useCompetition.js
│   │   └── useLeaderboard.js
│   ├── layouts/
│   ├── router/
│   ├── stores/                    # Pinia or Vuex
│   ├── views/
│   ├── App.vue
│   └── main.ts
├── vite.config.ts
├── index.html
└── package.json
```

---

## Performance Patterns for 5K+ Users

### Database Query Optimization

```javascript
// ✅ Select only needed columns
const competitions = await Competition.findAll({
  attributes: ['id', 'title', 'slug', 'status', 'type', 'startDate', 'participantCount', 'imageUrl'],
  where: { status: 'open' },
  order: [['startDate', 'ASC']],
  limit: 20,
});

// ✅ Use separate:true for hasMany includes to avoid cartesian product
const competition = await Competition.findByPk(id, {
  include: [
    { model: User, as: 'creator', attributes: ['id', 'username', 'avatarUrl'] },
    {
      model: CompetitionUser,
      as: 'participants',
      separate: true,           // subquery instead of JOIN — prevents N×M row explosion
      where: { status: 'active' },
      include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatarUrl'] }],
      limit: 50,
    },
  ],
});

// ✅ Denormalize participant_count to avoid COUNT(*) on every list query
// Already in model: participantCount field updated on join/leave

// ✅ Use raw queries for complex leaderboards
const leaderboard = await sequelize.query(`
  SELECT
    us.user_id,
    u.username,
    u.avatar_url,
    us.score,
    us.wins,
    us.matches_played,
    RANK() OVER (ORDER BY us.score DESC, us.wins DESC) AS rank
  FROM user_scores us
  JOIN users u ON u.id = us.user_id
  WHERE us.competition_id = :competitionId
  ORDER BY rank
  LIMIT :limit OFFSET :offset
`, {
  replacements: { competitionId, limit, offset },
  type: QueryTypes.SELECT,
});
```

### Caching Hot Data

```javascript
const cache = require('../utils/cache');

// Cache active competitions for 30 seconds
async getActiveCompetitions() {
  return cache.getOrSet('competitions:active', async () => {
    return Competition.findAll({
      where: { status: { [Op.in]: ['open', 'active'] } },
      attributes: ['id', 'title', 'slug', 'type', 'status', 'startDate', 'participantCount', 'imageUrl'],
      order: [['startDate', 'ASC']],
    });
  }, 30);
}

// Cache leaderboard top 100 for 5 seconds
async getTopLeaderboard(competitionId) {
  return cache.getOrSet(`leaderboard:top:${competitionId}`, async () => {
    return this.getLeaderboard(competitionId, { page: 1, limit: 100 });
  }, 5);
}

// Invalidate on score change
async onScoreUpdate(competitionId) {
  cache.del(`leaderboard:top:${competitionId}`);
}
```

---

This architecture provides a complete foundation for a competition platform handling 5000+ concurrent users with real-time updates, efficient database queries, proper state management, and clean separation of concerns.