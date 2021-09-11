async function auth() {
	const token = localStorage.getItem('api_token')
	if (!token) {
		const res = await fetch(window.location.origin + '/auth')
		const { token: new_token, redirect_url }  = await res.json() 
		localStorage.setItem('api_token', new_token)
		return redirect_url
	}
	else {
		return null
	}
}

async function callAuthed(url) {
	const token = localStorage.getItem('api_token')
	if (token) {
		const res = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } })
		if (res.status == 401) {
			localStorage.removeItem('api_token')
			throw new Error('unauthorised')
		}
		else if (res.status == 403) {
			throw new Error('forbidden')
		}
		else if (res.status != 200) {
			throw new Error('error ' + res.status)
		}
		return res
	}
	throw new Error('unauthorised')
}

async function getItems() {
	const res = await callAuthed(window.location.origin + '/items')
	return await res.json()
}

async function getPublicKey() {
	const res = await callAuthed(window.location.origin + '/public-key')
	let { public_key_b58 } =  await res.json()
	return public_key_b58
}

async function getUser() {
	const res = await callAuthed(window.location.origin + '/user')
	const { screen_name: screenName, id, admin } = await res.json()
	return { screenName, id, admin }
}

async function getAdminToken() {
	const res = await callAuthed(window.location.origin + '/admin-token')
	const { admin_token } = await res.json()
	return admin_token
}

async function clearTemplateCache() {
	const res = await callAuthed(window.location.origin + '/clear-template-cache')
	const { cleared } = await res.json()
	return cleared
}

async function logout() {
	localStorage.removeItem('api_token')
}


export default { auth, getItems, getUser, logout, getPublicKey, getAdminToken }