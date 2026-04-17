# Angular Review Checklist

Framework-specific review checklist for Angular 20+ code.
Apply this checklist when reviewing PRs that contain Angular components, services, or templates.

## Checklist

For each item, report **PASS**, **FAIL**, or **N/A**. Explain every FAIL and provide a corrected snippet.

### TypeScript
- [ ] `strict: true` is enabled in `tsconfig.json`
- [ ] No `any` types without justification
- [ ] Types are explicit where inference is not obvious

### Components
- [ ] `standalone: true` is **not** set explicitly (it is the default in Angular 17+)
- [ ] `ChangeDetectionStrategy.OnPush` is set
- [ ] Uses `input()` / `output()` functions, not `@Input()` / `@Output()` decorators
- [ ] No `@HostBinding` / `@HostListener` (uses `host: {}` instead)
- [ ] Static images use `NgOptimizedImage`

### State & Reactivity
- [ ] Local state uses `signal()`
- [ ] Derived state uses `computed()`
- [ ] No `.mutate()` calls on signals
- [ ] `effect()` used sparingly and only for side effects (e.g., syncing to `localStorage`)

### Templates
- [ ] Uses `@if`, `@for`, `@switch` (not `*ngIf`, `*ngFor`, `*ngSwitch`)
- [ ] Uses `class` bindings (not `ngClass`)
- [ ] Uses `style` bindings (not `ngStyle`)
- [ ] Every `@for` loop has a `track` expression
- [ ] No complex logic in the template — moved to `computed()` or component class
- [ ] Uses `@defer` blocks for heavy UI sections not needed on first render

### Forms
- [ ] Reactive Forms preferred over Template-driven Forms
- [ ] Form groups are explicitly typed: `FormGroup<{ field: FormControl<type> }>`

### Services & DI
- [ ] Uses `inject()` for dependency injection (not constructor injection)
- [ ] Services have single responsibility
- [ ] Singleton services use `providedIn: 'root'`

### Routing
- [ ] Feature routes use `loadComponent` or `loadChildren` (lazy loading)
- [ ] Guards use the functional `CanActivateFn` shape (not class-based guards)

### Performance
- [ ] Avoids unnecessary subscriptions; prefers signals and `async` pipe
- [ ] No heavy computation in templates without `computed()`

## Correct Component Example

```typescript
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-greeting',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<p>{{ message() }}</p>`,
})
export class GreetingComponent {
  name = input.required<string>();
  message = computed(() => `Hello, ${this.name()}!`);
}
```
