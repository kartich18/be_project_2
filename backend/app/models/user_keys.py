from app import db

class UserKeys(db.Model):
    """Stores encrypted public/private keypairs for a user."""
    
    __tablename__ = "user_keys"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    
    # ML-KEM-768
    kem_public_key = db.Column(db.LargeBinary, nullable=False)
    kem_private_key_enc = db.Column(db.LargeBinary, nullable=False)
    kem_salt = db.Column(db.LargeBinary, nullable=False)
    kem_nonce = db.Column(db.LargeBinary, nullable=False)

    # RSA-2048
    rsa_public_key = db.Column(db.LargeBinary, nullable=False)
    rsa_private_key_enc = db.Column(db.LargeBinary, nullable=False)
    rsa_salt = db.Column(db.LargeBinary, nullable=False)
    rsa_nonce = db.Column(db.LargeBinary, nullable=False)

    user = db.relationship("User", backref=db.backref("keys", uselist=False))

    def __repr__(self) -> str:
        return f"<UserKeys user_id={self.user_id}>"
