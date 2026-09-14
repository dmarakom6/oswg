<script lang="ts">
	import { notifications } from '$lib/stores/notifications';

	const TYPE_STYLES = {
		success: 'border-success/50 text-success',
		error: 'border-destructive/50 text-destructive',
		warning: 'border-amber-500/50 text-amber-600 dark:text-amber-400',
		info: 'border-primary/50 text-foreground'
	};

	const TYPE_ICONS = {
		success: '✓',
		error: '✕',
		warning: '⚠',
		info: 'ℹ'
	};
</script>

{#if $notifications.length > 0}
	<div
		class="pointer-events-none fixed right-4 top-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
		role="status"
		aria-live="polite"
	>
		{#each $notifications as notification}
			<div
				class="pointer-events-auto flex items-start gap-2 rounded-md border border-border bg-background p-3 shadow-lg"
				style="animation: fade-in 150ms ease"
			>
				<span class="mt-0.5 shrink-0 text-sm {TYPE_STYLES[notification.type]}">
					{TYPE_ICONS[notification.type]}
				</span>
				<p class="flex-1 text-sm text-foreground">{notification.message}</p>
				<button
					type="button"
					onclick={() => notifications.dismiss(notification.id)}
					class="shrink-0 text-xs text-muted-foreground transition-colors hover:text-foreground"
					aria-label="Dismiss notification"
				>✕</button>
			</div>
		{/each}
	</div>
{/if}