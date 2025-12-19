class Task:
    def __init__(self, task_id, description, is_completed=False):
        self.task_id = task_id
        self.description = description
        self.is_completed = is_completed

    def mark_completed(self):
        self.is_completed = True

    def __repr__(self):
        return f"Task(task_id={self.task_id}, description='{self.description}', is_completed={self.is_completed})"