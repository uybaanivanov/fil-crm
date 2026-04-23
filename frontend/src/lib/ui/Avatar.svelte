<script>
    let { name = '', size = 36, accent = null, role = null } = $props();
    const initials = $derived(
        (name || '?').split(' ').map(s => s[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
    );
    const ROLE_AVATARS = { owner: '/avatars/owner.png', admin: '/avatars/admin.png', maid: '/avatars/maid.png' };
    const src = $derived(role && ROLE_AVATARS[role] ? ROLE_AVATARS[role] : null);
</script>

{#if src}
    <img
        class="avatar img"
        src={src}
        alt={name}
        width={size}
        height={size}
        style:width="{size}px"
        style:height="{size}px"
        style:border-radius="{size/2}px"
    />
{:else}
    <div
        class="avatar"
        style:width="{size}px"
        style:height="{size}px"
        style:border-radius="{size/2}px"
        style:font-size="{Math.round(size*0.33)}px"
        style:background={accent || 'var(--bg-subtle)'}
        style:color={accent ? '#fff' : 'var(--ink)'}
    >
        {initials}
    </div>
{/if}

<style>
    .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 600;
        flex-shrink: 0;
    }
    .avatar.img {
        object-fit: cover;
        image-rendering: pixelated;
        background: var(--bg-subtle);
    }
</style>
