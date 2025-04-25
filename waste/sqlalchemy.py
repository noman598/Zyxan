'''1. ✅ SELECT / Read Data

db: This is the SQLAlchemy Session object, used to interact with the database.

.query(User): This creates a query for the User table/model.

.filter(User.email == user.email): Applies a filter to find records where the email in the table matches user.email.

.first(): Returns the first matching record or None if no match is found.




# Get all users
users = db.query(User).all()

# Get user by ID
user = db.query(User).filter(User.id == 1).first()



2. ➕ INSERT / Create New Record

new_user = User(name="Alice", email="alice@example.com")
db.add(new_user)
db.commit()
db.refresh(new_user)  # Optional: refresh to get updated fields like auto-generated ID


3. ✏️ UPDATE / Modify Existing Record

user = db.query(User).filter(User.id == 1).first()
if user:
    user.name = "Updated Name"
    db.commit()


4. ❌ DELETE / Remove a Record
user = db.query(User).filter(User.id == 1).first()
if user:
    db.delete(user)
    db.commit()


5. 🔎 FILTER with Multiple Conditions
users = db.query(User).filter(User.age > 18, User.active == True).all()
Or using .filter_by():
user = db.query(User).filter_by(name="Alice", active=True).first()



6. 📊 Aggregate Functions
from sqlalchemy import func

# Count users
count = db.query(func.count(User.id)).scalar()

# Get average age
average_age = db.query(func.avg(User.age)).scalar()



7. 📂 Order and Limit
# Latest 5 users
users = db.query(User).order_by(User.created_at.desc()).limit(5).all()


8. 🔗 Join Queries
# Assume Post is another table with a foreign key to User
results = db.query(User, Post).join(Post).filter(User.id == Post.user_id).all()

'''