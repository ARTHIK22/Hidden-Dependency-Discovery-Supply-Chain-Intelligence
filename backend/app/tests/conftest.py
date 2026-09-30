import os

# The suite uses an isolated in-memory database; local PostgreSQL is optional.
os.environ["DATABASE_URL"] = "sqlite://"
