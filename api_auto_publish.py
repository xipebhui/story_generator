#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号驱动自动发布API扩展
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time, timedelta
import logging
import uuid
from sqlalchemy import text
import json
import inspect

from auth_middleware import get_current_user, require_auth
from pipeline_registry import get_pipeline_registry
from ring_scheduler import get_ring_scheduler
from account_driven_executor import get_account_driven_executor
from platform_monitor import get_platform_monitor
from strategy_engine import get_strategy_engine
from schedule_executor import get_schedule_executor
from database import get_db_manager
from models_auto_publish import AccountGroupModel, AccountGroupMemberModel, PublishStrategyModel

# 配置logger，确保输出到正确的日志文件
logger = logging.getLogger(__name__)
# 添加文件处理器
if not logger.handlers:
    file_handler = logging.FileHandler('logs/api_with_db.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

# 创建路由器
router = APIRouter(prefix="/api/auto-publish", tags=["auto-publish"])

# ============ 请求/响应模型 ============

class CreateAccountGroupRequest(BaseModel):
    """创建账号组请求"""
    group_name: str = Field(..., description="账号组名称")
    group_type: str = Field("production", description="组类型: experiment, production, test")
    description: Optional[str] = Field(None, description="描述")
    account_ids: List[str] = Field(..., description="账号ID列表")
    
class AccountGroupResponse(BaseModel):
    """账号组响应"""
    group_id: str
    group_name: str
    group_type: str
    description: Optional[str]
    is_active: bool
    member_count: int
    created_at: datetime
    
class CreatePublishConfigRequest(BaseModel):
    """创建发布配置请求"""
    config_name: str = Field(..., description="配置名称")
    group_id: str = Field(..., description="账号组ID")
    pipeline_id: str = Field(..., description="Pipeline ID")
    trigger_type: str = Field(..., description="触发类型: scheduled, monitor, manual")
    trigger_config: Dict[str, Any] = Field(..., description="触发器配置")
    strategy_id: Optional[str] = Field(None, description="策略ID")
    priority: int = Field(50, ge=0, le=100, description="优先级")
    pipeline_params: Optional[Dict[str, Any]] = Field(None, description="Pipeline参数配置")
    pipeline_config: Optional[Dict[str, Any]] = Field(None, description="Pipeline配置（兼容旧字段）")
    
    @field_validator('config_name')
    @classmethod
    def validate_config_name(cls, v):
        logger.debug(f"[Pydantic] 校验 config_name: {v}")
        if not v or not v.strip():
            raise ValueError('配置名称不能为空')
        return v
    
    @field_validator('trigger_type')
    @classmethod
    def validate_trigger_type(cls, v):
        logger.debug(f"[Pydantic] 校验 trigger_type: {v}")
        valid_types = ['scheduled', 'monitor', 'manual', 'event']
        if v not in valid_types:
            raise ValueError(f'触发类型必须是: {", ".join(valid_types)}')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        logger.debug(f"[Pydantic] 校验 priority: {v}")
        if v < 0 or v > 100:
            raise ValueError('优先级必须在0-100之间')
        return v
    
    @field_validator('pipeline_params', 'pipeline_config', mode='before')
    @classmethod
    def validate_pipeline_params(cls, v):
        logger.debug(f"[Pydantic] 校验 pipeline参数: {v}, 类型: {type(v)}")
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                logger.error(f"[Pydantic] pipeline参数JSON解析失败: {e}, 原始值: {v}")
                raise ValueError(f'pipeline参数必须是有效的JSON: {e}')
        return v
    
    @model_validator(mode='after')
    def validate_all(self):
        logger.info(f"[Pydantic] 完整请求数据校验: {json.dumps({k: str(v)[:100] for k, v in self.model_dump().items()}, ensure_ascii=False)}")
        return self
    
class PublishConfigResponse(BaseModel):
    """发布配置响应"""
    config_id: str
    config_name: str
    group_id: str
    pipeline_id: str
    trigger_type: str
    trigger_config: Dict[str, Any]
    strategy_id: Optional[str]
    priority: int
    is_active: bool
    created_at: datetime
    
class GenerateSlotsRequest(BaseModel):
    """生成调度槽位请求"""
    config_id: str = Field(..., description="配置ID")
    target_date: date = Field(..., description="目标日期")
    start_hour: int = Field(6, ge=0, le=23, description="开始时间")
    end_hour: int = Field(23, ge=0, le=23, description="结束时间")
    strategy: str = Field("even", description="分配策略: even, random")
    
class CreateStrategyRequest(BaseModel):
    """创建策略请求"""
    strategy_name: str = Field(..., description="策略名称")
    strategy_type: str = Field(..., description="策略类型: ab_test, round_robin, weighted")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    description: Optional[str] = Field(None, description="描述")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    
class AssignStrategyRequest(BaseModel):
    """分配策略请求"""
    strategy_id: str = Field(..., description="策略ID")
    group_id: str = Field(..., description="账号组ID")
    variant_name: str = Field(..., description="变体名称")
    variant_config: Optional[Dict[str, Any]] = Field(None, description="变体配置")
    weight: float = Field(1.0, ge=0, description="权重")
    is_control: bool = Field(False, description="是否为对照组")
    
class MonitorConfigRequest(BaseModel):
    """监控配置请求"""
    platform: str = Field(..., description="平台: youtube, bilibili, douyin, tiktok")
    monitor_type: str = Field(..., description="监控类型: competitor, trending, keyword, channel")
    target_identifier: str = Field(..., description="目标标识符")
    check_interval: int = Field(3600, ge=60, description="检查间隔(秒)")
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")

# ============ 账号组管理 ============

@router.post("/account-groups", response_model=AccountGroupResponse)
async def create_account_group(
    request: CreateAccountGroupRequest,
    current_user: Dict = Depends(require_auth)
):
    """创建账号组"""
    try:
        db = get_db_manager()
        
        # 创建账号组
        group_id = f"group_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        with db.get_session() as session:
            # 检查组名是否已存在
            existing = session.query(AccountGroupModel).filter_by(
                group_name=request.group_name
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail=f"账号组名称 '{request.group_name}' 已存在")
            
            # 创建账号组
            group = AccountGroupModel(
                group_id=group_id,
                group_name=request.group_name,
                group_type=request.group_type,
                description=request.description,
                is_active=True
            )
            session.add(group)
            
            # 添加成员
            logger.info(f"准备添加成员到账号组 {group_id}: {request.account_ids}")
            for account_id in request.account_ids:
                # 检查账号是否存在
                from database import Account
                account = session.query(Account).filter_by(account_id=account_id).first()
                if not account:
                    logger.warning(f"账号 {account_id} 不存在，跳过")
                    continue
                    
                member = AccountGroupMemberModel(
                    group_id=group_id,
                    account_id=account_id,
                    role='member',
                    is_active=True
                )
                session.add(member)
                logger.debug(f"添加成员 {account_id} 到组 {group_id}")
            
            session.commit()
            
            # 验证成员是否成功添加
            actual_members = session.query(AccountGroupMemberModel).filter_by(
                group_id=group_id,
                is_active=True
            ).count()
            
            logger.info(f"创建账号组: {group_id}, 请求成员数: {len(request.account_ids)}, 实际成员数: {actual_members}")
            
            return AccountGroupResponse(
                group_id=group_id,
                group_name=request.group_name,
                group_type=request.group_type,
                description=request.description,
                is_active=True,
                member_count=len(request.account_ids),
                created_at=group.created_at
            )
            
    except Exception as e:
        logger.error(f"创建账号组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups")
async def list_account_groups(
    group_type: Optional[str] = Query(None, description="筛选组类型"),
    is_active: bool = Query(True, description="是否只返回活跃组"),
    current_user: Dict = Depends(require_auth)
):
    """列出账号组"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /account-groups called - group_type: {group_type}, is_active: {is_active}")
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            query = session.query(AccountGroupModel)
            
            # 筛选条件
            if group_type:
                query = query.filter_by(group_type=group_type)
            if is_active:
                query = query.filter_by(is_active=is_active)
            
            groups = query.all()
            
            # 获取每个组的成员数和账号信息
            result = []
            for group in groups:
                # 获取成员列表
                members = session.query(AccountGroupMemberModel).filter_by(
                    group_id=group.group_id,
                    is_active=True
                ).all()
                
                member_count = len(members)
                
                # 获取账号详细信息
                account_list = []
                if members:
                    from database import Account
                    for member in members:
                        account = session.query(Account).filter_by(
                            account_id=member.account_id
                        ).first()
                        if account:
                            account_list.append({
                                "account_id": account.account_id,
                                "account_name": account.account_name,
                                "profile_id": account.profile_id,
                                "platform": "youtube",  # Default platform
                                "role": member.role,
                                "join_date": member.join_date.isoformat() if member.join_date else None
                            })
                
                # 构建响应
                group_data = {
                    "group_id": group.group_id,
                    "group_name": group.group_name,
                    "group_type": group.group_type,
                    "description": group.description,
                    "is_active": group.is_active,
                    "member_count": member_count,
                    "members": account_list,  # 添加成员列表
                    "created_at": group.created_at.isoformat() if group.created_at else None
                }
                result.append(group_data)
            
            return {"groups": result}
        
    except Exception as e:
        logger.error(f"列出账号组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups/{group_id}")
async def get_account_group_detail(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取账号组详情（包含成员信息）"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /account-groups/{{group_id}} called - group_id: {group_id}")
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 获取组信息
            group = session.query(AccountGroupModel).filter_by(
                group_id=group_id
            ).first()
            
            if not group:
                raise HTTPException(status_code=404, detail=f"账号组不存在: {group_id}")
            
            # 获取成员列表
            members = session.query(AccountGroupMemberModel).filter_by(
                group_id=group_id,
                is_active=True
            ).all()
            
            # 获取账号详细信息
            from database import Account
            account_list = []
            for member in members:
                account = session.query(Account).filter_by(
                    account_id=member.account_id
                ).first()
                
                if account:
                    account_list.append({
                        "account_id": account.account_id,
                        "account_name": account.account_name,
                        "profile_id": account.profile_id,
                        "platform": "youtube",  # Default platform
                        "role": member.role,
                        "join_date": member.join_date.isoformat() if member.join_date else None
                    })
            
            return {
                "group_id": group.group_id,
                "group_name": group.group_name,
                "group_type": group.group_type,
                "description": group.description,
                "is_active": group.is_active,
                "member_count": len(account_list),
                "members": account_list,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"获取账号组详情失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups/{group_id}/members")
async def get_account_group_members(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取账号组成员"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /account-groups/{{group_id}}/members called - group_id: {group_id}")
    try:
        logger.info(f"[GET_MEMBERS] 开始获取账号组成员 - group_id: {group_id}")
        db = get_db_manager()
        
        with db.get_session() as session:
            # 检查组是否存在
            logger.debug(f"[GET_MEMBERS] 查询账号组: {group_id}")
            group = session.query(AccountGroupModel).filter_by(
                group_id=group_id
            ).first()
            
            if not group:
                logger.warning(f"[GET_MEMBERS] 账号组不存在: {group_id}")
                raise HTTPException(status_code=404, detail=f"账号组不存在: {group_id}")
            
            logger.debug(f"[GET_MEMBERS] 找到账号组: {group.group_name}")
            
            # 获取成员列表
            logger.debug(f"[GET_MEMBERS] 查询账号组成员...")
            members = session.query(AccountGroupMemberModel).filter_by(
                group_id=group_id,
                is_active=True
            ).all()
            
            logger.info(f"[GET_MEMBERS] 找到 {len(members)} 个成员记录")
            
            # 获取账号详细信息
            from database import Account
            result = []
            for i, member in enumerate(members):
                logger.debug(f"[GET_MEMBERS] 处理成员 {i+1}/{len(members)}: account_id={member.account_id}")
                account = session.query(Account).filter_by(
                    account_id=member.account_id
                ).first()
                
                if account:
                    member_info = {
                        "account_id": account.account_id,
                        "account_name": account.account_name,
                        "profile_id": account.profile_id,
                        "platform": "youtube",  # 添加platform字段
                        "role": member.role,
                        "join_date": member.join_date.isoformat() if member.join_date else None,
                        "is_active": member.is_active
                    }
                    result.append(member_info)
                    logger.debug(f"[GET_MEMBERS] 成员信息: {member_info}")
                else:
                    logger.warning(f"[GET_MEMBERS] 账号不存在: account_id={member.account_id}")
            
            response = {
                "group_id": group_id,
                "group_name": group.group_name,
                "members": result
            }
            
            logger.info(f"[GET_MEMBERS] 成功返回 {len(result)} 个成员信息")
            logger.debug(f"[GET_MEMBERS] 响应数据: {json.dumps(response, ensure_ascii=False)}")
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账号组成员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 发布配置管理 ============

# 存储发布配置的临时字典（实际应该存储在数据库中）
publish_configs_storage = {}

@router.post("/publish-configs", response_model=PublishConfigResponse)
async def create_publish_config(
    request: CreatePublishConfigRequest,
    current_user: Dict = Depends(require_auth)
):
    """创建发布配置"""
    try:
        # 记录接收到的原始请求数据
        logger.info(f"[API] 创建配置请求数据: {request.model_dump()}")
        # 验证Pipeline是否存在
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline(request.pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline不存在: {request.pipeline_id}")
        
        # 创建配置
        config_id = f"config_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        db = get_db_manager()
        
        # 使用事务确保配置和时间槽一起创建
        with db.get_session() as session:
            try:
                # 1. 插入配置到数据库
                session.execute(text("""
                    INSERT INTO publish_configs (
                        config_id, config_name, group_id, pipeline_id, 
                        pipeline_config, trigger_type, trigger_config, 
                        strategy_id, priority, is_active, created_at, updated_at
                    ) VALUES (
                        :config_id, :config_name, :group_id, :pipeline_id,
                        :pipeline_config, :trigger_type, :trigger_config,
                        :strategy_id, :priority, :is_active, :created_at, :updated_at
                    )
                """), {
                    "config_id": config_id,
                    "config_name": request.config_name,
                    "group_id": request.group_id,
                    "pipeline_id": request.pipeline_id,
                    "pipeline_config": json.dumps(request.pipeline_params or request.pipeline_config or {}),
                    "trigger_type": request.trigger_type,
                    "trigger_config": json.dumps(request.trigger_config),
                    "strategy_id": request.strategy_id,
                    "priority": request.priority,
                    "is_active": True,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
                
                logger.info(f"创建发布配置: {config_id}")
        
                # 2. 如果是定时触发，在同一事务中生成时间槽
                if request.trigger_type == 'scheduled':
                    trigger_config = request.trigger_config
                    schedule_type = trigger_config.get('schedule_type')
                    
                    if schedule_type == 'interval':
                        # 间隔调度：生成均匀分布的时间槽
                        ring_scheduler = get_ring_scheduler()
                        
                        # 获取组内第一个账号
                        accounts = session.execute(text("""
                            SELECT a.account_id FROM accounts a
                            JOIN account_group_members agm ON a.account_id = agm.account_id
                            WHERE agm.group_id = :group_id AND a.is_active = 1
                            LIMIT 1
                        """), {"group_id": request.group_id}).fetchall()
                        
                        if accounts:
                            # 获取同组其他间隔配置的数量（不包括当前正在创建的）
                            existing_interval_configs = session.execute(text("""
                                SELECT COUNT(*) FROM publish_configs
                                WHERE group_id = :group_id
                                AND trigger_type = 'scheduled'
                                AND JSON_EXTRACT(trigger_config, '$.schedule_type') = 'interval'
                                AND is_active = 1
                                AND config_id != :config_id
                            """), {"group_id": request.group_id, "config_id": config_id}).scalar() or 0
                            
                            # 计算间隔小时数
                            interval_value = trigger_config.get('schedule_interval', trigger_config.get('interval', 1))
                            interval_unit = trigger_config.get('schedule_interval_unit', trigger_config.get('unit', 'hours'))
                            
                            # 转换为小时
                            if interval_unit == 'minutes':
                                interval_hours = interval_value / 60
                            elif interval_unit == 'hours':
                                interval_hours = interval_value
                            elif interval_unit == 'days':
                                interval_hours = interval_value * 24
                            else:
                                interval_hours = 1
                            
                            # 生成时间槽
                            account_id = accounts[0][0]
                            config_index = existing_interval_configs  # 当前配置的索引
                            total_configs = config_index + 1  # 包含当前配置的总数
                            
                            slots = ring_scheduler.generate_interval_slots(
                                config_id=config_id,
                                account_id=account_id,
                                interval_hours=interval_hours,
                                config_index=config_index,
                                total_configs=total_configs,
                                days_ahead=7
                            )
                            
                            logger.info(f"为间隔配置 {config_id} 生成了 {len(slots)} 个时间槽，偏移索引: {config_index}")
                            
                            # 3. 在同一事务中保存时间槽
                            if slots:
                                # 直接在当前session中保存槽位
                                for slot in slots:
                                    session.execute(text("""
                                        INSERT INTO ring_schedule_slots (
                                            config_id, account_id, slot_date, 
                                            slot_hour, slot_minute, slot_index,
                                            status, metadata
                                        ) VALUES (
                                            :config_id, :account_id, :slot_date,
                                            :slot_hour, :slot_minute, :slot_index,
                                            :status, :metadata
                                        )
                                    """), {
                                        "config_id": slot.config_id,
                                        "account_id": slot.account_id,
                                        "slot_date": slot.slot_date,
                                        "slot_hour": slot.slot_time.hour,
                                        "slot_minute": slot.slot_time.minute,
                                        "slot_index": slot.slot_index,
                                        "status": slot.status,
                                        "metadata": json.dumps(slot.metadata) if slot.metadata else None
                                    })
                                
                                logger.info(f"已在事务中保存 {len(slots)} 个时间槽")
                    else:
                        # 其他调度类型（daily, weekly, monthly, cron等）
                        logger.info(f"处理调度类型: {request.trigger_config.get('schedule_type')}")
                        
                        # 为daily类型生成槽位
                        if request.trigger_config.get('schedule_type') == 'daily':
                            logger.info(f"开始为daily类型配置生成槽位")
                            
                            # 获取账号组的账号
                            accounts_query = text("""
                                SELECT a.account_id 
                                FROM accounts a
                                JOIN account_group_members agm ON a.account_id = agm.account_id
                                WHERE agm.group_id = :group_id 
                                AND a.is_active = 1
                            """)
                            accounts = session.execute(accounts_query, {"group_id": request.group_id}).fetchall()
                            
                            if not accounts:
                                logger.warning(f"账号组 {request.group_id} 没有活跃账号")
                            else:
                                account_id = accounts[0][0]
                                scheduled_time = request.trigger_config.get('time', '00:00')
                                logger.info(f"使用账号 {account_id}，每日执行时间: {scheduled_time}")
                                
                                # 生成未来7天的槽位
                                # 注意：json模块已在文件顶部导入，date、time、timedelta也已导入
                                
                                hour, minute = map(int, scheduled_time.split(':'))
                                start_date = date.today()
                                
                                # 如果今天的时间还没过，也生成今天的槽位
                                current_time = datetime.now()
                                if current_time.hour < hour or (current_time.hour == hour and current_time.minute < minute):
                                    logger.info(f"今天的执行时间未过，生成今天的槽位")
                                else:
                                    logger.info(f"今天的执行时间已过，从明天开始生成槽位")
                                    start_date = start_date + timedelta(days=1)
                                
                                slots_created = 0
                                for i in range(7):
                                    slot_date = start_date + timedelta(days=i)
                                    
                                    try:
                                        # 插入槽位
                                        insert_slot_query = text("""
                                            INSERT INTO ring_schedule_slots (
                                                config_id, account_id, slot_date, 
                                                slot_hour, slot_minute, slot_index,
                                                status, metadata, created_at, updated_at
                                            ) VALUES (
                                                :config_id, :account_id, :slot_date,
                                                :slot_hour, :slot_minute, :slot_index,
                                                :status, :metadata, datetime('now'), datetime('now')
                                            )
                                        """)
                                        
                                        session.execute(insert_slot_query, {
                                            "config_id": config_id,
                                            "account_id": account_id,
                                            "slot_date": slot_date,
                                            "slot_hour": hour,
                                            "slot_minute": minute,
                                            "slot_index": i,
                                            "status": "pending",
                                            "metadata": json.dumps({
                                                "schedule_type": "daily",
                                                "scheduled_time": scheduled_time
                                            })
                                        })
                                        slots_created += 1
                                        logger.info(f"创建槽位: {slot_date} {hour:02d}:{minute:02d}")
                                    except Exception as e:
                                        logger.warning(f"槽位创建失败或已存在: {slot_date} {hour:02d}:{minute:02d} - {e}")
                                
                                logger.info(f"成功创建 {slots_created} 个daily类型槽位")
                        
                        # 注册到调度执行器（保留原有逻辑）
                        schedule_executor = get_schedule_executor()
                        schedule_executor.add_config(config_id, request.trigger_config)
                        logger.info(f"已将配置 {config_id} 注册到调度执行器")
                
                # 4. 提交事务
                session.commit()
                logger.info(f"事务提交成功，配置和时间槽已原子性创建")
                
            except Exception as e:
                session.rollback()
                logger.error(f"事务回滚: {e}")
                raise
        
        return PublishConfigResponse(
            config_id=config_id,
            config_name=request.config_name,
            group_id=request.group_id,
            pipeline_id=request.pipeline_id,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
            strategy_id=request.strategy_id,
            priority=request.priority,
            is_active=True,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建发布配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/publish-configs")
async def list_publish_configs(
    group_id: Optional[str] = Query(None, description="筛选账号组"),
    pipeline_id: Optional[str] = Query(None, description="筛选Pipeline"),
    is_active: Optional[bool] = Query(None, description="是否只返回活跃配置"),
    search: Optional[str] = Query(None, description="搜索配置名称"),
    current_user: Dict = Depends(require_auth)
):
    """列出发布配置"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /publish-configs called - group_id: {group_id}, pipeline_id: {pipeline_id}, is_active: {is_active}, search: {search}")
    try:
        logger.info(f"开始列出发布配置，筛选条件: group_id={group_id}, pipeline_id={pipeline_id}, is_active={is_active}, search={search}")
        db = get_db_manager()
        with db.get_session() as session:
            # 构建查询
            query = "SELECT * FROM publish_configs WHERE 1=1"
            params = {}
            
            if group_id:
                query += " AND group_id = :group_id"
                params["group_id"] = group_id
            if pipeline_id:
                query += " AND pipeline_id = :pipeline_id"
                params["pipeline_id"] = pipeline_id
            if is_active is not None:
                query += " AND is_active = :is_active"
                params["is_active"] = is_active
            if search:
                query += " AND config_name LIKE :search"
                params["search"] = f"%{search}%"
            
            query += " ORDER BY created_at DESC"
            
            logger.info(f"执行SQL查询: {query}")
            logger.info(f"查询参数: {params}")
            
            results = session.execute(text(query), params).fetchall()
            logger.info(f"查询到 {len(results)} 条配置记录")
            
            configs = []
            for i, row in enumerate(results):
                print(row)
                logger.debug(f"处理第 {i+1} 条记录: {row[0]}, 列数: {len(row)}")
                try:
                    config = {
                        "config_id": row[0],
                        "config_name": row[1],
                        "group_id": row[2],
                        "pipeline_id": row[3],
                        "trigger_type": row[4],
                        "trigger_config": json.loads(row[5]) if row[5] and row[5].strip() else {},
                        "strategy_id": row[6],
                        "priority": row[7],
                        "is_active": row[8],
                        "created_at": row[10] if row[10] else None,
                        "updated_at": row[11] if row[11] else None,
                        "pipeline_config": json.loads(row[12]) if len(row) > 12 and row[12] and row[12].strip() else {}
                    }
                    configs.append(config)
                    logger.debug(f"成功处理配置: {config['config_id']}")
                except Exception as row_error:
                    logger.error(f"处理第 {i+1} 行数据时出错: {row_error}")
                    logger.error(f"错误的行数据: {row}")
                    raise
        
        logger.info(f"成功构建 {len(configs)} 个配置对象")
        return {"configs": configs, "total": len(configs)}
        
    except Exception as e:
        import traceback
        logger.error(f"列出发布配置失败: {e}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/publish-configs/{config_id}")
async def get_publish_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取单个发布配置详情"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /publish-configs/{{config_id}} called - config_id: {config_id}")
    try:
        db = get_db_manager()
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT * FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            config = {
                "config_id": result[0],
                "config_name": result[1],
                "group_id": result[2],
                "pipeline_id": result[3],
                "trigger_type": result[4],
                "trigger_config": json.loads(result[5]) if result[5] and result[5].strip() else {},
                "strategy_id": result[6],
                "priority": result[7],
                "is_active": result[8],
                "created_at": result[10],
                "updated_at": result[11],
                "pipeline_config": json.loads(result[12]) if result[12] and result[12].strip() else {}
            }
        
        return PublishConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发布配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/publish-configs/{config_id}")
async def update_publish_config(
    config_id: str,
    request: CreatePublishConfigRequest,
    current_user: Dict = Depends(require_auth)
):
    """更新发布配置"""
    logger.info(f"[API] 开始更新配置, config_id: {config_id}")
    logger.info(f"[API] 更新配置请求数据: {request.model_dump()}")
    try:
        db = get_db_manager()
        
        # 从数据库获取配置
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT * FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        # 验证Pipeline是否存在
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline(request.pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline不存在: {request.pipeline_id}")
        
        # 统一使用pipeline_params字段（兼容前端发送的pipeline_params）
        pipeline_config_data = request.pipeline_params or request.pipeline_config or {}
        logger.info(f"[API] <request.pipeline_params>: {request.pipeline_params}")
        logger.info(f"[API] < merge pipeline_config_data>: {pipeline_config_data}")
        # 更新数据库
        with db.get_session() as session:
            session.execute(text("""
                UPDATE publish_configs 
                SET config_name = :config_name,
                    group_id = :group_id,
                    pipeline_id = :pipeline_id,
                    pipeline_config = :pipeline_config,
                    trigger_type = :trigger_type,
                    trigger_config = :trigger_config,
                    strategy_id = :strategy_id,
                    priority = :priority,
                    updated_at = :updated_at
                WHERE config_id = :config_id
            """), {
                "config_id": config_id,
                "config_name": request.config_name,
                "group_id": request.group_id,
                "pipeline_id": request.pipeline_id,
                "pipeline_config": json.dumps(pipeline_config_data),
                "trigger_type": request.trigger_type,
                "trigger_config": json.dumps(request.trigger_config),
                "strategy_id": request.strategy_id,
                "priority": request.priority,
                "updated_at": datetime.now()
            })
            session.commit()
        
        logger.info(f"更新发布配置成功: {config_id}, pipeline_config: {pipeline_config_data}")
        
        # 返回更新后的配置
        with db.get_session() as session:
            updated = session.execute(text("""
                SELECT * FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            return {
                "config_id": updated[0],
                "config_name": updated[1],
                "group_id": updated[2],
                "pipeline_id": updated[3],
                "trigger_type": updated[4],
                "trigger_config": json.loads(updated[5]) if updated[5] and updated[5].strip() else {},
                "strategy_id": updated[6],
                "priority": updated[7],
                "is_active": updated[8],
                "pipeline_config": json.loads(updated[12]) if len(updated) > 12 and updated[12] and updated[12].strip() else {},
                "created_at": updated[10] if updated[10] else None,
                "updated_at": updated[11] if updated[11] else None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"更新发布配置失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/publish-configs/{config_id}")
async def delete_publish_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """删除发布配置"""
    try:
        db = get_db_manager()
        with db.get_session() as session:
            # 检查配置是否存在
            result = session.execute(text("""
                SELECT config_id FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            # 先删除相关的槽位
            session.execute(text("""
                DELETE FROM ring_schedule_slots 
                WHERE config_id = :config_id
                AND status IN ('pending', 'scheduled')
            """), {"config_id": config_id})
            
            # 再删除配置
            session.execute(text("""
                DELETE FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id})
            session.commit()
            
            logger.info(f"已删除配置 {config_id} 及其相关的槽位")
        
        logger.info(f"删除发布配置: {config_id}")
        
        return {"message": "配置删除成功", "config_id": config_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除发布配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/publish-configs/{config_id}/toggle")
async def toggle_publish_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """切换发布配置状态（启用/禁用）"""
    try:
        db = get_db_manager()
        with db.get_session() as session:
            # 获取当前状态
            result = session.execute(text("""
                SELECT is_active FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            # 切换状态
            new_status = not result[0]
            session.execute(text("""
                UPDATE publish_configs 
                SET is_active = :is_active, updated_at = :updated_at
                WHERE config_id = :config_id
            """), {
                "is_active": new_status,
                "updated_at": datetime.now(),
                "config_id": config_id
            })
            session.commit()
            
            logger.info(f"切换发布配置状态: {config_id} -> {new_status}")
            
            # 返回更新后的配置
            result = session.execute(text("""
                SELECT * FROM publish_configs WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            config = {
                "config_id": result[0],
                "config_name": result[1],
                "group_id": result[2],
                "pipeline_id": result[3],
                "trigger_type": result[4],
                "trigger_config": json.loads(result[5]) if result[5] and result[5].strip() else {},
                "strategy_id": result[6],
                "priority": result[7],
                "is_active": result[8],
                "created_at": result[10],
                "updated_at": result[11],
                "pipeline_config": json.loads(result[12]) if result[12] and result[12].strip() else {}
            }
        
        return PublishConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换发布配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish-configs/{config_id}/trigger")
async def manual_trigger_config(
    config_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth)
):
    """手动触发发布配置"""
    try:
        # 获取配置
        db = get_db_manager()
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT config_id, config_name, group_id, pipeline_id, pipeline_config,
                       trigger_type, trigger_config, strategy_id, priority, is_active
                FROM publish_configs
                WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            logger.info(f"[手动触发] 从数据库读取配置: {result}")
            logger.info(f"[手动触发] pipeline_config原始值: {result[4]}")
            
            config = {
                "config_id": result[0],
                "config_name": result[1],
                "group_id": result[2],
                "pipeline_id": result[3],
                "pipeline_config": json.loads(result[4]) if result[4] and result[4].strip() else {},
                "trigger_type": result[5],
                "trigger_config": json.loads(result[6]) if result[6] and result[6].strip() else {},
                "strategy_id": result[7],
                "priority": result[8],
                "is_active": result[9]
            }
            
            logger.info(f"[手动触发] 解析后的pipeline_config: {config['pipeline_config']}")
            
            if not config["is_active"]:
                raise HTTPException(status_code=400, detail="配置未启用，无法手动触发")
            
            # 获取账号组的所有账号
            accounts = session.execute(text("""
                SELECT a.account_id, a.account_name, a.profile_id, a.is_active
                FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                WHERE agm.group_id = :group_id AND a.is_active = 1
            """), {"group_id": config["group_id"]}).fetchall()
            
            if not accounts:
                raise HTTPException(status_code=400, detail="账号组中没有可用账号")
            
            # 获取Pipeline
            registry = get_pipeline_registry()
            pipeline = registry.get_pipeline(config["pipeline_id"])
            if not pipeline:
                raise HTTPException(status_code=404, detail=f"Pipeline不存在: {config['pipeline_id']}")
            
            # 为每个账号创建任务
            created_tasks = []
            for account in accounts:
                task_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # 创建任务记录
                session.execute(text("""
                    INSERT INTO auto_publish_tasks (
                        task_id, config_id, group_id, account_id, pipeline_id, 
                        pipeline_status, created_at
                    ) VALUES (
                        :task_id, :config_id, :group_id, :account_id, :pipeline_id,
                        'pending', :created_at
                    )
                """), {
                    "task_id": task_id,
                    "config_id": config_id,
                    "group_id": config["group_id"],
                    "account_id": account[0],
                    "pipeline_id": config["pipeline_id"],
                    "created_at": datetime.now()
                })
                
                created_tasks.append({
                    "task_id": task_id,
                    "account_id": account[0],
                    "account_name": account[1]
                })
                
                # 异步执行Pipeline
                background_tasks.add_task(
                    execute_pipeline_task,
                    task_id,
                    account[0],
                    config["pipeline_id"],
                    config.get("pipeline_config", {})
                )
            
            session.commit()
            
            logger.info(f"手动触发配置 {config_id}，创建了 {len(created_tasks)} 个任务")
            
            return {
                "message": f"成功触发配置，创建了 {len(created_tasks)} 个任务",
                "config_id": config_id,
                "task_count": len(created_tasks),
                "tasks": created_tasks
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动触发配置失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

async def execute_pipeline_task(task_id: str, account_id: str, pipeline_id: str, pipeline_config: dict):
    """执行Pipeline任务（后台任务）"""
    try:
        db = get_db_manager()
        registry = get_pipeline_registry()
        
        # 更新任务状态为运行中
        with db.get_session() as session:
            session.execute(text("""
                UPDATE auto_publish_tasks
                SET pipeline_status = 'running', started_at = :started_at
                WHERE task_id = :task_id
            """), {
                "task_id": task_id,
                "started_at": datetime.now()
            })
            session.commit()
        
        # 获取Pipeline
        logger.info(f"[Pipeline执行] 开始获取Pipeline: {pipeline_id}")
        pipeline_metadata = registry.get_pipeline(pipeline_id)
        logger.info(f"[Pipeline执行] Pipeline元数据: {pipeline_metadata}, 类型: {type(pipeline_metadata)}")
        
        if not pipeline_metadata:
            logger.error(f"[Pipeline执行] Pipeline不存在: {pipeline_id}")
            raise Exception(f"Pipeline不存在: {pipeline_id}")
        
        # 检查是否是PipelineMetadata对象
        if hasattr(pipeline_metadata, 'pipeline_class'):
            # 如果是PipelineMetadata对象，获取实际的类
            pipeline_class_str = pipeline_metadata.pipeline_class
            logger.info(f"[Pipeline执行] Pipeline类路径: {pipeline_class_str}")
            
            # 动态导入Pipeline类
            module_name, class_name = pipeline_class_str.rsplit('.', 1)
            logger.info(f"[Pipeline执行] 导入模块: {module_name}, 类名: {class_name}")
            
            import importlib
            module = importlib.import_module(module_name)
            pipeline_class = getattr(module, class_name)
            logger.info(f"[Pipeline执行] 成功导入Pipeline类: {pipeline_class}")
        else:
            # 直接使用返回的类
            pipeline_class = pipeline_metadata
            logger.info(f"[Pipeline执行] 直接使用Pipeline类: {pipeline_class}")
        
        # 获取账号信息
        logger.info(f"[Pipeline执行] 获取账号信息: {account_id}")
        with db.get_session() as session:
            account = session.execute(text("""
                SELECT account_id, account_name, profile_id, channel_url
                FROM accounts
                WHERE account_id = :account_id
            """), {"account_id": account_id}).fetchone()
            
            if not account:
                logger.error(f"[Pipeline执行] 账号不存在: {account_id}")
                raise Exception(f"账号不存在: {account_id}")
            
            logger.info(f"[Pipeline执行] 账号信息: ID={account[0]}, 名称={account[1]}")
        
        # 执行Pipeline
        logger.info(f"[Pipeline执行] 创建Pipeline实例，配置: {pipeline_config}")
        pipeline_instance = pipeline_class(pipeline_config)
        logger.info(f"[Pipeline执行] Pipeline实例创建成功: {pipeline_instance}")
        
        # 合并账号参数和pipeline配置参数
        execute_params = {
            "account_id": account[0],
            "account_name": account[1],
            "profile_id": account[2],
            "channel_url": account[3],
            "platform": "youtube",  # 默认平台
            "cookies": {},  # 暂时使用空的cookies
            **pipeline_config  # 合并pipeline配置参数（如video_id等）
        }
        logger.info(f"[Pipeline执行] 执行参数: {execute_params}")
        
        logger.info(f"[Pipeline执行] 开始执行Pipeline...")
        # execute方法现在是异步的，需要await
        result = await pipeline_instance.execute(execute_params)
        logger.info(f"[Pipeline执行] Pipeline执行完成，结果: {result}")
        
        # 根据执行结果更新任务状态
        if result and result.get('success'):
            # 执行成功
            with db.get_session() as session:
                session.execute(text("""
                    UPDATE auto_publish_tasks
                    SET pipeline_status = 'completed',
                        completed_at = :completed_at,
                        pipeline_result = :pipeline_result
                    WHERE task_id = :task_id
                """), {
                    "task_id": task_id,
                    "completed_at": datetime.now(),
                    "pipeline_result": json.dumps(result) if result else None
                })
                session.commit()
            logger.info(f"任务 {task_id} 执行成功")
        else:
            # 执行失败
            error_msg = result.get('error', 'Pipeline execution failed') if result else 'Pipeline returned no result'
            with db.get_session() as session:
                session.execute(text("""
                    UPDATE auto_publish_tasks
                    SET pipeline_status = 'failed',
                        completed_at = :completed_at,
                        error_message = :error_message,
                        pipeline_result = :pipeline_result
                    WHERE task_id = :task_id
                """), {
                    "task_id": task_id,
                    "completed_at": datetime.now(),
                    "error_message": error_msg,
                    "pipeline_result": json.dumps(result) if result else None
                })
                session.commit()
            logger.error(f"任务 {task_id} 执行失败: {error_msg}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 更新任务状态为失败
        try:
            db = get_db_manager()
            with db.get_session() as session:
                session.execute(text("""
                    UPDATE auto_publish_tasks
                    SET pipeline_status = 'failed',
                        completed_at = :completed_at,
                        error_message = :error_message
                    WHERE task_id = :task_id
                """), {
                    "task_id": task_id,
                    "completed_at": datetime.now(),
                    "error_message": str(e)
                })
                session.commit()
        except Exception as update_error:
            logger.error(f"更新任务状态失败: {update_error}")
            import traceback
            logger.error(traceback.format_exc())

@router.get("/publish-configs/{config_id}/tasks")
async def get_config_tasks(
    config_id: str,
    status: Optional[str] = Query(None, description="任务状态筛选"),
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict = Depends(require_auth)
):
    """获取配置关联的任务列表"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /publish-configs/{{config_id}}/tasks called - config_id: {config_id}, status: {status}, limit: {limit}")
    try:
        logger.info(f"获取配置任务列表: config_id={config_id}, status={status}, limit={limit}")
        
        # 从数据库验证配置是否存在
        db = get_db_manager()
        
        # 写入调试文件
        with open("/tmp/debug_api.log", "a") as f:
            f.write(f"\n[DEBUG] Database URL: {db.db_url}\n")
            f.write(f"[DEBUG] Looking for config_id: {config_id}\n")
        
        with db.get_session() as session:
            try:
                # 先查询所有配置看看
                all_configs = session.execute(text("SELECT config_id FROM publish_configs")).fetchall()
                
                with open("/tmp/debug_api.log", "a") as f:
                    f.write(f"[DEBUG] All configs in DB: {all_configs}\n")
                
                config_check = session.execute(text("""
                    SELECT config_id FROM publish_configs WHERE config_id = :config_id
                """), {"config_id": config_id}).fetchone()
                
                with open("/tmp/debug_api.log", "a") as f:
                    f.write(f"[DEBUG] Query result for {config_id}: {config_check}\n")
                
                logger.info(f"配置查询结果: config_id={config_id}, found={config_check is not None}")
            except Exception as e:
                with open("/tmp/debug_api.log", "a") as f:
                    f.write(f"[DEBUG] Query failed: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
                logger.error(f"查询配置失败: {e}", exc_info=True)
                config_check = None
            
            if not config_check:
                logger.warning(f"配置不存在: {config_id}")
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        db = get_db_manager()
        
        with db.get_session() as session:
            # 构建查询
            query = """
                SELECT 
                    apt.task_id,
                    apt.pipeline_id,
                    a.account_name,
                    apt.pipeline_status as status,
                    apt.created_at,
                    apt.started_at,
                    apt.completed_at,
                    CASE 
                        WHEN apt.completed_at IS NOT NULL AND apt.started_at IS NOT NULL
                        THEN (julianday(apt.completed_at) - julianday(apt.started_at)) * 86400
                        ELSE NULL
                    END as duration
                FROM auto_publish_tasks apt
                LEFT JOIN accounts a ON apt.account_id = a.account_id
                WHERE apt.config_id = :config_id
            """
            
            params = {"config_id": config_id}
            
            if status:
                query += " AND apt.pipeline_status = :status"
                params["status"] = status
            
            query += " ORDER BY apt.created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            results = session.execute(text(query), params).fetchall()
            
            tasks = []
            for r in results:
                tasks.append({
                    "task_id": r[0],
                    "pipeline_id": r[1],
                    "account_name": r[2] or "未知账号",
                    "status": r[3],
                    "created_at": str(r[4]) if r[4] else None,
                    "started_at": str(r[5]) if r[5] else None,
                    "completed_at": str(r[6]) if r[6] else None,
                    "duration": int(r[7]) if r[7] else None
                })
            
            logger.info(f"成功获取 {len(tasks)} 个任务")
            return {"tasks": tasks, "total": len(tasks)}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/publish-configs/{config_id}/stats")
async def get_config_stats(
    config_id: str,
    period: str = Query("week", regex="^(today|week|month)$"),
    current_user: Dict = Depends(require_auth)
):
    """获取配置执行统计"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /publish-configs/{{config_id}}/stats called - config_id: {config_id}, period: {period}")
    try:
        logger.info(f"获取配置统计: config_id={config_id}, period={period}")
        
        db = get_db_manager()
        
        # 从数据库验证配置是否存在
        with db.get_session() as session:
            try:
                config_check = session.execute(text("""
                    SELECT config_id FROM publish_configs WHERE config_id = :config_id
                """), {"config_id": config_id}).fetchone()
                logger.info(f"[stats] 配置查询结果: config_id={config_id}, found={config_check is not None}")
            except Exception as e:
                logger.error(f"[stats] 查询配置失败: {e}", exc_info=True)
                config_check = None
            
            if not config_check:
                logger.warning(f"配置不存在: {config_id}")
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        db = get_db_manager()
        
        with db.get_session() as session:
            # 获取统计数据
            results = session.execute(text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    AVG(CASE 
                        WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400
                        ELSE NULL
                    END) as avg_duration
                FROM auto_publish_tasks
                WHERE config_id = :config_id
                  AND created_at >= :start_date
            """), {
                "config_id": config_id,
                "start_date": start_date
            }).fetchone()
            
            stats = {
                "total_tasks": results[0] or 0,
                "success_count": results[1] or 0,
                "failed_count": results[2] or 0,
                "success_rate": round((results[1] or 0) / (results[0] or 1) * 100, 1),
                "avg_duration": int(results[3]) if results[3] else 0,
                "period": period
            }
            
            logger.info(f"成功获取统计数据: {stats}")
            return stats
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 调度管理 ============

@router.post("/schedule/generate-slots")
async def generate_schedule_slots(
    request: GenerateSlotsRequest,
    current_user: Dict = Depends(require_auth)
):
    """生成调度槽位"""
    try:
        scheduler = get_ring_scheduler()
        
        # 获取账号组的账号列表
        # 这里简化处理，实际应该从数据库查询
        accounts = ["account_1", "account_2", "account_3"]
        
        # 生成槽位
        slots = scheduler.generate_slots(
            config_id=request.config_id,
            accounts=accounts,
            target_date=request.target_date,
            start_hour=request.start_hour,
            end_hour=request.end_hour,
            strategy=request.strategy
        )
        
        # 保存槽位
        success = scheduler.save_slots(slots)
        
        if success:
            return {
                "success": True,
                "message": f"成功生成 {len(slots)} 个调度槽位",
                "slots": [
                    {
                        "account_id": slot.account_id,
                        "slot_time": slot.datetime.isoformat(),
                        "slot_index": slot.slot_index
                    }
                    for slot in slots
                ]
            }
        else:
            raise HTTPException(status_code=500, detail="保存槽位失败")
            
    except Exception as e:
        logger.error(f"生成调度槽位失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule/slots/{config_id}")
async def get_schedule_slots(
    config_id: str,
    target_date: date,
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: Dict = Depends(require_auth)
):
    """获取调度槽位"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /schedule/slots/{{config_id}} called - config_id: {config_id}, target_date: {target_date}, status: {status}")
    try:
        scheduler = get_ring_scheduler()
        
        slots = scheduler.get_slots_by_date(
            config_id=config_id,
            target_date=target_date,
            status=status
        )
        
        return {
            "config_id": config_id,
            "target_date": target_date.isoformat(),
            "total_slots": len(slots),
            "slots": [
                {
                    "slot_id": slot.slot_id,
                    "account_id": slot.account_id,
                    "slot_time": slot.datetime.isoformat(),
                    "status": slot.status,
                    "task_id": slot.task_id
                }
                for slot in slots
            ]
        }
        
    except Exception as e:
        logger.error(f"获取调度槽位失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 执行器控制 ============

@router.post("/executor/start")
async def start_executor(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth)
):
    """启动执行器"""
    try:
        executor = get_account_driven_executor()
        
        # 在后台启动执行器
        background_tasks.add_task(executor.start)
        
        return {
            "success": True,
            "message": "执行器启动中"
        }
        
    except Exception as e:
        logger.error(f"启动执行器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/executor/stop")
async def stop_executor(
    current_user: Dict = Depends(require_auth)
):
    """停止执行器"""
    try:
        executor = get_account_driven_executor()
        await executor.stop()
        
        return {
            "success": True,
            "message": "执行器已停止"
        }
        
    except Exception as e:
        logger.error(f"停止执行器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executor/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取任务状态"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /executor/task/{{task_id}} called - task_id: {task_id}")
    try:
        executor = get_account_driven_executor()
        task_status = executor.get_task_status(task_id)
        
        if task_status:
            return task_status
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 策略管理 ============

@router.get("/strategies")
async def list_strategies(
    strategy_type: Optional[str] = Query(None, description="筛选策略类型"),
    is_active: bool = Query(True, description="是否只返回活跃策略"),
    current_user: Dict = Depends(require_auth)
):
    """列出策略"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /strategies called - strategy_type: {strategy_type}, is_active: {is_active}")
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            query = session.query(PublishStrategyModel)
            
            # 筛选条件
            if strategy_type:
                query = query.filter_by(strategy_type=strategy_type)
            if is_active:
                query = query.filter_by(is_active=is_active)
            
            strategies = query.all()
            
            result = []
            for strategy in strategies:
                result.append({
                    "strategy_id": strategy.strategy_id,
                    "strategy_name": strategy.strategy_name,
                    "strategy_type": strategy.strategy_type,
                    "parameters": strategy.parameters,
                    "description": strategy.description,
                    "is_active": strategy.is_active,
                    "start_date": strategy.start_date.isoformat() if strategy.start_date else None,
                    "end_date": strategy.end_date.isoformat() if strategy.end_date else None,
                    "created_at": strategy.created_at.isoformat()
                })
            
            return {"strategies": result}
            
    except Exception as e:
        logger.error(f"列出策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies")
async def create_strategy(
    request: CreateStrategyRequest,
    current_user: Dict = Depends(require_auth)
):
    """创建策略"""
    try:
        engine = get_strategy_engine()
        
        strategy = engine.create_strategy(
            strategy_name=request.strategy_name,
            strategy_type=request.strategy_type,
            parameters=request.parameters,
            description=request.description,
            start_date=datetime.combine(request.start_date, time()) if request.start_date else None,
            end_date=datetime.combine(request.end_date, time()) if request.end_date else None
        )
        
        if strategy:
            return {
                "success": True,
                "strategy_id": strategy.strategy_id,
                "message": f"成功创建策略: {strategy.strategy_name}"
            }
        else:
            raise HTTPException(status_code=500, detail="创建策略失败")
            
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/assign")
async def assign_strategy(
    request: AssignStrategyRequest,
    current_user: Dict = Depends(require_auth)
):
    """分配策略到账号组"""
    try:
        engine = get_strategy_engine()
        
        success = engine.assign_group_to_strategy(
            strategy_id=request.strategy_id,
            group_id=request.group_id,
            variant_name=request.variant_name,
            variant_config=request.variant_config,
            weight=request.weight,
            is_control=request.is_control
        )
        
        if success:
            return {
                "success": True,
                "message": f"成功分配账号组 {request.group_id} 到策略 {request.strategy_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="分配策略失败")
            
    except Exception as e:
        logger.error(f"分配策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/report")
async def get_strategy_report(
    strategy_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取策略报告"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /strategies/{{strategy_id}}/report called - strategy_id: {strategy_id}")
    try:
        engine = get_strategy_engine()
        report = engine.get_strategy_report(strategy_id)
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 平台监控 ============

@router.post("/monitors")
async def create_monitor(
    request: MonitorConfigRequest,
    current_user: Dict = Depends(require_auth)
):
    """创建监控配置"""
    try:
        monitor_id = f"monitor_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 这里简化处理，实际应该保存到数据库
        monitor = {
            "monitor_id": monitor_id,
            "platform": request.platform,
            "monitor_type": request.monitor_type,
            "target_identifier": request.target_identifier,
            "check_interval": request.check_interval,
            "config": request.config,
            "is_active": True,
            "created_at": datetime.now()
        }
        
        logger.info(f"创建监控配置: {monitor_id}")
        
        return {
            "success": True,
            "monitor_id": monitor_id,
            "message": f"成功创建监控配置"
        }
        
    except Exception as e:
        logger.error(f"创建监控配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitors/fetch")
async def fetch_monitored_content(
    platform: str = Query(..., description="平台"),
    monitor_type: str = Query(..., description="监控类型"),
    target: str = Query(..., description="目标"),
    max_results: int = Query(10, ge=1, le=50, description="最大结果数"),
    current_user: Dict = Depends(require_auth)
):
    """手动获取监控内容"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /monitors/fetch called - platform: {platform}, monitor_type: {monitor_type}, target: {target}, max_results: {max_results}")
    try:
        monitor = get_platform_monitor()
        
        items = await monitor.fetch_content(
            platform=platform,
            monitor_type=monitor_type,
            target=target,
            max_results=max_results
        )
        
        return {
            "platform": platform,
            "monitor_type": monitor_type,
            "target": target,
            "total": len(items),
            "items": [item.to_dict() for item in items]
        }
        
    except Exception as e:
        logger.error(f"获取监控内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitors/start")
async def start_monitoring(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth)
):
    """启动平台监控"""
    try:
        monitor = get_platform_monitor()
        
        # 在后台启动监控
        background_tasks.add_task(monitor.start_monitoring)
        
        return {
            "success": True,
            "message": "平台监控启动中"
        }
        
    except Exception as e:
        logger.error(f"启动平台监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Pipeline注册表 ============

@router.get("/pipelines")
async def list_pipelines(
    pipeline_type: Optional[str] = Query(None, description="筛选类型"),
    platform: Optional[str] = Query(None, description="筛选平台"),
    status: Optional[str] = Query(None, description="筛选状态"),
    current_user: Dict = Depends(require_auth)
):
    """列出Pipeline"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /pipelines called - pipeline_type: {pipeline_type}, platform: {platform}, status: {status}")
    try:
        registry = get_pipeline_registry()
        
        pipelines = registry.list_pipelines(
            pipeline_type=pipeline_type,
            platform=platform,
            status=status
        )
        
        # 添加调试日志
        logger.info(f"获取到 {len(pipelines)} 个Pipeline")
        
        result_pipelines = []
        for p in pipelines:
            # 记录每个pipeline的schema信息
            logger.debug(f"Pipeline {p.pipeline_id} config_schema: {p.config_schema}")
            
            pipeline_data = {
                "pipeline_id": p.pipeline_id,
                "pipeline_name": p.pipeline_name,
                "pipeline_type": p.pipeline_type,
                "pipeline_class": p.pipeline_class,
                "config_schema": p.config_schema,  # 添加config_schema
                "supported_platforms": p.supported_platforms,
                "version": p.version,
                "status": p.status,
                "metadata": p.metadata if hasattr(p, 'metadata') else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            result_pipelines.append(pipeline_data)
        
        return {
            "total": len(pipelines),
            "pipelines": result_pipelines
        }
        
    except Exception as e:
        logger.error(f"列出Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PipelineRegisterRequest(BaseModel):
    pipeline_id: str
    pipeline_name: str
    pipeline_type: str
    pipeline_class: str
    config_schema: Dict[str, Any]
    supported_platforms: List[str] = ["youtube"]
    version: str = "1.0.0"

@router.post("/pipelines/register")
async def register_pipeline(
    request: PipelineRegisterRequest,
    current_user: Dict = Depends(require_auth)
):
    """注册Pipeline"""
    try:
        registry = get_pipeline_registry()
        
        # 添加日志记录接收到的数据
        logger.info(f"注册Pipeline请求: pipeline_id={request.pipeline_id}")
        logger.info(f"config_schema类型: {type(request.config_schema)}")
        logger.info(f"config_schema内容: {json.dumps(request.config_schema, indent=2, ensure_ascii=False)}")
        
        success = registry.register_pipeline(
            pipeline_id=request.pipeline_id,
            pipeline_name=request.pipeline_name,
            pipeline_type=request.pipeline_type,
            pipeline_class=request.pipeline_class,
            config_schema=request.config_schema,
            supported_platforms=request.supported_platforms,
            version=request.version
        )
        
        # 验证保存结果
        if success:
            saved_pipeline = registry.get_pipeline(request.pipeline_id)
            if saved_pipeline:
                logger.info(f"Pipeline保存成功，验证config_schema: {saved_pipeline.config_schema}")
            else:
                logger.warning(f"Pipeline保存后无法获取: {request.pipeline_id}")
        
        if success:
            return {
                "success": True,
                "message": f"成功注册Pipeline: {request.pipeline_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="注册Pipeline失败")
            
    except Exception as e:
        import traceback
        logger.error(f"注册Pipeline失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取Pipeline详情"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /pipelines/{{pipeline_id}} called - pipeline_id: {pipeline_id}")
    try:
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline(pipeline_id)
        
        if pipeline:
            return {
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_name": pipeline.pipeline_name,
                "pipeline_type": pipeline.pipeline_type,
                "pipeline_class": pipeline.pipeline_class,
                "config_schema": pipeline.config_schema,
                "supported_platforms": pipeline.supported_platforms,
                "version": pipeline.version,
                "status": pipeline.status,
                "created_at": pipeline.created_at.isoformat() if pipeline.created_at else None,
                "updated_at": pipeline.updated_at.isoformat() if pipeline.updated_at else None
            }
        else:
            raise HTTPException(status_code=404, detail="Pipeline不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    request: Dict[str, Any],
    current_user: Dict = Depends(require_auth)
):
    """更新Pipeline"""
    try:
        registry = get_pipeline_registry()
        
        # 更新Pipeline
        success = registry.update_pipeline(pipeline_id, request)
        
        if success:
            return {
                "success": True,
                "message": f"成功更新Pipeline: {pipeline_id}"
            }
        else:
            raise HTTPException(status_code=404, detail="Pipeline不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    current_user: Dict = Depends(require_auth)
):
    """删除Pipeline"""
    try:
        registry = get_pipeline_registry()
        
        # 检查是否有关联的配置
        db = get_db_manager()
        with db.get_session() as session:
            from sqlalchemy import text
            config_count = session.execute(
                text("SELECT COUNT(*) FROM publish_configs WHERE pipeline_id = :pipeline_id"),
                {"pipeline_id": pipeline_id}
            ).fetchone()[0]
            
            if config_count > 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Pipeline有{config_count}个关联配置，无法删除"
                )
        
        # 删除Pipeline
        success = registry.delete_pipeline(pipeline_id)
        
        if success:
            return {
                "success": True,
                "message": f"成功删除Pipeline: {pipeline_id}"
            }
        else:
            raise HTTPException(status_code=404, detail="Pipeline不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 全局概览 ============

@router.get("/overview/stats")
async def get_overview_stats(
    period: str = Query("today", regex="^(today|week|month)$"),
    current_user: Dict = Depends(require_auth)
):
    """获取概览统计数据"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /overview/stats called - period: {period}")
    try:
        from datetime import timedelta
        db = get_db_manager()
        
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        with db.get_session() as session:
            # 查询Pipeline总数
            pipeline_count = session.execute(
                text("SELECT COUNT(*) as count FROM pipeline_registry WHERE status = 'active'")
            ).fetchone()[0]
            
            # 查询配置总数
            config_count = session.execute(
                text("SELECT COUNT(*) as count FROM publish_configs WHERE is_active = 1")
            ).fetchone()[0]
            
            # 查询任务统计
            task_stats = session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN created_at >= :start_date THEN 1 ELSE 0 END) as period_count,
                    SUM(CASE WHEN created_at >= :today AND pipeline_status = 'completed' THEN 1 ELSE 0 END) as today_success,
                    SUM(CASE WHEN created_at >= :today THEN 1 ELSE 0 END) as today_total,
                    SUM(CASE WHEN created_at >= :week AND pipeline_status = 'completed' THEN 1 ELSE 0 END) as week_success,
                    SUM(CASE WHEN created_at >= :week THEN 1 ELSE 0 END) as week_total,
                    SUM(CASE WHEN created_at >= :month AND pipeline_status = 'completed' THEN 1 ELSE 0 END) as month_success,
                    SUM(CASE WHEN created_at >= :month THEN 1 ELSE 0 END) as month_total,
                    SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN pipeline_status = 'running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN pipeline_status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM auto_publish_tasks
            """), {
                "start_date": start_date,
                "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
                "week": now - timedelta(days=7),
                "month": now - timedelta(days=30)
            }).fetchone()
            
            # 查询账号统计
            account_stats = session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM account_groups WHERE is_active = 1) as groups,
                    (SELECT COUNT(*) FROM accounts WHERE is_active = 1) as total,
                    (SELECT COUNT(DISTINCT account_id) FROM auto_publish_tasks 
                     WHERE created_at >= :start_date) as active
                FROM accounts LIMIT 1
            """), {"start_date": start_date}).fetchone()
            
            # 计算成功率
            success_rates = {}
            if task_stats:
                today_total = task_stats[3] if task_stats[3] is not None else 0
                today_success = task_stats[2] if task_stats[2] is not None else 0
                week_total = task_stats[5] if task_stats[5] is not None else 0
                week_success = task_stats[4] if task_stats[4] is not None else 0
                month_total = task_stats[7] if task_stats[7] is not None else 0
                month_success = task_stats[6] if task_stats[6] is not None else 0
                
                success_rates["today"] = round((today_success / today_total) * 100, 1) if today_total > 0 else 0
                success_rates["week"] = round((week_success / week_total) * 100, 1) if week_total > 0 else 0
                success_rates["month"] = round((month_success / month_total) * 100, 1) if month_total > 0 else 0
            else:
                success_rates["today"] = 0
                success_rates["week"] = 0
                success_rates["month"] = 0
            
            return {
                "pipelines": pipeline_count or 0,
                "configs": config_count or 0,
                "tasks": {
                    "total": (task_stats[0] if task_stats else 0) or 0,
                    "today": (task_stats[3] if task_stats else 0) or 0,
                    "week": (task_stats[5] if task_stats else 0) or 0,
                    "month": (task_stats[7] if task_stats else 0) or 0,
                    "success": (task_stats[8] if task_stats else 0) or 0,
                    "failed": (task_stats[9] if task_stats else 0) or 0,
                    "running": (task_stats[10] if task_stats else 0) or 0,
                    "pending": (task_stats[11] if task_stats else 0) or 0
                },
                "accounts": {
                    "groups": (account_stats[0] if account_stats else 0) or 0,
                    "total": (account_stats[1] if account_stats else 0) or 0,
                    "active": (account_stats[2] if account_stats else 0) or 0
                },
                "successRate": success_rates
            }
            
    except Exception as e:
        logger.error(f"获取概览统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview/task-time-distribution")
async def get_task_time_distribution(
    period: str = Query("today", regex="^(today|week|month)$"),
    current_user: Dict = Depends(require_auth)
):
    """获取任务时间分布数据"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /overview/task-time-distribution called - period: {period}")
    try:
        from datetime import timedelta
        db = get_db_manager()
        
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        with db.get_session() as session:
            # SQLite使用strftime函数获取小时
            results = session.execute(text("""
                SELECT 
                    CASE 
                        WHEN CAST(strftime('%H', created_at) AS INTEGER) < 6 THEN '00-06'
                        WHEN CAST(strftime('%H', created_at) AS INTEGER) < 12 THEN '06-12'
                        WHEN CAST(strftime('%H', created_at) AS INTEGER) < 18 THEN '12-18'
                        ELSE '18-24'
                    END as timeRange,
                    COUNT(*) as count
                FROM auto_publish_tasks
                WHERE created_at >= :start_date
                GROUP BY timeRange
                ORDER BY timeRange
            """), {"start_date": start_date}).fetchall()
            
            # 计算百分比
            distribution = []
            total = sum(r[1] for r in results) if results else 0
            
            # 确保所有时间段都有数据
            time_ranges = ['00-06', '06-12', '12-18', '18-24']
            result_dict = {r[0]: r[1] for r in results} if results else {}
            
            for time_range in time_ranges:
                count = result_dict.get(time_range, 0)
                percentage = round((count / total) * 100, 1) if total > 0 else 0
                distribution.append({
                    "timeRange": time_range,
                    "count": count,
                    "percentage": percentage
                })
            
            return distribution
            
    except Exception as e:
        logger.error(f"获取任务时间分布失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview/top-accounts")
async def get_top_accounts(
    limit: int = Query(5, ge=1, le=10),
    period: str = Query("today", regex="^(today|week|month)$"),
    metric: str = Query("views", regex="^(views|likes|subscribers)$"),
    current_user: Dict = Depends(require_auth)
):
    """获取账号TOP榜"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /overview/top-accounts called - limit: {limit}, period: {period}, metric: {metric}")
    try:
        from datetime import timedelta
        db = get_db_manager()
        
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        with db.get_session() as session:
            # 查询TOP账号
            results = session.execute(text("""
                SELECT 
                    a.account_id,
                    a.account_name,
                    COUNT(apt.task_id) as task_count,
                    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_count
                FROM accounts a
                LEFT JOIN auto_publish_tasks apt ON a.account_id = apt.account_id
                WHERE apt.created_at >= :start_date
                  AND apt.pipeline_status = 'completed'
                GROUP BY a.account_id, a.account_name
                ORDER BY success_count DESC
                LIMIT :limit
            """), {"start_date": start_date, "limit": limit}).fetchall()
            
            top_accounts = []
            for r in results:
                # 模拟的指标数据（实际应该从任务元数据中提取）
                import random
                top_accounts.append({
                    "account_id": r[0],
                    "account_name": r[1],
                    "metrics": {
                        "views": random.randint(1000, 50000),
                        "likes": random.randint(50, 2000),
                        "comments": random.randint(10, 500),
                        "subscribers_gained": random.randint(10, 1000)
                    }
                })
            
            return top_accounts
            
    except Exception as e:
        logger.error(f"获取账号TOP榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview/recent-tasks")
async def get_recent_tasks(
    limit: int = Query(10, ge=1, le=20),
    current_user: Dict = Depends(require_auth)
):
    """获取最近执行任务"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /overview/recent-tasks called - limit: {limit}")
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            results = session.execute(text("""
                SELECT 
                    apt.task_id,
                    pr.pipeline_name,
                    a.account_name,
                    apt.pipeline_status as status,
                    apt.created_at,
                    CASE 
                        WHEN apt.completed_at IS NOT NULL AND apt.started_at IS NOT NULL
                        THEN (julianday(apt.completed_at) - julianday(apt.started_at)) * 86400
                        ELSE NULL
                    END as duration
                FROM auto_publish_tasks apt
                LEFT JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
                LEFT JOIN accounts a ON apt.account_id = a.account_id
                ORDER BY apt.created_at DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            recent_tasks = []
            for r in results:
                recent_tasks.append({
                    "task_id": r[0],
                    "pipeline_name": r[1] or "未知Pipeline",
                    "account_name": r[2] or "未知账号",
                    "status": r[3],
                    "created_at": r[4] if r[4] else None,
                    "duration": int(r[5]) if r[5] else None
                })
            
            return recent_tasks
            
    except Exception as e:
        logger.error(f"获取最近执行任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Tab 3: 执行记录管理 API ============

@router.get("/tasks")
async def get_task_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    config_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict = Depends(require_auth)
):
    """获取任务列表"""
    logger.info(f"[Line {inspect.currentframe().f_lineno}] GET /tasks called - page: {page}, page_size: {page_size}, status: {status}, config_id: {config_id}, account_id: {account_id}, start_date: {start_date}, end_date: {end_date}")
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 构建查询条件
            where_clauses = []
            params = {}
            
            if status:
                where_clauses.append("apt.pipeline_status = :status")
                params["status"] = status
            if config_id:
                where_clauses.append("apt.config_id = :config_id")
                params["config_id"] = config_id
            if account_id:
                where_clauses.append("apt.account_id = :account_id")
                params["account_id"] = account_id
            if start_date:
                where_clauses.append("apt.created_at >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where_clauses.append("apt.created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # 获取总数
            count_result = session.execute(text(f"""
                SELECT COUNT(*) FROM auto_publish_tasks apt
                WHERE {where_clause}
            """), params).fetchone()
            total = count_result[0] if count_result else 0
            
            # 获取任务列表
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset
            
            results = session.execute(text(f"""
                SELECT 
                    apt.task_id,
                    apt.config_id,
                    pc.config_name,
                    apt.group_id,
                    ag.group_name,
                    apt.account_id,
                    a.account_name,
                    apt.pipeline_id,
                    pr.pipeline_name,
                    apt.pipeline_status,
                    apt.pipeline_result,
                    apt.publish_status,
                    apt.publish_result,
                    apt.priority,
                    apt.retry_count,
                    apt.error_message,
                    apt.created_at,
                    apt.scheduled_at,
                    apt.started_at,
                    apt.completed_at,
                    apt.metadata
                FROM auto_publish_tasks apt
                LEFT JOIN publish_configs pc ON apt.config_id = pc.config_id
                LEFT JOIN account_groups ag ON apt.group_id = ag.group_id
                LEFT JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
                LEFT JOIN accounts a ON apt.account_id = a.account_id
                WHERE {where_clause}
                ORDER BY apt.created_at DESC
                LIMIT :limit OFFSET :offset
            """), params).fetchall()
            
            tasks = []
            for r in results:
                tasks.append({
                    "task_id": r[0],
                    "config_id": r[1],
                    "config_name": r[2] or "未知配置",
                    "group_id": r[3],
                    "group_name": r[4] or "未知组",
                    "account_id": r[5],
                    "account_name": r[6] or "未知账号",
                    "pipeline_id": r[7],
                    "pipeline_name": r[8] or "未知Pipeline",
                    "pipeline_status": r[9],
                    "pipeline_result": r[10],
                    "publish_status": r[11],
                    "publish_result": r[12],
                    "priority": r[13],
                    "retry_count": r[14],
                    "error_message": r[15],
                    "created_at": r[16] if r[16] else None,
                    "scheduled_at": r[17] if r[17] else None,
                    "started_at": r[18] if r[18] else None,
                    "completed_at": r[19] if r[19] else None,
                    "metadata": r[20]
                })
            
            return {
                "tasks": tasks,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
    except Exception as e:
        import traceback
        logger.error(f"获取任务列表失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{config_id}/group-executions")
async def get_group_executions(
    config_id: str,
    execution_time: str = Query(...),
    current_user: Dict = Depends(require_auth)
):
    """获取账号组的所有账号执行情况"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 1. 获取配置信息
            config_result = session.execute(text("""
                SELECT 
                    pc.config_id,
                    pc.config_name,
                    pc.group_id,
                    ag.group_name
                FROM publish_configs pc
                JOIN account_groups ag ON pc.group_id = ag.group_id
                WHERE pc.config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not config_result:
                raise HTTPException(404, "Config not found")
            
            # 2. 获取同批次的所有任务（同一配置、相近时间）
            exec_time = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
            time_window_start = exec_time - timedelta(minutes=5)
            time_window_end = exec_time + timedelta(minutes=5)
            
            tasks_results = session.execute(text("""
                SELECT 
                    apt.task_id,
                    apt.account_id,
                    a.account_name,
                    'youtube' as platform,
                    apt.pipeline_status,
                    apt.pipeline_result,
                    apt.started_at,
                    apt.completed_at,
                    apt.error_message,
                    apt.metadata
                FROM auto_publish_tasks apt
                JOIN accounts a ON apt.account_id = a.account_id
                WHERE apt.config_id = :config_id
                  AND apt.created_at BETWEEN :time_start AND :time_end
                ORDER BY apt.account_id
            """), {
                "config_id": config_id,
                "time_start": time_window_start,
                "time_end": time_window_end
            }).fetchall()
            
            # 3. 构建账号执行列表
            accounts = []
            total_views = 0
            total_likes = 0
            success_count = 0
            failed_count = 0
            running_count = 0
            pending_count = 0
            total_duration = 0
            duration_count = 0
            
            for task in tasks_results:
                # 计算执行时长
                duration = None
                if task[6] and task[7]:  # started_at and completed_at
                    # 确保是datetime对象
                    started_at = task[6] if isinstance(task[6], datetime) else datetime.fromisoformat(str(task[6]))
                    completed_at = task[7] if isinstance(task[7], datetime) else datetime.fromisoformat(str(task[7]))
                    duration = int((completed_at - started_at).total_seconds())
                    total_duration += duration
                    duration_count += 1
                
                # 获取性能数据
                performance = None
                video_url = None
                if task[9]:  # metadata
                    import json
                    try:
                        metadata = json.loads(task[9]) if isinstance(task[9], str) else task[9]
                        performance = metadata.get('performance')
                        if performance:
                            total_views += performance.get('views', 0)
                            total_likes += performance.get('likes', 0)
                    except:
                        pass
                
                if task[5]:  # pipeline_result
                    import json
                    try:
                        result = json.loads(task[5]) if isinstance(task[5], str) else task[5]
                        video_url = result.get('video_url')
                    except:
                        pass
                
                # 统计状态
                status = task[4]
                if status == 'completed':
                    success_count += 1
                elif status == 'failed':
                    failed_count += 1
                elif status == 'running':
                    running_count += 1
                elif status == 'pending':
                    pending_count += 1
                
                accounts.append({
                    'account_id': task[1],
                    'account_name': task[2],
                    'platform': task[3],
                    'task_id': task[0],
                    'status': status,
                    'video_url': video_url,
                    'duration': duration,
                    'error_message': task[8],
                    'performance': performance or {
                        "views": 0,
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                        "watch_time_minutes": 0,
                        "ctr": 0,
                        "retention_rate": 0,
                        "subscriber_gained": 0
                    }
                })
            
            # 4. 计算汇总数据
            avg_duration = int(total_duration / duration_count) if duration_count > 0 else 0
            
            summary = {
                'total': len(accounts),
                'success': success_count,
                'failed': failed_count,
                'running': running_count,
                'pending': pending_count,
                'avg_duration': avg_duration,
                'total_views': total_views,
                'total_likes': total_likes
            }
            
            return {
                'config_id': config_result[0],
                'config_name': config_result[1],
                'group_id': config_result[2],
                'group_name': config_result[3],
                'execution_time': execution_time,
                'total_accounts': len(accounts),
                'accounts': accounts,
                'summary': summary
            }
            
    except Exception as e:
        logger.error(f"获取账号组执行详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/subtitle")
async def upload_subtitle(
    task_id: str,
    subtitle_file: str,  # In real implementation, this would be UploadFile
    current_user: Dict = Depends(require_auth)
):
    """上传字幕文件"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 1. 验证任务存在
            task_result = session.execute(text(
                "SELECT task_id, metadata FROM auto_publish_tasks WHERE task_id = :task_id"
            ), {"task_id": task_id}).fetchone()
            
            if not task_result:
                raise HTTPException(404, "Task not found")
            
            # 2. 更新任务元数据
            import json
            metadata = json.loads(task_result[1]) if task_result[1] else {}
            metadata['subtitle_file'] = subtitle_file
            
            session.execute(text("""
                UPDATE auto_publish_tasks 
                SET metadata = :metadata
                WHERE task_id = :task_id
            """), {"metadata": json.dumps(metadata), "task_id": task_id})
            
            session.commit()
            
            return {
                "success": True,
                "file_path": subtitle_file
            }
            
    except Exception as e:
        logger.error(f"上传字幕文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}/performance")
async def get_task_performance(
    task_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取任务性能数据"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT 
                    apt.task_id,
                    'youtube' as platform,
                    apt.pipeline_result,
                    apt.metadata,
                    apt.updated_at
                FROM auto_publish_tasks apt
                LEFT JOIN accounts a ON apt.account_id = a.account_id
                WHERE apt.task_id = :task_id
            """), {"task_id": task_id}).fetchone()
            
            if not result:
                raise HTTPException(404, "Task not found")
            
            import json
            video_url = None
            if result[2]:  # pipeline_result
                try:
                    pipeline_result = json.loads(result[2]) if isinstance(result[2], str) else result[2]
                    video_url = pipeline_result.get('video_url')
                except:
                    pass
            
            performance = {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "watch_time_minutes": 0,
                "ctr": 0,
                "retention_rate": 0,
                "subscriber_gained": 0,
                "revenue": 0
            }
            
            if result[3]:  # metadata
                try:
                    metadata = json.loads(result[3]) if isinstance(result[3], str) else result[3]
                    performance = metadata.get('performance', performance)
                except:
                    pass
            
            return {
                "task_id": result[0],
                "platform": result[1] or "youtube",
                "video_url": video_url,
                "performance": performance,
                "updated_at": result[4].isoformat() if result[4] else None
            }
            
    except Exception as e:
        logger.error(f"获取任务性能数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    current_user: Dict = Depends(require_auth)
):
    """重试任务"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 获取原任务信息
            task_result = session.execute(text("""
                SELECT * FROM auto_publish_tasks WHERE task_id = :task_id
            """), {"task_id": task_id}).fetchone()
            
            if not task_result:
                raise HTTPException(404, "Task not found")
            
            # 创建新的重试任务
            new_task_id = f"task_retry_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            session.execute(text("""
                INSERT INTO auto_publish_tasks (
                    task_id, config_id, group_id, account_id, pipeline_id,
                    pipeline_config, pipeline_status, priority, retry_count
                ) VALUES (
                    :task_id, :config_id, :group_id, :account_id, :pipeline_id,
                    :pipeline_config, 'pending', :priority, :retry_count
                )
            """), {
                "task_id": new_task_id,
                "config_id": task_result[1],
                "group_id": task_result[2],
                "account_id": task_result[3],
                "pipeline_id": task_result[4],
                "pipeline_config": task_result[5],
                "priority": task_result[10],
                "retry_count": task_result[11] + 1
            })
            
            session.commit()
            
            return {
                "success": True,
                "new_task_id": new_task_id
            }
            
    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Tab 4: 账号组管理 API ============

@router.put("/account-groups/{group_id}")
async def update_account_group(
    group_id: str,
    request: Dict,
    current_user: Dict = Depends(require_auth)
):
    """更新账号组"""
    try:
        logger.info(f"[UPDATE_GROUP] 开始更新账号组 - group_id: {group_id}")
        logger.debug(f"[UPDATE_GROUP] 请求数据: {json.dumps(request, ensure_ascii=False)}")
        
        db = get_db_manager()
        
        # 从请求中提取参数
        group_name = request.get("group_name")
        group_type = request.get("group_type")
        description = request.get("description")
        is_active = request.get("is_active")
        account_ids = request.get("account_ids", [])
        
        logger.info(f"[UPDATE_GROUP] 参数 - group_name: {group_name}, group_type: {group_type}, account_ids数量: {len(account_ids)}")
        
        with db.get_session() as session:
            # 1. 验证账号组存在
            from models_auto_publish import AccountGroupModel, AccountGroupMemberModel
            group = session.query(AccountGroupModel).filter_by(
                group_id=group_id
            ).first()
            
            if not group:
                raise HTTPException(404, "Account group not found")
            
            # 2. 如果更改名称，验证唯一性
            if group_name and group_name != group.group_name:
                existing = session.query(AccountGroupModel).filter(
                    AccountGroupModel.group_name == group_name,
                    AccountGroupModel.group_id != group_id
                ).first()
                
                if existing:
                    raise HTTPException(400, "Group name already exists")
            
            # 3. 更新账号组基本信息
            if group_name:
                group.group_name = group_name
            if group_type:
                group.group_type = group_type
            if description is not None:
                group.description = description
            if is_active is not None:
                group.is_active = is_active
            
            # 4. 更新账号组成员
            if account_ids is not None:
                logger.info(f"[UPDATE_GROUP] 更新成员列表，新成员数量: {len(account_ids)}")
                
                # 删除现有成员
                deleted_count = session.query(AccountGroupMemberModel).filter_by(
                    group_id=group_id
                ).delete()
                logger.debug(f"[UPDATE_GROUP] 删除了 {deleted_count} 个现有成员")
                
                # 添加新成员
                added_count = 0
                for account_id in account_ids:
                    logger.debug(f"[UPDATE_GROUP] 正在添加成员: {account_id}")
                    # 验证账号存在
                    from database import Account
                    account = session.query(Account).filter_by(
                        account_id=account_id
                    ).first()
                    
                    if account:
                        member = AccountGroupMemberModel(
                            group_id=group_id,
                            account_id=account_id,
                            role="member",
                            is_active=True
                        )
                        session.add(member)
                        added_count += 1
                        logger.debug(f"[UPDATE_GROUP] 成功添加成员: {account_id} - {account.account_name}")
                    else:
                        logger.warning(f"[UPDATE_GROUP] 账号不存在: {account_id}")
                
                logger.info(f"[UPDATE_GROUP] 成功添加 {added_count} 个新成员")
            else:
                logger.info(f"[UPDATE_GROUP] 未提供account_ids，不更新成员列表")
            
            session.commit()
            logger.info(f"[UPDATE_GROUP] 账号组 {group_id} 更新成功")
            
            # 验证更新后的成员
            updated_members = session.query(AccountGroupMemberModel).filter_by(
                group_id=group_id,
                is_active=True
            ).count()
            logger.info(f"[UPDATE_GROUP] 更新后账号组有 {updated_members} 个成员")
            
            return {"success": True}
            
    except Exception as e:
        logger.error(f"更新账号组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/account-groups/{group_id}")
async def delete_account_group(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """删除账号组"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 检查是否有活跃配置或运行中的任务
            check_result = session.execute(text("""
                SELECT 
                    COUNT(DISTINCT pc.config_id) as active_configs,
                    COUNT(DISTINCT apt.task_id) as running_tasks
                FROM account_groups ag
                LEFT JOIN publish_configs pc ON ag.group_id = pc.group_id AND pc.is_active = 1
                LEFT JOIN auto_publish_tasks apt ON ag.group_id = apt.group_id 
                    AND apt.pipeline_status IN ('pending', 'running')
                WHERE ag.group_id = :group_id
            """), {"group_id": group_id}).fetchone()
            
            if check_result[0] > 0:
                raise HTTPException(400, f"Cannot delete group with {check_result[0]} active configs")
            if check_result[1] > 0:
                raise HTTPException(400, f"Cannot delete group with {check_result[1]} running tasks")
            
            # 删除成员关系
            session.execute(text(
                "DELETE FROM account_group_members WHERE group_id = :group_id"
            ), {"group_id": group_id})
            
            # 删除账号组
            session.execute(text(
                "DELETE FROM account_groups WHERE group_id = :group_id"
            ), {"group_id": group_id})
            
            session.commit()
            
            return {"success": True, "message": "Account group deleted successfully"}
            
    except Exception as e:
        logger.error(f"删除账号组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/account-groups/{group_id}/members")
async def add_group_members(
    group_id: str,
    account_ids: List[str],
    role: str = "member",
    current_user: Dict = Depends(require_auth)
):
    """添加账号组成员"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            added = 0
            for account_id in account_ids:
                # 检查是否已存在
                existing = session.execute(text("""
                    SELECT * FROM account_group_members 
                    WHERE group_id = :group_id AND account_id = :account_id
                """), {"group_id": group_id, "account_id": account_id}).fetchone()
                
                if not existing:
                    session.execute(text("""
                        INSERT INTO account_group_members (group_id, account_id, role, is_active)
                        VALUES (:group_id, :account_id, :role, 1)
                    """), {"group_id": group_id, "account_id": account_id, "role": role})
                    added += 1
            
            session.commit()
            
            return {"success": True, "added": added}
            
    except Exception as e:
        logger.error(f"添加成员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/account-groups/{group_id}/members/{account_id}")
async def remove_group_member(
    group_id: str,
    account_id: str,
    current_user: Dict = Depends(require_auth)
):
    """移除账号组成员"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            session.execute(text("""
                DELETE FROM account_group_members 
                WHERE group_id = :group_id AND account_id = :account_id
            """), {"group_id": group_id, "account_id": account_id})
            
            session.commit()
            
            return {"success": True}
            
    except Exception as e:
        logger.error(f"移除成员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups/{group_id}/stats")
async def get_group_stats(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取账号组统计信息"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 1. 获取任务统计
            task_stats = session.execute(text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks,
                    SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
                FROM auto_publish_tasks
                WHERE group_id = :group_id
            """), {"group_id": group_id}).fetchone()
            
            # 2. 获取配置数量
            config_count = session.execute(text("""
                SELECT COUNT(*) as count
                FROM publish_configs
                WHERE group_id = :group_id AND is_active = 1
            """), {"group_id": group_id}).fetchone()[0]
            
            # 3. 获取成员统计
            member_stats_results = session.execute(text("""
                SELECT 
                    a.account_id,
                    a.account_name,
                    COUNT(apt.task_id) as total_tasks,
                    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks
                FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                LEFT JOIN auto_publish_tasks apt ON a.account_id = apt.account_id
                WHERE agm.group_id = :group_id
                GROUP BY a.account_id, a.account_name
            """), {"group_id": group_id}).fetchall()
            
            member_stats = []
            total_views = 0
            for ms in member_stats_results:
                member_stats.append({
                    "account_id": ms[0],
                    "account_name": ms[1],
                    "total_tasks": ms[2],
                    "success_tasks": ms[3],
                    "total_views": 0  # Would need to aggregate from metadata
                })
            
            # 4. 计算成功率
            success_rate = 0
            if task_stats[0] > 0:
                success_rate = round(task_stats[1] / task_stats[0] * 100, 1)
            
            return {
                "total_tasks": task_stats[0],
                "success_tasks": task_stats[1],
                "failed_tasks": task_stats[2],
                "success_rate": success_rate,
                "active_configs": config_count,
                "total_views": total_views,
                "member_stats": member_stats
            }
            
    except Exception as e:
        logger.error(f"获取账号组统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups/{group_id}/configs")
async def get_group_configs(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取账号组关联的配置"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            results = session.execute(text("""
                SELECT 
                    pc.config_id,
                    pc.config_name,
                    pc.pipeline_id,
                    pr.pipeline_name,
                    pc.is_active,
                    COUNT(apt.task_id) as task_count
                FROM publish_configs pc
                LEFT JOIN pipeline_registry pr ON pc.pipeline_id = pr.pipeline_id
                LEFT JOIN auto_publish_tasks apt ON pc.config_id = apt.config_id
                WHERE pc.group_id = :group_id
                GROUP BY pc.config_id, pc.config_name, pc.pipeline_id, pr.pipeline_name, pc.is_active
            """), {"group_id": group_id}).fetchall()
            
            configs = []
            for r in results:
                configs.append({
                    "config_id": r[0],
                    "config_name": r[1],
                    "pipeline_id": r[2],
                    "pipeline_name": r[3] or "未知Pipeline",
                    "is_active": bool(r[4]),
                    "task_count": r[5]
                })
            
            return {
                "configs": configs,
                "total": len(configs)
            }
            
    except Exception as e:
        logger.error(f"获取账号组配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 调度状态管理 ============

@router.get("/schedule/status")
async def get_schedule_status(
    current_user: Dict = Depends(require_auth)
):
    """获取所有调度配置的状态"""
    try:
        schedule_executor = get_schedule_executor()
        status_list = schedule_executor.get_schedule_status()
        
        return {
            "total": len(status_list),
            "schedules": status_list
        }
    except Exception as e:
        logger.error(f"获取调度状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/test/{config_id}")
async def test_schedule_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """测试调度配置（显示下次运行时间）"""
    try:
        db = get_db_manager()
        
        # 获取配置
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT trigger_config
                FROM publish_configs
                WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            trigger_config = json.loads(result[0])
            
        # 创建临时调度配置计算下次运行时间
        schedule_executor = get_schedule_executor()
        from schedule_executor import ScheduleConfig, ScheduleType
        
        config = ScheduleConfig(
            config_id=config_id,
            schedule_type=ScheduleType(trigger_config.get('schedule_type', 'daily')),
            schedule_config=trigger_config
        )
        
        next_run = schedule_executor._calculate_next_run(config)
        
        return {
            "config_id": config_id,
            "schedule_type": trigger_config.get('schedule_type'),
            "trigger_config": trigger_config,
            "next_run_time": next_run.isoformat() if next_run else None,
            "message": f"下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}" if next_run else "无法计算下次运行时间"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试调度配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/schedule/pause/{config_id}")
async def pause_schedule(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """暂停调度配置"""
    try:
        schedule_executor = get_schedule_executor()
        success = schedule_executor.pause_config(config_id)
        
        if success:
            # 更新数据库状态
            db = get_db_manager()
            with db.get_session() as session:
                session.execute(text("""
                    UPDATE publish_configs
                    SET is_active = false, updated_at = :updated_at
                    WHERE config_id = :config_id
                """), {
                    "config_id": config_id,
                    "updated_at": datetime.now()
                })
                session.commit()
            
            return {"message": f"已暂停调度配置: {config_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"调度配置不存在: {config_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停调度配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/schedule/resume/{config_id}")
async def resume_schedule(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """恢复调度配置"""
    try:
        schedule_executor = get_schedule_executor()
        
        # 从数据库获取配置
        db = get_db_manager()
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT trigger_config
                FROM publish_configs
                WHERE config_id = :config_id
            """), {"config_id": config_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
            
            trigger_config = json.loads(result[0])
            
            # 恢复调度
            schedule_executor.update_config(config_id, trigger_config)
            schedule_executor.resume_config(config_id)
            
            # 更新数据库状态
            session.execute(text("""
                UPDATE publish_configs
                SET is_active = true, updated_at = :updated_at
                WHERE config_id = :config_id
            """), {
                "config_id": config_id,
                "updated_at": datetime.now()
            })
            session.commit()
        
        return {"message": f"已恢复调度配置: {config_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复调度配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule/{config_id}")
async def delete_schedule(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """删除调度配置"""
    try:
        # 从调度执行器移除
        schedule_executor = get_schedule_executor()
        schedule_executor.remove_config(config_id)
        
        # 从数据库删除
        db = get_db_manager()
        with db.get_session() as session:
            session.execute(text("""
                DELETE FROM publish_configs
                WHERE config_id = :config_id
            """), {"config_id": config_id})
            session.commit()
        
        logger.info(f"删除调度配置: {config_id}")
        return {"message": f"已删除调度配置: {config_id}"}
        
    except Exception as e:
        logger.error(f"删除调度配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))