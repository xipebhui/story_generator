#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证中间件模块
提供Bearer Token认证和用户管理功能
"""

import os
import uuid
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_db_manager, User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token 认证
bearer_scheme = HTTPBearer(auto_error=False)

def get_auth_enabled() -> bool:
    """获取认证开关状态"""
    return os.environ.get('AUTH_ENABLED', 'true').lower() == 'true'

def get_invite_code() -> str:
    """获取邀请码"""
    return os.environ.get('INVITE_CODE', '15361578057')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)

def generate_api_key() -> str:
    """生成API Key"""
    return str(uuid.uuid4())

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[User]:
    """
    获取当前用户（可选认证）
    如果AUTH_ENABLED=false，返回None表示无需认证
    如果AUTH_ENABLED=true，验证Bearer Token并返回用户
    """
    # 检查是否启用认证
    if not get_auth_enabled():
        return None
    
    # 如果启用了认证但没有提供credentials
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败：需要Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证API Key
    db_manager = get_db_manager()
    user = db_manager.get_user_by_api_key(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败：无效的API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    return user

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> User:
    """
    强制认证（用于认证相关接口）
    总是需要Bearer Token，不受AUTH_ENABLED影响
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败：需要Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证API Key
    db_manager = get_db_manager()
    user = db_manager.get_user_by_api_key(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败：无效的API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    return user