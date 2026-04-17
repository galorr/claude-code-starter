---
name: codepilot-be
description: Orchestrate full end-to-end NestJS backend feature development from a Jira ticket — retrieving specs, designing API architecture, implementing controllers/services/modules, writing unit tests, validating output, and committing code. Use this skill when the user provides a Jira ticket link and wants the full backend development loop handled autonomously. Trigger on phrases like "implement this backend ticket", "build this API story", "start on this backend task", or when a Jira URL is pasted with backend/API context. This skill coordinates architecture, NestJS implementation, and API validation in sequence.
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue
---

# CodePilot BE — Autonomous NestJS Backend Feature Development

Full backend development loop from Jira ticket to Git push.

## Required Inputs
- Jira ticket URL
- (Optional) User availability: `available` | `unavailable`

## Development Loop

### Phase 1: Retrieve & Parse Ticket

Fetch ticket from Jira MCP:
```
Fields to extract:
- ticket.title
- ticket.description
- ticket.acceptanceCriteria
- ticket.apiContracts[]         (Swagger/OpenAPI links, API specs)
- ticket.relatedServices[]      (upstream/downstream services)
- ticket.relatedComponents[]
- ticket.databaseChanges[]      (migration requirements)
```

If fields are missing and user is unavailable → send clarification question, poll for response every 30 seconds.

Transition ticket to **In Progress** using `mcp__atlassian__getTransitionsForJiraIssue` + `mcp__atlassian__transitionJiraIssue` (look for a transition named "In Progress" or "In Progress - Direct").

### Phase 2: Analyze Existing Codebase & API Contracts

Before designing anything, understand the landscape:
- Scan the existing NestJS project structure (`apps/`, `libs/`, module boundaries)
- Identify existing modules, services, and controllers that relate to the ticket
- Review existing API contracts (Swagger decorators, DTOs, OpenAPI specs)
- Check for existing database entities/schemas related to the feature
- Identify shared libraries, utilities, and common patterns already in use

Store findings as `existingContext`.

#### 2b. Search Golden Repos for Patterns

Before designing the architecture, search known-good repositories for established patterns.
(See: `skills/_shared/references/sourcegraph-search.md`)

1. Identify the key technical concepts in the ticket (e.g., "guard", "interceptor", "DTO", "migration", "queue")
2. Search the backend golden repo for each concept:
   - Use `mcp__github__search_code` or `gh search code` to find canonical implementations
   - Look for file structure, naming conventions, decorator usage, DI patterns
3. Search shared libraries for utilities that might already solve part of the problem
4. Log what you found:
   ```
   Golden repo patterns found:
   - [pattern] from backend-golden/[file] — [how it applies to this ticket]
   - [shared utility] from shared-libs/[file] — [can reuse for X]
   ```

Store findings in `existingContext.goldenPatterns`.

#### 2c. Search Internal Documentation

Search Confluence for relevant architecture decisions and guidelines.
(See: `skills/_shared/references/documentation-search.md`)

1. Search for ADRs related to the feature area
2. Search for API design guidelines
3. Log references found:
   ```
   Documentation referenced:
   - [ADR/doc title] — [key constraint or guideline]
   ```

### Phase 3: Architecture Planning

Switch to architect mode. Produce:

```typescript
{
  modulePath: string;                    // Where the NestJS module lives
  module: {
    name: string;
    imports: string[];                   // Other modules to import
    controllers: string[];
    providers: string[];                 // Services, repositories, guards, etc.
    exports: string[];                   // What to expose to other modules
  };
  controllers: Array<{
    name: string;
    basePath: string;
    endpoints: Array<{
      method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
      path: string;
      description: string;
      params?: string[];
      queryParams?: string[];
      requestBody?: string;              // DTO class name
      responseBody?: string;             // DTO class name
      guards?: string[];
      interceptors?: string[];
      pipes?: string[];
    }>;
  }>;
  services: Array<{
    name: string;
    responsibility: string;
    dependencies: string[];              // Injected services
    methods: string[];
  }>;
  dtos: Array<{
    name: string;
    purpose: 'request' | 'response' | 'internal';
    validationRules: string[];           // class-validator decorators
  }>;
  entities: Array<{                      // Database entities if needed
    name: string;
    tableName: string;
    fields: string[];
    relations: string[];
  }>;
  guards: string[];
  interceptors: string[];
  pipes: string[];
  migrations: string[];                  // Database migration files if needed
}
```

Write plan to `architecture.md`.

**If a major architectural decision is needed** (module placement, database schema design, sync vs async, REST vs event-driven) → present 2-4 options to user before proceeding.

### Phase 4: Setup Git Branch

Follow the project's branch naming convention. Check recent `git log --oneline` to determine the pattern, then:
```bash
git checkout staging
git pull
git checkout -b feat-<TICKET-KEY>
```

### Phase 5: Implement Backend Feature

Implement following NestJS best practices and the architecture plan. Build in this order:

#### 5.1 — DTOs & Validation
```typescript
// Create request/response DTOs with class-validator decorators
import { IsString, IsNotEmpty, IsOptional, IsNumber } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateFeatureDto {
  @ApiProperty({ description: '...' })
  @IsString()
  @IsNotEmpty()
  name: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  priority?: number;
}
```

#### 5.2 — Database Entities & Migrations (if needed)
- Create TypeORM/Prisma/Mongoose entities matching the architecture plan
- Generate and review migration files
- Never auto-run migrations — leave for user approval

#### 5.3 — Service Layer
```typescript
@Injectable()
export class FeatureService {
  constructor(
    @InjectRepository(FeatureEntity)
    private readonly featureRepo: Repository<FeatureEntity>,
  ) {}

  // Implement business logic here
  // Keep controllers thin, services fat
}
```

#### 5.4 — Controller Layer
```typescript
@ApiTags('feature')
@Controller('feature')
@UseGuards(AuthGuard)
export class FeatureController {
  constructor(private readonly featureService: FeatureService) {}

  @Post()
  @ApiOperation({ summary: '...' })
  @ApiResponse({ status: 201, type: FeatureResponseDto })
  async create(@Body() dto: CreateFeatureDto): Promise<FeatureResponseDto> {
    return this.featureService.create(dto);
  }
}
```

#### 5.5 — Guards, Interceptors & Pipes (if needed)
- Implement custom guards for authorization logic
- Add interceptors for response transformation, logging, or caching
- Create custom pipes for complex validation or transformation

#### 5.6 — Module Registration
```typescript
@Module({
  imports: [TypeOrmModule.forFeature([FeatureEntity])],
  controllers: [FeatureController],
  providers: [FeatureService],
  exports: [FeatureService],           // Only if other modules need it
})
export class FeatureModule {}
```
Register in the parent module's imports array.

#### 5.7 — Build Validation
```bash
npx nx build <project-name>
# or
npm run build
```
Fix any TypeScript compilation errors before proceeding.

### Phase 6: Unit Tests

Invoke `/unit-testing` for each new service and controller, or write tests directly:

```typescript
describe('FeatureService', () => {
  let service: FeatureService;
  let repo: Repository<FeatureEntity>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        FeatureService,
        { provide: getRepositoryToken(FeatureEntity), useClass: Repository },
      ],
    }).compile();

    service = module.get(FeatureService);
    repo = module.get(getRepositoryToken(FeatureEntity));
  });

  // Test each service method
  // Mock external dependencies
  // Test error cases and edge cases
});
```

Validation checks:
- All services have corresponding `.spec.ts` files
- All controller endpoints are tested
- Edge cases and error paths are covered
- `npx jest --passWithNoTests` passes with no failures

Returns: `{ status: "approved" | "rejected", failedTests[], coverageGaps[] }`

**If rejected** → fix failing tests, re-run validation.

### Phase 7: API Validation

Verify the implementation meets the ticket requirements:
- All acceptance criteria from the ticket are satisfied
- API endpoints match the architecture plan
- Swagger/OpenAPI decorators are present on all endpoints
- DTOs have proper validation decorators
- Error responses follow the project's error handling conventions
- No circular dependencies between modules

Run a final build check:
```bash
npx nx build <project-name>
npx nx test <project-name>
```

### Phase 8: Commit & Push (With Approval)

**Always ask the user before committing:**
> "Are you happy with the final implementation? Should I commit and push the code?"

If user is unavailable → send via notification channel, poll every 30s.

Only after explicit approval, follow the commit convention from recent `git log --oneline` (typically `feat: [TICKET-KEY] description`):
```bash
git add <specific files>
git commit -m "feat: [TICKET-KEY] <feature description>"
git push --set-upstream origin feat-<TICKET-KEY>
```

Then open a PR against `staging` using:
```bash
gh pr create --title "feat: [TICKET-KEY] ..." --body "..." --base staging
```

### Phase 9: CR Review & Fix

After the PR is created, poll for review comments:

```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/reviews --hostname <github_hostname>
```

Parse each review body for findings. For each finding:
1. Identify the severity (critical/medium/low/minor)
2. Locate the relevant file(s) in the codebase
3. Apply the fix
4. Note what was changed

After all findings are addressed:
```bash
git add <changed files>
git commit -m "fix: [TICKET-KEY] address CR findings"
git push
```

Re-fetch reviews to confirm no new blockers remain.

**Severity priority:**
- Critical / Medium → must fix before merge
- Low → fix if straightforward, otherwise note in PR comment
- Minor → fix if trivial, otherwise acknowledge in PR comment

## Key Rules

- Always get user approval before committing
- Use `architecture.md` as implementation contract
- Re-validate (build + tests) after every fix cycle
- Never push without user sign-off
- Never skip services/controllers defined in architecture plan
- Always transition Jira ticket to In Progress at the start of Phase 1
- Always follow the project's existing branch and commit naming conventions
- Keep controllers thin — business logic belongs in services
- Always use DTOs for request/response — never expose raw entities
- Use class-validator for input validation on all endpoints
- Add Swagger/OpenAPI decorators to every controller and endpoint
- Never auto-run database migrations — always require user approval
- Prefer constructor injection over property injection
- Use async/await consistently — avoid mixing with raw Promises
- Handle errors with NestJS exception filters, not try/catch in controllers
- Always search golden repos (backend golden repo, shared libraries) before designing architecture
- Log all patterns and documentation referenced in the architecture plan

## NestJS Best Practices (from docs.nestjs.com)

### Production Deployment Readiness
- Optimize `tsconfig.json` — enable `"incremental": true` and exclude test files from production builds
- Use `@nestjs/config` with `ConfigModule.forRoot()` for environment-specific configuration
- Validate env vars with `class-validator` and `class-transformer` via `validationSchema`
- Tree-shake unused modules — only import what each module needs

### Architecture Patterns
- **Modular design**: Each feature is a self-contained module with its own controllers, services, and DTOs
- **Separation of concerns**: Controllers handle HTTP, services handle business logic, repositories handle data
- **Dependency injection**: Let NestJS DI container manage service lifecycles — avoid manual instantiation
- **Guards for auth**: Use `@UseGuards()` with custom guards for authentication and role-based access control
- **Interceptors for cross-cutting concerns**: Logging, caching, response transformation
- **Pipes for validation**: Use `ValidationPipe` globally or per-endpoint for DTO validation
- **Exception filters**: Centralize error handling with custom exception filters

### Testing Strategy
- Unit test every service and controller using `@nestjs/testing` `Test.createTestingModule()`
- Mock external dependencies (database, HTTP, message queues) in unit tests
- Use `supertest` for integration/e2e tests against actual HTTP endpoints
- Aim for service-level coverage of business logic edge cases

## Dependency Injection Note

Before injecting services into feature modules:
- Analyze the dependency graph first
- Only inject services truly needed for core functionality
- Use module `exports` deliberately — don't export everything
- Watch for circular dependencies between modules — use `forwardRef()` only as a last resort
- Prefer event-based communication (EventEmitter2, message queues) for cross-module side effects
