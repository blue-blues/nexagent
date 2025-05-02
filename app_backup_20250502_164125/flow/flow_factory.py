from typing import Dict, List, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.parallel import ParallelFlow, ParallelWorkflowFlow
from app.flow.planning import PlanningFlow
from app.flow.integrated_flow import IntegratedFlow
# Import self-improving flows if available
try:
    from app.flow.self_improving import SelfImprovingParallelFlow, SelfImprovingParallelWorkflowFlow
except SyntaxError:
    # Create stub classes if there's a syntax error
    class SelfImprovingParallelFlow(ParallelFlow):
        pass

    class SelfImprovingParallelWorkflowFlow(ParallelWorkflowFlow):
        pass
from app.flow.modular_coordination import ModularCoordinationFlow


class FlowFactory:
    """Factory for creating different types of flows with support for multiple agents"""

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        flows = {
            FlowType.PLANNING: PlanningFlow,
            FlowType.PARALLEL: ParallelFlow,
            FlowType.PARALLEL_WORKFLOW: ParallelWorkflowFlow,
            FlowType.SELF_IMPROVING_PARALLEL: SelfImprovingParallelFlow,
            FlowType.SELF_IMPROVING_WORKFLOW: SelfImprovingParallelWorkflowFlow,
            FlowType.MODULAR_COORDINATION: ModularCoordinationFlow,
            FlowType.INTEGRATED: IntegratedFlow,
        }

        flow_class = flows.get(flow_type)
        if not flow_class:
            raise ValueError(f"Unknown flow type: {flow_type}")

        return flow_class(agents, **kwargs)
