<script lang="ts">
	import SegmentedControl from './SegmentedControl.svelte';

	type AuthType = 'basic' | 'digest' | 'ntlm';
	type HttpAuth = { authType: AuthType | ''; authUser: string; authPass: string };

	let {
		authType,
		authUser,
		authPass,
		onchange
	}: {
		authType: AuthType | '';
		authUser: string;
		authPass: string;
		onchange: (value: HttpAuth) => void;
	} = $props();

	function setType(next: AuthType | '') {
		onchange({ authType: next, authUser, authPass });
	}

	function setUser(value: string) {
		onchange({ authType, authUser: value, authPass });
	}

	function setPass(value: string) {
		onchange({ authType, authUser, authPass });
	}
</script>

<div class="space-y-3">
	<div class="space-y-1.5">
		<span class="block text-sm font-medium text-foreground">HTTP auth</span>
		<SegmentedControl
			value={authType}
			onchange={(v) => setType(v as AuthType | '')}
			options={[
				{ value: '', label: 'None' },
				{ value: 'basic', label: 'Basic' },
				{ value: 'digest', label: 'Digest' },
				{ value: 'ntlm', label: 'NTLM' }
			]}
		/>
	</div>

	{#if authType}
		<div class="space-y-1.5">
			<label for="auth-user" class="block text-sm font-medium text-foreground">Username</label>
			<input
				id="auth-user"
				type="text"
				value={authUser}
				oninput={(e) => setUser(e.currentTarget.value)}
				onchange={(e) => setUser(e.currentTarget.value)}
				placeholder="HTTP auth username"
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
			/>
		</div>
		<div class="space-y-1.5">
			<label for="auth-pass" class="block text-sm font-medium text-foreground">Password</label>
			<input
				id="auth-pass"
				type="password"
				value={authPass}
				oninput={(e) => setPass(e.currentTarget.value)}
				onchange={(e) => setPass(e.currentTarget.value)}
				placeholder="HTTP auth password"
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
			/>
		</div>
		<p class="text-xs text-muted-foreground">
			Sent alongside any cookies/session configured above.
			{#if authType === 'ntlm'}
				<span class="text-muted-foreground">
					Requires the optional dependency. Install with <span class="font-mono">pip install 'oswg[auth]'</span>.
				</span>
			{/if}
		</p>
	{/if}
</div>