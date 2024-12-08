from flask import render_template, request, redirect, url_for, jsonify
from app.models import db, Child, Chore, CompletedChore
from datetime import datetime, timedelta
import calendar
import pytz

tz = pytz.timezone('US/Pacific')

def calculate_next_due_date(current_date, frequency):
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "every 2 days":
        return current_date + timedelta(days=2)
    elif frequency == "weekly":
        return current_date + timedelta(weeks=1)
    elif frequency == "bi-weekly":
        return current_date + timedelta(weeks=2)
    elif frequency == "monthly":
        # Add one month, adjust day overflow
        new_month = (current_date.month % 12) + 1
        year_increment = (current_date.month + 1) // 12
        new_year = current_date.year + year_increment
        try:
            return current_date.replace(month=new_month, year=new_year)
        except ValueError:  # Handle month overflow
            return current_date.replace(day=28, month=new_month, year=new_year)
    return current_date

def create_tables(app):
    with app.app_context():
        db.create_all()

        # Check if Marcus and Lucas exist; add them if they don't
        if not Child.query.filter_by(name="Marcus").first():
            db.session.add(Child(name="Marcus"))
        if not Child.query.filter_by(name="Lucas").first():
            db.session.add(Child(name="Lucas"))
        
        db.session.commit()  # Save changes to the database

def get_children_and_update_allowance():
    children = Child.query.all()
    today = datetime.now(tz).date()

    for child in children:
        if child.last_allowance_date:
            weeks_due = (today - child.last_allowance_date).days // 7
            if weeks_due > 0:
                child.balance += weeks_due * child.weekly_allowance
                child.last_allowance_date += timedelta(weeks=weeks_due)
        else:
            # Initialize the last_allowance_date if not set
            child.last_allowance_date = today

        db.session.commit()
    return children

def init_routes(app):
    @app.route("/")
    def home():
        children = get_children_and_update_allowance()
        today = datetime.now(tz).date()
        
        # Sort chores for each child: due (today or past) first, then future
        for child in children:
            child.chores.sort(key=lambda chore: (chore.due_date > today, chore.due_date))
            for chore in child.chores:
                day_of_week = calendar.day_name[chore.due_date.weekday()]
                month_name = calendar.month_name[chore.due_date.month]
                if chore.due_date.year == today.year:
                    chore.friendly_date = f'{day_of_week}, {month_name} {chore.due_date.day}'
                else:
                    chore.friendly_date = f'{day_of_week}, {month_name} {chore.due_date.day}, {chore.year}'

        completed_chores = CompletedChore.query.order_by(CompletedChore.completed_date.desc()).all()
        return render_template("index.html", children=children, completed_chores=completed_chores, today=today)



    @app.route("/add_chore", methods=["GET", "POST"])
    def add_chore():
        if request.method == "POST":
            name = request.form["name"]
            due_date = request.form["due_date"]
            frequency = request.form["frequency"]
            child_id = request.form["child_id"]
            
            # Create a new chore
            chore = Chore(
                name=name,
                due_date=datetime.strptime(due_date, "%Y-%m-%d"),
                frequency=frequency,
                child_id=child_id
            )
            db.session.add(chore)
            db.session.commit()
            return redirect(url_for("home"))
        
        # Fetch all children to populate the dropdown
        children = Child.query.all()
        return render_template("add_chore.html", children=children)


    @app.route("/mark_complete/<int:chore_id>", methods=["POST"])
    def mark_complete(chore_id):
        from app.models import Chore, CompletedChore

        with app.app_context():
            chore = Chore.query.get(chore_id)
            if not chore:
                return jsonify({"error": "Chore not found"}), 404
            
            if chore.is_complete:
                return jsonify({"message": "Chore is already complete"}), 400

            # Log the completed chore
            completed_chore = CompletedChore(
                chore_id=chore.id,
                child_id=chore.child_id,
                name=chore.name,
                completed_date=datetime.now(tz)
            )
            db.session.add(completed_chore)

            # Update the chore for recurring tasks
            current_date = datetime.now(tz).date()
            if chore.frequency in ["daily", "every 2 days", "weekly", "bi-weekly", "monthly"]:
                chore.due_date = calculate_next_due_date(current_date, chore.frequency)
                chore.is_complete = False  # Reset for the next occurrence
            else:
                chore.is_complete = True  # Non-recurring chores stay complete
            
            db.session.commit()
            return jsonify({
                "message": "Chore marked complete",
                "new_due_date": chore.due_date.strftime("%Y-%m-%d"),
                "chore_id": chore.id
            }), 200

    @app.route("/edit_chores", methods=["GET"])
    def edit_chores():
        from app.models import Chore, Child

        chores = Chore.query.all()
        children = Child.query.all()
        return render_template("edit_chores.html", chores=chores, children=children)

    @app.route("/update_chore/<int:chore_id>", methods=["POST"])
    def update_chore(chore_id):
        from app.models import Chore
        chore = Chore.query.get(chore_id)
        if not chore:
            return jsonify({"error": "Chore not found"}), 404

        # Update the chore fields
        chore.name = request.form["name"]
        chore.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()
        chore.frequency = request.form["frequency"]
        chore.child_id = request.form["child_id"]

        db.session.commit()
        return redirect(url_for("edit_chores"))

    @app.route("/delete_chore/<int:chore_id>", methods=["POST"])
    def delete_chore(chore_id):
        from app.models import Chore
        chore = Chore.query.get(chore_id)
        if not chore:
            return jsonify({"error": "Chore not found"}), 404

        db.session.delete(chore)
        db.session.commit()
        return redirect(url_for("edit_chores"))


    @app.route("/configure_allowances", methods=["GET", "POST"])
    def configure_allowances():

        if request.method == "POST":
            # Handle updating or withdrawing allowance
            action = request.form.get("action")
            child_id = int(request.form["child_id"])
            child = Child.query.get(child_id)

            if action == "withdraw":
                amount = float(request.form["amount"])
                if child.balance >= amount:
                    child.balance -= amount
                    db.session.commit()
                else:
                    return f"Error: Insufficient balance for {child.name}", 400

            elif action == "update_allowance":
                child.weekly_allowance = float(request.form["weekly_allowance"])
                db.session.commit()

            return redirect(url_for("configure_allowances"))

        # GET: Calculate allowances for children
        children = get_children_and_update_allowance()
        return render_template("configure_allowances.html", children=children)
