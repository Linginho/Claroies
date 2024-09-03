import access_db
from access_db import Userdata
from access_db import Dailydata

user_id = "abcdef"
user_data = Userdata(user_id)
daily_data = Dailydata(user_id)
# user_data = access_db.Userdata(user_id)
# daily_data = access_db.Dailydata(user_id)
user_data.add_data(u_id=user_id)

print(user_data.add_data("gg", "kk", "True", 20, 80, 180, 1.2))
print(user_data.search_data("u_id", "gg"))
print(user_data.update_data("gg", "age", 50))
print(user_data.get_all_columns())
# print(user.delete_data(u_id="gg"))

daily_data.add_data("gg")
daily_data.add_data("gg")
