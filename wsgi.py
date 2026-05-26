"""WSGI entry point for deployed demo API."""

from web_server import create_app

app = create_app()
