<script>
    let { tone = 'info', children } = $props();
    const MAP = {
        ok:     ['var(--positive-bg)', 'var(--positive)'],
        due:    ['var(--caution-bg)',  'var(--caution)'],
        late:   ['var(--danger-bg)',   'var(--danger)'],
        info:   ['var(--info-bg)',     'var(--info)'],
        draft:  ['var(--bg-subtle)',   'var(--muted)'],
        accent: ['var(--accent-bg)',   'var(--accent)']
    };
    const colors = $derived(MAP[tone] || MAP.info);
</script>

<span class="chip" style:background={colors[0]} style:color={colors[1]}>
    <span class="dot" style:background={colors[1]}></span>
    {@render children?.()}
</span>

<style>
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 3px;
        white-space: nowrap;
    }
    .dot {
        width: 4px;
        height: 4px;
        border-radius: 999px;
    }
</style>
