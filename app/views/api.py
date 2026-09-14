from flask import Blueprint

from app.views.media_api import register_media_routes
from app.views.comment_api import register_comment_routes
from app.views.youtube_api_view import register_youtube_routes
from app.views.markdown_api import register_markdown_routes
from app.views.calendar_api import register_calendar_routes
from app.views.clipboard_api import register_clipboard_routes

api_bp = Blueprint("api", __name__)

register_media_routes(api_bp)
register_comment_routes(api_bp)
register_youtube_routes(api_bp)
register_markdown_routes(api_bp)
register_calendar_routes(api_bp)
register_clipboard_routes(api_bp)
