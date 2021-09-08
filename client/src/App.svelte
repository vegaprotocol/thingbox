<script>
	import api from './api.js'
	import Itemlist from './ItemList.svelte'
	import Admin from './Admin.svelte'

	let items
	let authUrl
	let screenName = localStorage.getItem('screen_name')
	let isAdminUser
	let inAdminMode
	let serverPublicKey
	let adminToken

	async function getApiData() {
		try {
			({ screenName, admin: isAdminUser } = await api.getUser())
			if (screenName) {
				localStorage.setItem('screen_name', screenName)
			}
			items = await api.getItems()
			serverPublicKey = await api.getPublicKey()
		}
		catch (e) {
			if (e.message === 'unauthorised') {
				authUrl = await api.auth()	
			}
		}
	}

	async function logout() {
		await api.logout()
		authUrl = await api.auth()
		screenName = null
		items = null
	}

	async function toggleAdminMode() {
		inAdminMode = !inAdminMode
	}

	async function generateAdminToken() {
		if (!inAdminMode) return null
		try {
			adminToken = await api.getAdminToken()
		}
		catch {
			await getApiData()
			return null
		}
	}

	getApiData()

</script>

<main>
	<header>
		<nav>
			<h1>Fairground incentives 🎡</h1>
			{#if screenName} 
				<p>	
					<a on:click={logout} href="#logout">Log out @{screenName}</a>
					{#if isAdminUser}
					/ <a href="#toggle-admin" on:click={toggleAdminMode}>{inAdminMode ? 'home' : 'admin'}</a>
					{/if}
				</p>
			{/if}
		</nav>
	</header>
	{#if !screenName || authUrl}
		<section>
			<p>Sign in with Twitter to access your Fairground incentives claim links. You must use the same Twitter account that you used to register with Vega Fairground.</p>
			{#if authUrl}
				<p>👉 <a href={authUrl}>Connect my Twitter account</a></p>
			{/if}
		</section>
	{:else if items !== undefined && !inAdminMode}
		<Itemlist {items} />
	{:else if items !== undefined && inAdminMode}
		<Admin {serverPublicKey} {adminToken} {generateAdminToken} />
	{/if}
	<footer><section><p>&copy; 2021 Gobalsky Labs Ltd. Made with 💛 and 🦔 by the Vega project team.</p></section></footer>
</main>

<style>
</style>
