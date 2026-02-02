"""
Transaction model for payments
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class TransactionType(str, enum.Enum):
    """Transaction type enum"""
    DEPOSIT = "deposit"  # Пополнение
    USAGE = "usage"  # Использование
    REFUND = "refund"  # Возврат


class TransactionStatus(str, enum.Enum):
    """Transaction status enum"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(Base):
    """Transaction model"""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    description = Column(Text, nullable=True)
    
    # Payment provider info
    payment_provider = Column(String, nullable=True)  # e.g., "yookassa"
    payment_id = Column(String, nullable=True)  # External payment ID
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction {self.type} {self.amount} for user {self.user_id}>"
