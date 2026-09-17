<script lang="ts">
	let {
		value,
		onchange,
		options,
		disabled = false
	}: {
		value: number | string;
		onchange: (val: number | string) => void;
		options: { value: number | string; label: string }[];
		disabled?: boolean;
	} = $props();
</script>

<div class="inline-flex max-w-full overflow-x-auto rounded-md border border-border {disabled ? 'opacity-50' : ''}">
	{#each options as opt}
		<button
			type="button"
			disabled={disabled}
			class="shrink-0 whitespace-nowrap px-3 py-1.5 text-sm transition-colors first:rounded-l-md last:rounded-r-md
				{disabled ? 'cursor-not-allowed'
				: value === opt.value
				? 'bg-primary text-primary-foreground'
				: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}"
			onclick={() => onchange(opt.value)}
		>
			{opt.label}
		</button>
	{/each}
</div>
