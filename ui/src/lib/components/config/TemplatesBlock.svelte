<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import { templatesVersion } from '$lib/stores/templates';
	import type { PresetsResponse, TemplateInfo } from '$lib/api/types';

	let {
		type,
		onApply
	}: {
		type: 'generate' | 'scrape';
		onApply: (config: Record<string, unknown>) => void;
	} = $props();

	let presets = $state<PresetsResponse['presets']>({});
	let templates = $state<TemplateInfo[]>([]);
	let appliedPreset = $state('');
	let appliedTemplate = $state('');

	async function loadTemplates() {
		try {
			const res = await endpoints.listTemplates();
			templates = res.templates;
		} catch {
			templates = [];
		}
	}

	$effect(() => {
		endpoints.getPresets().then((r) => (presets = r.presets));
		loadTemplates();
		void $templatesVersion;
	});

	function applyPreset(value: string) {
		if (!value || !presets[value]) return;
		appliedPreset = value;
		onApply({ ...presets[value] });
	}

	async function applyTemplate(value: string) {
		if (!value) return;
		try {
			const record = await endpoints.getTemplate(value);
			appliedTemplate = value;
			onApply({ ...record.config });
		} catch {
			// template may have been deleted; refresh the list
			loadTemplates();
		}
	}
</script>

<details class="rounded-md border border-border bg-muted/20">
	<summary class="cursor-pointer select-none px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
		Templates &amp; Presets
	</summary>

	<div class="space-y-3 p-3">
		<div class="space-y-1.5">
			<label for="template-preset" class="block text-sm font-medium text-foreground">Preset</label>
			<select
				id="template-preset"
				value={appliedPreset}
				onchange={(e) => applyPreset(e.currentTarget.value)}
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
			>
				<option value="">None</option>
				{#each Object.keys(presets) as presetName}
					<option value={presetName}>{presetName}</option>
				{/each}
			</select>
		</div>

		<div class="space-y-1.5">
			<label for="template-select" class="block text-sm font-medium text-foreground">Template</label>
			<select
				id="template-select"
				value={appliedTemplate}
				onchange={(e) => applyTemplate(e.currentTarget.value)}
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
			>
				<option value="">None</option>
				{#each templates as t}
					<option value={t.name}>{t.name} ({t.type})</option>
				{/each}
			</select>
		</div>
	</div>
</details>