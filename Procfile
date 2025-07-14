web: gunicorn --config gunicorn.conf.py main:app
release: python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"