<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { getUser } from '$lib/auth.js';

    onMount(() => {
        const user = getUser();
        if (!user) goto('/login');
        else goto(user.role === 'maid' ? '/cleaning' : '/apartments');
    });
</script>
