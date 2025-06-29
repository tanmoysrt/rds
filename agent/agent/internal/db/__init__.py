from peewee import SqliteDatabase

local_database = SqliteDatabase(
	"data/agent/db.sqlite3",
	timeout=15,
	pragmas={
		"journal_mode": "wal",
		"synchronous": "normal",
		"mmap_size": 2**32 - 1,
		"page_size": 8192,
	},
)
