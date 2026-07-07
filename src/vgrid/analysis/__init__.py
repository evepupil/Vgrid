"""分析层：从历史行情算派生指标（网格适配评分等），纯函数，供 web / CLI 消费。"""

from vgrid.analysis.grid_fitness import GridFitness, grid_fitness

__all__ = ["GridFitness", "grid_fitness"]
