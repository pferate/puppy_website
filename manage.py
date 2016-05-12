import os
from puppy import create_app, db
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand


app = create_app(os.getenv('APP_SETTINGS') or 'default')

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
