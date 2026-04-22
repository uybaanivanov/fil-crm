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
        if (saving) return;
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
