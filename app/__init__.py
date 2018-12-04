from app.app import setup_app, setup_migrate

APP = setup_app()
MIGRATE = setup_migrate(APP)
