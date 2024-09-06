import access_db

user_id = "aa"
user = access_db.Userdata(user_id)
print(user.add_data("kk", True, 20, 80, 180, 1.2))
print(user.search_data("u_id", "gg"))
print(user.update_data("age", 50))
daily_data = access_db.Dailydata(user_id)
daily_data.add_data(food_name="fff", food_calories=500)
daily_data.add_data(exercise_name="run", exercise_duration=300)
print(daily_data.search_data(field="u_id", data=user_id))
print(daily_data.search_all_data(field="u_id", data=user_id))
print(daily_data.search_data("u_id", "gg"))
print(daily_data.search_all_data("date", "10d"))
food_items = [
    {"name": "水餃", "calories": 1000, "quantity": 1},
    {"name": "蘋果", "calories": 52, "quantity": 1},
    {"name": "炒飯", "calories": 500, "quantity": 1}
]
for i in range(len(food_items)):
    daily_data.add_data(food_name=food_items[i]["name"], food_calories=food_items[i]["calories"])

print(daily_data.search_data("u_id", "gg"))
print(daily_data.search_all_data("date", "10d"))
