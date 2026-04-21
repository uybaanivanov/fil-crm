<script>
    let {
        title = '',
        sub = null,
        left = null,
        right = null,
        onclick = null,
        last = false
    } = $props();
</script>

<button class="row" class:last onclick={onclick} type="button">
    {#if left}<div class="left">{@render left()}</div>{/if}
    <div class="body">
        <div class="title">{title}</div>
        {#if sub}<div class="sub">{@render sub()}</div>{/if}
    </div>
    {#if right}<div class="right">{@render right()}</div>{/if}
</button>

<style>
    .row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
        background: transparent;
        border-top: none;
        border-left: none;
        border-right: none;
        width: 100%;
        text-align: left;
        cursor: pointer;
    }
    .row.last { border-bottom: none; }
    .row:hover { background: var(--card-hi); }
    .body { flex: 1; min-width: 0; }
    .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        letter-spacing: -0.1px;
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
</style>
