import structlog


class OriginLogger:
    def __init__(self, origin: str):
        self.logger = structlog.get_logger().bind(origin=origin)
