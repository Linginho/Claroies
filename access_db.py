import sqlite3


class Userdata:
    DB_CONN = None
    USER_CURSOR = None
    db = ""
    table = "users"
    user_data = []

    def open_db(self):
        self.DB_CONN = sqlite3.connect(self.db)
        self.USER_CURSOR = self.DB_CONN.cursor()

    def close_db(self):
        self.DB_CONN.commit()
        self.DB_CONN.close()

    def __init__(self, user_id):
        self.db = user_id+f".db"
        self.open_db()
        self.USER_CURSOR.execute('CREATE TABLE IF NOT EXISTS users('
                                 'u_id TEXT PRIMARY KEY NOT NULL, '
                                 'name TEXT, '
                                 'gender BOOLEAN, '
                                 'age INTEGER, '
                                 'weight FLOATING, '
                                 'height FLOATING, '
                                 'activity_level FLOATING )')
        self.close_db()

    def run_sql_comm(self, comm):
        self.open_db()
        self.USER_CURSOR.execute(comm)
        self.close_db()

    def get_sql_result(self, comm):
        self.open_db()
        result = self.USER_CURSOR.execute(comm).fetchone()
        self.close_db()
        return result

    def add_data(self, u_id: str, name: str = "gg", gender: bool = True, age: float = 20,
                 weight: float = 60, height: float = 160, activity_level: float = 1.2):

        comm = (f"insert into {self.table} values(\'{str(u_id)}\', \'{str(name)}\', {bool(gender)},"
                f"{int(age)}, {float(weight)}, {float(height)}, {float(activity_level)})")
        if not self.search_data("u_id", u_id):
            self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def search_data(self, field, data):
        comm = f"select * from {self.table} where {field}=\'{data}\'"
        return self.get_sql_result(comm=comm)

    def update_data(self, u_id, field, data):
        comm = f"update {self.table} set {field}={float(data)} where u_id=\'{str(u_id)}\'"
        if self.search_data("u_id", u_id):
            self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def delete_data(self, u_id):
        comm = f"delete from {self.table} where u_id=\'{str(u_id)}\'"
        if self.search_data("u_id", u_id):
            self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def get_all_columns(self):
        # table_name = "users"
        column_names = []
        self.open_db()
        result = self.USER_CURSOR.execute(f"PRAGMA table_info({self.table});").fetchall()
        self.close_db()
        for col in result:
            column_names.append(col[1])
        return column_names

class Dailydata:
    DB_CONN = None
    USER_CURSOR = None
    db = ""
    table = "daily_info"
    user_data = []

    def open_db(self):
        self.DB_CONN = sqlite3.connect(self.db)
        self.USER_CURSOR = self.DB_CONN.cursor()

    def close_db(self):
        self.DB_CONN.commit()
        self.DB_CONN.close()

    def __init__(self, db):
        self.db = db+f".db"
        self.open_db()
        self.USER_CURSOR.execute(f'CREATE TABLE IF NOT EXISTS {self.table}('
                                 'u_id TEXT, '
                                 'data_time TEXT, '
                                 'food_name TEXT, '
                                 'food_calories FLOATING, '
                                 'exercise_name TEXT, '
                                 'exercise_duration FLOATING)')
        self.close_db()

    def run_sql_comm(self, comm):
        self.open_db()
        self.USER_CURSOR.execute(comm)
        self.close_db()

    def get_sql_result(self, comm):
        self.open_db()
        result = self.USER_CURSOR.execute(comm).fetchone()
        self.close_db()
        return result

    def add_data(self, u_id: str = "None", data_time: str = "None", food_name: str = "food",
                 food_calories: float = 0, exercise_name: str = "run",
                 exercise_duration: float = 0):

        comm = (f"insert into {self.table} values(\'{str(u_id)}\', \'{str(data_time)}\',"
                f" \'{str(food_name)}\', {float(food_calories)}, \'{str(exercise_name)}\',"
                f" {float(exercise_duration)})")
        self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def search_data(self, field, data):
        comm = f"select * from {self.table} where {field}=\'{data}\'"
        return self.get_sql_result(comm=comm)

    def update_data(self, u_id, field, data):
        comm = f"update {self.table} set {field}={float(data)} where u_id=\'{str(u_id)}\'"
        self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def delete_data(self, u_id):
        comm = f"delete from {self.table} where u_id=\'{str(u_id)}\'"
        if self.search_data("u_id", u_id):
            self.run_sql_comm(comm=comm)
        return self.search_data("u_id", u_id)

    def get_all_columns(self):
        # table_name = "users"
        column_names = []
        self.open_db()
        result = self.USER_CURSOR.execute(f"PRAGMA table_info({self.table});").fetchall()
        self.close_db()
        for col in result:
            column_names.append(col[1])
        return column_names


if __name__ == '__main__':
    user = Userdata("aa")
    # user.USER_CURSOR("aa")
    # print(user.add_data("gg", 20, 160, 1880))
    # u_id, name, gender, age, weight, height, activity_level, bmr, tdee
    print(user.add_data("gg", "kk", "True", 20, 80, 180, 1.2))
    print(user.search_data("u_id", "gg"))
    print(user.update_data("gg", "age", 50))
    print(user.get_all_columns())
    # print(user.delete_data(u_id="gg"))
    dailydata = Dailydata("aa")
    dailydata.add_data("gg")
