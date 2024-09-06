import access_db

user_id = "aa"
user = access_db.Userdata(user_id)
print(user.add_data("gg", "kk", "True", 20, 80, 180, 1.2))
print(user.search_data("u_id", "gg"))
print(user.update_data("gg", "age", 50))
print(user.get_all_columns())
dailydata = access_db.Dailydata(user_id)
dailydata.add_data(user_id)
dailydata.add_data(user_id)
print(dailydata.search_data("u_id", user_id))
print(dailydata.search_all_data("u_id", user_id))
food_items = [
    {"name": "水餃", "calories": 1000, "quantity": 1},
    {"name": "蘋果", "calories": 52, "quantity": 1},
    {"name": "炒飯", "calories": 500, "quantity": 1}
]
# for i in range(len(food_items)):
#     daily_data.add_data(u_id=user_id, food_name=food_items[i]["name"], food_calories=food_items[i]["calories"])


print(dailydata.search_data("u_id", "gg"))
print(dailydata.search_all_data("date", "10d"))
