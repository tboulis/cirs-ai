import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CIRS-Agent"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cirs_llm.db")
    
    # LLM Settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # Provide a safe string default (empty string) to satisfy Pydantic; runtime resolves dynamically
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "")
    # OpenAI-compatible (e.g., LM Studio) endpoint
    OPENAI_COMPAT_BASE_URL: Optional[str] = os.getenv("OPENAI_COMPAT_BASE_URL")
    OPENAI_COMPAT_API_KEY: Optional[str] = os.getenv("OPENAI_COMPAT_API_KEY")
    
    # Chat Settings
    MAX_CONVERSATION_LENGTH: int = 20
    MAX_RESPONSE_TOKENS: int = 1000
    TEMPERATURE: float = 0.7
    
    # Document Processing
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".docx", ".txt", ".md"]
    
    # Vector Database
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")  # required, see main.py
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Conversation relevance: max cosine similarity to the domain descriptions below.
    # 0.25 separates on-topic from off-topic questions in a calibration set of 42 on-topic and
    # 20 off-topic questions (lowest on-topic similarity 0.30, highest off-topic 0.19)
    CONVERSATION_RELEVANCE_THRESHOLD: float = 0.25

    # Create the demo accounts lyra_1..lyra_5 on startup (local development only)
    SEED_DEMO_USERS: bool = False
    
    # Domain descriptions for relevance filtering, separated by "||". Each one is kept
    # short because the embedding model truncates inputs at 128 tokens
    DOMAIN_DESCRIPTION: str = os.getenv(
        "DOMAIN_DESCRIPTION",
        " || ".join([
            "Critical infrastructure resilience: risk assessment and risk management, business continuity, disaster recovery, crisis management and preparedness for fires, floods, earthquakes and power outages in hospitals, energy, water, transport, telecommunications and finance.",
            "Cybersecurity of critical entities: incident response and incident reporting, ransomware, phishing, malware, data breaches, compromised accounts, security monitoring with SIEM, EDR and logs, access control, backups and third-party risk.",
            "Regulatory compliance and standards for resilience and security: EU directives CER, NIS2 and DORA, ISO 31000, ISO 22301, ISO/IEC 27001, NIST, COSO and COBIT, policies, audits and documented evidence.",
            "Ανθεκτικότητα κρίσιμων υποδομών: εκτίμηση και διαχείριση κινδύνου, επιχειρησιακή συνέχεια, ανάκαμψη από καταστροφές, διαχείριση κρίσεων και ετοιμότητα για πυρκαγιές, πλημμύρες, σεισμούς και διακοπές ρεύματος.",
            "Κυβερνοασφάλεια κρίσιμων οντοτήτων: απόκριση και αναφορά συμβάντων, ransomware, phishing, κακόβουλο λογισμικό, διαρροή δεδομένων, παραβιασμένοι λογαριασμοί, παρακολούθηση με SIEM, EDR και logs, έλεγχος πρόσβασης, αντίγραφα ασφαλείας.",
            "Κανονιστική συμμόρφωση και πρότυπα: οδηγίες CER, NIS2 και DORA, ISO 31000, ISO 22301, ISO/IEC 27001, NIST, COSO, COBIT, πολιτικές, έλεγχοι και τεκμήρια για νοσοκομεία, ενέργεια, μεταφορές, ύδρευση και χρηματοπιστωτικούς φορείς."
        ])
    )
    
    # Pydantic v2 configuration for environment loading
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()