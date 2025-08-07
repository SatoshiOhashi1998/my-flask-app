from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class VideoDataModel(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.String, primary_key=True)  # sqliteではTEXT主キーでもOK
    original_name = db.Column(db.String, nullable=False)
    new_name = db.Column(db.String, nullable=False)
    path = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<VideoData(id={self.id}, original_name={self.original_name}, new_name={self.new_name}, path={self.path})>"
