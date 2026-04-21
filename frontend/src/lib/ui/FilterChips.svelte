<script>
    // items: [{ label, count?, value, active? }]
    let { items = [], onselect = null } = $props();
</script>

<div class="chips">
    {#each items as item}
        <button
            class="chip"
            class:active={item.active}
            type="button"
            onclick={() => onselect?.(item.value)}
        >
            {item.label}
            {#if item.count != null}<span class="count">{item.count}</span>{/if}
        </button>
    {/each}
</div>

<style>
    .chips {
        display: flex;
        gap: 8px;
        padding: 0 20px 14px;
        overflow-x: auto;
    }
    .chip {
        padding: 6px 12px;
        border-radius: 999px;
        background: var(--card);
        color: var(--ink);
        border: 1px solid var(--border);
        font-size: 12px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
        cursor: pointer;
    }
    .chip.active {
        background: var(--ink);
        color: var(--bg);
        border-color: var(--ink);
    }
    .count {
        font-family: var(--font-mono);
        font-size: 10px;
        opacity: 0.6;
    }
</style>
