.PHONY: migrate revision upgrade downgrade

migrate: upgrade

revision:
	alembic revision --autogenerate -m "$(message)"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1
