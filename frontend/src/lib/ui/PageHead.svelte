<script>
    let { title = '', sub = null, right = null, back = null, backOnClick = null } = $props();
</script>

<div class="head">
    {#if back}
        <div class="back-row">
            <button class="back" onclick={backOnClick} type="button">
                <svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true">
                    <path d="M7 1L1 7l6 6" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" />
                </svg>
                <span>{back}</span>
            </button>
            {#if right}<div class="right">{@render right()}</div>{/if}
        </div>
    {/if}
    <div class="title-row" class:with-back={!!back}>
        <div class="title-wrap">
            <h1 class="title">{title}</h1>
            {#if sub}<div class="sub">{sub}</div>{/if}
        </div>
        {#if !back && right}<div class="right">{@render right()}</div>{/if}
    </div>
</div>

<style>
    .back-row {
        padding: 10px 16px 4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .back {
        background: transparent;
        border: none;
        padding: 0;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--accent);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
    }
    .title-row {
        padding: 14px 20px 18px;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 12px;
    }
    .title-row.with-back { padding-top: 6px; }
    .title {
        font-family: var(--font-serif);
        font-size: 32px;
        line-height: 1;
        letter-spacing: -0.5px;
        color: var(--ink);
        font-weight: 400;
        margin: 0;
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--faint);
        margin-top: 8px;
    }
    .right { flex-shrink: 0; }
</style>
