<script>
	export let serverPublicKey
	export let adminToken
	export let generateAdminToken
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
		<button on:click={generateAdminToken}>Generate API token</button>
	{/if}
</section>