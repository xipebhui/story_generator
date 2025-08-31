#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略引擎模块
实现A/B测试、策略分配和效果分析
"""

import logging
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import numpy as np
from scipy import stats

from database import get_db_manager

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型"""
    AB_TEST = "ab_test"         # A/B测试
    ROUND_ROBIN = "round_robin" # 轮流分配
    WEIGHTED = "weighted"        # 加权分配
    RANDOM = "random"           # 随机分配
    MANUAL = "manual"           # 手动指定


class VariantType(Enum):
    """变体类型"""
    CONTROL = "control"          # 对照组
    VARIANT_A = "variant_a"      # 实验组A
    VARIANT_B = "variant_b"      # 实验组B
    VARIANT_C = "variant_c"      # 实验组C


@dataclass
class Strategy:
    """策略定义"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class StrategyAssignment:
    """策略分配"""
    strategy_id: str
    group_id: str
    variant_name: str
    variant_config: Optional[Dict[str, Any]] = None
    weight: float = 1.0
    is_control: bool = False


@dataclass
class StrategyMetric:
    """策略指标"""
    strategy_id: str
    variant_name: str
    task_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_minutes: float = 0.0
    completion_rate: float = 0.0
    ctr: float = 0.0  # 点击率
    engagement_rate: float = 0.0  # 互动率
    measured_at: Optional[datetime] = None
    hours_since_publish: int = 0


class StrategyEngine:
    """策略引擎"""
    
    def __init__(self):
        self.db = get_db_manager()
        self._strategies_cache = {}
        self._assignments_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """加载策略缓存"""
        try:
            # 这里简化处理，实际应该从数据库加载
            logger.info("加载策略缓存")
        except Exception as e:
            logger.error(f"加载策略缓存失败: {e}")
    
    def create_strategy(
        self,
        strategy_name: str,
        strategy_type: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[Strategy]:
        """
        创建策略
        
        Args:
            strategy_name: 策略名称
            strategy_type: 策略类型
            parameters: 策略参数
            description: 描述
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            策略对象
        """
        try:
            strategy_id = f"strategy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 验证参数
            if not self._validate_parameters(strategy_type, parameters):
                logger.error(f"策略参数验证失败: {strategy_type}")
                return None
            
            strategy = Strategy(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                parameters=parameters,
                description=description,
                is_active=True,
                start_date=start_date,
                end_date=end_date,
                created_at=datetime.now()
            )
            
            # 保存到数据库
            self._save_strategy(strategy)
            
            # 更新缓存
            self._strategies_cache[strategy_id] = strategy
            
            logger.info(f"创建策略: {strategy_id} - {strategy_name}")
            return strategy
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return None
    
    def assign_group_to_strategy(
        self,
        strategy_id: str,
        group_id: str,
        variant_name: str,
        variant_config: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        is_control: bool = False
    ) -> bool:
        """
        分配账号组到策略
        
        Args:
            strategy_id: 策略ID
            group_id: 账号组ID
            variant_name: 变体名称
            variant_config: 变体配置
            weight: 权重
            is_control: 是否为对照组
        
        Returns:
            是否分配成功
        """
        try:
            assignment = StrategyAssignment(
                strategy_id=strategy_id,
                group_id=group_id,
                variant_name=variant_name,
                variant_config=variant_config,
                weight=weight,
                is_control=is_control
            )
            
            # 保存到数据库
            self._save_assignment(assignment)
            
            # 更新缓存
            if strategy_id not in self._assignments_cache:
                self._assignments_cache[strategy_id] = []
            self._assignments_cache[strategy_id].append(assignment)
            
            logger.info(f"分配账号组 {group_id} 到策略 {strategy_id} 的 {variant_name} 变体")
            return True
            
        except Exception as e:
            logger.error(f"分配账号组失败: {e}")
            return False
    
    def get_variant_for_task(
        self,
        strategy_id: str,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        获取任务的策略变体
        
        Args:
            strategy_id: 策略ID
            task_id: 任务ID
            group_id: 账号组ID
        
        Returns:
            (变体名称, 变体配置)
        """
        try:
            strategy = self._strategies_cache.get(strategy_id)
            if not strategy:
                logger.warning(f"策略不存在: {strategy_id}")
                return ("default", {})
            
            # 根据策略类型分配变体
            if strategy.strategy_type == StrategyType.AB_TEST.value:
                return self._allocate_ab_test(strategy, task_id, group_id)
            elif strategy.strategy_type == StrategyType.ROUND_ROBIN.value:
                return self._allocate_round_robin(strategy, task_id, group_id)
            elif strategy.strategy_type == StrategyType.WEIGHTED.value:
                return self._allocate_weighted(strategy, task_id, group_id)
            elif strategy.strategy_type == StrategyType.RANDOM.value:
                return self._allocate_random(strategy, task_id, group_id)
            else:
                return self._allocate_manual(strategy, task_id, group_id)
                
        except Exception as e:
            logger.error(f"获取策略变体失败: {e}")
            return ("default", {})
    
    def _allocate_ab_test(
        self,
        strategy: Strategy,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """A/B测试分配"""
        # 使用task_id的哈希值来稳定分配
        hash_value = int(hashlib.md5(task_id.encode()).hexdigest(), 16)
        
        # 获取该策略的所有分配
        assignments = self._assignments_cache.get(strategy.strategy_id, [])
        group_assignments = [a for a in assignments if a.group_id == group_id]
        
        if not group_assignments:
            return ("default", {})
        
        # 根据权重分配
        total_weight = sum(a.weight for a in group_assignments)
        threshold = hash_value % int(total_weight * 100)
        
        current_weight = 0
        for assignment in group_assignments:
            current_weight += assignment.weight * 100
            if threshold < current_weight:
                return (assignment.variant_name, assignment.variant_config or {})
        
        # 默认返回第一个
        return (group_assignments[0].variant_name, group_assignments[0].variant_config or {})
    
    def _allocate_round_robin(
        self,
        strategy: Strategy,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """轮流分配"""
        assignments = self._assignments_cache.get(strategy.strategy_id, [])
        group_assignments = [a for a in assignments if a.group_id == group_id]
        
        if not group_assignments:
            return ("default", {})
        
        # 使用任务序号来轮流分配
        task_index = self._get_task_index(strategy.strategy_id, group_id)
        assignment = group_assignments[task_index % len(group_assignments)]
        
        return (assignment.variant_name, assignment.variant_config or {})
    
    def _allocate_weighted(
        self,
        strategy: Strategy,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """加权分配"""
        assignments = self._assignments_cache.get(strategy.strategy_id, [])
        group_assignments = [a for a in assignments if a.group_id == group_id]
        
        if not group_assignments:
            return ("default", {})
        
        # 根据权重随机选择
        weights = [a.weight for a in group_assignments]
        chosen = random.choices(group_assignments, weights=weights)[0]
        
        return (chosen.variant_name, chosen.variant_config or {})
    
    def _allocate_random(
        self,
        strategy: Strategy,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """随机分配"""
        assignments = self._assignments_cache.get(strategy.strategy_id, [])
        group_assignments = [a for a in assignments if a.group_id == group_id]
        
        if not group_assignments:
            return ("default", {})
        
        # 随机选择
        chosen = random.choice(group_assignments)
        return (chosen.variant_name, chosen.variant_config or {})
    
    def _allocate_manual(
        self,
        strategy: Strategy,
        task_id: str,
        group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """手动分配"""
        assignments = self._assignments_cache.get(strategy.strategy_id, [])
        group_assignments = [a for a in assignments if a.group_id == group_id]
        
        if group_assignments:
            # 返回第一个分配
            return (group_assignments[0].variant_name, group_assignments[0].variant_config or {})
        
        return ("default", {})
    
    def record_metric(
        self,
        strategy_id: str,
        variant_name: str,
        task_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        记录策略指标
        
        Args:
            strategy_id: 策略ID
            variant_name: 变体名称
            task_id: 任务ID
            metrics: 指标数据
        
        Returns:
            是否记录成功
        """
        try:
            metric = StrategyMetric(
                strategy_id=strategy_id,
                variant_name=variant_name,
                task_id=task_id,
                views=metrics.get('views', 0),
                likes=metrics.get('likes', 0),
                comments=metrics.get('comments', 0),
                shares=metrics.get('shares', 0),
                watch_time_minutes=metrics.get('watch_time_minutes', 0.0),
                completion_rate=metrics.get('completion_rate', 0.0),
                ctr=metrics.get('ctr', 0.0),
                engagement_rate=metrics.get('engagement_rate', 0.0),
                measured_at=datetime.now(),
                hours_since_publish=metrics.get('hours_since_publish', 0)
            )
            
            # 保存到数据库
            self._save_metric(metric)
            
            logger.info(f"记录策略指标: {strategy_id} - {variant_name} - {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"记录策略指标失败: {e}")
            return False
    
    def analyze_strategy(
        self,
        strategy_id: str,
        metric_name: str = "views",
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        分析策略效果
        
        Args:
            strategy_id: 策略ID
            metric_name: 分析的指标名称
            confidence_level: 置信水平
        
        Returns:
            分析结果
        """
        try:
            # 获取策略的所有指标数据
            metrics = self._get_strategy_metrics(strategy_id)
            
            if not metrics:
                return {"error": "没有足够的数据进行分析"}
            
            # 按变体分组
            variant_data = {}
            for metric in metrics:
                if metric.variant_name not in variant_data:
                    variant_data[metric.variant_name] = []
                variant_data[metric.variant_name].append(getattr(metric, metric_name, 0))
            
            # 统计分析
            analysis = {
                "strategy_id": strategy_id,
                "metric_name": metric_name,
                "variants": {},
                "statistical_test": None,
                "winner": None,
                "confidence": confidence_level
            }
            
            # 计算每个变体的统计数据
            for variant_name, values in variant_data.items():
                if values:
                    analysis["variants"][variant_name] = {
                        "count": len(values),
                        "mean": np.mean(values),
                        "median": np.median(values),
                        "std": np.std(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "confidence_interval": self._calculate_confidence_interval(
                            values, confidence_level
                        )
                    }
            
            # 如果有对照组和实验组，进行统计检验
            if len(variant_data) == 2 and "control" in variant_data:
                control_data = variant_data["control"]
                experiment_name = [k for k in variant_data.keys() if k != "control"][0]
                experiment_data = variant_data[experiment_name]
                
                if len(control_data) > 1 and len(experiment_data) > 1:
                    # T检验
                    t_stat, p_value = stats.ttest_ind(control_data, experiment_data)
                    
                    analysis["statistical_test"] = {
                        "test": "t-test",
                        "t_statistic": t_stat,
                        "p_value": p_value,
                        "significant": p_value < (1 - confidence_level),
                        "effect_size": self._calculate_effect_size(
                            control_data, experiment_data
                        )
                    }
                    
                    # 判断胜者
                    if p_value < (1 - confidence_level):
                        control_mean = np.mean(control_data)
                        experiment_mean = np.mean(experiment_data)
                        if experiment_mean > control_mean:
                            analysis["winner"] = experiment_name
                            analysis["improvement"] = (
                                (experiment_mean - control_mean) / control_mean * 100
                            )
                        else:
                            analysis["winner"] = "control"
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析策略失败: {e}")
            return {"error": str(e)}
    
    def _calculate_confidence_interval(
        self,
        data: List[float],
        confidence_level: float
    ) -> Tuple[float, float]:
        """计算置信区间"""
        if len(data) < 2:
            return (0, 0)
        
        mean = np.mean(data)
        std_err = stats.sem(data)
        interval = std_err * stats.t.ppf((1 + confidence_level) / 2, len(data) - 1)
        
        return (mean - interval, mean + interval)
    
    def _calculate_effect_size(
        self,
        control_data: List[float],
        experiment_data: List[float]
    ) -> float:
        """计算效应大小(Cohen's d)"""
        control_mean = np.mean(control_data)
        experiment_mean = np.mean(experiment_data)
        
        # 合并标准差
        pooled_std = np.sqrt(
            ((len(control_data) - 1) * np.var(control_data) +
             (len(experiment_data) - 1) * np.var(experiment_data)) /
            (len(control_data) + len(experiment_data) - 2)
        )
        
        if pooled_std == 0:
            return 0
        
        return (experiment_mean - control_mean) / pooled_std
    
    def get_strategy_report(self, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略报告
        
        Args:
            strategy_id: 策略ID
        
        Returns:
            策略报告
        """
        try:
            strategy = self._strategies_cache.get(strategy_id)
            if not strategy:
                return {"error": "策略不存在"}
            
            # 分析主要指标
            views_analysis = self.analyze_strategy(strategy_id, "views")
            engagement_analysis = self.analyze_strategy(strategy_id, "engagement_rate")
            
            report = {
                "strategy": asdict(strategy),
                "analyses": {
                    "views": views_analysis,
                    "engagement": engagement_analysis
                },
                "summary": self._generate_summary(views_analysis, engagement_analysis),
                "recommendations": self._generate_recommendations(
                    views_analysis, engagement_analysis
                ),
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成策略报告失败: {e}")
            return {"error": str(e)}
    
    def _generate_summary(
        self,
        views_analysis: Dict[str, Any],
        engagement_analysis: Dict[str, Any]
    ) -> str:
        """生成摘要"""
        summary = []
        
        # 观看量分析
        if views_analysis.get("winner"):
            winner = views_analysis["winner"]
            improvement = views_analysis.get("improvement", 0)
            summary.append(
                f"观看量方面，{winner}变体表现更好，提升了{improvement:.1f}%"
            )
        else:
            summary.append("观看量方面，各变体表现相近，无显著差异")
        
        # 互动率分析
        if engagement_analysis.get("winner"):
            winner = engagement_analysis["winner"]
            summary.append(f"互动率方面，{winner}变体表现更优")
        else:
            summary.append("互动率方面，各变体表现相近")
        
        return "。".join(summary)
    
    def _generate_recommendations(
        self,
        views_analysis: Dict[str, Any],
        engagement_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 根据分析结果生成建议
        if views_analysis.get("winner") == engagement_analysis.get("winner"):
            winner = views_analysis.get("winner")
            if winner and winner != "control":
                recommendations.append(f"建议采用{winner}变体的策略")
                recommendations.append("可以逐步扩大该变体的流量比例")
        else:
            recommendations.append("不同指标表现不一致，建议继续测试")
            recommendations.append("可以考虑增加样本量或延长测试时间")
        
        # 检查样本量
        for variant_name, variant_stats in views_analysis.get("variants", {}).items():
            if variant_stats.get("count", 0) < 30:
                recommendations.append(f"{variant_name}变体样本量较少，建议继续收集数据")
                break
        
        return recommendations
    
    def _validate_parameters(
        self,
        strategy_type: str,
        parameters: Dict[str, Any]
    ) -> bool:
        """验证策略参数"""
        if strategy_type == StrategyType.AB_TEST.value:
            return "variants" in parameters
        elif strategy_type == StrategyType.WEIGHTED.value:
            return "weights" in parameters
        return True
    
    def _get_task_index(self, strategy_id: str, group_id: str) -> int:
        """获取任务序号"""
        # 这里简化处理，实际应该从数据库查询
        return random.randint(0, 100)
    
    def _get_strategy_metrics(self, strategy_id: str) -> List[StrategyMetric]:
        """获取策略指标"""
        # 这里简化处理，实际应该从数据库查询
        return []
    
    def _save_strategy(self, strategy: Strategy):
        """保存策略"""
        # 这里简化处理，实际应该保存到数据库
        logger.debug(f"保存策略: {strategy.strategy_id}")
    
    def _save_assignment(self, assignment: StrategyAssignment):
        """保存分配"""
        # 这里简化处理，实际应该保存到数据库
        logger.debug(f"保存分配: {assignment.strategy_id} - {assignment.group_id}")
    
    def _save_metric(self, metric: StrategyMetric):
        """保存指标"""
        # 这里简化处理，实际应该保存到数据库
        logger.debug(f"保存指标: {metric.strategy_id} - {metric.task_id}")


# 全局实例
_strategy_engine = None


def get_strategy_engine() -> StrategyEngine:
    """获取策略引擎实例"""
    global _strategy_engine
    if _strategy_engine is None:
        _strategy_engine = StrategyEngine()
    return _strategy_engine