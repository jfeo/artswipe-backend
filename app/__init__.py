from app.app import setup_app, setup_migrate, setup_security

APP = setup_app()
MIGRATE = setup_migrate(APP)
SECURITY = setup_security(APP)
