# Database Migrations

Snaglist Pro uses SQLAlchemy with auto-create via `Base.metadata.create_all()`.
For production schema changes, use Alembic:

```
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "description"
alembic upgrade head
```
