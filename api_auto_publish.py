#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号驱动自动发布API扩展
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time, timedelta
import asyncio
import logging
import uuid
from sqlalchemy import text

from auth_middleware import get_current_user, require_auth
from pipeline_registry import get_pipeline_registry
from ring_scheduler import get_ring_scheduler
from account_driven_executor import get_account_driven_executor
from platform_monitor import get_platform_monitor
from strategy_engine import get_strategy_engine
from database import get_db_manager
from models_auto_publish import AccountGroupModel, AccountGroupMemberModel, PublishStrategyModel

logger = logging.getLogger(__name__)

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
    trigger_type: str = Field(..., description="触发类型: scheduled, monitor")
    trigger_config: Dict[str, Any] = Field(..., description="触发器配置")
    strategy_id: Optional[str] = Field(None, description="策略ID")
    priority: int = Field(50, ge=0, le=100, description="优先级")
    
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
            for account_id in request.account_ids:
                member = AccountGroupMemberModel(
                    group_id=group_id,
                    account_id=account_id,
                    role='member',
                    is_active=True
                )
                session.add(member)
            
            session.commit()
            
            logger.info(f"创建账号组: {group_id}, 成员数: {len(request.account_ids)}")
            
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
            
            # 获取每个组的成员数
            result = []
            for group in groups:
                member_count = session.query(AccountGroupMemberModel).filter_by(
                    group_id=group.group_id,
                    is_active=True
                ).count()
                
                result.append(AccountGroupResponse(
                    group_id=group.group_id,
                    group_name=group.group_name,
                    group_type=group.group_type,
                    description=group.description,
                    is_active=group.is_active,
                    member_count=member_count,
                    created_at=group.created_at
                ))
            
            return {"groups": result}
        
    except Exception as e:
        logger.error(f"列出账号组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-groups/{group_id}/members")
async def get_account_group_members(
    group_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取账号组成员"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 检查组是否存在
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
            from database import Accounts
            result = []
            for member in members:
                account = session.query(Accounts).filter_by(
                    account_id=member.account_id
                ).first()
                
                if account:
                    result.append({
                        "account_id": account.account_id,
                        "account_name": account.account_name,
                        "profile_id": account.profile_id,
                        "role": member.role,
                        "join_date": member.join_date.isoformat() if member.join_date else None
                    })
            
            return {
                "group_id": group_id,
                "group_name": group.group_name,
                "members": result
            }
            
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
        # 验证Pipeline是否存在
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline(request.pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline不存在: {request.pipeline_id}")
        
        # 创建配置
        config_id = f"config_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        config = {
            "config_id": config_id,
            "config_name": request.config_name,
            "group_id": request.group_id,
            "pipeline_id": request.pipeline_id,
            "trigger_type": request.trigger_type,
            "trigger_config": request.trigger_config,
            "strategy_id": request.strategy_id,
            "priority": request.priority,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 存储配置
        publish_configs_storage[config_id] = config
        
        logger.info(f"创建发布配置: {config_id}")
        
        return PublishConfigResponse(**config)
        
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
    try:
        # 从存储中获取配置
        configs = list(publish_configs_storage.values())
        
        # 如果没有配置，添加默认测试配置
        if not configs:
            test_config = {
                "config_id": "test_config_1",
                "config_name": "每日故事视频发布",
                "group_id": "default_group",
                "pipeline_id": "story_v3",
                "trigger_type": "scheduled",
                "trigger_config": {
                    "schedule_type": "daily",
                    "time": "10:00",
                    "timezone": "Asia/Shanghai"
                },
                "strategy_id": None,
                "priority": 50,
                "is_active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            publish_configs_storage["test_config_1"] = test_config
            configs = [test_config]
        
        # 应用筛选条件
        if group_id:
            configs = [c for c in configs if c.get("group_id") == group_id]
        if pipeline_id:
            configs = [c for c in configs if c.get("pipeline_id") == pipeline_id]
        if is_active is not None:
            configs = [c for c in configs if c.get("is_active") == is_active]
        if search:
            configs = [c for c in configs if search.lower() in c.get("config_name", "").lower()]
        
        # 按创建时间倒序排序
        configs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        return {"configs": [PublishConfigResponse(**c) for c in configs]}
        
    except Exception as e:
        logger.error(f"列出发布配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/publish-configs/{config_id}")
async def get_publish_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取单个发布配置详情"""
    try:
        config = publish_configs_storage.get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
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
    try:
        config = publish_configs_storage.get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        # 验证Pipeline是否存在
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline(request.pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline不存在: {request.pipeline_id}")
        
        # 更新配置
        config.update({
            "config_name": request.config_name,
            "group_id": request.group_id,
            "pipeline_id": request.pipeline_id,
            "trigger_type": request.trigger_type,
            "trigger_config": request.trigger_config,
            "strategy_id": request.strategy_id,
            "priority": request.priority,
            "updated_at": datetime.now()
        })
        
        logger.info(f"更新发布配置: {config_id}")
        
        return PublishConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新发布配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/publish-configs/{config_id}")
async def delete_publish_config(
    config_id: str,
    current_user: Dict = Depends(require_auth)
):
    """删除发布配置"""
    try:
        if config_id not in publish_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        del publish_configs_storage[config_id]
        
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
        config = publish_configs_storage.get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")
        
        # 切换状态
        config["is_active"] = not config.get("is_active", True)
        config["updated_at"] = datetime.now()
        
        logger.info(f"切换发布配置状态: {config_id} -> {config['is_active']}")
        
        return PublishConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换发布配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/publish-configs/{config_id}/tasks")
async def get_config_tasks(
    config_id: str,
    status: Optional[str] = Query(None, description="任务状态筛选"),
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict = Depends(require_auth)
):
    """获取配置关联的任务列表"""
    try:
        config = publish_configs_storage.get(config_id)
        if not config:
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
                WHERE apt.pipeline_id = :pipeline_id
            """
            
            params = {"pipeline_id": config["pipeline_id"]}
            
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
                    "created_at": r[4].isoformat() if r[4] else None,
                    "started_at": r[5].isoformat() if r[5] else None,
                    "completed_at": r[6].isoformat() if r[6] else None,
                    "duration": int(r[7]) if r[7] else None
                })
            
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
    try:
        config = publish_configs_storage.get(config_id)
        if not config:
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
                WHERE pipeline_id = :pipeline_id
                  AND created_at >= :start_date
            """), {
                "pipeline_id": config["pipeline_id"],
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
    try:
        registry = get_pipeline_registry()
        
        pipelines = registry.list_pipelines(
            pipeline_type=pipeline_type,
            platform=platform,
            status=status
        )
        
        return {
            "total": len(pipelines),
            "pipelines": [
                {
                    "pipeline_id": p.pipeline_id,
                    "pipeline_name": p.pipeline_name,
                    "pipeline_type": p.pipeline_type,
                    "supported_platforms": p.supported_platforms,
                    "version": p.version,
                    "status": p.status
                }
                for p in pipelines
            ]
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
        
        success = registry.register_pipeline(
            pipeline_id=request.pipeline_id,
            pipeline_name=request.pipeline_name,
            pipeline_type=request.pipeline_type,
            pipeline_class=request.pipeline_class,
            config_schema=request.config_schema,
            supported_platforms=request.supported_platforms,
            version=request.version
        )
        
        if success:
            return {
                "success": True,
                "message": f"成功注册Pipeline: {request.pipeline_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="注册Pipeline失败")
            
    except Exception as e:
        logger.error(f"注册Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    current_user: Dict = Depends(require_auth)
):
    """获取Pipeline详情"""
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
            config_count = session.execute(
                "SELECT COUNT(*) FROM publish_configs WHERE pipeline_id = :pipeline_id",
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
                    "created_at": r[4].isoformat() if r[4] else None,
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
                    apt.pipeline_config,
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
                    "pipeline_config": r[9],
                    "pipeline_status": r[10],
                    "pipeline_result": r[11],
                    "publish_status": r[12],
                    "publish_result": r[13],
                    "priority": r[14],
                    "retry_count": r[15],
                    "error_message": r[16],
                    "created_at": r[17].isoformat() if r[17] else None,
                    "scheduled_at": r[18].isoformat() if r[18] else None,
                    "started_at": r[19].isoformat() if r[19] else None,
                    "completed_at": r[20].isoformat() if r[20] else None,
                    "metadata": r[21]
                })
            
            return {
                "tasks": tasks,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
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
                    a.platform,
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
                    duration = int((task[7] - task[6]).total_seconds())
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
                    a.platform,
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
    group_name: Optional[str] = None,
    group_type: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: Dict = Depends(require_auth)
):
    """更新账号组"""
    try:
        db = get_db_manager()
        
        with db.get_session() as session:
            # 1. 验证账号组存在
            group_result = session.execute(text(
                "SELECT * FROM account_groups WHERE group_id = :group_id"
            ), {"group_id": group_id}).fetchone()
            
            if not group_result:
                raise HTTPException(404, "Account group not found")
            
            # 2. 如果更改名称，验证唯一性
            if group_name and group_name != group_result[1]:
                existing = session.execute(text(
                    "SELECT * FROM account_groups WHERE group_name = :group_name AND group_id != :group_id"
                ), {"group_name": group_name, "group_id": group_id}).fetchone()
                
                if existing:
                    raise HTTPException(400, "Group name already exists")
            
            # 3. 更新账号组
            update_fields = []
            params = {"group_id": group_id}
            
            if group_name:
                update_fields.append("group_name = :group_name")
                params["group_name"] = group_name
            if group_type:
                update_fields.append("group_type = :group_type")
                params["group_type"] = group_type
            if description is not None:
                update_fields.append("description = :description")
                params["description"] = description
            if is_active is not None:
                update_fields.append("is_active = :is_active")
                params["is_active"] = is_active
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                query = f"""
                    UPDATE account_groups 
                    SET {', '.join(update_fields)}
                    WHERE group_id = :group_id
                """
                session.execute(text(query), params)
                session.commit()
            
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