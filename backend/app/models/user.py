from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    needs_onboarding = Column(Boolean, default=True)
    
    # Profile Information
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(255), nullable=True)
    
    # System Profile Information
    operating_system = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)
    linux_distro = Column(String(50), nullable=True)
    linux_distro_version = Column(String(50), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    total_memory = Column(Integer, nullable=True)  # in MB
    avatar = Column(String(50), default='sir-hawkington')
    
    # User Preferences
    preferences = Column(JSON, default=lambda: {
        "optimization_level": "moderate",
        "theme_preferences": {"use_dark_mode": True}
    })
    
    # Account Status & Security
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Security Tracking
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    
    # Use string-based relationships to avoid circular imports
    configurations = relationship(
        "SystemConfiguration", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    optimization_profiles = relationship(
        "OptimizationProfile", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    alerts = relationship(
        "SystemAlert", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    tuning_history = relationship(
        "TuningHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    
    # Additional Profile Fields
    location = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    github_username = Column(String(50), nullable=True)
    linkedin_profile = Column(String(200), nullable=True)
    
    # Preferences
    theme_preference = Column(String(20), default='system')
    notification_settings = Column(String(100), default='all')
    optimization_level = Column(String(50), default='balanced')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
