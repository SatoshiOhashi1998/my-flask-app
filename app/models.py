# models.py
import os
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class VideoDataModel(Base):
    """動画データをデータベースで管理するモデル"""
    __tablename__ = 'video_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dirpath = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    last_time = Column(Integer, nullable=False)
    memo = Column(String, nullable=True)

    def __repr__(self):
        return f"<VideoData(dirpath='{self.dirpath}', filename='{self.filename}', last_time={self.last_time}, memo='{self.memo}')>"

# データベース接続の設定
DATABASE_URL = os.getenv('MODEL_DB')  # SQLiteデータベースのURL
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)  # テーブルの作成

Session = sessionmaker(bind=engine)
