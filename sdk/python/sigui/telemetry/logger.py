import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "decision"):
            decision = record.decision
            log_record.update({
                "decision": getattr(decision, "decision", getattr(decision, "verdict", "UNKNOWN")),
                "risk_score": getattr(decision, "risk_score", 0.0),
                "reason": getattr(decision, "reason", ""),
            })
        return json.dumps(log_record)
        
def setup_structured_logger(level="INFO"):
    logger = logging.getLogger("sigui")
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger
