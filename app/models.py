from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class VideoDataModel(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.String, primary_key=True)
    new_name = db.Column(db.String, nullable=False)
    path = db.Column(db.String(collation="NOCASE"), nullable=False)
    original_name = db.Column(db.String(collation="NOCASE"), nullable=False)


    def __repr__(self):
        return f"<VideoData(id={self.id}, original_name={self.original_name}, new_name={self.new_name}, path={self.path})>"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), nullable=False) # 拡張子なしのID
    author = db.Column(db.String(50), default="ゲスト")  # 必要に応じて追加
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
