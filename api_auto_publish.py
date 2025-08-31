#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号驱动自动发布API扩展
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
import asyncio
import logging

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
        config_id = f"config_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
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
            "created_at": datetime.now()
        }
        
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
    is_active: bool = Query(True, description="是否只返回活跃配置"),
    current_user: Dict = Depends(require_auth)
):
    """列出发布配置"""
    try:
        # 这里简化处理，返回模拟数据
        configs = [
            {
                "config_id": "test_config_1",
                "config_name": "测试配置",
                "group_id": "default_group",
                "pipeline_id": "story_v3",
                "trigger_type": "scheduled",
                "trigger_config": {"interval": "daily"},
                "strategy_id": None,
                "priority": 50,
                "is_active": True,
                "created_at": datetime.now()
            }
        ]
        
        return {"configs": [PublishConfigResponse(**c) for c in configs]}
        
    except Exception as e:
        logger.error(f"列出发布配置失败: {e}")
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
                "message": f"成功注册Pipeline: {pipeline_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="注册Pipeline失败")
            
    except Exception as e:
        logger.error(f"注册Pipeline失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))