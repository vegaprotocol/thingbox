<script>
	export let serverPublicKey
	export let adminToken
	export let generateAdminToken
	export let clearTemplateCache
</script>

<section>
	<h2>Admin tools</h2>
	<h3>Server public key</h3>
	<p>Items are encrypted at rest and must be encrypted to this ed25519 public key before uploading. Unencrypted items will be rejected by the server.</p>
	<pre>{serverPublicKey}</pre>
	<h3>Admin API token</h3>
	<p>Using the API to manage items requires an authentication token which can be generated here. For security, these generally have a short lifespan. </p>
	{#if adminToken}
		<details>
			<summary>View secret admin token</summary>
			<pre>{ adminToken }</pre>
		</details>
	{:else}
		<p><button on:click={generateAdminToken}>Generate API token</button></p>
	{/if}
	<br>
	<h3>Clear template cache</h3>
	<p>Click the button below to clear the template cache (e.g. after performing manual DB updates).</p>
	<p><button on:click={clearTemplateCache}>Clear cache</button></p>
	</section>