from dataclasses import dataclass
import sqlite3
import shutil
from os import urandom
from base64 import b64decode
from typing import Optional
from base58 import b58encode
from nacl.public import PrivateKey, SealedBox
from threading import Lock, Thread
from datetime import datetime
from os import path, makedirs
from time import sleep


@dataclass
class BackupConfig:
	backup_path: str
	name_template: str
	tmp_path: Optional[str] = None
	backup_interval: Optional[int] = None
	backup_on_batch_close: bool = False


DEFAULT_SITE_TEMPLATES = {
	'site-title': '# My thingbox instance',
	'site-footer': '&copy; 2021 SuperEvilMegaCorp, your soul belongs to us now. (change me)',
	'site-home-logged-out': 'Login with Twitter to view your items.',
	'site-home-empty': '## No items.',
	'site-home-normal': '# My items\n\nSee your items below.',
}


class DB:
	
	def __init__(self, filepath, private_key_bytes, id_len_bytes, backup_config=None):
		self._id_len_bytes = id_len_bytes
		self._backup_config = backup_config
		self._write_mutex = Lock()
		self._db = sqlite3.connect(filepath, check_same_thread=False)
		self._db.row_factory = sqlite3.Row
		with self._db as sql: sql.execute('PRAGMA foreign_keys = ON')
		self.ensure_schema()
		self.ensure_site_templates()
		print(f'Database opened and initialised: {filepath}')
		private_key = PrivateKey(private_key_bytes)
		self._crypto = SealedBox(private_key)
		self._public_key = private_key.public_key
		print(f'Cryptographic keys initialised, server public key: {b58encode(self.get_public_key().encode()).decode()}')
		if self._backup_config and self._backup_config.backup_interval and self._backup_config.backup_interval > 0:
			self.backup()
			backup_thread = Thread(target=self.backup_periodically, args=())
			backup_thread.daemon = True
			backup_thread.start()

	def ensure_schema(self):
		with self._write_mutex, self._db as sql:
			sql.execute("""
				CREATE TABLE IF NOT EXISTS admins (
					id INTEGER PRIMARY KEY AUTOINCREMENT, 
					user_type TEXT NOT NULL, 
					user_id TEXT NOT NULL, 
					editor BOOLEAN NOT NULL DEFAULT FALSE,
					active BOOLEAN NOT NULL DEFAULT TRUE,
					UNIQUE (user_type, user_id)
				)
			""")
			sql.execute("""
				CREATE TABLE IF NOT EXISTS templates (
					id TEXT NOT NULL PRIMARY KEY,
					type TEXT NOT NULL,
					content TEXT NOT NULL
				)
			""")
			sql.execute("""
				CREATE TABLE IF NOT EXISTS batches (
					id TEXT NOT NULL PRIMARY KEY, 
					admin_id INTEGER NOT NULL,
					created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
					closed TIMESTAMP,
					FOREIGN KEY (admin_id) REFERENCES admins (id)
				)
			""")
			sql.execute("""
				CREATE TABLE IF NOT EXISTS items (
					id INTEGER PRIMARY KEY AUTOINCREMENT, 
					batch_id TEXT NOT NULL,
					target_type TEXT NOT NULL, 
					target_id TEXT NOT NULL, 
					category TEXT NOT NULL,
					data TEXT NOT NULL,
					template_id TEXT NOT NULL,
					created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
					archived BOOLEAN NOT NULL DEFAULT FALSE,
					FOREIGN KEY (batch_id) REFERENCES batches (id),
					FOREIGN KEY (template_id) REFERENCES templates (id)
				)
			""")
			sql.execute("""
				CREATE INDEX IF NOT EXISTS items_by_target ON items (target_type, target_id, category);
			""")

	def ensure_site_templates(self):
		with self._write_mutex, self._db as sql:
			for template_id, content in DEFAULT_SITE_TEMPLATES.items():
				sql.execute("""
					INSERT OR IGNORE INTO templates (id, type, content) VALUES (:template_id, 'site', :content)
				""", dict(template_id=template_id, content=content))

	def backup(self):
		filename = self._backup_config.name_template.format(**dict(timestamp=datetime.now().strftime('%Y%m%d-%H%M%S.%f')))
		self._backup_config.backup_path and makedirs(self._backup_config.backup_path, exist_ok=True)
		self._backup_config.tmp_path and makedirs(self._backup_config.tmp_path, exist_ok=True)
		create_filepath = path.join(self._backup_config.tmp_path or self._backup_config.backup_path, filename)
		backup_filepath = path.join(self._backup_config.backup_path, filename)
		print(f'Backup started, tmp={create_filepath}, target={backup_filepath}')
		with self._write_mutex:
			backup_db = sqlite3.connect(create_filepath)
			self._db.backup(backup_db)
			backup_db.close()
		if self._backup_config.tmp_path and create_filepath != backup_filepath:
			shutil.move(src=create_filepath, dst=backup_filepath)

	def backup_periodically(self):
		while True:
			sleep(self._backup_config.backup_interval)
			try:
				self.backup()
			except Exception as e:
				print(f'Error doing backup: {repr(e)}')

	def generate_uid(self):
		return b58encode(urandom(self._id_len_bytes)).decode('utf-8')
		
	def is_admin(self, user_type, user_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					id FROM admins 
				WHERE 
					user_type = :user_type 
					AND user_id = :user_id 
					AND active = TRUE
			""", dict(user_type=user_type, user_id=user_id))
			row = res.fetchone()
			return row and row['id']
		
	def is_editor(self, user_type, user_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					id FROM admins 
				WHERE 
					user_type = :user_type 
					AND user_id = :user_id 
					AND editor = TRUE
					AND active = TRUE
			""", dict(user_type=user_type, user_id=user_id))
			row = res.fetchone()
			return row and row['id']

	def make_admin(self, user_type, user_id):
		with self._write_mutex, self._db as sql:
			try:
				sql.execute("""
					INSERT OR REPLACE INTO admins (user_type, user_id, active) VALUES (:user_type, :user_id, TRUE)
				""", dict(user_type=user_type, user_id=user_id))
				return True
			except sqlite3.IntegrityError:
				return False
	
	def revoke_admin(self, user_type, user_id):
		with self._write_mutex, self._db as sql:
			try:
				sql.execute("""
					INSERT OR REPLACE INTO admins (user_type, user_id, active) VALUES (:user_type, :user_id, FALSE)
				""", dict(user_type=user_type, user_id=user_id))
				return True	
			except sqlite3.IntegrityError:
				return False

	def create_or_check_batch(self, admin, batch=None):
		if batch is None:
			with self._write_mutex, self._db as sql:
				try:
					batch = self.generate_uid()
					sql.execute("""
						INSERT INTO batches (id, admin_id) VALUES (:id, :admin_id)
					""", dict(id=batch, admin_id=admin))
					return batch
				except sqlite3.IntegrityError as e:
					return None
		else:
			with self._db as sql:
				res = sql.execute("""
					SELECT
						COUNT(*) FROM batches
					WHERE
						id = :batch_id
						AND admin_id = :admin_id
						AND closed IS NULL
				""", dict(admin_id=admin, batch_id=batch))
				if res.fetchone()[0] == 0: raise Exception(f'admin ({admin}) has no batch: {batch}')
				return batch

	def close_batch(self, batch):
		result = False
		with self._write_mutex, self._db as sql:
			try:
				sql.execute("""
					UPDATE batches SET closed = CURRENT_TIMESTAMP WHERE id = :batch_id
				""", dict(batch_id=batch))
				result = True
			except sqlite3.IntegrityError:
				result = False
		if self._backup_config and self._backup_config.backup_on_batch_close:
			self.backup()
		return result

	def decrypt_data(self, ciphertext):
		try:
			return self._crypto.decrypt(ciphertext=b64decode(ciphertext)).decode('utf-8')
		except:
			return None

	def add_item(self, batch, target_type, target_id, category, data_encrypted_b64, template):
		if self.decrypt_data(data_encrypted_b64) is None: return False
		with self._write_mutex, self._db as sql:
			try:
				sql.execute("""
					INSERT 
						INTO items (batch_id, target_type, target_id, category, data, template_id) 
						VALUES (:batch_id, :target_type, :target_id, :category, :data, :template_id)
				""", dict(batch_id=batch, target_type=target_type, target_id=target_id, category=category, data=data_encrypted_b64, template_id=template))
				return True
			except sqlite3.IntegrityError as e:
				return False
	
	def get_items(self, target_type, target_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					id, category, data, template_id FROM items 
				WHERE
					target_type = :target_type 
					AND target_id = :target_id
					AND archived = FALSE
				ORDER BY
					created DESC
			""", dict(target_type=target_type, target_id=target_id))
		rows = res.fetchall()
		decrypted_rows = [{ 'data': self.decrypt_data(r['data']), 'template_id': r['template_id'], 'id': r['id'] } for r in rows]
		return list(filter(lambda x: x['data'] is not None, decrypted_rows))

	def get_items_summary(self, target_type, target_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					id, category, template_id, batch_id, created, archived FROM items 
				WHERE
					target_type = :target_type 
					AND target_id = :target_id
					AND archived = FALSE
				ORDER BY
					created DESC
			""", dict(target_type=target_type, target_id=target_id))
		rows = res.fetchall()
		return list(rows)

	def get_template(self, template, type='item'):
		with self._db as sql:
			res = sql.execute("""
				SELECT
					content FROM templates
				WHERE
					id = :template_id
					AND type = :type
			""", dict(template_id=template, type=type))
		row = res.fetchone()
		return row and row['content']

	def add_template(self, template_id, content, type='item'):
		with self._write_mutex, self._db as sql:
			try:
				sql.execute("""
					INSERT 
						INTO templates (id, content, type) 
						VALUES (:id, :content, :type)
				""", dict(id=template_id, content=content, type=type))
				return True
			except Exception as e:
				print(repr(e))
				return False	

	def update_template(self, template_id, content, type='item'):
		with self._write_mutex, self._db as sql:
			if self.get_template(template=template_id, type=type) is None: return False
			sql.execute("""
				UPDATE templates SET content = :content WHERE id = :id AND type = :type
			""", dict(id=template_id, content=content, type=type))
			return True

	def get_templates(self):
		with self._db as sql:
			res = sql.execute("""
				SELECT
					id, content, type 
				FROM 
					templates
				ORDER BY
					type, id
			""")
		rows = res.fetchall()
		return list(rows)

	def get_site_content_multi(self, ids):
		res = [self.get_site_content(x) for x in ids]
		return {k: v for d in res for k, v in d.items()}
	
	def get_site_content(self, id):
		with self._db as sql:
			res = sql.execute("""
				SELECT
					id, content 
				FROM 
					templates
				WHERE
					id = :id
					AND type = 'site'
			""", dict(id=id))
			row = res.fetchone()
		return { row['id']: row['content'] } if row else {}

	def get_public_key(self):
		return self._public_key
