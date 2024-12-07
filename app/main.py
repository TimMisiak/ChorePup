from flask import Flask
from app.routes import init_routes, create_tables
from app.models import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chores.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
create_tables(app)
init_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)