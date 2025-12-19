import sqlite3
from sqlite3 import Error

class Database:
    def __init__(self, db_file):
        """ create a database connection to a SQLite database """
        self.connection = None
        try:
            self.connection = sqlite3.connect(db_file)
            print("Connection to SQLite DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

    def close_connection(self):
        """ close the database connection """ 
        if self.connection:
            self.connection.close()
            print("Connection to SQLite DB closed")

    def create_task(self, task):
        """ Create a new task in the tasks table """
        sql = '''INSERT INTO tasks(name, description) VALUES(?, ?)'''
        cur = self.connection.cursor()
        cur.execute(sql, task)
        self.connection.commit()
        return cur.lastrowid

    def read_task(self, task_id):
        """ Query task by id """ 
        sql = '''SELECT * FROM tasks WHERE id = ?''' 
        cur = self.connection.cursor()
        cur.execute(sql, (task_id,))
        return cur.fetchone()

    def update_task(self, task):
        """ Update a task by id """ 
        sql = '''UPDATE tasks SET name = ?, description = ? WHERE id = ?''' 
        cur = self.connection.cursor()
        cur.execute(sql, task)
        self.connection.commit()
        return cur.rowcount

    def delete_task(self, task_id):
        """ Delete a task by id """ 
        sql = '''DELETE FROM tasks WHERE id = ?''' 
        cur = self.connection.cursor()
        cur.execute(sql, (task_id,))
        self.connection.commit()
        return cur.rowcount
