from server.internal.db import local_database
from server.internal.db.models import Job


def init_db():
	local_database.create_tables([Job])

	# Create the indexes
	local_database.execute_sql(
		"CREATE INDEX IF NOT EXISTS idx_job_status ON job (status);",
		commit=True,
	)
	local_database.execute_sql(
		"CREATE INDEX IF NOT EXISTS idx_job_acknowledged ON job (acknowledged);",
		commit=True,
	)
