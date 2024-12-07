from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    weekly_allowance = db.Column(db.Float, default=0.0)  # Weekly allowance amount
    balance = db.Column(db.Float, default=0.0)  # Total balance for the child
    last_allowance_date = db.Column(db.Date, nullable=True)  # Last date allowance was added


class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'bi-weekly', 'monthly'
    is_complete = db.Column(db.Boolean, default=False)  # To track completion
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)

    child = db.relationship("Child", backref="chores")


class CompletedChore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, nullable=False)  # ID of the chore that was completed
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)  # ID of the child
    name = db.Column(db.String(200), nullable=False)  # Name of the chore
    completed_date = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp when completed

    # Relationship to access the child's name
    child = db.relationship("Child", backref="completed_chores")
