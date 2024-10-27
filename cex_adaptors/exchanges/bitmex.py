from .base import PublicClient


class Bitmex(PublicClient):
    name = "bitmex"

    def __init__(self):
        super().__init__()
