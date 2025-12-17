from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TodoItem(Base):
    __tablename__ = 'todo_items'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    done = Column(Boolean, default=False)

    def __repr__(self):
        return f"<TodoItem(id={self.id}, title='{self.title}', done={self.done})>"