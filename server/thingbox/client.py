import requests
from base58 import b58decode
from base64 import b64encode
from nacl.public import SealedBox, PublicKey


def server_url(server_base_url, path):
	server_base_url = server_base_url if server_base_url[-1] != '/' else server_base_url[:-1]
	return server_base_url + path


def get_public_key(server_base_url):
	res = requests.get(url=server_url(server_base_url, '/public-key'))
	if res.status_code == 200:
		json = res.json()
		return json['public_key_b58']
	else:
		raise Exception(f'error {res.status_code}')


def encrypt(plaintext, public_key_b58):
	box = SealedBox(PublicKey(b58decode(public_key_b58)))
	ciphertext = box.encrypt(plaintext=plaintext.encode())
	return b64encode(ciphertext).decode('utf-8')


def add_item(
		server_base_url, 
		auth_token, 
		target_type, 
		target_id, 
		category, 
		data_plaintext, 
		template_id, 
		batch_id=None):
	public_key = get_public_key(server_base_url)
	data_encrypted_b64 = encrypt(data_plaintext, public_key)
	res = requests.post(
		url=server_url(server_base_url, '/items'),
		params=dict(batch=batch_id) if batch_id else None,
		headers=dict(Authorization=f'Bearer {auth_token}'),
		json=dict(
				target_type=target_type, 
				target_id=target_id, 
				category=category, 
				data_encrypted_b64=data_encrypted_b64, 
				template=template_id))
	if res.status_code == 200:
		return 'item created'
	else:
		return f'error: {repr(res)}'


def add_items(
		server_base_url, 
		auth_token, 
		target_type_field='target_type',
		target_id_field='target_id',
		category_field='category',
		template_field='template',
		items, 
		content_field='content',
		template_id_field='template',
		override_target_type=None, 
		override_target_id=None,
		override_category=None,
		override_template_id=None,
		dry_run=False,
		log_fn=print):
	template = None
	if template_file:
		with open(template_file, 'r') as tf:
			template = tf.read()
	for i, item in enumerate(items):
		target_type = override_target_type or item[target_type_field] 
		target_id = override_target_id or item[target_id_field]
		if template:
			content = template.format(**item)
		else:
			content = item[content_field]
		if dry_run:
			log_fn(f'#{i} [DRY_RUN]: {target_type} {target_id} = ')
			log_fn(content)
		else:
			res = add_item(server_base_url, auth_token, target_type, target_id, content)
			log_fn(f'#{i}: {res} for {target_type} {target_id}')
