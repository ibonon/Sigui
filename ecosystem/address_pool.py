import random
import secrets

class AddressPool:
    """Pool d'adresses partagé entre tous les agents."""
    
    KNOWN_SAFE = [
        "0xSAFE_EXCHANGE_001_111111111111111111111",
        "0xSAFE_EXCHANGE_002_222222222222222222222",
        "0xSAFE_EXCHANGE_003_333333333333333333333",
        "0xSAFE_EXCHANGE_004_444444444444444444444",
        "0xSAFE_EXCHANGE_005_555555555555555555555",
        "0xSAFE_EXCHANGE_006_666666666666666666666",
        "0xSAFE_EXCHANGE_007_777777777777777777777",
        "0xSAFE_EXCHANGE_008_888888888888888888888",
    ]
    
    UNKNOWN_RISKY = []
    
    @classmethod
    def get_safe_destination(cls) -> str:
        return random.choice(cls.KNOWN_SAFE)
    
    @classmethod  
    def get_new_destination(cls) -> str:
        """Génère une nouvelle adresse et l'ajoute au pool risqué."""
        addr = "0x" + secrets.token_hex(20)
        cls.UNKNOWN_RISKY.append(addr)
        return addr
    
    @classmethod
    def get_attacker_destination(cls) -> str:
        """Les attackers réutilisent leurs adresses couramment -> MemoClaw les apprend."""
        if cls.UNKNOWN_RISKY and random.random() < 0.4:
            return random.choice(cls.UNKNOWN_RISKY)
        return cls.get_new_destination()
