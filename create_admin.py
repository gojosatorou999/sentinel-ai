from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(email='admin@gmail.com').first()
    if not admin:
        admin = User(username='admin', email='admin@gmail.com', role='official')
        admin.password = generate_password_hash('admin123')
        db.session.add(admin)
    else:
        admin.password = generate_password_hash('admin123')
        admin.role = 'official'
    db.session.commit()
    print('Admin created successfully!')
