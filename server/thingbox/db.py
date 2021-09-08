import sqlite3
from base58 import b58encode
from base64 import b64decode
from nacl.public import PrivateKey, SealedBox
from threading import Lock


class DB:
	
	def __init__(self, filepath, private_key_bytes):
		self._write_mutex = Lock()
		self._db = sqlite3.connect(filepath, check_same_thread=False)
		self._db.row_factory = sqlite3.Row
		self.ensure_schema()
		private_key = PrivateKey(private_key_bytes)
		self._crypto = SealedBox(private_key)
		self._public_key = b58encode(private_key.public_key.encode()).decode('utf-8')

	def ensure_schema(self):
		with self._write_mutex, self._db as sql:
			sql.execute("""
				CREATE TABLE IF NOT EXISTS admins (
					user_type TEXT NOT NULL, 
					user_id TEXT NOT NULL, 
					active BOOLEAN NOT NULL
				)
			""")
			sql.execute("""
				CREATE TABLE IF NOT EXISTS items (
					id INTEGER PRIMARY KEY AUTOINCREMENT, 
					target_type TEXT NOT NULL, 
					target_id TEXT NOT NULL, 
					item TEXT NOT NULL,
					created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
					archived BOOLEAN NOT NULL DEFAULT FALSE
				)
			""")

	def is_admin(self, user_type, user_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					COUNT(*) FROM admins 
				WHERE 
					user_type = :user_type 
					AND user_id = :user_id 
					AND active = TRUE
			""", dict(user_type=user_type, user_id=user_id))
			return res.fetchone()[0] > 0

	def make_admin(self, user_type, user_id):
		with self._write_mutex, self._db as sql:
			sql.execute("""
				INSERT OR REPLACE INTO admins (user_type, user_id, active) VALUES (:user_type, :user_id, TRUE)
			""", dict(user_type=user_type, user_id=user_id))
			return True
	
	def revoke_admin(self, user_type, user_id):
		with self._write_mutex, self._db as sql:
			sql.execute("""
				INSERT OR REPLACE INTO admins (user_type, user_id, active) VALUES (:user_type, :user_id, FALSE)
			""", dict(user_type=user_type, user_id=user_id))
			return True		
		
	def decrypt_item(self, ciphertext):
		try:
			return self._crypto.decrypt(ciphertext=b64decode(ciphertext)).decode('utf-8')
		except:
			return None

	def item_exists(self, target_type, target_id, item):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					COUNT(*) FROM items 
				WHERE 
					target_type = :target_type 
					AND target_id = :target_id 
					AND item = :item
			""", dict(target_type=target_type, target_id=target_id, item=item))
			return res.fetchone()[0] > 0		

	def add_item(self, target_type, target_id, item_encrypted_b64):
		if self.decrypt_item(item_encrypted_b64) is None: return False
		if self.item_exists(target_type=target_type, target_id=target_id, item=item_encrypted_b64): return True
		with self._write_mutex, self._db as sql:
			sql.execute("""
				INSERT INTO items (target_type, target_id, item) VALUES (:target_type, :target_id, :item)
			""", dict(target_type=target_type, target_id=target_id, item=item_encrypted_b64))
			return True
	
	def get_items(self, target_type, target_id):
		with self._db as sql:
			res = sql.execute("""
				SELECT 
					item FROM items 
				WHERE
					target_type = :target_type 
					AND target_id = :target_id
					AND archived = FALSE
				ORDER BY
					created DESC
			""", dict(target_type=target_type, target_id=target_id))
		rows = res.fetchall()
		items = [self.decrypt_item(r['item']) for r in rows]
		return list(filter(lambda x: x is not None, items))

	def get_public_key(self):
		return dict(public_key_b58=self._public_key)
