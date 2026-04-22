# Inline-редактирование полей карточки квартиры — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сделать все поля паспорта квартиры редактируемыми прямо на `/apartments/[id]` через один универсальный компонент `InlineEdit` (клик → инпут → Enter/blur сохраняет, Escape откатывает).

**Architecture:** Один новый компонент `InlineEdit.svelte` (текст/число, с серым пунктиром снизу, Enter/blur → PATCH, Escape откат, показ ошибок сервера). Интегрируется в `[id]/+page.svelte` — переписываем секцию «Характеристики» на `InlineEdit`-строки + общий хелпер `patchField(field, value)` с локальным обновлением `apt[field]` без refetch. Отдельная обработка ошибки «baseline обязателен» — баннер + скролл к блоку baseline.

**Tech Stack:** SvelteKit 5 runes (`$state`, `$derived`, `$props`, `$effect`). Без новых зависимостей.

**Spec:** `docs/superpowers/specs/2026-04-22-inline-edit-apartment-design.md`

---

## File Structure

- Create: `frontend/src/lib/ui/InlineEdit.svelte` — универсальный inline-editor (текст/число, save on Enter/blur, cancel on Escape, показ ошибки).
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte` — переписываем секцию «Характеристики» на `InlineEdit`, добавляем хелпер `patchField`, обработку ошибки «baseline обязателен» + баннер.

Без бэковых изменений — `PATCH /apartments/{id}` уже принимает все нужные поля и валидирует.

---

## Task 1: Компонент InlineEdit

**Files:**
- Create: `frontend/src/lib/ui/InlineEdit.svelte`

- [ ] **Step 1: Создать компонент**

Полный файл `frontend/src/lib/ui/InlineEdit.svelte`:

```svelte
<!--
  Inline-редактор одного поля.
  Показ: текст с пунктирной линией снизу (серый var(--border)).
  Клик: in-place превращается в <input>.
  Enter или blur (если изменено) → onSave(newValue).
  Escape → откат без запроса.
  Ошибка от onSave → красный border + сообщение под полем, остаётся в edit.

  Пропсы:
    value       — текущее значение (string|number|null)
    type        — 'text' | 'number'
    placeholder — показывается в режиме показа если value == null
    format      — опциональная функция форматирования для режима показа
    onSave      — (newValue) => Promise<void>; throw/reject = ошибка
    readonly    — если true, только текст без возможности редактировать
-->
<script>
    let {
        value,
        type = 'text',
        placeholder = '—',
        format = null,
        onSave,
        readonly = false,
    } = $props();

    let editing = $state(false);
    let draft = $state('');
    let saving = $state(false);
    let error = $state(null);
    let inputEl = $state(null);

    function displayText() {
        if (value == null || value === '') return placeholder;
        return format ? format(value) : String(value);
    }

    function startEdit() {
        if (readonly || saving) return;
        draft = value == null ? '' : String(value);
        error = null;
        editing = true;
        // фокус после ре-рендера
        queueMicrotask(() => {
            inputEl?.focus();
            inputEl?.select?.();
        });
    }

    function cancel() {
        editing = false;
        error = null;
        draft = '';
    }

    function parseDraft() {
        if (type === 'number') {
            const s = String(draft).trim();
            if (s === '') return null;
            const n = Number(s);
            if (!Number.isFinite(n)) {
                throw new Error('Нужно число');
            }
            return n;
        }
        const s = String(draft);
        return s === '' ? null : s;
    }

    async function save() {
        let parsed;
        try {
            parsed = parseDraft();
        } catch (e) {
            error = e.message;
            return;
        }
        if (parsed === value) {
            editing = false;
            return;
        }
        saving = true;
        error = null;
        try {
            await onSave(parsed);
            editing = false;
        } catch (e) {
            error = e?.message || 'Ошибка сохранения';
        } finally {
            saving = false;
        }
    }

    function onKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            save();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancel();
        }
    }

    function onBlur() {
        // если уже идёт save — не дёргаем повторно
        if (saving) return;
        // если draft равен исходному — просто отменяем
        const originalAsStr = value == null ? '' : String(value);
        if (draft === originalAsStr) {
            cancel();
            return;
        }
        save();
    }
</script>

{#if readonly}
    <span class="ie-text ie-readonly">{displayText()}</span>
{:else if editing}
    <span class="ie-wrap" class:has-error={!!error} class:saving>
        <input
            bind:this={inputEl}
            bind:value={draft}
            type={type === 'number' ? 'number' : 'text'}
            disabled={saving}
            onkeydown={onKeydown}
            onblur={onBlur}
        />
        {#if error}
            <span class="ie-err">{error}</span>
        {/if}
    </span>
{:else}
    <button type="button" class="ie-btn" onclick={startEdit}>
        <span class="ie-text" class:empty={value == null || value === ''}>
            {displayText()}
        </span>
    </button>
{/if}

<style>
    .ie-btn {
        background: none;
        border: none;
        padding: 0;
        margin: 0;
        cursor: text;
        text-align: inherit;
        font: inherit;
        color: inherit;
    }
    .ie-text {
        display: inline-block;
        border-bottom: 1px dashed var(--border);
        padding-bottom: 1px;
        transition: border-color 0.15s;
    }
    .ie-btn:hover .ie-text { border-bottom-color: var(--muted); }
    .ie-text.empty {
        color: var(--faint);
        font-style: italic;
    }
    .ie-text.ie-readonly {
        border-bottom: none;
    }
    .ie-wrap {
        display: inline-flex;
        flex-direction: column;
        gap: 2px;
    }
    .ie-wrap input {
        border: none;
        outline: none;
        background: transparent;
        font: inherit;
        color: var(--ink);
        border-bottom: 1px dashed var(--accent);
        padding: 0;
        width: 100%;
        min-width: 80px;
    }
    .ie-wrap.has-error input {
        border-bottom-color: var(--danger, #c33);
    }
    .ie-wrap.saving input {
        opacity: 0.6;
    }
    .ie-err {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--danger, #c33);
    }
</style>
```

- [ ] **Step 2: Проверить билд**

Run:
```bash
cd frontend && PATH=/home/uybaan/.nvm/versions/node/v25.8.1/bin:$PATH npm run build
```

Expected: `✓ built`, `✔ done`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ui/InlineEdit.svelte
git commit -m "feat(frontend): InlineEdit — inline-редактор поля (Enter/blur save, Esc cancel)"
```

---

## Task 2: Хелпер patchField + обработка ошибки baseline

**Files:**
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Добавить импорт и стейт**

В `<script>`-блок добавить импорт:

```javascript
import InlineEdit from '$lib/ui/InlineEdit.svelte';
```

Добавить стейт рядом с другими `$state` (после существующих `baseline*`-переменных):

```javascript
let baselineRequired = $state(false);
let baselineBlockEl = $state(null);
```

- [ ] **Step 2: Добавить хелпер patchField**

После существующей функции `saveBaseline()` добавить:

```javascript
async function patchField(field, value) {
    try {
        await api.patch(`/apartments/${aptId}`, { [field]: value });
        apt[field] = value; // локальное обновление без refetch
        baselineRequired = false;
    } catch (e) {
        const msg = e?.message || '';
        if (msg.includes('monthly_rent') || msg.includes('monthly_utilities')) {
            baselineRequired = true;
            queueMicrotask(() => {
                baselineBlockEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }
        throw e; // InlineEdit покажет сообщение в своём err-блоке
    }
}
```

- [ ] **Step 3: Расширить saveBaseline — сбрасывать баннер**

В существующей функции `saveBaseline()` сразу после успешного `api.patch(...)` (перед `editingBaseline = false`) добавить:

```javascript
baselineRequired = false;
```

- [ ] **Step 4: Привязать ref к секции baseline**

В разметке найти строку `<Section title="Обязательные суммы">` и заменить на:

```svelte
<div bind:this={baselineBlockEl}>
<Section title="Обязательные суммы">
```

И соответственно закрыть `</div>` после `</Section>` этой секции.

- [ ] **Step 5: Добавить баннер**

Прямо перед `<div bind:this={baselineBlockEl}>` добавить:

```svelte
{#if baselineRequired}
    <div class="baseline-banner">
        Сначала заполни обязательные суммы (аренда/ЖКХ) ниже — без них нельзя редактировать другие поля.
    </div>
{/if}
```

Стиль в `<style>`:

```css
.baseline-banner {
    margin: 0 20px 12px;
    padding: 10px 12px;
    background: var(--danger-bg, #fde);
    color: var(--danger, #c33);
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.4;
}
```

- [ ] **Step 6: Проверить билд**

Run:
```bash
cd frontend && PATH=/home/uybaan/.nvm/versions/node/v25.8.1/bin:$PATH npm run build
```

Expected: успех.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/routes/apartments/\[id\]/+page.svelte
git commit -m "feat(frontend): patchField хелпер + баннер обязательного baseline"
```

---

## Task 3: Заменить «Характеристики» на InlineEdit

**Files:**
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Переписать секцию «Характеристики»**

Найти блок:

```svelte
<!-- Характеристики -->
<Section title="Характеристики">
    <div class="wrap">
        <Card pad={0}>
            {@const rows = [
                ['Тип', apt.rooms || '—'],
                ['Площадь', apt.area_m2 ? apt.area_m2 + ' м²' : '—'],
                ['Этаж', apt.floor || '—'],
                ['Район', apt.district || '—'],
                ['Цена/ночь', fmtRub(apt.price_per_night)],
                ['Нужна уборка', apt.needs_cleaning
                    ? (apt.cleaning_due_at ? 'К ' + fmtDateTime(apt.cleaning_due_at) : 'Да')
                    : 'Нет']
            ]}
            {#each rows as [k, v], i}
                <div class="ch-row" class:last={i === rows.length - 1}>
                    <span class="ch-key">{k}</span>
                    <span class="ch-val">{v}</span>
                    {#if k === 'Нужна уборка' && isOverdue}
                        <span class="overdue"><Chip tone="late">Просрочено</Chip></span>
                    {/if}
                </div>
            {/each}
        </Card>
    </div>
</Section>
```

И полностью заменить на:

```svelte
<!-- Характеристики -->
<Section title="Характеристики">
    <div class="wrap">
        <Card pad={0}>
            <div class="ch-row">
                <span class="ch-key">Название</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.title}
                        type="text"
                        placeholder="Название"
                        onSave={v => patchField('title', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Адрес</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.address}
                        type="text"
                        placeholder="Адрес"
                        onSave={v => patchField('address', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Тип</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.rooms}
                        type="text"
                        placeholder="Напр. 1-комн"
                        onSave={v => patchField('rooms', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Площадь</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.area_m2}
                        type="number"
                        placeholder="— м²"
                        format={v => v + ' м²'}
                        onSave={v => patchField('area_m2', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Этаж</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.floor}
                        type="text"
                        placeholder="Этаж"
                        onSave={v => patchField('floor', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Район</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.district}
                        type="text"
                        placeholder="Район"
                        onSave={v => patchField('district', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Цена/ночь</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.price_per_night}
                        type="number"
                        placeholder="₽"
                        format={fmtRub}
                        onSave={v => patchField('price_per_night', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Позывной</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.callsign}
                        type="text"
                        placeholder="позывной"
                        onSave={v => patchField('callsign', v)}
                    />
                </span>
            </div>
            <div class="ch-row">
                <span class="ch-key">Обложка</span>
                <span class="ch-val">
                    <InlineEdit
                        value={apt.cover_url}
                        type="text"
                        placeholder="URL картинки"
                        onSave={v => patchField('cover_url', v)}
                    />
                </span>
            </div>
            <div class="ch-row last">
                <span class="ch-key">Нужна уборка</span>
                <span class="ch-val">
                    {apt.needs_cleaning
                        ? (apt.cleaning_due_at ? 'К ' + fmtDateTime(apt.cleaning_due_at) : 'Да')
                        : 'Нет'}
                </span>
                {#if isOverdue}
                    <span class="overdue"><Chip tone="late">Просрочено</Chip></span>
                {/if}
            </div>
        </Card>
    </div>
</Section>
```

- [ ] **Step 2: Проверить билд**

Run:
```bash
cd frontend && PATH=/home/uybaan/.nvm/versions/node/v25.8.1/bin:$PATH npm run build
```

Expected: успех.

- [ ] **Step 3: Ручной смок в браузере**

Поднять дев (бэк + фронт) и открыть квартиру с заполненным baseline:
1. Клик по «Цена/ночь» → появляется input с текущим значением.
2. Ввести новое число → Enter → значение обновилось в карточке без перезагрузки.
3. Клик → Escape → значение откатилось.
4. Клик → очистить → Enter → если поле обязательное (title), сервер вернёт 400, увидеть красный border + сообщение.
5. Клик по «Обложка» → вставить URL → Enter → cover-preview в шапке обновился.
6. Открыть квартиру БЕЗ baseline → попробовать изменить название → появляется красный баннер «Сначала заполни обязательные суммы» + скролл к блоку baseline. Заполнить baseline → баннер уходит → редактирование названия работает.

Если что-то из пунктов 1-6 не работает — исправить в том же шаге.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/apartments/\[id\]/+page.svelte
git commit -m "feat(frontend): InlineEdit для всех полей паспорта квартиры"
```

---

## Task 4: Финальный деплой

- [ ] **Step 1: Мерж в master и push**

```bash
git stash push -m "CLAUDE.md wip" -- CLAUDE.md 2>/dev/null; true
git checkout master
git merge --ff-only feat/prototype
git push origin master
git push origin feat/prototype
git checkout feat/prototype
git stash pop 2>/dev/null; true
```

Expected: fast-forward succeeds, обе ветки запушены.

- [ ] **Step 2: Задеплоить на прод**

```bash
ssh cms-gen-bot "cd /opt/fil-crm && git pull"
ssh cms-gen-bot 'cd /opt/fil-crm/frontend && . $HOME/.nvm/nvm.sh && nvm use node >/dev/null && npm run build'
ssh cms-gen-bot 'tmux send-keys -t fil-crm:backend C-c; sleep 1; tmux send-keys -t fil-crm:backend "uv run --env-file .env uvicorn backend.main:app --reload --port 8000" C-m'
```

Expected: `git pull` fast-forwards, build успешен, бэк рестартнут (`Application startup complete.`).

Миграции не нужны — бэковых изменений в этом релизе нет.

- [ ] **Step 3: Смок на проде**

Открыть sakha.gay, зайти на любую квартиру, кликнуть по полю «Цена/ночь», изменить — сохраняется. Если нет — diagnose через `tmux capture-pane -t fil-crm:backend -p | tail -20` и devtools в браузере.

---

## Out of Scope (напоминание из spec)

- `PageHead` не переписываем — `title`/`address` в шапке обновляются автоматически через реактивность `apt`.
- «Нужна уборка» через `InlineEdit` не делаем — остаётся существующий `CleaningDueDialog`.
- Фронтовых юнит-тестов не пишем.
- Клиентская валидация форматов (URL, email и т.п.) не делаем — полагаемся на серверные `Field()`.
