<!--
  Секция «Расходы по квартире» — список с переключателем месяца и формой добавления.
-->
<script>
    import { api } from '$lib/api.js';
    import { EXPENSE_CATEGORIES, categoryLabel } from '$lib/expenseCategories.js';
    import { fmtRub, fmtDate } from '$lib/format.js';

    let { apartmentId } = $props();

    let month = $state(new Date().toISOString().slice(0, 7));
    let items = $state([]);
    let loading = $state(false);
    let error = $state(null);

    let addOpen = $state(false);
    let addAmount = $state('');
    let addCategory = $state('internet');
    let addDescription = $state('');
    let addDate = $state(new Date().toISOString().slice(0, 10));
    let addError = $state(null);

    async function load() {
        loading = true;
        error = null;
        try {
            items = await api.get(
                `/expenses?apartment_id=${apartmentId}&month=${month}`
            );
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        if (apartmentId) load();
    });

    function shiftMonth(delta) {
        const [y, m] = month.split('-').map(Number);
        const d = new Date(y, m - 1 + delta, 1);
        month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    }

    async function saveExpense() {
        addError = null;
        const amount = parseInt(addAmount, 10);
        if (!amount || amount <= 0) { addError = 'Сумма > 0'; return; }
        try {
            await api.post('/expenses', {
                amount,
                category: addCategory,
                description: addDescription || null,
                occurred_at: addDate,
                apartment_id: apartmentId,
            });
            addOpen = false;
            addAmount = '';
            addDescription = '';
            await load();
        } catch (e) {
            addError = e.message;
        }
    }

    const total = $derived(items.reduce((s, x) => s + x.amount, 0));
</script>

<div class="expenses">
    <header>
        <button type="button" class="nav" onclick={() => shiftMonth(-1)}>‹</button>
        <span class="month">{month}</span>
        <button type="button" class="nav" onclick={() => shiftMonth(1)}>›</button>
        <span class="total">{fmtRub(total)}</span>
        <button type="button" class="add" onclick={() => (addOpen = !addOpen)}>
            {addOpen ? '×' : '+'}
        </button>
    </header>

    {#if addOpen}
        <div class="add-form">
            <input type="number" placeholder="Сумма" bind:value={addAmount} />
            <select bind:value={addCategory}>
                {#each EXPENSE_CATEGORIES as c}
                    <option value={c.value}>{c.label}</option>
                {/each}
            </select>
            <input type="date" bind:value={addDate} />
            <input type="text" placeholder="Описание" bind:value={addDescription} />
            {#if addError}<div class="err">{addError}</div>{/if}
            <button type="button" class="save" onclick={saveExpense}>Сохранить</button>
        </div>
    {/if}

    {#if loading}
        <div class="state">Загрузка…</div>
    {:else if error}
        <div class="state err">{error}</div>
    {:else if items.length === 0}
        <div class="state muted">Нет расходов</div>
    {:else}
        <ul class="list">
            {#each items as e}
                <li class="row">
                    <span class="date">{fmtDate(e.occurred_at)}</span>
                    <span class="cat">
                        {categoryLabel(e.category)}
                        {#if e.source === 'auto'}<span class="auto" title="Авто-генерация">⚙</span>{/if}
                    </span>
                    {#if e.description}<span class="desc">{e.description}</span>{/if}
                    <span class="amt">{fmtRub(e.amount)}</span>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .expenses { padding: 0 20px 14px; }
    header {
        display: flex; align-items: center; gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .nav {
        background: none; border: none; cursor: pointer;
        font-size: 18px; color: var(--muted);
    }
    .month { font-family: var(--font-mono); font-size: 12px; color: var(--ink); }
    .total { margin-left: auto; font-family: var(--font-mono); font-weight: 600; color: var(--ink); }
    .add {
        margin-left: 8px;
        background: var(--accent); color: #fff; border: none;
        width: 28px; height: 28px; border-radius: 6px; cursor: pointer;
    }
    .add-form {
        display: flex; flex-direction: column; gap: 6px;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .add-form input, .add-form select {
        height: 32px; padding: 0 8px;
        border: 1px solid var(--border); border-radius: 4px;
        background: var(--card); color: var(--ink);
    }
    .save {
        height: 34px; border: none; border-radius: 4px;
        background: var(--accent); color: #fff; font-weight: 600; cursor: pointer;
    }
    .list { list-style: none; padding: 0; margin: 0; }
    .row {
        display: grid;
        grid-template-columns: 68px 1fr auto;
        gap: 6px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
        font-size: 13px;
    }
    .date { font-family: var(--font-mono); font-size: 11px; color: var(--faint); }
    .cat { color: var(--ink); }
    .auto { margin-left: 4px; color: var(--faint); }
    .desc { grid-column: 2; font-size: 11px; color: var(--muted); }
    .amt { font-family: var(--font-mono); font-weight: 600; color: var(--ink); }
    .state { padding: 14px 0; text-align: center; color: var(--faint); font-size: 12px; }
    .state.err { color: var(--danger, #c33); }
    .state.muted { color: var(--faint); }
    .err { color: var(--danger, #c33); font-size: 11px; }
</style>
