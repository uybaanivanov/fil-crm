<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import { fmtShortRub, fmtRub, fmtMonth } from '$lib/format.js';

    const currentMonth = new Date().toISOString().slice(0, 7);

    let data = $state(null);
    let error = $state(null);
    let loading = $state(true);
    let addOpen = $state(false);
    let addAmount = $state('');
    let addCategory = $state('Уборка');
    let addDescription = $state('');
    let addDate = $state(new Date().toISOString().slice(0, 10));
    let addError = $state(null);

    const CATS = ['Уборка', 'ЖКХ', 'Ремонт', 'Комиссии', 'Прочее'];

    async function load() {
        loading = true;
        try {
            data = await api.get(`/finance/summary?month=${currentMonth}`);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function saveExpense() {
        addError = null;
        const amount = parseInt(addAmount, 10);
        if (!amount || amount <= 0) {
            addError = 'Сумма должна быть > 0';
            return;
        }
        try {
            await api.post('/expenses', {
                amount,
                category: addCategory,
                description: addDescription || null,
                occurred_at: addDate
            });
            addOpen = false;
            addAmount = '';
            addDescription = '';
            await load();
        } catch (e) {
            addError = e.message;
        }
    }

    onMount(load);

    // Мапим category → цвет для доната
    const CAT_COLORS = {
        'Уборка': 'var(--accent)',
        'ЖКХ': 'var(--positive)',
        'Ремонт': 'var(--caution)',
        'Комиссии': 'var(--info)'
    };
    function colorFor(cat) {
        return CAT_COLORS[cat] || 'var(--muted)';
    }
</script>

<PageHead title="Финансы" sub={fmtMonth(currentMonth)}
    back="Настройки" backOnClick={() => goto('/settings')}>
    {#snippet right()}
        <button class="add-expense" type="button" onclick={() => (addOpen = !addOpen)}>
            {addOpen ? '×' : '+'} расход
        </button>
    {/snippet}
</PageHead>

{#if addOpen}
    <div class="wrap">
        <Card pad={14}>
            <div class="form-grid">
                <label class="fl">
                    <span>Сумма ₽</span>
                    <input type="number" bind:value={addAmount} placeholder="4200" />
                </label>
                <label class="fl">
                    <span>Категория</span>
                    <select bind:value={addCategory}>
                        {#each CATS as c}<option value={c}>{c}</option>{/each}
                    </select>
                </label>
                <label class="fl full">
                    <span>Описание (опционально)</span>
                    <input type="text" bind:value={addDescription} placeholder="Лермонтова 58" />
                </label>
                <label class="fl">
                    <span>Дата</span>
                    <input type="date" bind:value={addDate} />
                </label>
            </div>
            {#if addError}<div class="form-err">{addError}</div>{/if}
            <div class="form-actions">
                <button class="save" type="button" onclick={saveExpense}>Сохранить</button>
            </div>
        </Card>
    </div>
{/if}

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !data}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Hero -->
    <div class="wrap">
        <div class="hero">
            <div class="hero-eyebrow">Чистая прибыль</div>
            <div class="hero-big">{fmtShortRub(data.net)}</div>
            <div class="hero-split">
                <div>
                    <div class="hero-label">Выручка</div>
                    <div class="hero-val">{fmtRub(data.revenue)}</div>
                </div>
                <div>
                    <div class="hero-label">Расходы</div>
                    <div class="hero-val">{fmtRub(data.expenses_total)}</div>
                </div>
            </div>
        </div>
    </div>

    {#if Object.keys(data.by_category).length > 0}
        <Section title="Расходы по категориям">
            <div class="wrap">
                <Card pad={14}>
                    {#each Object.entries(data.by_category) as [cat, amt], i}
                        {@const pct = data.expenses_total ? Math.round(amt / data.expenses_total * 100) : 0}
                        <div class="cat-row" class:last={i === Object.keys(data.by_category).length - 1}>
                            <span class="dot" style:background={colorFor(cat)}></span>
                            <span class="cat">{cat}</span>
                            <span class="amt">{fmtShortRub(amt)}</span>
                            <span class="pct">{pct}%</span>
                        </div>
                    {/each}
                </Card>
            </div>
        </Section>
    {/if}

    <Section title="Последние движения">
        <div class="wrap">
            {#if data.feed.length === 0}
                <Card pad={16}><div class="empty">Движений нет</div></Card>
            {:else}
                <Card pad={0}>
                    {#each data.feed as item, i}
                        <div class="feed-row" class:last={i === data.feed.length - 1}>
                            <div class="feed-icon" class:income={item.type === 'income'} class:expense={item.type === 'expense'}>
                                {item.type === 'income' ? '+' : '−'}
                            </div>
                            <div class="feed-body">
                                <div class="feed-label">{item.label}</div>
                                <div class="feed-date">{item.dt}</div>
                            </div>
                            <div class="feed-amt" class:pos={item.type === 'income'}>
                                {item.type === 'income' ? '+' : '−'} {fmtShortRub(item.amount)}
                            </div>
                        </div>
                    {/each}
                </Card>
            {/if}
        </div>
    </Section>
{/if}

<style>
    .add-expense {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
    }
    .wrap { padding: 0 20px 14px; }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty { color: var(--faint); text-align: center; padding: 12px; }

    .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .fl { display: flex; flex-direction: column; gap: 4px; }
    .fl.full { grid-column: 1 / -1; }
    .fl span {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--faint);
    }
    .fl input, .fl select {
        height: 40px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .form-err { color: var(--danger); font-size: 12px; margin-top: 8px; }
    .form-actions { margin-top: 12px; display: flex; justify-content: flex-end; }
    .save {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 10px 18px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }

    .hero {
        background: var(--ink);
        color: var(--bg);
        border-radius: 10px;
        padding: 18px;
    }
    .hero-eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--accent);
        letter-spacing: 0.1em;
    }
    .hero-big {
        font-family: var(--font-serif);
        font-size: 40px;
        line-height: 1;
        margin-top: 8px;
        letter-spacing: -0.5px;
    }
    .hero-split {
        display: flex;
        gap: 20px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    .hero-label {
        font-family: var(--font-mono);
        font-size: 9px;
        opacity: 0.6;
        text-transform: uppercase;
    }
    .hero-val {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
    }
    .cat-row {
        display: grid;
        grid-template-columns: 10px 1fr auto 42px;
        gap: 8px;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
        font-size: 13px;
    }
    .cat-row.last { border-bottom: none; }
    .dot { width: 8px; height: 8px; border-radius: 2px; }
    .cat { color: var(--ink); }
    .amt {
        font-family: var(--font-mono);
        color: var(--muted);
    }
    .pct {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-align: right;
    }
    .feed-row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
    }
    .feed-row.last { border-bottom: none; }
    .feed-icon {
        width: 30px;
        height: 30px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 16px;
        font-weight: 700;
    }
    .feed-icon.income { background: var(--positive-bg); color: var(--positive); }
    .feed-icon.expense { background: var(--bg-subtle); color: var(--muted); }
    .feed-body { flex: 1; }
    .feed-label { font-size: 13px; font-weight: 600; color: var(--ink); }
    .feed-date {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
    .feed-amt {
        font-family: var(--font-mono);
        font-size: 13px;
        font-weight: 600;
        color: var(--ink);
    }
    .feed-amt.pos { color: var(--positive); }
</style>
